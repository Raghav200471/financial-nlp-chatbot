"""
Text Preprocessor
=================
Handles text cleaning, tokenization, and lemmatization for the NLP pipeline.
Financial symbols ($, ₹, %, .) are preserved since they carry meaning in this domain.
"""

import re
import string


def clean_text(text: str) -> str:
    """
    Clean and normalize input text while preserving financial symbols.
    
    Keeps: alphanumeric, whitespace, ., %, $, ₹, /
    Removes: all other special characters
    """
    text = text.strip()
    # Lowercase but preserve ticker-like patterns first
    text = text.lower()
    # Remove special chars but keep financial symbols
    text = re.sub(r'[^\w\s.%$₹/\-]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def tokenize_simple(text: str) -> list[str]:
    """
    Simple whitespace tokenizer with basic stop word removal.
    Used when SpaCy is not available or for lightweight processing.
    """
    STOP_WORDS = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
        'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him',
        'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its',
        'itself', 'they', 'them', 'their', 'theirs', 'themselves',
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
        'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
        'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as',
        'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
        'against', 'between', 'through', 'during', 'before', 'after',
        'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
        'on', 'off', 'over', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'when', 'where', 'why', 'how',
        'all', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 's', 't', 'can', 'will', 'just',
        'don', 'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y'
    }
    cleaned = clean_text(text)
    tokens = cleaned.split()
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def extract_numbers(text: str) -> list[str]:
    """Extract all numeric values from text (including decimals and percentages)."""
    return re.findall(r'\d+\.?\d*%?', text)


def normalize_amount(text: str) -> float | None:
    """
    Attempt to parse Indian-style amount strings into numeric values.
    
    Examples:
        '10 lakh' -> 1000000.0
        '2.5 crore' -> 25000000.0
        '50000' -> 50000.0
    """
    text = text.lower().strip().replace(',', '')
    
    # Handle lakh/crore
    lakh_match = re.search(r'([\d.]+)\s*(?:lakh|lac|lakhs)', text)
    if lakh_match:
        return float(lakh_match.group(1)) * 100000
    
    crore_match = re.search(r'([\d.]+)\s*(?:crore|cr|crores)', text)
    if crore_match:
        return float(crore_match.group(1)) * 10000000

    # Handle million/billion/thousand/k
    billion_match = re.search(r'([\d.]+)\s*(?:billion|bil)', text)
    if billion_match:
        return float(billion_match.group(1)) * 1000000000

    million_match = re.search(r'([\d.]+)\s*(?:million|mil)', text)
    if million_match:
        return float(million_match.group(1)) * 1000000

    thousand_match = re.search(r'([\d.]+)\s*(?:thousand|k)\b', text)
    if thousand_match:
        return float(thousand_match.group(1)) * 1000
    
    # Handle plain numbers with optional currency symbols
    # Require >= 100 to avoid confusing small values (like 8.5) with rates
    plain_match = re.search(r'[$\u20b9]?\s*([\d,]+\.?\d*)', text)
    if plain_match:
        val = float(plain_match.group(1).replace(',', ''))
        if val >= 100:  # Anything < 100 without a unit is likely a rate, not an amount
            return val

    return None



def normalize_rate(text: str) -> float | None:
    """
    Parse interest rate strings into float values.
    
    Examples:
        '8.5%' -> 8.5
        '9 percent' -> 9.0
        '7.25' -> 7.25
    """
    text = text.lower().strip()
    
    rate_match = re.search(r'([\d.]+)\s*(?:%|percent|per\s*cent)', text)
    if rate_match:
        return float(rate_match.group(1))
    
    # Plain number (assume it's a rate if small enough)
    try:
        val = float(text)
        if 0 < val < 50:  # Reasonable interest rate range
            return val
    except ValueError:
        pass
    
    return None


def normalize_duration(text: str) -> float | None:
    """
    Parse duration strings into years.
    
    Examples:
        '20 years' -> 20.0
        '60 months' -> 5.0
        '365 days' -> 1.0
    """
    text = text.lower().strip()
    
    years_match = re.search(r'([\d.]+)\s*(?:year|years|yr|yrs)', text)
    if years_match:
        return float(years_match.group(1))
    
    months_match = re.search(r'([\d.]+)\s*(?:month|months|mo)', text)
    if months_match:
        return float(months_match.group(1)) / 12
    
    days_match = re.search(r'([\d.]+)\s*(?:day|days)', text)
    if days_match:
        return float(days_match.group(1)) / 365
    
    return None
