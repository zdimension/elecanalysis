# coding: utf-8
from datetime import date
from typing import Optional

import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

TOKEN = config["MED_TOKEN"]
METER_ID = config["METER_ID"]

API_FORMAT = "https://www.myelectricaldata.fr/{endpoint}/{meter_id}{params}/cache/"


def fetch_api(endpoint, range: Optional[tuple[date, date]] = None):
    url = API_FORMAT.format(endpoint=endpoint, meter_id=METER_ID,
                            params="" if range is None else f"/start/{range[0]}/end/{range[1]}")
    print("*", url)
    req = requests.get(url, headers={"Authorization": TOKEN})
    req.raise_for_status()
    res = req.json()
    return res


def get_meter_info():
    return fetch_api("contracts")
