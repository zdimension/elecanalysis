# coding: utf-8
from aiohttp_requests import requests

DATA_GOUV_ROOT = "https://www.data.gouv.fr"
API_FORMAT = DATA_GOUV_ROOT + "/api/1/{endpoint}"


async def get_resource_info(dataset: str, resource: str):
    url = API_FORMAT.format(endpoint=f"datasets/{dataset}/resources/{resource}")
    req = await requests.get(url)
    req.raise_for_status()
    return await req.json()


async def get_resource_content(resource: str):
    url = f"{DATA_GOUV_ROOT}/fr/datasets/r/{resource}"
    req = await requests.get(url)
    req.raise_for_status()
    return await req.text("utf-8")
