# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for items matching the user's description, with optional size and price filters. Returns the best matches first.

**Input parameters:**
- `description` (str): keywords describing what the user wants, e.g. "vintage graphic tee".
- `size` (str | None): size to filter by, e.g. "M". Matched loosely and case-insensitively since sizes in the data are messy ("S/M", "XL (oversized)"). None skips the filter.
- `max_price` (float | None): price ceiling, inclusive. None skips the filter.

**What it returns:**
A list of listing dicts, best match first. Each dict has: `id, title, description, category, style_tags, size, condition, price, colors, brand, platform`. Returns an empty list `[]` if nothing matches — never raises.

**What happens if it fails or returns nothing:**
Returns `[]`. The planning loop catches the empty list, sets an error message telling the user what to try (loosen size/price or use different words), and stops before calling the other tools.

---

### Tool 2: suggest_outfit

**What it does:**
Takes a found item and the user's wardrobe and asks the LLM for 1–2 outfit combinations using pieces the user already owns.

**Input parameters:**
- `new_item` (dict): the listing the user is considering (from `search_listings`).
- `wardrobe` (dict): `{"items": [...]}`, each item has `name, category, colors, style_tags, notes`. May be empty.

**What it returns:**
A short string with 1–2 outfit ideas. If the wardrobe is empty, it returns general styling advice for the item instead (what to pair it with, what vibe it fits) so it's still useful.

**What happens if it fails or returns nothing:**
Empty wardrobe → general advice (still a valid non-empty string). If the LLM call errors, it returns a plain fallback string so the agent keeps going instead of crashing.

---

### Tool 3: create_fit_card

**What it does:**
Turns the item + outfit into a short, casual caption you could actually post — like an OOTD/Instagram caption, not a product description.

**Input parameters:**
- `outfit` (str): the outfit suggestion from `suggest_outfit`.
- `new_item` (dict): the listing dict, used to mention the item name, price, and platform.

**What it returns:**
A 2–4 sentence caption string. Uses a higher temperature so it sounds different each time for different inputs.

**What happens if it fails or returns nothing:**
If `outfit` is empty or just whitespace, it returns a descriptive error string instead of calling the LLM — no exception.

---

### Additional Tools (if any)

None for the required build. (Possible stretch: a `compare_price` tool that checks an item's price against similar listings.)

---

## Planning Loop

**How does your agent decide which tool to call next?**

It's a short sequence with branches, not a fixed run of all three tools:

1. Parse the query into `description`, `size`, `max_price` and save to `session["parsed"]`.
2. Call `search_listings`. **If results are empty → set `session["error"]` and stop. Don't call the other tools.**
3. Otherwise pick the top result as `session["selected_item"]` and call `suggest_outfit` with it + the wardrobe.
4. Call `create_fit_card` with the outfit suggestion + selected item.
5. Return the session.

The branch in step 2 is what makes it a real planning loop — a no-results search ends the run early, so the agent behaves differently depending on what comes back.

---

## State Management

**How does information from one tool get passed to the next?**

A single `session` dict is the source of truth for the whole interaction. Each step writes its output into it, and the next step reads from it — the user never re-enters anything.

- `parsed` → description/size/max_price from the query
- `search_results` → list from `search_listings`
- `selected_item` → the top result, passed into `suggest_outfit` **and** `create_fit_card`
- `outfit_suggestion` → string from `suggest_outfit`, passed into `create_fit_card`
- `fit_card` → final caption
- `error` → set only if the run ended early; checked first by the caller

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns `[]`; the loop stops and tells the user: "No listings matched. Try loosening the size or price, or describing it differently." Does not call the next tools. |
| suggest_outfit | Wardrobe is empty | Gives general styling advice for the item instead of crashing or returning nothing. |
| create_fit_card | Outfit input is missing or incomplete | Returns a clear error string ("Can't make a fit card without an outfit") instead of raising. |

---

## Architecture

```
User query
    │
    ▼
Planning Loop (run_agent)
    │
    ├─ parse query → session["parsed"]
    │
    ├─► search_listings(description, size, max_price)
    │       │ results == []
    │       ├──► session["error"] = "No listings found..." → RETURN early
    │       │
    │       │ results == [item, ...]
    │       ▼
    │   session["selected_item"] = results[0]
    │       │
    ├─► suggest_outfit(selected_item, wardrobe)
    │       │
    │   session["outfit_suggestion"] = "..."
    │       │
    └─► create_fit_card(outfit_suggestion, selected_item)
            │
        session["fit_card"] = "..."
            │
            ▼
        Return session  ◄── error path also returns here
```

State (`session` dict) is read/written at every step and returned at the end.

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I'll use Claude. For each tool I'll paste that tool's block above (inputs, return value, failure mode) one at a time and ask it to implement the function in `tools.py` using `load_listings()` from the data loader. Before trusting each one I'll check it filters on all the params I defined, handles the failure mode (empty list / empty wardrobe / empty outfit), and matches the exact signature. Then I'll run it on 3 queries.

**Milestone 4 — Planning loop and state management:**
I'll give Claude the diagram above plus the Planning Loop and State Management sections, and ask it to implement `run_agent()`. I'll verify it branches on the `search_listings` result (stops early on empty), writes each output into the `session` dict, and does **not** call all three tools unconditionally before running it.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
Parse the query → `description="vintage graphic tee"`, `size=None`, `max_price=30.0`. Call `search_listings("vintage graphic tee", None, 30.0)`. It returns matching tees sorted by relevance; the top one is the bootleg graphic tee ($24, depop).

**Step 2:**
Save that as `selected_item`. Call `suggest_outfit(selected_item, wardrobe)`. Using the example wardrobe (baggy jeans, chunky sneakers, denim jacket…), the LLM returns something like: "Wear it with your baggy straight-leg jeans and chunky white sneakers, layer the black denim jacket on top for a 90s grunge look."

**Step 3:**
Call `create_fit_card(outfit_suggestion, selected_item)`. It returns a caption like: "found this faded bootleg tee on depop for $24 🖤 throwing it on with my baggy jeans + chunky sneakers, full grunge mode."

**Final output to user:**
The top listing, the outfit idea, and the fit card caption — all three panels filled in.
