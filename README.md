# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

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

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

Here are the three tools my FitFindr agent uses and they match exactly with the function signatures in `tools.py`.

### Tool 1 — `search_listings(description, size, max_price)`

- **Inputs:**
  - `description` (str) — the keywords of what the user is looking for like "vintage graphic tee"
  - `size` (str or None) — the size to filter on like M/L/S, or None if the user didnt give a size
  - `max_price` (float or None) — the price ceiling when the user says under some price, or None to skip the price filter
- **Returns:** `list[dict]` — a list of the matching listing dicts sorted with the best match first, and if nothing matches it returns a empty list `[]` and does not raise.
- **Purpose:** It takes the inputs and than filters all the listings on price and size first, and than scores whatever is left by keyword overlap with the description, drops the zero score ones and than gives back the top matches.

### Tool 2 — `suggest_outfit(new_item, wardrobe)`

- **Inputs:**
  - `new_item` (dict) — the listing dict which got shortlisted by `search_listings` (the top result)
  - `wardrobe` (dict) — the user's wardrobe dict which has a `items` key with a list inside it
- **Returns:** `str` — a non empty string with one or two complete outfit ideas.
- **Purpose:** It takes the new item and the wardrobe and than asks the LLM to suggest complete outfits using the new item with the named pieces from the wardrobe. If the wardrobe is empty it doesnt crash, instead it gives general styling advice for the item.

### Tool 3 — `create_fit_card(outfit, new_item)`

- **Inputs:**
  - `outfit` (str) — the outfit suggestion string which comes out of `suggest_outfit`
  - `new_item` (dict) — the same shortlisted listing dict from `search_listings`
- **Returns:** `str` — a short 2 to 4 sentence caption you can post on Instagram or TikTok, or a error message string if the outfit is empty.
- **Purpose:** It takes the outfit and the item and than builds a casual OOTD style caption that mentions the item name, its price and the platform. I keep the temperature high here so it sounds different each time.

---

## How the Planning Loop Works

The planning loop is in `run_agent()` inside `agent.py` and it is conditional, it doesnt call all the three tools blindly.

First it parses the raw user query with regex into a `description`, `size` and `max_price`. Than it calls `search_listings` with those. **Here is the first branch** — if the search comes back as a empty list than the agent sets a error message in the session and returns right there, it does NOT go and call `suggest_outfit` with empty input. If there are results than it sets `selected_item = search_results[0]` (the top match) and moves on.

Than `suggest_outfit` runs with the `selected_item` and the `wardrobe`. The empty wardrobe case is handled inside the tool itself so the loop keeps going either way and stores the result in `outfit_suggestion`. After that `create_fit_card` runs with the `outfit_suggestion` and the same `selected_item`, and that tool guards a empty outfit on its own. At the end the loop returns the full session dict.

So the only place the loop actually stops early is the no results branch from `search_listings`.

---

## State Management

Everything for one interaction lives in one `session` dict that gets made by `_new_session()` at the start, that dict is the single source of truth and nothing is re-prompted or hardcoded between the steps.

- `search_listings` runs and its output is stored in `session["search_results"]`. If thats empty than `session["error"]` is set and the loop stops.
- If there are results than `session["selected_item"]` is set to `search_results[0]`, and this exact same dict is the one passed into both `suggest_outfit` and `create_fit_card` (I checked this with an identity test, it is the same object not a copy).
- `suggest_outfit` reads `selected_item` and `wardrobe` from the session and stores its string into `session["outfit_suggestion"]`.
- `create_fit_card` reads `outfit_suggestion` and `selected_item` from the session and stores the final string into `session["fit_card"]`.

So each tool reads what the tool before it wrote into the session, and writes its own result back, thats how the info flows from one tool to the next.

---

## Interaction Walkthrough

<!-- Walk through a complete interaction step by step: natural language query → each tool call (and why) → final fit card.
     Walk through this carefully — it's how graders follow your agent's reasoning without a live demo.
     Use a specific example — do not leave this as a template. -->

**User query:**

**Step 1 — Tool called:**
- Tool:
- Input:
- Why this tool:
- Output:

**Step 2 — Tool called:**
- Tool:
- Input:
- Why this tool:
- Output:

**Step 3 — Tool called:**
- Tool:
- Input:
- Why this tool:
- Output:

**Final output to user:**

---

## Error Handling and Fail Points

Each tool handles its own failure mode so the agent doesnt crash.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listing matches the query | Returns a empty list `[]` (no exception). The planning loop sees the empty list, sets a error message and stops, it does not call `suggest_outfit`. |
| `suggest_outfit` | The wardrobe is empty | Doesnt stop the workflow, instead it gives general styling advice for the item so it never returns a empty string or crashes. |
| `create_fit_card` | The outfit string is empty or only whitespace | Guards it and returns a error message string instead of calling the LLM or crashing. |

**A concrete example from my testing:** I ran the query `"designer ballgown size XXS under $5"` (the no results test case in `agent.py`). `search_listings` returned `[]`, so the agent set `session["error"]` to "No listings found matching that search..." and `session["fit_card"]` stayed `None`. I also confirmed with a spy that `suggest_outfit` was called **0 times** on this path, which proves the loop didnt try to keep going with empty input. For `create_fit_card` I passed in `"   "` and it gave back the error string starting with "Error: cannot create a fit card..." instead of throwing.

---

## Spec Reflection

**One way planning.md helped during implementation:**
The Planning Loop and State Management sections really helped because I had already written down the exact branching before any code, so when I built `run_agent` I just followed it step by step. The part where I wrote "if results is empty set a error and return early, do not call suggest_outfit with empty input" turned straight into the first branch in the code, so I didnt have to figure out the control flow while coding, it was already decided.

**One divergence from your spec, and why:**
In my spec I first wrote that if the wardrobe is empty than the agent should set a error and stop the workflow. But while implementing I diverged from that, because the app gives the user a "Empty wardrobe (new user)" option, so if I stopped on empty wardrobe that option would always just show a error and never reach a fit card. So instead I made `suggest_outfit` handle the empty wardrobe by giving general styling advice and the loop keeps going, and than I updated planning.md to match this new behaviour.

---

## AI Usage

**Instance 1 — implementing the three tools:**
I directed the AI to implement the three tool stubs in `tools.py` using the specs from my planning.md, one tool at a time. For `search_listings` it gave me a keyword scoring approach which I kept. But I overrode the empty wardrobe behaviour for `suggest_outfit` — the AI first followed my planning.md which said make it a error, and I told it no, it should not crash and should give general advice instead, so we changed both the code and the spec to match.

**Instance 2 — wiring the planning loop and checking state:**
I directed the AI to implement `run_agent` and I specifically told it I wanted to review it before running, because I wanted to confirm it branches on the search result, stores values in the session dict, and does not call all three tools unconditionally. To verify the state was actually flowing and not getting re-prompted or hardcoded, I had it run a test with spies that checked the `selected_item` going into `suggest_outfit` and `create_fit_card` is the exact same object, and that `suggest_outfit` is called 0 times on the no results path. Both checks passed so I accepted it.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
