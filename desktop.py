# coding: utf-8
import asyncio

import nicegui.events
from nicegui import native, ui as nui, run as nrun
import webbrowser
import platformdirs
from starlette.responses import RedirectResponse
import sys

DATA_DIR = platformdirs.user_data_path("elecanalysis", "zdimension")

# set cwd to the data directory
import os
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
os.chdir(DATA_DIR)

sys.stdout = open('logs.txt', 'w')
print("Using", DATA_DIR, "as storage dir")

if not os.path.exists(DATA_DIR / ".env"):
    with open(DATA_DIR / ".env", "w") as f:
        f.write("PORT=8129\n")

import config

@nui.page("/setup")
def setup():
    nui.markdown("# Bienvenue dans elecanalysis")
    nui.label("Pour commencer, il faut établir une connexion à MyElectricalData pour pouvoir récupérer vos données "
              "de consommation.")
    nui.label("Cliquez ici pour ouvrir votre espace Enedis et activer l'accès :")
    nui.button("Connexion à MyElectricalData",
               on_click=lambda: webbrowser.open("https://mon-compte-particulier.enedis.fr/dataconnect/v1/oauth2/authorize?client_id=e551937c-5250-48bc-b4a6-2323af68db92&duration=P36M&response_type=code"))
    nui.label("Une fois que c'est fait, entrez le numéro de PDL et la clef :")
    pdl = nui.input("Point de livraison :")
    key = nui.input("Clef :")

    def save_settings():
        from dotenv import set_key
        set_key(".env", "METER_ID", pdl.value)
        set_key(".env", "MED_TOKEN", key.value)

        config.load()
        nui.open("/")

    nui.button("Valider", on_click=save_settings)

@nui.page("/loading")
def loading():
    log = ""
    def logger(*args):
        nonlocal log
        print("logger:", *args)
        log += " ".join(map(str, args)) + "\n"
        log_display.refresh()
    @nui.refreshable
    def log_display():
        nui.code(log, language="text").classes("w-full")
    import fetch_edf
    fetch_edf.log_callback = logger
    nui.markdown("# Récupération des données")
    log_display()
    task = asyncio.create_task(fetch_edf.fetch_loop())
    import ui
    _ = ui
    nui.timer(0.1, lambda: task.done() and nui.open("/app"))

@nui.page("/")
async def index():
    if not ("METER_ID" in config.config and "MED_TOKEN" in config.config):
        return setup()

    import db
    await db.load_meter_info()
    return RedirectResponse("/loading")

def run():
    title = "elecanalysis"

    import hacks
    if hacks.in_bundle:
        import _version
        title += f" {_version.__version__}"
    nui.run(reload=False, port=native.find_open_port(), native=True, window_size=(1366, 768), title=title)