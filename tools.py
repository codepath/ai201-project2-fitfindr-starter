"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

_MODEL = "llama-3.3-70b-versatile"


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _call_llm(prompt: str, temperature: float = 0.7) -> str:
    """Send a single user prompt to the LLM and return the text response."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# Common words that carry no search signal — ignored when scoring keyword overlap.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "under", "over", "in", "on",
    "of", "to", "i", "am", "is", "are", "want", "looking", "like", "some",
    "my", "me", "that", "this", "it", "at", "by",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase a string and split it into alphanumeric word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # 1. Filter by max_price and size (when provided).
    candidates = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.strip().lower() not in item["size"].lower():
            continue
        candidates.append(item)

    # 2. Tokenize the query, dropping punctuation and stopwords.
    query_tokens = {
        tok
        for tok in _tokenize(description)
        if tok not in _STOPWORDS
    }

    # 3. Score each candidate by how many query tokens appear in its text.
    scored = []
    for item in candidates:
        blob = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            " ".join(item.get("style_tags", [])),
            " ".join(item.get("colors", [])),
            item.get("brand") or "",
        ]).lower()
        blob_tokens = set(_tokenize(blob))
        score = len(query_tokens & blob_tokens)
        if score > 0:  # 4. Drop listings with no relevant matches.
            scored.append((score, item))

    # 5. Sort by score, highest first, and return the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    item_line = (
        f"{new_item.get('title', 'an item')} "
        f"(category: {new_item.get('category', 'unknown')}, "
        f"colors: {', '.join(new_item.get('colors', [])) or 'unspecified'}, "
        f"style: {', '.join(new_item.get('style_tags', [])) or 'unspecified'})"
    )

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe: give general styling advice rather than crashing.
        prompt = (
            "You are a thrift-fashion stylist. A shopper is considering buying "
            f"this item:\n  {item_line}\n\n"
            "They haven't told you anything about their existing wardrobe. "
            "Give general styling advice: describe the vibe this piece suits, what "
            "kinds of items (tops, bottoms, shoes, accessories) pair well with it, "
            "and one or two outfit directions they could build around it. "
            "Keep it friendly and concise (under 150 words)."
        )
        return _call_llm(prompt, temperature=0.7)

    # Non-empty wardrobe: ask for specific combinations using named pieces.
    wardrobe_lines = "\n".join(
        f"  - {w.get('name', 'item')} "
        f"(category: {w.get('category', 'unknown')}, "
        f"colors: {', '.join(w.get('colors', [])) or 'unspecified'})"
        for w in items
    )
    prompt = (
        "You are a thrift-fashion stylist. A shopper is considering buying "
        f"this item:\n  {item_line}\n\n"
        f"Here is their existing wardrobe:\n{wardrobe_lines}\n\n"
        "Suggest 1-2 complete outfits that combine the new item with specific, "
        "named pieces from their wardrobe. Reference the wardrobe items by name. "
        "For each outfit, briefly explain why it works. Keep it concise."
    )
    return _call_llm(prompt, temperature=0.7)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against a missing / empty / whitespace-only outfit string.
    if not outfit or not outfit.strip():
        return (
            "Error: cannot create a fit card without an outfit suggestion. "
            "Run suggest_outfit first to generate one."
        )

    # 2. Build the caption prompt with the item's details and the outfit.
    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a resale app")
    prompt = (
        "Write a short, shareable Instagram/TikTok-style outfit caption (an OOTD "
        "post) for a thrifted find. Make it 2-4 sentences, casual and authentic — "
        "NOT a product description. Capture the outfit's vibe in specific terms.\n\n"
        f"Item: {title}\n"
        f"Price: ${price}\n"
        f"Platform: {platform}\n"
        f"Outfit it's styled in: {outfit}\n\n"
        f"Mention the item name, the ${price} price, and that it's from {platform} "
        "naturally — once each. Return only the caption text."
    )

    # 3. Higher temperature so repeated calls on the same input read differently.
    return _call_llm(prompt, temperature=1.0)
