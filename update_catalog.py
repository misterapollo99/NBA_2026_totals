"""Merge catalog updates, normalize colors, adjust prices, and write three CSV outputs.

Inputs (data/): catalog.csv, updates.tsv, color_map.json
Outputs (output/): updated_catalog.csv, product_detail_only.csv, colors_summary.csv

Assumptions:
1. Every field is read as text, so ids like "123" or "0042" are never coerced and blanks
   stay as empty strings. Ids are stripped of surrounding whitespace before the join.
2. Updates are left-joined onto the catalog by id. Catalog rows without updates are kept.
   Update ids missing from the catalog are ignored with a note. A duplicate update id is
   an error, because applying two price changes to one SKU silently would be worse.
3. Color tokens are split on commas, stripped, and lowercased. Empty tokens are dropped.
4. Added colors are combined with the catalog colors first, then removals are applied, so
   a color that is both added and removed for one SKU ends up removed.
5. Removals match the raw synonym token before canonicalization. Removing "crimson" drops
   only "crimson", not "red", even though both map to Red.
6. A token missing from color_map.json falls back to title case and is reported on stderr.
7. price_adjust is a percentage such as "10%", "+10%" or "-5%". Blank means no change.
   An unparseable value is an error naming the SKU rather than a silent pass-through.
8. Prices use Decimal with ROUND_HALF_UP and are always written with two decimals
   (19 becomes 19.00). A blank catalog price stays blank.
9. updated_catalog.csv keeps the original columns in order: price is replaced in place and
   product_detail is appended. color_list is left as the original input; normalized colors
   are in product_detail.
10. A product with no colors left gets an empty product_detail and is not counted in
    colors_summary.csv, which counts distinct SKUs per final color, sorted by color.
"""

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

DATA = Path("data")
OUTPUT = Path("output")
PREFIX = "Lily Attributes:Color:"
CENTS = Decimal("0.01")
ADJUST_PATTERN = re.compile(r"^([+-]?)\s*(\d+(?:\.\d+)?)\s*%?$")


def parse_colors(text: str) -> list[str]:
    return [token.strip().lower() for token in text.split(",") if token.strip()]


def apply_removals(tokens: list[str], remove_text: str) -> list[str]:
    removed = set(parse_colors(remove_text))
    return [token for token in tokens if token not in removed]


def canonicalize(tokens: list[str], color_map: dict[str, str]) -> list[str]:
    return sorted({color_map.get(token, token.title()) for token in tokens})


def unmapped(tokens: list[str], color_map: dict[str, str]) -> list[str]:
    return [token for token in tokens if token not in color_map]


def adjust_price(price: str, adjust: str) -> str:
    price, adjust = price.strip(), adjust.strip()
    if not price:
        return ""
    amount = Decimal(price)
    if adjust:
        match = ADJUST_PATTERN.match(adjust)
        if not match:
            raise ValueError(f"unparseable price_adjust {adjust!r}")
        sign, percent = match.groups()
        factor = Decimal(percent) / 100 * (-1 if sign == "-" else 1)
        amount *= 1 + factor
    return str(amount.quantize(CENTS, rounding=ROUND_HALF_UP))


def build_product_detail(colors: list[str]) -> str:
    return ",".join(PREFIX + color for color in colors)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    catalog = pd.read_csv(DATA / "catalog.csv", dtype=str, keep_default_na=False)
    updates = pd.read_csv(DATA / "updates.tsv", sep="\t", dtype=str, keep_default_na=False)
    with open(DATA / "color_map.json", encoding="utf-8") as f:
        # Normalize keys the same way as tokens so a messy map still matches.
        color_map = {k.strip().lower(): v.strip() for k, v in json.load(f).items()}
    catalog["id"] = catalog["id"].str.strip()
    updates["id"] = updates["id"].str.strip()
    return catalog, updates, color_map


def main() -> None:
    catalog, updates, color_map = load_inputs()

    orphans = sorted(set(updates["id"]) - set(catalog["id"]))
    if orphans:
        print(f"note: ignoring updates for ids not in catalog: {orphans}", file=sys.stderr)

    merged = catalog.merge(updates, on="id", how="left", validate="many_to_one")
    # Catalog rows without an update come back as NaN after a left join.
    merged = merged.fillna("")

    final_colors, prices = [], []
    for row in merged.itertuples(index=False):
        tokens = parse_colors(row.color_list) + parse_colors(row.color_list_add)
        tokens = apply_removals(tokens, row.remove_colors)
        for token in unmapped(tokens, color_map):
            print(f"note: {row.id}: color {token!r} not in map, using title case", file=sys.stderr)
        final_colors.append(canonicalize(tokens, color_map))
        try:
            prices.append(adjust_price(row.price, row.price_adjust))
        except ValueError as err:
            raise ValueError(f"id {row.id}: {err}") from err

    updated = catalog.copy()
    updated["price"] = prices
    updated["product_detail"] = [build_product_detail(colors) for colors in final_colors]

    summary = (
        pd.DataFrame({"id": updated["id"], "color": final_colors})
        .explode("color")
        .dropna(subset=["color"])
        .groupby("color")["id"]
        .nunique()
        .reset_index(name="count")
        .sort_values("color")
    )

    OUTPUT.mkdir(exist_ok=True)
    csv_options = {"index": False, "encoding": "utf-8", "lineterminator": "\n"}
    updated.to_csv(OUTPUT / "updated_catalog.csv", **csv_options)
    updated[["id", "product_detail"]].to_csv(OUTPUT / "product_detail_only.csv", **csv_options)
    summary.to_csv(OUTPUT / "colors_summary.csv", **csv_options)
    print(f"wrote {len(updated)} products and {len(summary)} colors to {OUTPUT}/")


if __name__ == "__main__":
    main()
