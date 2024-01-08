# coding: utf-8
import json
import sqlite3
from datetime import date

try:
    db = sqlite3.connect("file:app.db?mode=rw", uri=True)
    cur = db.cursor()
    meter_info = json.loads(cur.execute("SELECT value FROM config WHERE key = 'meter_info'").fetchone()[0])
    sub_power = int(meter_info["customer"]["usage_points"][0]["contracts"]["subscribed_power"].split(" ")[0])
    activation_date = date.fromisoformat(
        meter_info["customer"]["usage_points"][0]["contracts"]["last_activation_date"][:10])
except sqlite3.OperationalError:
    db = sqlite3.connect("app.db")
    cur = db.cursor()
    cur.execute("""CREATE TABLE consumption (
        year INTEGER,
        month INTEGER,
        day INTEGER,
        slice INTEGER CHECK (slice BETWEEN 0 AND 47),
        value INTEGER,
        date TEXT GENERATED ALWAYS AS (PRINTF('%04d-%02d-%02d', year, month, day)) VIRTUAL,
        hour integer GENERATED ALWAYS AS (slice / 2) VIRTUAL,
        PRIMARY KEY (year, month, day, slice)
    );""")
    cur.execute("""CREATE TABLE tempo (
        year INTEGER,
        month INTEGER,
        day INTEGER,
        tempo INTEGER CHECK (tempo BETWEEN 0 AND 3),
        date TEXT GENERATED ALWAYS AS (PRINTF('%04d-%02d-%02d', year, month, day)) VIRTUAL,
        PRIMARY KEY (year, month, day)
    );
    CREATE UNIQUE INDEX tempo_date ON tempo (date);
    """)
    cur.execute("""CREATE TABLE config (
        key TEXT PRIMARY KEY,
        value TEXT
    );""")
    cur.execute("""CREATE TABLE edf_plan_slice (
        plan_id TEXT,
        start TEXT,
        power INTEGER,
        subscription INTEGER,
        day_kind INTEGER,
        kwh_hp INTEGER,
        kwh_hc INTEGER,
        end TEXT,
        PRIMARY KEY (plan_id, power, day_kind, start)
    );""")

    db.commit()
