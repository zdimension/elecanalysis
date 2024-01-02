import os
from collections import defaultdict
from typing import Optional
from dotenv import dotenv_values
import requests
import pickle
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, DataClassJsonMixin, config as djconfig
from datetime import date, timedelta, datetime
from calendar import monthrange

config = dotenv_values(".env")

TOKEN = config["TOKEN"]
METER_ID = config["METER_ID"]

API_FORMAT = "https://www.myelectricaldata.fr/{endpoint}/{meter_id}{params}/cache/"


def fetch_api(endpoint, range: Optional[tuple[date, date]] = None):
    url = API_FORMAT.format(endpoint=endpoint, meter_id=METER_ID,
                            params="" if range is None else f"/start/{range[0]}/end/{range[1]}")
    print("*", url)
    req = requests.get(url, headers={"Authorization": TOKEN})
    req.raise_for_status()
    res = req.json()
    return res


def get_meter_info():
    return fetch_api("contracts")


DayData = list[int]
MonthData = list[DayData]
YearData = list[MonthData]


@dataclass
class AppState(DataClassJsonMixin):
    meter_info: dict
    last_info: date = field(metadata=djconfig(encoder=date.isoformat, decoder=date.fromisoformat))
    consumption: dict[int, YearData]
    activation_date: date = field(metadata=djconfig(encoder=date.isoformat, decoder=date.fromisoformat))

    def iteryears(self, start_year=None):
        start_year = start_year or self.activation_date.year
        for year, year_data in sorted(self.consumption.items()):
            if year < start_year:
                continue
            yield year, year_data

    def itermonths(self, start: tuple[int, int] = None):
        start = start or (self.activation_date.year, self.activation_date.month)
        if first_year := self.consumption.get(start[0], None):
            for month, month_data in enumerate(first_year[start[1] - 1:], start[1]):
                yield (start[0], month), month_data
        for year, year_data in self.iteryears(start[0] + 1):
            for month, month_data in enumerate(year_data, 1):
                yield (year, month), month_data

    def iterdays(self, start: date = None):
        start = start or self.activation_date
        for (year, month), month_data in self.itermonths(start.year, start.month):
            for day, day_data in enumerate(month_data, 1):
                yield (year, month, day), day_data

    def get_month(self, year, month):
        if not (year_data := self.consumption.get(year, None)):
            year_data = [None] * 12
            self.consumption[year] = year_data
        month_data = year_data[month - 1]
        if month_data is None:
            month_data = [[None] * 48 for _ in range(monthrange(year, month)[1])]
            year_data[month - 1] = month_data
        return month_data


STATE_FILE = "app.json"


def save_state():
    # rename old file
    if os.path.exists(STATE_FILE):
        os.rename(STATE_FILE, STATE_FILE + ".bak")
    with open(STATE_FILE, "w") as f:
        f.write(state.to_json(default=str))


try:
    with open(STATE_FILE, "r") as f:
        state = AppState.from_json(f.read())
except FileNotFoundError:
    meter_info = get_meter_info()
    activation_date = date.fromisoformat(
        meter_info["customer"]["usage_points"][0]["contracts"]["last_activation_date"][:10])
    state = AppState(meter_info=meter_info,
                     last_info=activation_date - timedelta(days=1),
                     consumption={},
                     activation_date=activation_date)

    save_state()

start_date = None

while True:
    new_start_date = state.last_info + timedelta(days=1)
    if new_start_date == start_date or new_start_date >= date.today() - timedelta(days=1):
        break
    start_date = new_start_date
    end_date = start_date + timedelta(days=7)
    try:
        conso_data = fetch_api("consumption_load_curve", (start_date, end_date))[
            "meter_reading"]["interval_reading"]
    except requests.exceptions.HTTPError as e:
        print(e)
        break
    for reading in conso_data:
        dt = datetime.fromisoformat(reading["date"]) - timedelta(minutes=30)

        month_data = state.get_month(dt.year, dt.month)

        if dt.date() > state.last_info:
            state.last_info = dt.date()

        day_data = month_data[dt.day - 1]
        slice_idx = dt.hour * 2 + dt.minute // 30
        day_data[slice_idx] = int(reading["value"])
    save_state()

from nicegui import ui, context
import plotly.graph_objects as go
import numpy as np

fig = go.Figure()
timelabels = [f"{i:02d}:{j:02d}" for i in range(24) for j in (0, 30)]
def update_plot():
    fig.data = []
    y, m = int(year.value), int(month.value)
    month_data = np.array(state.get_month(y, m), dtype=np.float64) / 2
    #month_data[month_data == None] = np.nan
    #month_data[not np.isnan(month_data)] //= 2
    fig.add_trace(go.Heatmap(
        z=month_data,
        colorscale='hot',
        hovertemplate=f"%{{y}}/{m:02d}, %{{x}}: %{{z}} Wh<extra></extra>"))
    fig.update_yaxes(tickvals=list(range(len(month_data))), ticktext=list(map(str, range(1, len(month_data) + 1))))
    plot.update()

def set_view_date(y, m):
    while m < 1:
        y -= 1
        m += 12
    while m > 12:
        y += 1
        m -= 12
    year.set_value(str(y))
    month.set_value(str(m))

with ui.row():
    previous_month = ui.button("◀", on_click=lambda: set_view_date(int(year.value), int(month.value) - 1))
    year = ui.select(options=[str(y) for y in range(state.activation_date.year, date.today().year + 1)],
                     value=str(date.today().year), on_change=update_plot, label="Année")
    month = ui.select(options=[str(m) for m in range(1, 13)], value=str(date.today().month), on_change=update_plot, label="Mois")
    next_month = ui.button("▶", on_click=lambda: set_view_date(int(year.value), int(month.value) + 1))

context.get_client().content.classes('h-[100vh]')
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(tickvals=list(range(48)), ticktext=timelabels)
plot = ui.plotly(fig).classes('h-full w-full')
update_plot()

ui.run(port=int(config["PORT"]))
