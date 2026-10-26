"""Acceptance checks for the Lily.ai take-home.

Expected values were computed by hand from the input files before any code
was written. Run from the project root. Exits non-zero if any check fails.
"""

import csv
import sqlite3
import sys
from pathlib import Path

OUTPUT = Path("output")
DB = Path("sql/nba.db")

EXPECTED = {
    "123": (["Black", "Gray"], "98.99"),
    "A-7789": (["Blue"], "56.53"),
    "B001": (["White"], "19.00"),
    "SKU-5": (["Green"], "103.20"),
    "9Z9Z": (["Red"], "12.99"),
    "ABC12": (["Beige"], "40.19"),
    "X-0007": (["Black"], "22.00"),
    "FLEX9": (["Blue"], "39.00"),
    "LT-42": (["Gray"], "65.00"),
    "BY-88": (["Silver"], "25.92"),
}
EXPECTED_SUMMARY = {
    "Beige": 1,
    "Black": 2,
    "Blue": 2,
    "Gray": 2,
    "Green": 1,
    "Red": 1,
    "Silver": 1,
    "White": 1,
}
PREFIX = "Lily Attributes:Color:"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def detail_for(colors: list[str]) -> str:
    return ",".join(PREFIX + c for c in colors)


def check_python_outputs() -> None:
    files = ["updated_catalog.csv", "product_detail_only.csv", "colors_summary.csv"]
    for name in files:
        check(f"{name} exists", (OUTPUT / name).exists())
    if not all((OUTPUT / n).exists() for n in files):
        return

    catalog = {r["id"]: r for r in read_csv(OUTPUT / "updated_catalog.csv")}
    check("ids preserved as text", set(catalog) == set(EXPECTED), f"got {sorted(catalog)}")

    required_cols = {"id", "title", "price", "color_list", "description", "product_detail"}
    cols = set(next(iter(catalog.values()), {}).keys())
    check("updated_catalog columns", required_cols <= cols, f"missing {required_cols - cols}")

    for sku, (colors, price) in EXPECTED.items():
        row = catalog.get(sku)
        if row is None:
            check(f"{sku} present", False)
            continue
        check(f"{sku} price", row["price"] == price, f"expected {price}, got {row['price']}")
        want = detail_for(colors)
        got = row.get("product_detail", "")
        check(f"{sku} product_detail", got == want, f"expected {want!r}, got {got!r}")

    detail_only = read_csv(OUTPUT / "product_detail_only.csv")
    check(
        "product_detail_only columns",
        list(detail_only[0].keys()) == ["id", "product_detail"] if detail_only else False,
    )

    summary = {r["color"]: int(r["count"]) for r in read_csv(OUTPUT / "colors_summary.csv")}
    check("colors_summary counts", summary == EXPECTED_SUMMARY, f"got {summary}")


def check_sql() -> None:
    if not DB.exists():
        check("SQL database (skipped, sql/nba.db not built yet)", True)
        return
    con = sqlite3.connect(DB)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
        check("player_stats table exists", "player_stats" in tables)
        if "player_stats" in tables:
            cols = [r[1] for r in con.execute("PRAGMA table_info(player_stats)")]
            bad = [c for c in cols if not c.replace("_", "").isalnum() or c[0].isdigit()]
            check("column names cleaned", not bad, f"bad: {bad}")
        if "player_season" in tables:
            n = con.execute("SELECT COUNT(*) FROM player_season").fetchone()[0]
            check("player count plausible (450-800)", 450 <= n <= 800, f"got {n}")
    finally:
        con.close()


def main() -> int:
    check_python_outputs()
    check_sql()
    width = max(len(n) for n, _, _ in results)
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        line = f"{mark}  {name.ljust(width)}"
        if not ok and detail:
            line += f"  ({detail})"
        print(line)
    failed = sum(not ok for _, ok, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
