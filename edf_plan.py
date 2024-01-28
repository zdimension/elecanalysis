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
    TOTALSTDFIXE = "totalstdfixe"
    TOTALSTDFIXEHC = "totalstdfixehc"

    def display_name(self) -> str:
        match self:
            case EdfPlan.BASE:
                return "Bleu Base"
            case EdfPlan.HPHC:
                return "Bleu Heures Creuses"
            case EdfPlan.TEMPO:
                return "Bleu Tempo"
            case EdfPlan.ZENFLEX:
                return "Zen Flex"
            case EdfPlan.ZENWEEKEND:
                return "Zen Week-End"
            case EdfPlan.ZENWEEKENDHC:
                return "Zen Week-End + Heures Creuses"
            case EdfPlan.TOTALSTDFIXE:
                return "Total Standard Fixe"
            case EdfPlan.TOTALSTDFIXEHC:
                return "Total Standard Fixe + Heures Creuses"

    def is_hp_sql(self) -> Optional[str]:
        """
        Gives an SQL expression that evaluates to true if the current hour is in the HP period.

        Assumes `hour` exists and is an INTEGER.

        If the plan doesn't differentiate HC/HP, returns None.
        """
        match self:
            case EdfPlan.HPHC | EdfPlan.TEMPO | EdfPlan.ZENWEEKENDHC | EdfPlan.TOTALSTDFIXEHC:
                return "6 <= hour and hour < 22"
            case EdfPlan.ZENFLEX:
                return "8 <= hour and hour < 13 or 18 <= hour and hour < 20"
            case _:
                return None

    def day_kind_sql(self) -> Optional[str]:
        """
        Gives an SQL expression that evaluates to the day kind (e.g. 1/2/3 for Tempo, 1/2 for Zen Week-End, 0 for Base, ...).

        Assumes `c` is a table with a `date` column (YYYY-MM-DD) and an `hour` column (0-23).
        """
        match self:
            case EdfPlan.TEMPO:
                # noinspection SqlResolve
                return "SELECT tempo FROM tempo t WHERE t.date = IIF(c.hour < 6, DATE(c.date, '-1 day'), c.date)"
            case EdfPlan.ZENFLEX:
                # todo
                # noinspection SqlResolve
                return "SELECT IIF(tempo = 3, 2, 1) FROM tempo t WHERE t.date = c.date"
            case EdfPlan.ZENWEEKEND | EdfPlan.ZENWEEKENDHC:
                return "SELECT IIF(strftime('%w', c.date) IN ('0', '6'), 2, 1)"
            case _:
                return None


def query_plan_stats(plans: list[EdfPlan] = EdfPlan) -> str:
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
        f"({p.is_hp_sql() or '0'}) as hp_{p.value}, ({p.day_kind_sql() or '0'}) as day_{p.value}" for p in plans
    ]) + """,
    c.date,
    hour,
    c.slice,
    c.value / 2 as value
    FROM consumption c"""


def query_plan_prices_bihourly(plans: list[EdfPlan] = EdfPlan, price_mode = "real") -> str:
    """
    Gives an SQL statement that returns the summarized consumption stats for each 30min slice with the following columns:
    - date: YYYY-MM-DD
    - slice: slice index (0-47)
    - value: consumption in Wh
    - eur_{plan}: cost in € for {plan}
    """
    match price_mode:
        case "real":
            price_query = "and c.date between start and end"
        case "current":
            price_query = "order by start desc limit 1"
        case _:
            raise NotImplementedError(price_mode)
    return "SELECT c.date, c.slice, c.value, " + ",".join([
        f"""COALESCE((
            select 
                iif(hp_{p.value}, kwh_hp, kwh_hc) * c.value + 
                subscription * 100000 / 12 / cast(JULIANDAY(date, '+1 month') - JULIANDAY(date) as integer) / 48
            from edf_plan_slice s
            where plan_id='{p.value}' and power = {sub_power} and day_kind = day_{p.value}
            {price_query}), 1e999) as eur_{p.value}""" for p in plans
    ]) + f" FROM ({query_plan_stats(plans)}) c"


def query_plan_prices_monthly(plans: list[EdfPlan] = EdfPlan) -> str:
    """
    Gives an SQL statement that returns the summarized consumption stats for each month with the following columns:
    - date: YYYY-MM
    - value: consumption in Wh
    - eur_{plan}: cost in € for {plan}
    """
    return query_plan_prices_period(plans, date="strftime('%Y-%m', c.date)", filter="1")


def query_plan_prices_period(plans: list[EdfPlan] = EdfPlan, price_mode="real", date: str = "c.date", filter: str = "1", with_total: bool = False) -> str:
    """
    Gives an SQL statement that returns the summarized consumption stats for each day with the following columns:
    - date: YYYY-MM-DD
    - value: consumption in Wh
    - eur_{plan}: cost in € for {plan}
    """
    query = f"SELECT {date}, sum(c.value) as value, " + ",".join([
        f"SUM(eur_{p.value}) as eur_{p.value}" for p in plans
    ]) + f" FROM ({query_plan_prices_bihourly(plans, price_mode)}) c WHERE {filter} GROUP BY {date}"
    if with_total:
        return f"""
        WITH prices AS ({query}) 
        SELECT * FROM prices 
        UNION ALL 
        SELECT 'Total', sum(value), """ + ",".join([
            f"SUM(eur_{p.value}) as eur_{p.value}" for p in plans
        ]) + " FROM prices"
    else:
        return query
