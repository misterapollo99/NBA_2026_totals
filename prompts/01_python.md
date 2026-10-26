# Prompt 1: Python catalog merge

Start a fresh Claude Code session in plan mode (Shift+Tab until it shows plan mode), then paste everything below the line.

---

<context>
I'm completing the Python part of a take-home assessment for a Solutions Engineer role at Lily.ai. Instructions are in docs/assessment.pdf (the "Python Test" section). Inputs are in data/: catalog.csv, updates.tsv, color_map.json. Project conventions are in CLAUDE.md.

Reviewers judge correctness, readability, robustness to messy data, and how clearly assumptions are stated. I will explain and defend this code in an interview, so clarity beats cleverness.
</context>

<instructions>
Before writing code, read the three input files and the PDF, then show me a plan listing every ambiguity you find and the assumption you propose for each. Wait for my approval.

Then build update_catalog.py at the repo root, a single pandas script that:

1. Reads inputs with id as text (dtype=str, keep_default_na=False) so ids like "123" and "B001" are never coerced and blanks never become NaN.
2. Left-joins updates onto catalog by id so catalog rows without updates are kept.
3. Builds the final color list per product in this exact order:
   a. Split catalog.color_list and updates.color_list_add on commas; strip whitespace; lowercase; drop empty tokens.
   b. Remove tokens listed in updates.remove_colors, matching case-insensitively on the RAW synonym token, before canonicalization.
   c. Canonicalize remaining tokens with color_map.json. For a token missing from the map, fall back to title case and note it.
   d. De-duplicate and sort alphabetically.
   Why b before c: canonicalizing first would make removing "crimson" also remove "red" (both map to Red), leaving several products with no colors.
4. Adjusts price when price_adjust is present. Values look like "10%", "-5%", "-20%" or blank. Use Decimal with ROUND_HALF_UP and always format to two decimals (19 becomes "19.00").
5. Builds product_detail as "Lily Attributes:Color:<Color>" triplets joined by commas, no spaces after colons. Empty color list gives an empty string.
6. Writes to output/:
   - updated_catalog.csv: original catalog columns with price replaced by the updated price, plus product_detail.
   - product_detail_only.csv: id, product_detail.
   - colors_summary.csv: color, count (distinct SKUs per final color), sorted by color.

Code style: small named pure functions (parse_colors, apply_removals, canonicalize, adjust_price, build_product_detail) and a main(). Module docstring lists every assumption in plain English. Target under about 120 lines.
</instructions>

<verification>
When the script runs, invoke /check-takehome and show me its pass/fail table. Expected results it checks:
- 123: Black, Gray | 98.99
- A-7789: Blue | 56.53
- B001: White | 19.00
- SKU-5: Green | 103.20
- 9Z9Z: Red | 12.99
- ABC12: Beige | 40.19
- X-0007: Black | 22.00
- FLEX9: Blue | 39.00
- LT-42: Gray | 65.00
- BY-88: Silver | 25.92
- colors_summary: Beige 1, Black 2, Blue 2, Gray 2, Green 1, Red 1, Silver 1, White 1

If anything fails, explain why before changing code. Never change the expected values.
</verification>

<deliverable>
Commit the working script and outputs. Then give me: the file list, a 3 to 5 bullet summary of assumptions for the README, and anything a reviewer might push back on.
</deliverable>
