"""
Financial Calculator Module
===========================
Implements deterministic math functions for financial calculations.
Includes EMI, Compound Interest, and Simple Interest.
"""

from nlp.preprocessor import normalize_amount, normalize_rate, normalize_duration


def calculate_emi(principal_str: str, rate_str: str, duration_str: str, currency: str) -> dict:
    """
    Calculate EMI using the standard formula.
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    """
    principal = normalize_amount(str(principal_str))
    rate = normalize_rate(str(rate_str))
    duration_years = normalize_duration(str(duration_str))

    if principal is None or rate is None or duration_years is None:
        return {"success": False, "error": "Could not parse one or more numerical inputs."}

    monthly_rate = rate / 12 / 100
    n_months = duration_years * 12

    if n_months == 0:
        return {"success": False, "error": "Duration cannot be 0 for EMI calculations."}

    if monthly_rate == 0:
        emi = principal / n_months
    else:
        emi = principal * monthly_rate * ((1 + monthly_rate) ** n_months) / (
            ((1 + monthly_rate) ** n_months) - 1
        )

    total_payment = emi * n_months
    total_interest = total_payment - principal

    return {
        "success": True,
        "principal": principal,
        "rate": rate,
        "duration": duration_str,
        "currency": currency,
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
    }


def calculate_interest(principal_str: str, rate_str: str, duration_str: str, currency: str, is_compound: bool = True) -> dict:
    """
    Calculate Compound or Simple Interest.
    Compound (Annual): A = P * (1 + r/100)^t
    Simple: A = P * (1 + (r/100)*t)
    """
    principal = normalize_amount(str(principal_str))
    rate = normalize_rate(str(rate_str))
    duration_years = normalize_duration(str(duration_str))

    if principal is None or rate is None or duration_years is None:
        return {"success": False, "error": "Could not parse one or more numerical inputs."}

    r_decimal = rate / 100

    if is_compound:
        # Default to annual compounding
        total_amount = principal * ((1 + r_decimal) ** duration_years)
    else:
        # Simple interest
        total_amount = principal * (1 + (r_decimal * duration_years))

    total_interest = total_amount - principal

    return {
        "success": True,
        "principal": principal,
        "rate": rate,
        "duration": duration_str,
        "currency": currency,
        "type": "Compound" if is_compound else "Simple",
        "total_amount": round(total_amount, 2),
        "total_interest": round(total_interest, 2),
    }
