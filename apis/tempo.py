# coding: utf-8
import requests

API_FORMAT = "https://www.api-couleur-tempo.fr/api/{endpoint}"


def get_days(days: list[str]) -> list[str]:
    url = API_FORMAT.format(endpoint="joursTempo")
    req = requests.get(url, params={"dateJour[]": days})
    req.raise_for_status()
    res = req.json()
    return res
