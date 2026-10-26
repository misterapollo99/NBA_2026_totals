import json

import pandas as pd
import pytest

import update_catalog as uc

CATALOG = "id,title,price,color_list,description\n"
UPDATES = "id\tcolor_list_add\tremove_colors\tprice_adjust\n"


@pytest.mark.parametrize("adjust", ["+10%", " 10 % ", "10%"])
def test_positive_adjust_formats_parse(adjust):
    assert uc.adjust_price("100", adjust) == "110.00"


def test_negative_adjust_parses():
    assert uc.adjust_price("100", "-5%") == "95.00"


def test_blank_adjust_leaves_price_unchanged():
    assert uc.adjust_price("19", "") == "19.00"
    assert uc.adjust_price("19", "   ") == "19.00"


def test_malformed_adjust_raises():
    with pytest.raises(ValueError, match="unparseable"):
        uc.adjust_price("10", "ten percent")


def test_rounds_half_up():
    # 59.5 * 0.95 = 56.525 exactly in Decimal. Float math would give 56.52.
    assert uc.adjust_price("59.5", "-5%") == "56.53"


def test_unmapped_color_falls_back_to_title_case():
    assert uc.canonicalize(["dusty rose", "crimson"], {"crimson": "Red"}) == ["Dusty Rose", "Red"]
    assert uc.unmapped(["dusty rose", "crimson"], {"crimson": "Red"}) == ["dusty rose"]


def run_main(tmp_path, monkeypatch, catalog_rows, update_rows, color_map=None):
    """Write inputs under tmp_path and run main() against them, never touching data/."""
    data, out = tmp_path / "data", tmp_path / "output"
    data.mkdir()
    (data / "catalog.csv").write_text(CATALOG + catalog_rows, encoding="utf-8")
    (data / "updates.tsv").write_text(UPDATES + update_rows, encoding="utf-8")
    (data / "color_map.json").write_text(json.dumps(color_map or {"red": "Red"}), encoding="utf-8")
    monkeypatch.setattr(uc, "DATA", data)
    monkeypatch.setattr(uc, "OUTPUT", out)
    uc.main()
    return out


def test_malformed_adjust_names_the_sku(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="id B001"):
        run_main(tmp_path, monkeypatch, "B001,Tee,19,red,desc\n", "B001\t\t\tabc%\n")


def test_duplicate_update_id_raises(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match=r"duplicate ids in updates.tsv: \['B001'\]"):
        run_main(tmp_path, monkeypatch, "B001,Tee,19,red,desc\n", "B001\t\t\t10%\nB001\t\t\t5%\n")


def test_duplicate_catalog_id_raises(tmp_path, monkeypatch):
    catalog_rows = "B001,Tee,19,red,desc\nB001,Tee copy,20,red,desc\n"
    with pytest.raises(ValueError, match=r"duplicate ids in catalog.csv: \['B001'\]"):
        run_main(tmp_path, monkeypatch, catalog_rows, "B001\t\t\t10%\n")


def test_orphan_update_id_is_ignored(tmp_path, monkeypatch, capsys):
    out = run_main(tmp_path, monkeypatch, "B001,Tee,19,red,desc\n", "B001\t\t\t10%\nZZZ\t\t\t50%\n")
    result = pd.read_csv(out / "updated_catalog.csv", dtype=str, keep_default_na=False)
    assert list(result["id"]) == ["B001"]
    assert result.loc[0, "price"] == "20.90"
    assert "ZZZ" in capsys.readouterr().err


def read_text_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def run_on_real_data(out, monkeypatch):
    """Run main() on the real inputs (read-only) with outputs redirected to `out`."""
    monkeypatch.setattr(uc, "OUTPUT", out)
    uc.main()
    return out


def test_leading_zero_id_survives_outputs(tmp_path, monkeypatch):
    out = run_main(tmp_path, monkeypatch, "00123,Tee,19,red,desc\n", "00123\t\t\t\n")
    for name in ("updated_catalog.csv", "product_detail_only.csv"):
        assert list(read_text_csv(out / name)["id"]) == ["00123"]
        assert (out / name).read_text(encoding="utf-8").splitlines()[1].startswith("00123,")
    # colors_summary has no id column, so there is nothing to preserve there.
    assert read_text_csv(out / "colors_summary.csv").to_dict("records") == [
        {"color": "Red", "count": "1"}
    ]


def test_non_price_columns_identical_to_input(tmp_path, monkeypatch):
    out = run_on_real_data(tmp_path / "output", monkeypatch)
    original = read_text_csv(uc.DATA / "catalog.csv")
    result = read_text_csv(out / "updated_catalog.csv")
    assert list(result.columns) == [*original.columns, "product_detail"]
    untouched = [c for c in original.columns if c != "price"]
    pd.testing.assert_frame_equal(result[untouched], original[untouched])
    # The real data has a description with a quoted comma; make sure it was exercised.
    assert any("," in d for d in original["description"])


def test_real_data_reconciles(tmp_path, monkeypatch):
    out = run_on_real_data(tmp_path / "output", monkeypatch)
    original = read_text_csv(uc.DATA / "catalog.csv")
    updated = read_text_csv(out / "updated_catalog.csv")
    detail_only = read_text_csv(out / "product_detail_only.csv")
    summary = read_text_csv(out / "colors_summary.csv")

    assert len(updated) == len(detail_only) == len(original)
    assert set(updated["id"]) == set(detail_only["id"]) == set(original["id"])

    for frame in (updated, detail_only, summary):
        cells = {str(v).strip().lower() for v in frame.to_numpy().ravel()}
        assert not cells & {"nan", "none"}

    allowed = set(json.loads((uc.DATA / "color_map.json").read_text(encoding="utf-8")).values())
    pairs = [
        part.removeprefix(uc.PREFIX)
        for detail in updated["product_detail"]
        for part in detail.split(",")
        if part
    ]
    assert set(pairs) <= allowed
    assert set(summary["color"]) <= allowed
    assert summary["count"].astype(int).sum() == len(pairs)


def test_rerun_is_byte_identical(tmp_path, monkeypatch):
    out = run_on_real_data(tmp_path / "output", monkeypatch)
    names = ("updated_catalog.csv", "product_detail_only.csv", "colors_summary.csv")
    first = {name: (out / name).read_bytes() for name in names}
    run_on_real_data(out, monkeypatch)
    assert {name: (out / name).read_bytes() for name in names} == first


@pytest.mark.parametrize("remove", ["BLUE", " blue ", "Blue"])
def test_removal_ignores_case_and_whitespace(tmp_path, monkeypatch, remove):
    out = run_main(
        tmp_path,
        monkeypatch,
        'B001,Tee,19,"blue, red",desc\n',
        f"B001\t\t{remove}\t\n",
        color_map={"red": "Red", "blue": "Blue"},
    )
    assert read_text_csv(out / "updated_catalog.csv").loc[0, "product_detail"] == uc.PREFIX + "Red"


def test_product_with_all_colors_removed(tmp_path, monkeypatch):
    out = run_main(
        tmp_path,
        monkeypatch,
        "A1,Tee,19,red,desc\nA2,Cap,20,blue,desc\n",
        "A1\t\tRED\t\nA2\t\t\t\n",
        color_map={"red": "Red", "blue": "Blue"},
    )
    updated = read_text_csv(out / "updated_catalog.csv").set_index("id")
    assert updated.loc["A1", "product_detail"] == ""
    assert read_text_csv(out / "product_detail_only.csv").set_index("id").loc["A1"].item() == ""
    assert read_text_csv(out / "colors_summary.csv").to_dict("records") == [
        {"color": "Blue", "count": "1"}
    ]


def test_zero_percent_leaves_price_unchanged():
    assert uc.adjust_price("12.99", "0%") == "12.99"
