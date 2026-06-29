"""Standalone CLI: nested-file navigation + process auto-discovery."""

import numpy as np
import pytest

from PlotKit import cli

uproot = pytest.importorskip("uproot")

EDGES = np.linspace(0, 200, 21)


def _write_nested(path):
    """Write a FLAF-like merged file: <channel>/<region>/<category>/<process>."""
    rng = np.random.default_rng(0)
    procs = {
        "DY": 30 * np.exp(-EDGES[:-1] / 90),
        "TT": 50 * np.exp(-EDGES[:-1] / 70),
        "XtoHHto2B2W_2L_300": rng.uniform(0, 2, len(EDGES) - 1),
        "XtoHHto2B2W_2L_1000": rng.uniform(0, 2, len(EDGES) - 1),
        "XtoHHto2B2W_1L_300": rng.uniform(0, 2, len(EDGES) - 1),
        "Data_Full": np.round(80 * np.exp(-EDGES[:-1] / 80)),
    }
    with uproot.recreate(path) as f:
        for name, values in procs.items():
            f[f"eMu/SR/res2b/{name}"] = (values, EDGES)


def test_discover_classifies_and_selects(tmp_path):
    fpath = str(tmp_path / "MT2_bb.root")
    _write_nested(fpath)

    hists = cli._discover_histograms(
        fpath,
        path="eMu/SR/res2b",
        signal_regex="XtoHHto",
        signal_select=r"XtoHHto2B2W_2L_(300)$",
        data_names=["Data_Full"],
    )

    groups = {name: entry[3] for name, entry in hists.items()}
    # Backgrounds and data classified correctly.
    assert groups["DY"] == "backgrounds"
    assert groups["TT"] == "backgrounds"
    assert groups["Data_Full"] == "data"
    # Only the selected signal family member survives; the others are dropped
    # (NOT demoted to background).
    assert groups["XtoHHto2B2W_2L_300"] == "signals"
    assert "XtoHHto2B2W_2L_1000" not in hists
    assert "XtoHHto2B2W_1L_300" not in hists
    # Underscores in the display label are shown as spaces (no mathtext subscripts).
    assert hists["XtoHHto2B2W_2L_300"][1] == "XtoHHto2B2W 2L 300"


def test_cli_main_renders_from_nested_file(tmp_path):
    fpath = str(tmp_path / "MT2_bb.root")
    _write_nested(fpath)
    out = tmp_path / "MT2_bb.pdf"

    page_cfg = tmp_path / "page.yaml"
    page_cfg.write_text(
        "page_setup: {draw_ratio: true, legend: legend}\n"
        "legend: {text_size: 0.03}\n"
        "cms_text: {text: CMS}\nscope_text: {text: Preliminary}\n"
        "lumi_text: {text: '1 fb^{-1} (13.6 TeV)'}\nana_text: {text: demo}\n"
        "bkg_hist: {unc_hist: bkg_unc_hist}\n"
        "bkg_unc_hist: {fill_style: 3013, fill_color: kCyan-5, legend_title: Bkg. unc.}\n"
        "sgn_hist: {line_style: 2, line_width: 3}\ndata_hist: {marker_color: kBlack}\n"
    )
    hist_cfg = tmp_path / "hist.yaml"
    hist_cfg.write_text("MT2_bb: {x_title: MT2 bb, y_title: Events}\n")

    rc = cli.main(
        [
            "--page-cfg",
            str(page_cfg),
            "--hist-cfg",
            str(hist_cfg),
            "--input",
            fpath,
            "--hist-name",
            "MT2_bb",
            "--path",
            "eMu/SR/res2b",
            "--signal-regex",
            "XtoHHto",
            "--signal-select",
            r"XtoHHto2B2W_2L_300$",
            "--signal-scale",
            "100",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists() and out.stat().st_size > 0
