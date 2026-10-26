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


def run_main(tmp_path, monkeypatch, catalog_rows, update_rows):
    """Write inputs under tmp_path and run main() against them, never touching data/."""
    data, out = tmp_path / "data", tmp_path / "output"
    data.mkdir()
    (data / "catalog.csv").write_text(CATALOG + catalog_rows, encoding="utf-8")
    (data / "updates.tsv").write_text(UPDATES + update_rows, encoding="utf-8")
    (data / "color_map.json").write_text(json.dumps({"red": "Red"}), encoding="utf-8")
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
