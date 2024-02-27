import argparse
import sys

import hacks

parser = argparse.ArgumentParser()
parser.add_argument("--app", action="store_true", help="Run as desktop app", default=hacks.in_bundle)
args, unknown = parser.parse_known_args()

hacks.init()

if args.app:
    import desktop
    desktop.run()
else:
    import asyncio
    import web_ui
    asyncio.run(web_ui.run_ui())
