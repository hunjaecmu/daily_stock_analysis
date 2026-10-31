# -*- coding: utf-8 -*-
"""Build the "밤사이 미국" headline with the US 10-year yield and the dollar index."""

import io
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Callable, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
YIELD_SERIES = "DGS10"
DOLLAR_SYMBOL = "DX-Y.NYB"
LOOKBACK_DAYS = 20  # Long enough to reach past holiday gaps and publication lag.
REQUEST_TIMEOUT_SECONDS = 20
FETCH_TIMEOUT_SECONDS = 30  # A stuck source must not hold up the report.
UNAVAILABLE = "확인 실패"


def _start_date() -> str:
    return (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()


def _latest_value(series: "pd.Series", name: str) -> Tuple[float, str]:
    series = series.dropna()
    if series.empty:
        raise ValueError(f"no data for {name}")
    return float(series.iloc[-1]), series.index[-1].strftime("%Y-%m-%d")


def _fetch_fred_latest(series_id: str) -> Tuple[float, str]:
    """Read FRED's CSV directly: FinanceDataReader forward-fills holidays, which would misdate the value."""
    response = requests.get(
        FRED_CSV_URL,
        params={"id": series_id, "cosd": _start_date()},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    frame = pd.read_csv(
        io.StringIO(response.text),
        parse_dates=["observation_date"],
        index_col="observation_date",
        na_values=".",
    )
    return _latest_value(frame[series_id], series_id)


def _fetch_dollar_latest() -> Tuple[float, str]:
    import FinanceDataReader as fdr

    return _latest_value(fdr.DataReader(DOLLAR_SYMBOL, _start_date())["Close"], DOLLAR_SYMBOL)


def _format_item(
    label: str,
    fetch: Callable[[], Tuple[float, str]],
    pool: ThreadPoolExecutor,
    suffix: str = "",
) -> str:
    """Each number carries its own date; a failed one is marked, never filled in."""
    try:
        value, as_of = pool.submit(fetch).result(timeout=FETCH_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("US overnight fetch failed for %s: %s", label, type(exc).__name__)
        return f"{label} {UNAVAILABLE}"
    return f"{label} {value:.2f}{suffix} ({as_of} 기준)"


def build_us_overnight_line() -> Optional[str]:
    """Return the headline, or None when neither number could be fetched."""
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        items = [
            _format_item("10년물 금리", lambda: _fetch_fred_latest(YIELD_SERIES), pool, "%"),
            _format_item("달러 인덱스", _fetch_dollar_latest, pool),
        ]
    finally:
        pool.shutdown(wait=False)
    if all(item.endswith(UNAVAILABLE) for item in items):
        return None
    return f"**밤사이 미국** | {' · '.join(items)}"
