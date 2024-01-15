# coding: utf-8
import io
import itertools
from datetime import date, timedelta, datetime
from decimal import Decimal

import pandas as pd
import requests

from apis import myelectricaldata, tempo, datagouvfr
from db import cur, db, activation_date
from edf_plan import EdfPlan


def fetch_enedis(upto=None):
    """
    Fetches the consumption data from Enedis using the MyElectricalData API.

    7 days of consumption are retrieved at a time. The loop starts at the meter's activation date and continues until
    either MyElectricalData returns an error or the current day is reached.
    """
    start_date = None

    try:
        last_info = date(*map(int, cur.execute(
            "SELECT year, month, day FROM consumption ORDER BY year DESC, month DESC, day DESC LIMIT 1").fetchone()))
    except TypeError:
        last_info = activation_date - timedelta(days=1)

    while True:
        # last info is max ymd from db
        new_start_date = last_info + timedelta(days=1)
        if new_start_date == start_date or new_start_date >= (upto or (date.today() - timedelta(days=1))):
            break
        start_date = new_start_date
        end_date = start_date + timedelta(days=7)
        try:
            conso_data = myelectricaldata.fetch_api("consumption_load_curve", (start_date, end_date))[
                "meter_reading"]["interval_reading"]
        except requests.exceptions.HTTPError as e:
            print(e)
            break
        print("Saving", len(conso_data), "Enedis rows")
        for reading in conso_data:
            dt = datetime.fromisoformat(reading["date"]) - timedelta(minutes=30)

            slice_idx = dt.hour * 2 + dt.minute // 30

            if dt.date() > last_info:
                last_info = dt.date()

            cur.execute("INSERT OR REPLACE INTO consumption VALUES (?, ?, ?, ?, ?)",
                        (dt.year, dt.month, dt.day, slice_idx, int(reading["value"])))
        db.commit()


def fetch_tempo():
    """
    Fetches the Tempo data from the api-couleur-tempo.fr API.

    7 days of data are retrieved at a time. The loop starts at the meter's activation date and continues until
    either api-couleur-tempo.fr returns an error or the current day is reached.

    The day kind is {1, 2, 3}. If the API returns 0 for a day, it means the day kind for the day hasn't been retrieved
    yet -- in that case, the day is ignored and not inserted in the database.

    TODO: can the API ever return 0 for a day other than the last one?
    """
    start_date = None

    try:
        last_info = date(*map(int, cur.execute(
            "SELECT year, month, day FROM tempo ORDER BY year DESC, month DESC, day DESC LIMIT 1").fetchone()))
    except TypeError:
        last_info = activation_date - timedelta(days=1)

    while True:
        # last info is max ymd from db
        new_start_date = last_info + timedelta(days=1)
        if new_start_date == start_date or new_start_date >= date.today() - timedelta(days=1):
            break
        start_date = new_start_date
        try:
            tempo_data = tempo.get_days([str(start_date + timedelta(days=i)) for i in range(7)])
        except requests.exceptions.HTTPError as e:
            print(e)
            break

        print("Saving", len(tempo_data), "Tempo rows")
        for reading in tempo_data:
            dt = date.fromisoformat(reading["dateJour"])
            val = reading["codeJour"]

            if val != 0:
                cur.execute("INSERT OR REPLACE INTO tempo VALUES (?, ?, ?, ?)",
                            (dt.year, dt.month, dt.day, val))

                if dt > last_info:
                    last_info = dt
        db.commit()


# polyfill for Python <3.12
if not hasattr(itertools, "batched"):
    def batched(iterable, n):
        it = iter(iterable)
        while True:
            chunk = tuple(itertools.islice(it, n))
            if not chunk:
                return
            yield chunk


    setattr(itertools, "batched", batched)


def fetch_prices():
    """
    Fetches the prices for Base and Bleu from data.gouv.fr and inserts them in the database.

    The datasets are in CSV format and contain both the yearly subscription price and the price per kWh for each
    pricing period.
    """
    for name, rid in (
            ("base", "c13d05e5-9e55-4d03-bf7e-042a2ade7e49"), ("hphc", "f7303b3a-93c7-4242-813d-84919034c416")):
        existing = cur.execute(f"SELECT value FROM config WHERE key = 'tarif_{name}'").fetchone()
        if existing is None:
            update = True
        else:
            update = date.today() - date.fromisoformat(existing[0]) > timedelta(days=1)

        if update:
            csv = datagouvfr.get_resource_content(rid)
            # parse using pandas
            df = pd.read_csv(io.StringIO(csv.decode("utf-8")), sep=";")
            # check if column PART_VARIABLE_TTC exists
            if "PART_VARIABLE_TTC" in df.columns:
                df["PART_VARIABLE_HC_TTC"] = df["PART_VARIABLE_TTC"]
                df["PART_VARIABLE_HP_TTC"] = df["PART_VARIABLE_TTC"]

            def dmy_to_iso(dmy):
                if type(dmy) is not str:
                    return "9999-12-31"
                d, m, y = dmy.split("/")
                return f"{y}-{m}-{d}"

            def dec_to_fixed(dec, digits):
                # go from "0,0578" to 578
                return int(Decimal(dec.replace(",", ".")) * (10 ** digits))

            for index, row in df.iterrows():
                cur.execute("INSERT OR REPLACE INTO edf_plan_slice VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
                            (name, dmy_to_iso(row["DATE_DEBUT"]), row["P_SOUSCRITE"],
                             dec_to_fixed(row["PART_FIXE_TTC"], 2), dec_to_fixed(row["PART_VARIABLE_HP_TTC"], 4),
                             dec_to_fixed(row["PART_VARIABLE_HC_TTC"], 4), dmy_to_iso(row["DATE_FIN"])))

            print("Updated tariff", name)
            cur.execute(f"INSERT OR REPLACE INTO config VALUES ('tarif_{name}', ?)", (date.today().isoformat(),))
            db.commit()

def add_prices_pdf():
    """
    Some prices aren't provided by any API, so we have to get them from the public PDF price sheets. One day, this will
    maybe download the files and try and extract the tables from them, but for now, it's just a hardcoded dict.

    Since the prices are laid out in tables, it's easy to copy and paste the data from a PDF file to here.
    """

    # https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille_prix_Tarif_Bleu.pdf
    # https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/Grille-prix-zen-flex.pdf
    # https://particulier.edf.fr/content/dam/2-Actifs/Documents/Offres/grille-prix-zen-week-end.pdf

    edf_pdf_data = {
        "tempo": {
            "2023-01-01": """
6 12,28 9,70 12,49 11,40 15,08 12,16 67,12
9 15,33 9,70 12,49 11,40 15,08 12,16 67,12
12 18,78 9,70 12,49 11,40 15,08 12,16 67,12
15 21,27 9,70 12,49 11,40 15,08 12,16 67,12
18 23,98 9,70 12,49 11,40 15,08 12,16 67,12
30 36,06 9,70 12,49 11,40 15,08 12,16 67,12
36 41,90 9,70 12,49 11,40 15,08 12,16 67,12
    """,
            "2023-08-01": """
6 12,80 10,56 13,69 12,46 16,54 13,28 73,24
9 16,00 10,56 13,69 12,46 16,54 13,28 73,24
12 19,29 10,56 13,69 12,46 16,54 13,28 73,24
15 22,30 10,56 13,69 12,46 16,54 13,28 73,24
18 25,29 10,56 13,69 12,46 16,54 13,28 73,24
30 38,13 10,56 13,69 12,46 16,54 13,28 73,24
36 44,28 10,56 13,69 12,46 16,54 13,28 73,24
    """
        },
        "zenflex": {
            "2023-08-01": """
6 12,62 12,95 22,28 22,28 67,12
9 15,99 12,95 22,28 22,28 67,12
12 19,27 12,95 22,28 22,28 67,12
15 22,40 12,95 22,28 22,28 67,12
18 25,46 12,95 22,28 22,28 67,12
24 32,01 12,95 22,28 22,28 67,12
30 38,07 12,95 22,28 22,28 67,12
36 43,88 12,95 22,28 22,28 67,12
    """,
            "2023-09-14": """
6 13,03 14,64 24,60 24,60 73,24
9 16,55 14,64 24,60 24,60 73,24
12 19,97 14,64 24,60 24,60 73,24
15 23,24 14,64 24,60 24,60 73,24
18 26,48 14,64 24,60 24,60 73,24
24 33,28 14,64 24,60 24,60 73,24
30 39,46 14,64 24,60 24,60 73,24
36 45,72 14,64 24,60 24,60 73,24
    """
        },
        "zenweekend": {
            "2023-09-14": """
3 9,47 25,25 17,71
6 12,44 25,25 17,71
9 15,63 25,25 17,71
12 19,25 25,25 17,71
15 22,37 25,25 17,71
18 25,46 25,25 17,71
24 32,32 25,25 17,71
30 37,29 25,25 17,71
36 43,99 25,25 17,71
    """
        },
        "zenweekendhc": {
            "2023-09-14": """
6 13,03 26,83 18,81 18,81 18,81
9 16,55 26,83 18,81 18,81 18,81
12 19,97 26,83 18,81 18,81 18,81
15 23,24 26,83 18,81 18,81 18,81
18 26,48 26,83 18,81 18,81 18,81
24 33,28 26,83 18,81 18,81 18,81
30 39,46 26,83 18,81 18,81 18,81
36 45,72 26,83 18,81 18,81 18,81
    """
        }
    }

    for plan, vals in edf_pdf_data.items():
        plan_data = EdfPlan(plan)
        for (dt, val), dt_end in zip(vals.items(), [(date.fromisoformat(k) - timedelta(days=1)).isoformat() for k in vals.keys()][1:] + ["9999-12-31"]):
            val = val.strip().replace(",", "").split("\n")
            for row in val:
                power, sub, *kwh = row.split(" ")
                sub = 12 * int(sub)
                if plan_data.is_hp_sql() is None:
                    for day_kind, hchp in enumerate(kwh, 1):
                        cur.execute("INSERT OR REPLACE INTO edf_plan_slice VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (plan, dt, power, sub, day_kind, hchp, hchp, dt_end))
                else:
                    for day_kind, (hc, hp) in enumerate(itertools.batched(kwh, 2), 1):
                        cur.execute("INSERT OR REPLACE INTO edf_plan_slice VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (plan, dt, power, sub, day_kind, hp, hc, dt_end))

    db.commit()


def fetch_loop():
    fetch_enedis()
    fetch_tempo()
    fetch_prices()
    add_prices_pdf()
