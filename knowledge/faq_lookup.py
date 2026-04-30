"""
FAQ Knowledge Base Lookup
==========================
TF-IDF similarity-based FAQ matching against the static knowledge base.

Usage:
    from knowledge.faq_lookup import find_best_faq
    answer = find_best_faq("What is a savings account?")
"""

import json
import os
import sys

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class FAQLookup:
    """
    Matches user queries to the closest FAQ using TF-IDF cosine similarity.
    Loaded once as a singleton for efficiency.
    """

    def __init__(self, faq_path: str = None):
        if faq_path is None:
            faq_path = os.path.join(PROJECT_ROOT, 'data', 'faq_knowledge_base.json')

        with open(faq_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.faqs = data['faqs']
        self.questions = [faq['question'] for faq in self.faqs]

        # Also include tags in the matching corpus for better recall
        self.corpus = []
        for faq in self.faqs:
            combined = faq['question'] + ' ' + ' '.join(faq.get('tags', []))
            self.corpus.append(combined)

        # Build TF-IDF matrix
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            max_features=3000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        print(f"[OK] FAQ knowledge base loaded: {len(self.faqs)} FAQs")

    def find_best_match(self, query: str, threshold: float = 0.35) -> dict:
        """
        Find the best matching FAQ for a given query.

        Args:
            query: User's question
            threshold: Minimum similarity score to consider a match

        Returns:
            dict with keys: answer, question, similarity, matched
        """
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        best_idx = similarities.argmax()
        best_score = similarities[best_idx]

        if best_score >= threshold:
            return {
                "answer": self.faqs[best_idx]['answer'],
                "question": self.faqs[best_idx]['question'],
                "category": self.faqs[best_idx].get('category', ''),
                "similarity": float(best_score),
                "matched": True
            }

        return {
            "answer": (
                "I don't have a specific answer for that in my knowledge base. "
                "Could you rephrase, or ask about loans, EMI calculations, "
                "stock prices, or banking topics?"
            ),
            "question": query,
            "category": "",
            "similarity": float(best_score),
            "matched": False
        }


# ---- Module-level singleton ----
_faq_instance: FAQLookup | None = None


def find_best_faq(query: str) -> str:
    """
    Public function: find the best FAQ match and return the answer string.

    Args:
        query: User's question

    Returns:
        Answer string
    """
    global _faq_instance
    if _faq_instance is None:
        _faq_instance = FAQLookup()
    result = _faq_instance.find_best_match(query)
    return result['answer']


def find_best_faq_detailed(query: str) -> dict:
    """
    Public function: find the best FAQ match and return full details.

    Args:
        query: User's question

    Returns:
        dict with answer, matched question, similarity score, match status
    """
    global _faq_instance
    if _faq_instance is None:
        _faq_instance = FAQLookup()
    return _faq_instance.find_best_match(query)
