"""
Currency Exchange API Integration (Corporate Firewall Safe)
=============================================================
Fetches exchange rates with cascading fallback:
    1. exchangerate-api.com (free, no key, trusted CDN)
    2. Local CSV fallback (data/exchange_rates.csv)

Usage:
    from integrations.currency_api import get_exchange_rate
    data = get_exchange_rate({"CURRENCY": "USD", "CURRENCY_TO": "INR", "AMOUNT": "100"})
"""

import os
import sys

import requests
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'exchange_rates.csv')


def get_exchange_rate(entities: dict) -> dict:
    """
    Fetch exchange rate and perform currency conversion.
    Tries live API first, falls back to CSV.

    Args:
        entities: Dict with keys CURRENCY (from), CURRENCY_TO (to), AMOUNT (optional)

    Returns:
        dict with: from_currency, to_currency, rate, amount, converted, source, success
    """
    from_curr = entities.get("CURRENCY", "USD").upper()
    to_curr = entities.get("CURRENCY_TO", "INR").upper()

    # Parse amount
    amount_str = entities.get("AMOUNT", "1")
    try:
        amount = float(str(amount_str).replace(",", ""))
    except (ValueError, TypeError):
        amount = 1.0

    # Strategy 1: Live API
    result = _fetch_live(from_curr, to_curr, amount)
    if result["success"]:
        return result

    # Strategy 2: CSV fallback
    result = _fetch_csv(from_curr, to_curr, amount)
    if result["success"]:
        return result

    return {
        "success": False,
        "error": (
            f"Could not fetch exchange rate for {from_curr} to {to_curr}. "
            "The live API may be blocked and this pair is not in the local CSV."
        )
    }


def _fetch_live(from_curr: str, to_curr: str, amount: float) -> dict:
    """Fetch from exchangerate-api.com (free, no key)."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
        resp = requests.get(url, timeout=10, verify=True)
        resp.raise_for_status()
        data = resp.json()

        rate = data.get("rates", {}).get(to_curr)
        if rate is None:
            return {"success": False, "error": f"Currency '{to_curr}' not found."}

        return {
            "from_currency": from_curr,
            "to_currency": to_curr,
            "rate": round(rate, 4),
            "amount": amount,
            "converted": round(amount * rate, 2),
            "source": "Live API",
            "success": True
        }

    except requests.exceptions.SSLError:
        return {"success": False, "error": "SSL blocked (corporate firewall)"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection blocked"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Exchange rate API timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _fetch_csv(from_curr: str, to_curr: str, amount: float) -> dict:
    """Look up exchange rate from local CSV fallback."""
    try:
        if not os.path.exists(CSV_PATH):
            return {"success": False, "error": "Exchange rate CSV not found."}

        df = pd.read_csv(CSV_PATH)
        df['from_currency'] = df['from_currency'].str.strip().str.upper()
        df['to_currency'] = df['to_currency'].str.strip().str.upper()

        match = df[(df['from_currency'] == from_curr) & (df['to_currency'] == to_curr)]

        if match.empty:
            return {
                "success": False,
                "error": f"Pair {from_curr}/{to_curr} not in local CSV."
            }

        row = match.iloc[0]
        rate = float(row['rate'])

        return {
            "from_currency": from_curr,
            "to_currency": to_curr,
            "rate": round(rate, 4),
            "amount": amount,
            "converted": round(amount * rate, 2),
            "source": f"Local CSV (as of {row.get('last_updated', 'unknown')})",
            "success": True
        }

    except Exception as e:
        return {"success": False, "error": f"CSV error: {str(e)}"}
