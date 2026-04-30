"""
Stock API Integration (Corporate Firewall Safe)
================================================
Fetches stock data using a cascading fallback strategy:
    1. Stooq (free, no API key, uses pandas-datareader style URL)
    2. FMP - Financial Modeling Prep (requires free API key)
    3. Local CSV fallback (data/stock_data.csv)

Why this cascade:
    Corporate firewalls with SSL interception block Yahoo Finance, Finnhub,
    Alpha Vantage, etc. Stooq and FMP use highly trusted CDNs that often
    pass through enterprise SSL inspection. CSV is the guaranteed last resort.

Usage:
    from integrations.stock_api import get_stock_price
    data = get_stock_price("AAPL")
"""

import os
import sys
import csv
from datetime import datetime

import requests
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings

# Path to the local CSV fallback
CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'stock_data.csv')


def get_stock_price(ticker: str) -> dict:
    """
    Fetch stock data using cascading fallback strategy.
    Tries live APIs first, falls back to CSV if all APIs are blocked.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE.NS")

    Returns:
        dict with keys: ticker, company, current_price, day_high,
                        day_low, volume, source, success
    """
    ticker = ticker.strip().upper()

    # Strategy 1: Stooq (free, no key required)
    result = _fetch_stooq(ticker)
    if result["success"]:
        return result

    # Strategy 2: FMP (requires free API key from financialmodelingprep.com)
    if settings.FMP_API_KEY:
        result = _fetch_fmp(ticker)
        if result["success"]:
            return result

    # Strategy 3: Local CSV fallback (always available, offline data)
    result = _fetch_csv(ticker)
    if result["success"]:
        return result

    return {
        "ticker": ticker,
        "company": ticker,
        "current_price": "N/A",
        "day_high": "N/A",
        "day_low": "N/A",
        "volume": "N/A",
        "source": "none",
        "success": False,
        "error": (
            "Could not fetch stock data. All live APIs are blocked by your "
            "network and this ticker is not in the local CSV dataset. "
            "Add it to data/stock_data.csv for offline access."
        )
    }


# ---- Strategy 1: Stooq ----
def _fetch_stooq(ticker: str) -> dict:
    """
    Fetch from Stooq's free CSV endpoint.
    Works for US tickers (AAPL) and some international ones.
    No API key required. Often passes through corporate firewalls.
    """
    try:
        # Stooq uses lowercase tickers and provides CSV output
        stooq_ticker = ticker.lower()
        if '.ns' in stooq_ticker:
            stooq_ticker = stooq_ticker.replace('.ns', '.in')
        elif '.' not in stooq_ticker:
            stooq_ticker += '.us'
            
        url = f"https://stooq.com/q/l/?s={stooq_ticker}&f=sd2t2ohlcv&h&e=csv"

        resp = requests.get(url, timeout=10, verify=True)
        resp.raise_for_status()

        # Parse the CSV response
        lines = resp.text.strip().split('\n')
        if len(lines) < 2:
            return {"success": False, "error": "Empty response from Stooq", "ticker": ticker}

        # Parse header and data
        headers = [h.strip().lower() for h in lines[0].split(',')]
        values = [v.strip() for v in lines[1].split(',')]

        if len(values) < len(headers):
            return {"success": False, "error": "Incomplete data from Stooq", "ticker": ticker}

        data_dict = dict(zip(headers, values))

        close_price = data_dict.get('close', data_dict.get('last', ''))
        if not close_price or close_price in ('N/D', 'N/A', ''):
            return {"success": False, "error": "No price data from Stooq", "ticker": ticker}

        return {
            "ticker": ticker,
            "company": ticker,
            "current_price": round(float(close_price), 2),
            "day_high": round(float(data_dict.get('high', 0)), 2) or "N/A",
            "day_low": round(float(data_dict.get('low', 0)), 2) or "N/A",
            "volume": f"{int(float(data_dict.get('vol', data_dict.get('volume', 0)))):,}" if data_dict.get('vol', data_dict.get('volume')) else "N/A",
            "source": "Stooq (Live)",
            "success": True
        }

    except requests.exceptions.SSLError:
        return {"success": False, "error": "SSL blocked (corporate firewall)", "ticker": ticker}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection blocked", "ticker": ticker}
    except Exception as e:
        return {"success": False, "error": f"Stooq error: {str(e)}", "ticker": ticker}


# ---- Strategy 2: Financial Modeling Prep (FMP) ----
def _fetch_fmp(ticker: str) -> dict:
    """
    Fetch from Financial Modeling Prep API.
    Requires a free API key from https://financialmodelingprep.com
    Uses highly trusted CDNs, often works behind corporate firewalls.
    """
    try:
        # FMP doesn't support Indian tickers with .NS suffix directly
        fmp_ticker = ticker.replace('.NS', '.NSE').replace('.BS', '.BSE')
        url = f"https://financialmodelingprep.com/api/v3/quote/{fmp_ticker}"

        resp = requests.get(
            url,
            params={"apikey": settings.FMP_API_KEY},
            timeout=10,
            verify=True
        )
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, list) or len(data) == 0:
            return {"success": False, "error": "No data from FMP", "ticker": ticker}

        quote = data[0]
        return {
            "ticker": ticker,
            "company": quote.get("name", ticker),
            "current_price": round(float(quote.get("price", 0)), 2),
            "day_high": round(float(quote.get("dayHigh", 0)), 2) or "N/A",
            "day_low": round(float(quote.get("dayLow", 0)), 2) or "N/A",
            "volume": f"{quote.get('volume', 0):,}" if quote.get("volume") else "N/A",
            "source": "FMP (Live)",
            "success": True
        }

    except requests.exceptions.SSLError:
        return {"success": False, "error": "SSL blocked (corporate firewall)", "ticker": ticker}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection blocked", "ticker": ticker}
    except Exception as e:
        return {"success": False, "error": f"FMP error: {str(e)}", "ticker": ticker}


# ---- Strategy 3: Local CSV Fallback ----
def _fetch_csv(ticker: str) -> dict:
    """
    Look up stock data from the local CSV file (data/stock_data.csv).
    This is the guaranteed fallback when all live APIs are blocked.
    Data is static but reliable.
    """
    try:
        if not os.path.exists(CSV_PATH):
            return {"success": False, "error": "CSV file not found", "ticker": ticker}

        df = pd.read_csv(CSV_PATH)
        df['ticker'] = df['ticker'].str.strip().str.upper()

        match = df[df['ticker'] == ticker]
        if match.empty:
            return {
                "success": False,
                "error": f"Ticker '{ticker}' not found in local CSV. Add it to data/stock_data.csv.",
                "ticker": ticker
            }

        row = match.iloc[0]
        return {
            "ticker": ticker,
            "company": row.get('company', ticker),
            "current_price": round(float(row['current_price']), 2),
            "day_high": round(float(row.get('day_high', 0)), 2) or "N/A",
            "day_low": round(float(row.get('day_low', 0)), 2) or "N/A",
            "volume": str(row.get('volume', 'N/A')),
            "source": f"Local CSV (as of {row.get('last_updated', 'unknown')})",
            "success": True
        }

    except Exception as e:
        return {"success": False, "error": f"CSV error: {str(e)}", "ticker": ticker}
