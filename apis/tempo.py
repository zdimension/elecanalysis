# coding: utf-8
from aiohttp_requests import requests

API_FORMAT = "https://www.api-couleur-tempo.fr/api/{endpoint}"


async def get_days(days: list[str]) -> list[dict]:
    url = API_FORMAT.format(endpoint="joursTempo")
    req = await requests.get(url, params={"dateJour[]": days})
    req.raise_for_status()
    res = await req.json()
    return res
