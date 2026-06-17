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
It takes input as "description size maxprice " and using those inputs and than filters the serach based on the availability and than collects the top result and if it does not find the serach it stops and does not calls the tool suggest_outfit.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): it represents the quailty of the garment like how old it is , if there is any wear and tear and so on.
- `size` (str): It takes the size like M/L/S and others
- `max_price` (float): If the user inputs i want a garment under some particular price it sets that as max price.

**What it returns:**
It returns 3 matching listing based on evalution and than the model chooses the best and closest.

**What happens if it fails or returns nothing:**
If there is no finding it should suggest user that it did not find it and find other outfit.

---

### Tool 2: suggest_outfit

**What it does:**
This tool takes the new item which is filters and got out and seraches with the user's wardrobe and than suggest one or more complete outfit combination.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): item which is suggested and filtered by the serach_listings tool
- `wardrobe` (dict): checking what is inside the wardrobe than matching with the new item the one which matches 

**What it returns:**
It provides the complete outfit based on the new and wardrobe outfit.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, this is NOT a hard error — the tool still returns general styling advice for the new item (vibe, what pairs well), and the workflow continues to create_fit_card. It never returns an empty string or crashes.

---

### Tool 3: create_fit_card

**What it does:**
Using the input which is suggested outfit and from suggest_outfit and new item which we shortlisted in first tool it creates a card with Instagram like caption and shares that output with the user.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): output from the suggest_outfittool
- `new_item` (dict): new item which is selected by the serach_listings tool

**What it returns:**
It returns a short, shareable description of a complete outfit which is created by the create_fit_card tool.

**What happens if it fails or returns nothing:**
The agent should evealuate and tell the user no outfit matched or the outfit did not go with a fit.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
After search_listings runs, check if results is empty. If yes, set an error message in the session and return early. If no, set selected_item = results[0] and proceed to suggest_outfit

Than if there is output from serach_listings go than the suggest_outfit tool runs whre input will be selected_item and wardrobe. suggest the output in outfit_suggestion based on both the inputs and move to create_fit_card. If the wardrobe is empty, this is NOT an early-exit error: suggest_outfit returns general styling advice for the item and the loop continues to create_fit_card normally.

In create_fit_card tool the output outfit_suggestion will be input and the selected_item . Then the tool should combine and provide a string as an output which describes the outfit with its price and based on the outfit suggesion as an caption.Also if the outfit suggestion is incomplete or empty set an error message in session and return early. 

If search_listings returns nothing, FitFindr tells the user what to try differently and stops it does not call suggest_outfit with empty input.

---

## State Management

**How does information from one tool get passed to the next?**
`search_listings` first runs and stores its output in `results`. If `results` is empty, the agent stores an `error_message` in the session telling the user to try a different search and stops the workflow. It does not call `suggest_outfit` with empty input.

If listings are found, the agent sets `selected_item = results[0]` and moves to `suggest_outfit`.

`suggest_outfit` uses `selected_item` and `wardrobe` from the session as inputs. If `wardrobe` is empty, it does NOT stop the workflow — it generates general styling advice for the item instead. Either way it stores the result in `outfit_suggestion` and proceeds to `create_fit_card`.

**Query parsing (Step 2):** `run_agent` parses the raw query with regex (in `_parse_query`). It pulls `max_price` from patterns like "under $30" / "under 30" / "$30", `size` from "size M" / "size 8", and uses the remaining text (with those phrases stripped) as the `description`.

`create_fit_card` takes `selected_item` and `outfit_suggestion` from the session. If `outfit_suggestion` is empty or incomplete, it stores an `error_message` and returns early. Otherwise, it combines the selected item's details, including its price, with the outfit suggestion to generate the final fit card description and caption for the user.


---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool             | Failure mode                       | Agent response                                                                                           |
|------------------|------------------------------------|------------------------------------------------------------------------------------------------------------|
| search_listings  | No results match the query         | Set an error message in the session, tell the user to try a different search, and stop the workflow.    |
| suggest_outfit   | Wardrobe is empty                  | NOT a stop condition — return general styling advice for the item and continue the workflow.            |
| create_fit_card  | Outfit input is missing or incomplete | Set an error message in the session and stop the workflow without creating the fit card.              |

---

## Architecture

User Input
    │
    ▼
Planning Loop ───────────────────────────────────────────────────────────┐
    │                                                                    │
    ├─► search_listings(description, size, max_price)                    │
    │       │                                                            │
    │   Session: results = [...]                                         │
    │       │                                                            │
    │       │ results = []                                               │
    │       ├──► [ERROR] Set error_message =                             │
    │       │      "No listings found. Try different search criteria."   │
    │       │      Return early and stop workflow                        │
    │       │                                                            │
    │       │ results = [item, ...]                                      │
    │       ▼                                                            │
    │   Session: selected_item = results[0]                              │
    │       │                                                            │
    ├─► suggest_outfit(selected_item, wardrobe)                          │
    │       │                                                            │
    │       │ wardrobe = empty → general styling advice (NOT an error)   │
    │       │ wardrobe = filled → specific outfit combinations           │
    │       ▼                                                            │
    │   Session: outfit_suggestion = "..."                               │
    │       │                                                            │
    └─► create_fit_card(outfit_suggestion, selected_item)                │
            │                                                            │
            │ outfit_suggestion is empty or incomplete                   │
            ├──► [ERROR] Set error_message =                             │
            │      "Outfit suggestion is incomplete."                    │
            │      Return early and stop workflow                        │
            │                                                            │
            ▼                                                            │
        Session: fit_card =                                               │
        "Outfit description + item price + caption"                      │
            │                                                            └─ Error paths return here
            ▼
        Return Session / Final Response

---

## AI Tool Plan

I will first use Claude Code to understand the project structure, existing files, and how the provided utilities and data loaders are set up and intended to be used. Based on that understanding, I will create my `planning.md` file describing the workflow, tool inputs and outputs, session state, and error handling.

After completing `planning.md`, I will use ChatGPT to generate the ASCII architecture diagram showing the Planning Loop, tools, state/session flow, and error branches.

Next, I will implement each tool one by one using Claude Code. For `search_listings`, I will provide Claude with the Tool 1 specification from `planning.md` including its inputs, outputs, and failure modes, and ask it to implement the function using the appropriate data loader. Before accepting the generated code, I will verify that it filters listings correctly and handles the empty-results case as specified. I will then test it using multiple search queries.

I will repeat the same process for `suggest_outfit` by providing the corresponding section from `planning.md`. I will ensure that it uses `selected_item` and `wardrobe` correctly, stores the generated `outfit_suggestion` in the session, and properly handles the case where the wardrobe is empty. I will test both successful and failure scenarios.

I will then implement `create_fit_card` using its specification from `planning.md`. I will verify that it combines `selected_item` and `outfit_suggestion` to generate the final fit card containing the outfit description, price information, and caption. I will also check that it returns early with an appropriate error message when the outfit suggestion is missing or incomplete.

Finally, I will integrate all tools into the complete agent workflow, test the end-to-end execution path, validate that session state is passed correctly between tools, and confirm that all defined error paths behave according to the plan documented in `planning.md`.


**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
So the Agent First calls the using the search_listings tool and using inputs as one of this "id, title, description, category, style_tags, size, condition, price, colors, brand" and than filters the serach based on the availability and than collects the top result and if it does not find the serach it stops and does not calls the tool search_listings

**Step 2:**
The new tool takes the new item which is filters and got out and seraches with the user's wardrobe and than suggest one or more complete outfit combination.

**Step 3:**
Using the input which is suggested outfit and  from suggest_outfit and new item which we shortlisted in first tool it creates a card with Instagram like caption and shares that output with the user.

**Final output to user:**
The user see a card with new outfit as suggested by FitFindr matched with outfit in the wardrobe with a catchy captions.
