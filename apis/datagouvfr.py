# coding: utf-8
import requests

DATA_GOUV_ROOT = "https://www.data.gouv.fr"
API_FORMAT = DATA_GOUV_ROOT + "/api/1/{endpoint}"


def get_resource_info(dataset: str, resource: str):
    url = API_FORMAT.format(endpoint=f"datasets/{dataset}/resources/{resource}")
    req = requests.get(url)
    req.raise_for_status()
    return req.json()


def get_resource_content(resource: str):
    url = f"{DATA_GOUV_ROOT}/fr/datasets/r/{resource}"
    req = requests.get(url)
    req.raise_for_status()
    return req.content
