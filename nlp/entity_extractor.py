"""
Entity Extractor
=================
Loads the custom SpaCy NER model and extracts financial entities from text.

Recognized entities:
    - TICKER:    Stock ticker symbols (AAPL, TSLA, RELIANCE.NS)
    - AMOUNT:    Monetary amounts (10 lakh, $50,000)
    - RATE:      Interest rates (8.5%, 7 percent)
    - DURATION:  Time periods (20 years, 60 months)
    - CURRENCY:  Currency codes (USD, INR, EUR)
    - LOAN_TYPE: Loan categories (home loan, personal loan)

Usage:
    from nlp.entity_extractor import EntityExtractor
    extractor = EntityExtractor()
    entities = extractor.extract("Calculate EMI for 10 lakh at 8.5% for 20 years")
    # → [{"entity": "AMOUNT", "value": "10 lakh", ...}, ...]
"""

import os
import sys
import re

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings


class EntityExtractor:
    """
    Extracts financial entities from user text using a combination of
    the trained SpaCy NER model and rule-based fallback patterns.
    """

    def __init__(self):
        self.nlp = None
        self.use_model = False
        self._load_model()

    def _load_model(self):
        """Load the trained SpaCy NER model, fall back to rule-based if unavailable."""
        import spacy

        model_path = os.path.join(PROJECT_ROOT, settings.NER_MODEL_PATH)

        if os.path.exists(model_path):
            try:
                self.nlp = spacy.load(model_path)
                self.use_model = True
                print("[OK] Entity extractor loaded: SpaCy NER model")
                return
            except Exception as e:
                print(f"[WARN] Failed to load NER model: {e}. Using rule-based fallback.")

        # Fallback: load base SpaCy model for basic NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
            print("[OK] Entity extractor loaded: Rule-based fallback (en_core_web_sm)")
        except OSError:
            self.nlp = spacy.blank("en")
            print("[WARN] Entity extractor loaded: Blank model (rules only)")

    def extract(self, text: str) -> list[dict]:
        """
        Extract entities from text using model + rule-based patterns.

        Args:
            text: Raw user input string.

        Returns:
            List of entity dicts with keys:
                - "entity" (str): Entity label (TICKER, AMOUNT, etc.)
                - "value" (str): The extracted text span
                - "start" (int): Start character index
                - "end" (int): End character index
        """
        entities = []

        # 1. SpaCy model extraction
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                entities.append({
                    "entity": ent.label_,
                    "value": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char
                })

        # 2. Rule-based fallback for entities that the model might miss
        rule_entities = self._extract_by_rules(text)

        # Merge: add rule-based entities only if they don't overlap with model entities
        for rule_ent in rule_entities:
            if not self._overlaps(rule_ent, entities):
                entities.append(rule_ent)

        # 3. Post-filter: remove AMOUNT entities that are standalone year numbers
        entities = [
            e for e in entities
            if not (e["entity"] == "AMOUNT" and self._is_year(e["value"]))
        ]
        
        # 4. Normalize tickers: If the model extracts a full company name as a TICKER, convert it to the actual ticker
        COMPANY_TO_TICKER = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
            "alphabet": "GOOGL", "amazon": "AMZN", "tesla": "TSLA",
            "meta": "META", "facebook": "META", "nvidia": "NVDA",
            "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
            "hdfc": "HDFCBANK.NS", "icici": "ICICIBANK.NS", "wipro": "WIPRO.NS",
            "sbi": "SBIN.NS", "tata motors": "TATAMOTORS.NS", "itc": "ITC.NS",
            "uber": "UBER", "adobe": "ADBE", "salesforce": "CRM",
        }
        for e in entities:
            if e["entity"] == "TICKER":
                val_lower = e["value"].lower()
                if val_lower in COMPANY_TO_TICKER:
                    e["value"] = COMPANY_TO_TICKER[val_lower]

        return entities

    @staticmethod
    def _is_year(value: str) -> bool:
        """Check if a value looks like a standalone year (1900-2099)."""
        cleaned = value.strip().replace(',', '')
        try:
            num = float(cleaned)
            return 1900 <= num <= 2099 and cleaned == str(int(num))
        except (ValueError, OverflowError):
            return False

    def _extract_by_rules(self, text: str) -> list[dict]:
        """
        Rule-based entity extraction using regex patterns.
        Acts as a safety net for entities the ML model might miss.
        """
        entities = []

        # TICKER: Known-ticker lookup (case-insensitive for common tickers)
        KNOWN_TICKERS = {
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA",
            "JPM", "V", "JNJ", "WMT", "PG", "MA", "HD", "DIS", "NFLX",
            "INTC", "AMD", "CRM", "ADBE", "UBER", "XOM", "BAC", "KO", "PEP",
            "UNH", "BRK.B",
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
            "WIPRO.NS", "SBIN.NS", "BAJFINANCE.NS", "TATAMOTORS.NS", "ITC.NS",
            "LT.NS", "HCLTECH.NS",
        }
        COMPANY_TO_TICKER = {
            "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
            "alphabet": "GOOGL", "amazon": "AMZN", "tesla": "TSLA",
            "meta": "META", "facebook": "META", "nvidia": "NVDA",
            "netflix": "NFLX", "intel": "INTC", "amd": "AMD",
            "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
            "hdfc": "HDFCBANK.NS", "icici": "ICICIBANK.NS", "wipro": "WIPRO.NS",
            "sbi": "SBIN.NS", "tata motors": "TATAMOTORS.NS", "itc": "ITC.NS",
            "uber": "UBER", "adobe": "ADBE", "salesforce": "CRM",
        }
        known_tickers_lower = {t.lower(): t for t in KNOWN_TICKERS}

        # 1. Known tickers (case-insensitive word match)
        for word in re.findall(r'\b[\w.]+\b', text):
            if word.lower() in known_tickers_lower:
                ticker_val = known_tickers_lower[word.lower()]
                start = text.lower().find(word.lower())
                entities.append({
                    "entity": "TICKER",
                    "value": ticker_val,
                    "start": start,
                    "end": start + len(word)
                })

        # 2. Company names -> ticker
        text_lower = text.lower()
        for company, ticker_val in COMPANY_TO_TICKER.items():
            if company in text_lower:
                existing_tickers = {e["value"] for e in entities if e["entity"] == "TICKER"}
                if ticker_val not in existing_tickers:
                    start = text_lower.find(company)
                    entities.append({
                        "entity": "TICKER",
                        "value": ticker_val,
                        "start": start,
                        "end": start + len(company)
                    })

        # 3. Fallback: All-caps 2-5 letter words with optional .XX suffix
        ticker_pattern = r'\b([A-Z]{2,5}(?:\.[A-Z]{1,2})?)\b'
        for match in re.finditer(ticker_pattern, text):
            candidate = match.group(1)
            non_tickers = {'I', 'A', 'THE', 'AND', 'OR', 'FOR', 'IN', 'ON', 'AT',
                          'TO', 'IS', 'IT', 'OF', 'IF', 'MY', 'ME', 'AM', 'AN',
                          'DO', 'SO', 'UP', 'NO', 'HI', 'BY', 'OK', 'EMI',
                          'RBI', 'SIP', 'FD', 'RD', 'PPF', 'NPS', 'EPF',
                          'GST', 'TDS', 'NAV', 'GDP', 'IPO'}
            existing_tickers = {e["value"] for e in entities if e["entity"] == "TICKER"}
            if candidate not in non_tickers and candidate not in existing_tickers and len(candidate) >= 2:
                entities.append({
                    "entity": "TICKER",
                    "value": candidate,
                    "start": match.start(),
                    "end": match.end()
                })

        # CURRENCY: Common currency codes
        currency_code_pattern = r'\b(USD|INR|EUR|GBP|JPY|AUD|CAD|SGD|AED|CHF|SAR|KWD|NZD|THB|MYR)\b'
        for match in re.finditer(currency_code_pattern, text, re.IGNORECASE):
            entities.append({
                "entity": "CURRENCY",
                "value": match.group(1).upper(),
                "start": match.start(),
                "end": match.end()
            })

        # Map natural-language currency words to ISO codes (with typo tolerance)
        currency_word_map = {
            r'\brupp?ee?s?\b': 'INR',
            r'\brupe?s?\b': 'INR',
            r'\bindia?n?\s*rupp?ee?s?\b': 'INR',
            r'\bdoll?a?r?s?\b': 'USD',
            r'\bdoll?e?r?s?\b': 'USD',
            r'\beuro?s?\b': 'EUR',
            r'\bpounds?\b': 'GBP',
            r'\byen\b': 'JPY',
            r'\bdirhams?\b': 'AED',
        }
        for pattern, code in currency_word_map.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                candidate = {"entity": "CURRENCY", "value": code,
                             "start": match.start(), "end": match.end()}
                if not self._overlaps(candidate, entities):
                    entities.append(candidate)

        # Currency symbols -> CURRENCY entity
        symbol_map = [('\u20b9', 'INR'), ('$', 'USD')]
        for sym, code in symbol_map:
            idx = text.find(sym)
            if idx != -1:
                candidate = {"entity": "CURRENCY", "value": code,
                             "start": idx, "end": idx + len(sym)}
                if not self._overlaps(candidate, entities):
                    entities.append(candidate)

        # RATE: Percentage patterns
        rate_pattern = r'(\d+\.?\d*)\s*(?:%|percent|per\s*cent)'
        for match in re.finditer(rate_pattern, text, re.IGNORECASE):
            entities.append({
                "entity": "RATE",
                "value": match.group(0),
                "start": match.start(),
                "end": match.end()
            })

        # AMOUNT: Lakh/crore/million/billion/thousand amounts or large numbers
        amount_patterns = [
            r'(\d+\.?\d*)\s*(?:lakh|lac|lakhs|crore|crores|cr)\b',
            r'(\d+\.?\d*)\s*(?:million|mil|billion|bil|thousand)\b',
            r'(\d+\.?\d*)\s*k\b',
            r'[\u20b9$]\s*(\d[\d,]*\.?\d*)',
            r'\b(\d[\d,]*\.?\d*)\s*(?:rupees|dollars|euros|pounds)',
            # Bare integers >= 100 with no %, year, month suffix = likely an amount
            r'(?<![.\d])(\d{3,}(?:,\d{3})*)(?!\s*(?:%|percent|year|years|yr|yrs|month|months|mo|day|days))',
        ]
        for pattern in amount_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_val = match.group(0).strip()
                # Filter out 4-digit year-like numbers (1900-2099)
                try:
                    num_only = float(re.sub(r'[^\d.]', '', raw_val))
                    if 1900 <= num_only <= 2099 and raw_val == str(int(num_only)):
                        continue
                except (ValueError, OverflowError):
                    pass
                entities.append({
                    "entity": "AMOUNT",
                    "value": raw_val,
                    "start": match.start(),
                    "end": match.end()
                })

        # DURATION: Year/month patterns
        duration_pattern = r'(\d+\.?\d*)\s*(?:years?|yrs?|months?|mo|days?)\b'
        for match in re.finditer(duration_pattern, text, re.IGNORECASE):
            entities.append({
                "entity": "DURATION",
                "value": match.group(0),
                "start": match.start(),
                "end": match.end()
            })

        # LOAN_TYPE: Known loan types
        loan_patterns = [
            r'\b(home\s+loan|housing\s+loan)\b',
            r'\b(personal\s+loan)\b',
            r'\b(car\s+loan|vehicle\s+loan|auto\s+loan)\b',
            r'\b(education\s+loan|student\s+loan)\b',
            r'\b(gold\s+loan)\b',
            r'\b(loan\s+against\s+property)\b',
            r'\b(agricultural?\s+loan|farm\s+loan)\b',
        ]
        for pattern in loan_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "entity": "LOAN_TYPE",
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                })

        return entities

    def _overlaps(self, new_entity: dict, existing: list[dict]) -> bool:
        """Check if a new entity overlaps with any existing entity."""
        for ent in existing:
            if (new_entity["start"] < ent["end"] and new_entity["end"] > ent["start"]):
                return True
        return False

    def extract_as_dict(self, text: str) -> dict:
        """
        Extract entities and return as a flat dict keyed by entity label.
        For entities that appear multiple times (e.g., two CURRENCY values),
        stores the first and appends '_TO' suffix for the second.

        Example:
            "Convert 100 USD to INR" → {"AMOUNT": "100", "CURRENCY": "USD", "CURRENCY_TO": "INR"}
        """
        entities = self.extract(text)
        result = {}
        counts = {}

        for ent in entities:
            label = ent["entity"]
            count = counts.get(label, 0)
            if count == 0:
                result[label] = ent["value"]
            elif count == 1:
                result[f"{label}_TO"] = ent["value"]
            else:
                result[f"{label}_{count}"] = ent["value"]
            counts[label] = count + 1

        return result
