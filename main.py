import argparse
import sys

import fetch_edf
import hacks
import web_ui

in_bundle = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

parser = argparse.ArgumentParser()
parser.add_argument("--app", action="store_true", help="Run as desktop app", default=in_bundle)
args = parser.parse_args()

hacks.init()

fetch_edf.fetch_loop()

if args.app:
    from nicegui import native, ui
    ui.run(reload=False, port=native.find_open_port(), native=True)
else:

    web_ui.run_ui()