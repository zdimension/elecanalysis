from nicegui import ui as nui

from config import config

async def run_ui():
    import db
    await db.load_meter_info()
    import fetch_edf
    await fetch_edf.fetch_loop()
    import ui
    _ = ui
    @nui.page("/")
    def index():
        return ui.index()
    nui.run(port=int(config["PORT"]), show=False, title="elecanalysis")
