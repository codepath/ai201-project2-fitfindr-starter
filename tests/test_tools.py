"""
Tests for the three FitFindr tools in tools.py.

At least one test per failure mode:
- search_listings: results found / empty results / price filter (pure Python).
- suggest_outfit: empty-wardrobe path returns a non-empty string (calls the LLM).
- create_fit_card: empty-outfit guard returns an error string (no LLM call).

The LLM-dependent tests are skipped automatically when GROQ_API_KEY is missing,
is the placeholder, or the key is rejected — so the suite passes offline too.
"""

import os

import pytest
from dotenv import load_dotenv

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

load_dotenv()


def _has_real_api_key() -> bool:
    key = os.environ.get("GROQ_API_KEY", "")
    return key.startswith("gsk_")


requires_api = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="No real GROQ_API_KEY set (placeholder or missing) — skipping LLM call.",
)


# ── Tool 1: search_listings (pure Python, no API needed) ────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Impossible query → empty list, no exception (failure mode).
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter_case_insensitive():
    # "m" should match sizes like "S/M" or "M" regardless of case.
    results = search_listings("shirt", size="m", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


# ── Tool 2: suggest_outfit (calls the LLM) ──────────────────────────────────────

@requires_api
def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", None, 50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


@requires_api
def test_suggest_outfit_empty_wardrobe_does_not_crash():
    # Failure mode: empty wardrobe must return general advice, not crash/empty.
    item = search_listings("vintage graphic tee", None, 50)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


# ── Tool 3: create_fit_card ─────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit_returns_error_string():
    # Failure mode: empty/whitespace outfit → error string, no exception, no LLM call.
    item = search_listings("vintage graphic tee", None, 50)[0]
    result = create_fit_card("   ", item)
    assert isinstance(result, str)
    assert result.lower().startswith("error")


def test_create_fit_card_none_outfit_returns_error_string():
    item = search_listings("vintage graphic tee", None, 50)[0]
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert "error" in result.lower()


@requires_api
def test_create_fit_card_varies_on_repeat():
    # High temperature → repeated calls on the same input should differ.
    item = search_listings("vintage graphic tee", None, 50)[0]
    outfit = "Paired with baggy jeans and chunky white sneakers."
    cards = {create_fit_card(outfit, item) for _ in range(3)}
    assert len(cards) > 1, "Captions were identical — raise the LLM temperature."
