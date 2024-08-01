# coding: utf-8
from datetime import date
from typing import Optional

from aiohttp_requests import requests
import config

API_FORMAT = "https://www.myelectricaldata.fr/{endpoint}/{meter_id}{params}/cache/"


async def fetch_api(endpoint, range: Optional[tuple[date, date]] = None):
    url = API_FORMAT.format(endpoint=endpoint, meter_id=config.config["METER_ID"],
                            params="" if range is None else f"/start/{range[0]}/end/{range[1]}")
    req = await requests.get(url, headers={"Authorization": config.config["MED_TOKEN"]})
    res = await req.json()
    if not req.ok:
        print(res)
    req.raise_for_status()
    return res


async def get_meter_info():
    return await fetch_api("contracts")
