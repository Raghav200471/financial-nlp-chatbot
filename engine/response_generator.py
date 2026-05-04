"""
Response Generator
==================
Template-based response engine for the financial chatbot.
Maps handler results to human-friendly, formatted responses.

Gemini summarization support is available when USE_GEMINI is enabled.
"""

# ---- Response Templates ----
RESPONSE_TEMPLATES = {
    "stock_price": (
        "**{company} ({ticker})**\n"
        "* Current Price: {currency_symbol}{current_price}\n"
        "* Day High: {currency_symbol}{day_high}\n"
        "* Day Low: {currency_symbol}{day_low}\n"
        "* Volume: {volume}\n"
        "_Source: {source}_"
    ),

    "stock_price_error": (
        "I couldn't fetch the stock price for **{ticker}**. "
        "Please check the ticker symbol and try again.\n"
        "Error: {error}"
    ),

    "emi_result": (
        "**EMI Calculation Result**\n"
        "---\n"
        "* Loan Amount: {currency} {principal:,.2f}\n"
        "* Interest Rate: {rate}% per annum\n"
        "* Tenure: {duration}\n"
        "---\n"
        "* **Monthly EMI: {currency} {emi:,.2f}**\n"
        "* Total Payment: {currency} {total_payment:,.2f}\n"
        "* Total Interest: {currency} {total_interest:,.2f}"
    ),

    "interest_result": (
        "**{type} Interest Calculation Result**\n"
        "* Principal Amount: {currency} {principal:,.2f}\n"
        "* Interest Rate: {rate}% per annum\n"
        "* Tenure: {duration}\n"
        "---\n"
        "* **Total Interest Earned: {currency} {total_interest:,.2f}**\n"
        "* Maturity Value: {currency} {total_amount:,.2f}"
    ),

    "exchange_rate": (
        "**Exchange Rate**\n"
        "* {from_currency} -> {to_currency}\n"
        "* Rate: 1 {from_currency} = {rate} {to_currency}\n"
        "* **{amount} {from_currency} = {converted} {to_currency}**\n"
        "_Source: {source}_"
    ),

    "exchange_rate_error": (
        "I couldn't fetch the exchange rate. {error}"
    ),

    "loan_eligibility": (
        "**Loan Eligibility Assessment**\n"
        "Based on the information provided:\n"
        "* Requested Amount: {amount}\n"
        "* Duration: {duration}\n\n"
        "General eligibility criteria:\n"
        "* Minimum CIBIL score: 700+\n"
        "* Stable income source (min 2 years)\n"
        "* Age: 21-65 years\n"
        "* EMI should not exceed 40-50% of monthly income\n\n"
        "*For a formal eligibility assessment, please contact your bank directly.*"
    ),

    "faq_answer": "{answer}",

    "greeting": (
        "Hello! I'm your **Financial Assistant**. I can help you with:\n\n"
        "* **Stock Prices** -- \"What is the price of AAPL?\"\n"
        "* **EMI Calculations** -- \"Calculate EMI for 10 lakh at 8.5% for 20 years\"\n"
        "* **Loan Information** -- \"What is a home loan?\"\n"
        "* **Currency Exchange** -- \"USD to INR rate\"\n"
        "* **Financial FAQs** -- \"What is SIP?\"\n\n"
        "How can I help you today?"
    ),

    "goodbye": (
        "Goodbye! Thank you for using the Financial Assistant. "
        "Feel free to return anytime with your financial queries. Have a great day!"
    ),

    "slot_ask": "I need a bit more information. {prompt}",

    "error": "Sorry, I encountered an error: {error_message}. Please try again.",

    "fallback": (
        "I'm not sure I understand that query. I can help with:\n"
        "* Stock prices\n"
        "* EMI calculations\n"
        "* Loan information & eligibility\n"
        "* Currency exchange rates\n"
        "* Financial FAQs\n\n"
        "Could you rephrase your question?"
    ),

    "gemini_unavailable": (
        "I don't have enough information to answer that question with my "
        "built-in knowledge. This type of complex financial question would benefit "
        "from expert analysis. Please try rephrasing with a more specific query."
    ),
}


def generate_response(template_key: str, data: dict) -> str:
    """
    Generate a formatted response string from a template.

    Args:
        template_key: Key from RESPONSE_TEMPLATES
        data: Dict of values to fill into the template

    Returns:
        Formatted response string
    """
    template = RESPONSE_TEMPLATES.get(template_key, RESPONSE_TEMPLATES["fallback"])
    try:
        return template.format(**data)
    except KeyError as e:
        return RESPONSE_TEMPLATES["error"].format(
            error_message=f"Missing data field: {e}"
        )
    except Exception as e:
        return RESPONSE_TEMPLATES["error"].format(
            error_message=str(e)
        )
