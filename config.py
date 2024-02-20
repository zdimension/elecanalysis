# coding: utf-8
from dotenv import dotenv_values

DOTENV_PATH = ".env"

config = None

def load():
    global config
    config = dotenv_values(DOTENV_PATH)

load()
