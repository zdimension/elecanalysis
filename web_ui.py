# coding: utf-8
import math
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time, timedelta, datetime

import numpy as np
import plotly.graph_objects as go
from nicegui import ui, context
from plotly.subplots import make_subplots

import fetch_edf
from config import config
from db import cur, activation_date
from edf_plan import EdfPlan


@dataclass
class YearMonthInput:
    on_change: callable
    year: int = date.today().year
    month: int = date.today().month

    def view(self):
        def set_view_date(y, m):
            while m < 1:
                y -= 1
                m += 12
            while m > 12:
                y += 1
                m -= 12
            year.set_value(str(y))
            month.set_value(str(m))
            change_handler()

        def change_handler():
            self.year = int(year.value)
            self.month = int(month.value)
            self.on_change(self.year, self.month)

        with ui.row().classes("items-end year-month-input"):
            previous_month = ui.button("◀", on_click=lambda: set_view_date(int(year.value), int(month.value) - 1))
            year = ui.select(options=[str(y) for y in range(activation_date.year, date.today().year + 1)],
                             value=str(self.year), on_change=change_handler, label="Année")
            month = ui.select(options=[str(m) for m in range(1, 13)], value=str(self.month), on_change=change_handler,
                              label="Mois")
            next_month = ui.button("▶", on_click=lambda: set_view_date(int(year.value), int(month.value) + 1))


tabs = []


def tab(name):
    def decorator(f):
        tabs.append([name, f, None])
        return f

    return decorator


@tab("Consommation par jour")
def content():
    def nanmax(a):
        # if all nan
        if np.isnan(a).all():
            return np.nan
        return np.nanmax(a)

    def update_plot(y, m):
        fig.data = []
        days_in_month = monthrange(y, m)[1]
        tempo_data_db = np.transpose(np.array(cur.execute("SELECT day, tempo FROM tempo WHERE year = ? AND month = ? ORDER BY day", (y, m)).fetchall()))
        tempo_data = np.full(days_in_month, np.nan, dtype=np.float32)
        if len(tempo_data_db) > 0:
            tempo_data[tempo_data_db[0] - 1] = tempo_data_db[1]
        fig.add_trace(go.Heatmap(
            z=tempo_data.reshape((days_in_month, 1)),
            zmin=1,
            # zmax=nanmax(month_data),
            zmax=3,
            colorscale=[
                [0, "rgb(21, 101, 192)"],
                [0.5, "rgb(240, 240, 240)"],
                [1, "rgb(198, 40, 40)"]
            ],
            text=[[["n/a", "Bleu", "Blanc", "Rouge"][0 if math.isnan(x) else int(x)]] for x in tempo_data],
            hovertemplate=f"%{{y}}/{m:02d}: Jour %{{text}}<extra></extra>",
            showscale=False,
            ygap=1
        ), row=1, col=1)
        month_data_db = np.transpose(np.array(cur.execute(
            "SELECT (day - 1) * 48 + slice, value FROM consumption WHERE year = ? AND month = ? ORDER BY day, slice",
            (y, m)).fetchall(),
                                              dtype=np.int32))
        month_data = np.full(48 * days_in_month, np.nan, dtype=np.float32)
        if len(month_data_db) > 0:
            month_data[month_data_db[0]] = month_data_db[1]
        month_data = month_data.reshape((days_in_month, 48)) / 2
        fig.add_trace(go.Heatmap(
            z=month_data,
            zmin=0,
            # zmax=nanmax(month_data),
            zmax=2000,
            colorscale='hot',
            colorbar=dict(
                x=0.748,
                ticksuffix="&nbsp;Wh",
                tickformat="d",
            ),
            text=[[*timelabels[1:], "00:00"]] * days_in_month,
            hovertemplate=f"%{{y}}/{m:02d}, %{{x}}-%{{text}}: %{{z}} Wh<extra></extra>"), row=1, col=2)
        fig.update_yaxes(tickvals=list(range(days_in_month)), ticktext=list(map(str, range(1, days_in_month + 1))))
        sum_per_day = np.nansum(month_data, axis=1).reshape((-1, 1)) / 1000
        sum_per_day[np.isnan(month_data).all(axis=1)] = np.nan
        fig.add_trace(go.Heatmap(
            z=sum_per_day,
            zmin=0,
            # zmax=nanmax(sum_per_day),
            zmax=40,
            colorscale='hot',
            colorbar=dict(
                x=1,
                ticksuffix="&nbsp;kWh",
                tickformat="d"
            ),
            hovertemplate=f"%{{y}}/{m:02d}: %{{z:.1f}} kWh<extra></extra>"), row=1, col=3)
        plot.update()

    date_sel = YearMonthInput(update_plot)
    date_sel.view()

    fig = make_subplots(rows=1, cols=3, column_widths=[0.03, 0.75, 0.15], subplot_titles=("Tempo", "Consommation", "Total par jour"),
                        horizontal_spacing=0, specs=[
            [{}, {"l": 0.02, "r": 0.09}, {}]
        ])
    timelabels = [f"{i:02d}:{j:02d}" for i in range(24) for j in (0, 30)]
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickvals=list(range(48)), ticktext=timelabels, col=2)
    fig.update_xaxes(visible=False, col=3)
    fig.update_xaxes(visible=False, col=1)
    fig.update_yaxes(showticklabels=False, col=1)
    plot = ui.plotly(fig).classes('h-full w-full')
    update_plot(date_sel.year, date_sel.month)


@tab("Coût")
def content():
    ui.html("""
    <div class="bg-gray-100 border-l-4 border-gray-500 text-gray-700 p-3" role="alert">
        <p>Ici, une case grisée signifie que les prix pour la période et l'offre concernées ne sont pas connus.</p>
    </span>""")

    compare_base = "base"
    plans_show = [p.value for p in (EdfPlan.BASE, EdfPlan.HPHC, EdfPlan.TEMPO, EdfPlan.ZENFLEX)]

    @ui.refreshable
    def price_table():
        columns = [
            dict(name="month", label="Mois", field="month"),
            {'name': "kwh", 'label': "kWh", 'field': "kwh"},
        ]

        plans_obj = list(map(EdfPlan, plans_show))

        for plan in plans_obj:
            columns.append(dict(name=f"plan_{plan.value}", label=f"Prix {plan.display_name()}", field=f"plan_{plan.value}"))
            columns.append({'name': f"diff_{plan.value}", 'label': f"% {EdfPlan(compare_base).display_name()}",
                            'field': f"diff_{plan.value}"})

        conso = cur.execute(EdfPlan.query_plan_prices_monthly()).fetchall()

        def process(row):
            res = {"month": row[0], "kwh": f"{row[1] / 1000:.1f}"}
            vals = {}
            for p, v in zip(plans_obj, row[2:]):
                f = f"plan_{p.value}"
                vals[p.value] = float("nan")
                res[f] = "-"
                res[f"{f}_bgcolor"] = "background-color: rgb(240, 240, 240)"
                if v is not None and not math.isinf(v):
                    vals[p.value] = v / 10000000
                    res[f] = "{0:.2f} €".format(vals[p.value])
                    del res[f"{f}_bgcolor"]
            for i, p in enumerate(plans_obj):
                diff = (vals[p.value] - vals[compare_base]) / vals[compare_base]
                if math.isnan(diff):
                    color = "rgb(240, 240, 240)"
                    text = "-"
                else:
                    correction_factor = 1.5
                    corrected = 100 * (abs(diff) ** (1 / correction_factor))
                    color = f"color-mix(in lch, {'rgb(76, 175, 80)' if diff < 0 else 'rgb(244, 67, 54)'} {corrected}%, transparent)"
                    text = "{0:+.1f}%".format(100 * diff)
                res[f"diff_{p.value}"], res[f"diff_{p.value}_bgcolor"] = text, f"background-color: {color}"
            return res

        rows = [process(row) for row in conso]

        table = ui.table(columns=columns, rows=rows).classes("h-full w-full table-fixed")
        table.props("separator=cell wrap-cells")
        if dense.value:
            table.props("dense")
        for p in EdfPlan:
            table.add_slot(f"body-cell-plan_{p.value}", f'<q-td key="plan_{p.value}" :props="props" :style="props.row.plan_{p.value}_bgcolor">'
                           + "{{ props.value }}</q-td>")
            table.add_slot(f"body-cell-diff_{p.value}", f'<q-td key="diff_{p.value}" :props="props" :style="props.row.diff_{p.value}_bgcolor">'
                           + "{{ props.value }}</q-td>")

    def base_changed(e):
        nonlocal compare_base
        compare_base = e.value
        price_table.refresh()

    def show_changed(e):
        nonlocal plans_show
        plans_show = sorted(e.value)
        plans.set_value(plans_show)
        price_table.refresh()

    with ui.row().classes("items-end"):
        dense = ui.checkbox(text="Dense", value=False, on_change=price_table.refresh)
        ui.select({p.value: p.display_name() for p in EdfPlan}, value=compare_base, label="Base 100%", on_change=base_changed)
        plans = ui.select({p.value: p.display_name() for p in EdfPlan}, label="Offres à comparer",
                          multiple=True,
                          value=plans_show, on_change=show_changed)
        plans.add_slot("option", f"""
          <q-item v-bind="props.itemProps">
            <q-item-section>
              <q-item-label v-html="props.opt.label" />
            </q-item-section>
            <q-item-section side>
              <q-toggle :model-value="props.selected" @update:model-value="props.toggleOption(props.opt)" />
            </q-item-section>
          </q-item>
        """)

    price_table()


@tab("Statistiques")
def content():
    ui.label("Rien ici pour l'instant")


@ui.page("/")
def index():
    ui.add_head_html("""
        <style>
            .q-field__label {
                overflow: visible;
            }
            
            /*.year-month-input*/ .q-select__dropdown-icon {
                --tw-translate-y: 25%;
                transform: translateY(var(--tw-translate-y));
            }
            
            .table-fixed table {
                table-layout: fixed;
            }
        </style>
    """)

    @ui.refreshable
    def all_tabs():
        with ui.tabs().classes("w-full") as tabbar:
            for i, (name, *_) in enumerate(tabs):
                tabs[i][2] = ui.tab(name)
        with ui.tab_panels(tabbar, value=tabs[0][2]).classes("w-full h-full"):
            for name, f, *_ in tabs:
                with ui.tab_panel(name):
                    f()

    with ui.row():
        ui.button("Forcer màj Enedis", on_click=lambda: (fetch_edf.fetch_enedis(upto=date.today() + timedelta(days=1)), all_tabs.refresh()))

    all_tabs()

    context.get_client().content.classes('h-[100vh]')


def run_ui():
    ui.run(port=int(config["PORT"]), show=False)
