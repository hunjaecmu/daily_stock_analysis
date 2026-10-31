# -*- coding: utf-8 -*-
"""Build the "밤사이 미국" headline with the US 10-year yield and the dollar index."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)

YIELD_SYMBOL = "FRED:DGS10"
DOLLAR_SYMBOL = "DX-Y.NYB"
LOOKBACK_DAYS = 20  # FRED leaves US holidays empty, so read back past them.
FETCH_TIMEOUT_SECONDS = 30  # A stuck source must not hold up the report.
UNAVAILABLE = "확인 실패"


def _fetch_latest(symbol: str, column: str) -> Tuple[float, str]:
    import FinanceDataReader as fdr

    start = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    series = fdr.DataReader(symbol, start)[column].dropna()
    if series.empty:
        raise ValueError(f"no data for {symbol}")
    return float(series.iloc[-1]), series.index[-1].strftime("%Y-%m-%d")


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
            _format_item("10년물 금리", lambda: _fetch_latest(YIELD_SYMBOL, "DGS10"), pool, "%"),
            _format_item("달러 인덱스", lambda: _fetch_latest(DOLLAR_SYMBOL, "Close"), pool),
        ]
    finally:
        pool.shutdown(wait=False)
    if all(item.endswith(UNAVAILABLE) for item in items):
        return None
    return f"**밤사이 미국** | {' · '.join(items)}"
