# FitFindr 🛍️

A multi-tool AI agent that helps you thrift secondhand pieces and figure out how to wear them. You describe what you're after in plain language; FitFindr searches a listings dataset, suggests an outfit using clothes you already own, and writes a shareable caption for the find.

It runs as a small planning loop over three tools, passing state between them and stopping early with a helpful message when a step can't produce anything useful.

---

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file in the project root (free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

**Run the app:**
```bash
python app.py
```
Open the URL it prints (usually http://localhost:7860).

**Run the tests:**
```bash
python -m pytest tests/
```

---

## Tool Inventory

All three live in `tools.py`. Signatures match the documentation below exactly.

### `search_listings(description, size=None, max_price=None) -> list[dict]`
- **Inputs:**
  - `description` (str) — keywords for what the user wants, e.g. `"vintage graphic tee"`
  - `size` (str | None) — size to filter by; matched loosely and case-insensitively since real sizes are messy (`"S/M"`, `"XL (oversized)"`). `None` skips the filter.
  - `max_price` (float | None) — inclusive price ceiling. `None` skips the filter.
- **Output:** a list of listing dicts ranked best-match-first. Each dict has `id, title, description, category, style_tags, size, condition, price, colors, brand, platform`. Returns `[]` when nothing matches — never raises.
- **Purpose:** find candidate items to buy and pick the most relevant ones.

### `suggest_outfit(new_item, wardrobe) -> str`
- **Inputs:**
  - `new_item` (dict) — a listing dict (the item being considered)
  - `wardrobe` (dict) — `{"items": [...]}`; each item has `name, category, colors, style_tags, notes`. May be empty.
- **Output:** a string with 1–2 outfit ideas. With a wardrobe, it names specific pieces the user owns; with an empty wardrobe, it gives general styling advice for the item.
- **Purpose:** turn a found item into a wearable outfit grounded in the user's actual closet.

### `create_fit_card(outfit, new_item) -> str`
- **Inputs:**
  - `outfit` (str) — the suggestion text from `suggest_outfit`
  - `new_item` (dict) — the listing dict (for name, price, platform)
- **Output:** a 2–4 sentence casual caption. Generated at a higher temperature so it varies between runs.
- **Purpose:** produce something shareable — the kind of caption you'd actually post.

---

## How the Planning Loop Works

`run_agent(query, wardrobe)` in `agent.py` runs a short sequence with a real branch, not a fixed run of all three tools:

1. **Parse** the query into `description`, `size`, and `max_price` (regex in `_parse_query`).
2. **Search** with those parameters.
3. **Branch:** if `search_listings` returns `[]`, set `session["error"]` with a helpful message and **return early** — the LLM tools are never called on empty input.
4. Otherwise **select** the top-ranked result.
5. **Suggest** an outfit from that item + the wardrobe.
6. **Create** a fit card from the outfit + item.
7. Return the session.

The behavior genuinely changes based on what comes back: a no-results search ends the interaction after step 3, while a successful search runs all the way through. That conditional in step 3 is the planning loop.

---

## State Management

A single `session` dict (built in `_new_session`) is the source of truth for one interaction. Each step writes its output into it, and the next step reads its input from it — the user enters the query once and never re-types anything.

| Field | Set by | Read by |
|-------|--------|---------|
| `parsed` | query parser | `search_listings` |
| `search_results` | `search_listings` | branch check + selection |
| `selected_item` | top result | `suggest_outfit` **and** `create_fit_card` |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` |
| `fit_card` | `create_fit_card` | final output |
| `error` | early-return branch | checked first by the caller |

The exact dict stored in `session["selected_item"]` is the same object passed into `suggest_outfit` (verifiable with `is`), so there's no copying or re-deriving between steps.

---

## Error Handling and Fail Points

Each tool owns its failure mode — it never crashes the agent or fails silently.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match | Returns `[]`; the loop stops and tells the user what matched nothing and what to try (loosen size/price, reword). The LLM tools are not called. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice for the item instead of failing. (LLM errors fall back to a safe generic suggestion.) |
| `create_fit_card` | Outfit is empty / whitespace | Returns a descriptive error string without calling the LLM. (LLM errors fall back to a short generic caption.) |

**Concrete example from testing:** running the query `designer ballgown size XXS under $5` produces no matches. Instead of crashing or sending empty input downstream, the agent returns:

> `No listings matched "designer ballgown" (size XXS, under $5). Try loosening the size or price, or describing it differently.`

and leaves `selected_item`, `outfit_suggestion`, and `fit_card` all `None`. Confirmed via `python agent.py` and the `test_search_empty_results` test.

---

## Interaction Walkthrough

**User query:** `vintage graphic tee under $30` (with the example wardrobe selected)

**Step 1 — `search_listings`**
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why: the agent always searches first to find a real item before reasoning about it.
- Output: matching tees ranked by relevance; top result is the *Y2K Baby Tee — Butterfly Print* ($18, depop).

**Step 2 — `suggest_outfit`**
- Input: the Y2K Baby Tee dict + the example wardrobe.
- Why: with a real item selected, the agent styles it against clothes the user owns.
- Output: e.g. "Pair it with your baggy straight-leg jeans and chunky white sneakers… throw on your vintage black denim jacket."

**Step 3 — `create_fit_card`**
- Input: the outfit text + the Y2K Baby Tee dict.
- Why: to package the look as something postable.
- Output: e.g. "Just scored this adorable Y2K Baby Tee for $18 on Depop and I'm obsessed 🦋…"

**Final output to user:** all three UI panels populate — the listing, the outfit idea, and the fit card.

---

## Spec Reflection

**One way planning.md helped during implementation:**
Writing the tool specs first meant the function signatures and return shapes were settled before any code existed. When I prompted the AI to implement each tool, I pasted the spec block and the generated code matched the interface on the first try — so wiring the planning loop later was just reading and writing known session fields, not reconciling mismatched shapes.

**One divergence from my spec, and why:**
The plan said the query parser would extract size, but in practice messy real sizes (`"S/M"`, `"XL (oversized)"`) meant exact size matching threw away good results. I changed `search_listings` to match size as a case-insensitive substring instead of an exact match, which keeps relevant items that exact matching would have dropped. The interface stayed the same; only the matching logic loosened.

---

## AI Usage

**1. Implementing `search_listings`.** I gave the AI the Tool 1 block from `planning.md` (the three parameters, the ranked-list return value, and the "return `[]` on no match" failure mode) and asked it to implement the function using `load_listings()` from the data loader. Before trusting it I checked that it filtered on all three parameters and returned an empty list rather than raising. I tightened the keyword scoring so very short words don't create noise matches, and confirmed the behavior with three queries plus the pytest cases.

**2. Implementing the planning loop.** I gave the AI the architecture diagram plus the Planning Loop and State Management sections, and asked it to implement `run_agent`. I reviewed it specifically for the branch: it had to stop and set `session["error"]` on an empty search and **not** call `suggest_outfit` / `create_fit_card` on empty input. I verified this by running the no-results query and confirming `fit_card` stayed `None`, and by checking with `is` that the selected item is the exact object passed into `suggest_outfit`.
