# coding: utf-8
import enum
from typing import Optional

from db import sub_power


class EdfPlan(enum.Enum):
    BASE = "base"
    HPHC = "hphc"
    TEMPO = "tempo"
    ZENFLEX = "zenflex"
    ZENWEEKEND = "zenweekend"
    ZENWEEKENDHC = "zenweekendhc"

    def display_name(self) -> str:
        match self:
            case EdfPlan.BASE:
                return "Bleu Base"
            case EdfPlan.HPHC:
                return "Bleu Heures Creuses"
            case EdfPlan.TEMPO:
                return "Bleu Tempo"
            case EdfPlan.ZENFLEX:
                return "Zen Flex"
            case EdfPlan.ZENWEEKEND:
                return "Zen Week-End"
            case EdfPlan.ZENWEEKENDHC:
                return "Zen Week-End + Heures Creuses"

    def is_hp_sql(self) -> Optional[str]:
        """
        Gives an SQL expression that evaluates to true if the current hour is in the HP period.

        Assumes `hour` exists and is an INTEGER.

        If the plan doesn't differentiate HC/HP, returns None.
        """
        match self:
            case EdfPlan.HPHC | EdfPlan.TEMPO | EdfPlan.ZENWEEKENDHC:
                return "6 <= hour and hour < 22"
            case EdfPlan.ZENFLEX:
                return "8 <= hour and hour < 13 or 18 <= hour and hour < 20"
            case _:
                return None

    def day_kind_sql(self) -> str:
        """
        Gives an SQL expression that evaluates to the day kind (e.g. 1/2/3 for Tempo, 1/2 for Zen Week-End, 0 for Base, ...).

        Assumes `c` is a table with a `date` column (YYYY-MM-DD) and an `hour` column (0-23).
        """
        match self:
            case EdfPlan.TEMPO:
                # noinspection SqlResolve
                #return "SELECT tempo FROM tempo t WHERE t.date = c.date"
                return "SELECT tempo FROM tempo t WHERE t.date = IIF(c.hour < 6, DATE(c.date, '-1 day'), c.date)"
            case EdfPlan.ZENFLEX:
                # todo
                return "1"
            case EdfPlan.ZENWEEKEND | EdfPlan.ZENWEEKENDHC:
                return "SELECT IIF(strftime('%w', c.date) IN ('0', '6'), 2, 1)"
            case _:
                return "0"

    @staticmethod
    def query_plan_stats() -> str:
        """
        Gives an SQL statement that returns the consumption stats with the following columns:
        - hp_{plan}: 1 if the current hour is in the HP period for {plan}
        - day_{plan}: the day kind for {plan}
        - date: YYYY-MM-DD
        - hour: hour (0-23)
        - slice: slice index (0-47)
        - value: consumption in Wh
        """
        return "SELECT " + ",".join([
            f"({p.is_hp_sql() or '0'}) as hp_{p.value}, ({p.day_kind_sql()}) as day_{p.value}" for p in EdfPlan
        ]) + """,
        c.date,
        hour,
        c.slice,
        c.value / 2 as value
        FROM consumption c"""

    @staticmethod
    def query_plan_prices_bihourly() -> str:
        """
        Gives an SQL statement that returns the summarized consumption stats for each 30min slice with the following columns:
        - date: YYYY-MM-DD
        - slice: slice index (0-47)
        - value: consumption in Wh
        - eur_{plan}: cost in € for {plan}
        """
        return "SELECT c.date, c.slice, c.value, " + ",".join([
            f"""COALESCE((
                select 
                    iif(hp_{p.value}, kwh_hp, kwh_hc) * c.value + 
                    subscription * 100000 / 12 / cast(JULIANDAY(date, '+1 month') - JULIANDAY(date) as integer) / 48
                from edf_plan_slice s
                where plan_id='{p.value}' and power = {sub_power} and day_kind = day_{p.value}
                and c.date between start and end), 1e999) as eur_{p.value}""" for p in EdfPlan
        ]) + f" FROM ({EdfPlan.query_plan_stats()}) c"

    @staticmethod
    def query_plan_prices_daily() -> str:
        """
        Gives an SQL statement that returns the summarized consumption stats for each day with the following columns:
        - date: YYYY-MM-DD
        - value: consumption in Wh
        - eur_{plan}: cost in € for {plan}
        """
        return "SELECT c.date, sum(c.value) as value, " + ",".join([
            f"SUM(eur_{p.value}) as eur_{p.value}" for p in EdfPlan
        ]) + f" FROM ({EdfPlan.query_plan_prices_bihourly()}) c GROUP BY c.date"

    @staticmethod
    def query_plan_prices_monthly() -> str:
        """
        Gives an SQL statement that returns the summarized consumption stats for each month with the following columns:
        - date: YYYY-MM
        - value: consumption in Wh
        - eur_{plan}: cost in € for {plan}
        """
        return "SELECT strftime('%Y-%m', c.date) as date, sum(c.value) as value, " + ",".join([
            f"SUM(eur_{p.value}) as eur_{p.value}" for p in EdfPlan
        ]) + f" FROM ({EdfPlan.query_plan_prices_bihourly()}) c GROUP BY strftime('%Y-%m', c.date)"

