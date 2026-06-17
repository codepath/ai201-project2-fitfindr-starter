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

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

MODEL = "llama-3.3-70b-versatile"


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _ask_llm(prompt: str, temperature: float = 0.7) -> str:
    """Send a single prompt to the LLM and return the text reply."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


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

    # Filter by price ceiling and size before scoring relevance.
    candidates = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        candidates.append(item)

    # Score each candidate by how many query keywords it matches.
    keywords = [w for w in description.lower().split() if len(w) > 2]

    scored = []
    for item in candidates:
        haystack = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item["brand"] or "",
        ]).lower()

        score = sum(1 for word in keywords if word in haystack)
        if score > 0:
            scored.append((score, item))

    # Best match first.
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
    item_line = f"{new_item['title']} ({new_item['category']}, " \
                f"colors: {', '.join(new_item['colors'])}, " \
                f"style: {', '.join(new_item['style_tags'])})"

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe — give general styling advice instead of failing.
        prompt = (
            f"A shopper just found this secondhand item: {item_line}.\n"
            "They haven't told us what's in their closet yet. In 2-3 sentences, "
            "suggest what kinds of pieces would pair well with it and what vibe "
            "it suits. Keep it friendly and practical."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {it['name']} ({it['category']})" for it in items
        )
        prompt = (
            f"A shopper just found this secondhand item: {item_line}.\n\n"
            f"Here is what's already in their closet:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that pair the new item with specific "
            "pieces from their closet (name the pieces). Keep it to a few "
            "sentences and make it sound like a stylish friend giving advice."
        )

    try:
        return _ask_llm(prompt, temperature=0.7)
    except Exception:
        return (
            "Couldn't generate an outfit suggestion right now, but this piece is "
            "versatile — try pairing it with neutral basics and your go-to shoes."
        )


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
    if not outfit or not outfit.strip():
        return "Can't make a fit card without an outfit suggestion to work from."

    prompt = (
        "Write a short, casual social-media caption (2-4 sentences) for an "
        "outfit post about a secondhand find. Sound like a real person posting "
        "their fit, not a product listing. You can use an emoji or two.\n\n"
        f"Item: {new_item['title']} — ${new_item['price']:.0f} on {new_item['platform']}\n"
        f"How they're styling it: {outfit}\n\n"
        "Mention the item name, price, and platform naturally (once each)."
    )

    try:
        # Higher temperature so captions vary for different inputs.
        return _ask_llm(prompt, temperature=1.0)
    except Exception:
        return (
            f"thrifted this {new_item['title']} off {new_item['platform']} for "
            f"${new_item['price']:.0f} and i'm obsessed ✨"
        )
