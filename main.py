import fetch_edf
import hacks
import web_ui

hacks.init()

fetch_edf.fetch_loop()

web_ui.run_ui()