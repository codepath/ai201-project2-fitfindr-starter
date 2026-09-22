"""
Tests for the three FitFindr tools.

Run with:  pytest tests/

The search_listings tests run offline. The suggest_outfit / create_fit_card
tests that exercise the happy path call the live LLM, so they need a
GROQ_API_KEY in .env — they are skipped automatically if the key is missing.
"""

import os

import pytest

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

needs_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)


# ── search_listings ─────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: nothing matches -> empty list, no exception.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


# ── suggest_outfit ──────────────────────────────────────────────────────────

@needs_key
def test_suggest_outfit_empty_wardrobe():
    # Failure mode: empty wardrobe -> still returns useful advice, not "".
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


@needs_key
def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


# ── create_fit_card ─────────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    # Failure mode: empty outfit -> descriptive error string, no exception.
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert result.strip() != ""


@needs_key
def test_create_fit_card_happy_path():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = create_fit_card("Pair it with baggy jeans and sneakers.", item)
    assert isinstance(result, str)
    assert result.strip() != ""
