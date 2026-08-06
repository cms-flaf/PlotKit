import numpy as np
import pytest

from PlotKit.Plotter import Plotter
from PlotKit.histogram import Hist1D

PAGE_CFG = {
    "page_setup": {"draw_ratio": True, "max_ratio": 1.5, "legend": "legend"},
    "legend": {"text_size": 0.03},
    "cms_text": {"text": "CMS"},
    "scope_text": {"text": "Preliminary"},
    "lumi_text": {"text": "1 fb^{-1} (13.6 TeV)"},
    "ana_text": {"text": "demo"},
    "bkg_hist": {"unc_hist": "bkg_unc_hist"},
    "bkg_unc_hist": {
        "fill_style": 3013,
        "fill_color": "kCyan-5",
        "legend_title": "Bkg. unc.",
    },
    "sgn_hist": {"line_style": 2, "line_width": 3},
    "data_hist": {"marker_color": "kBlack"},
}
HIST_CFG = {
    "v": {"x_title": "m_{T} (GeV)", "y_title": "Events", "divide_by_bin_width": False}
}


def _synthetic():
    edges = np.linspace(0, 200, 21)
    bkg1 = Hist1D(edges, 40 * np.exp(-edges[:-1] / 80), name="bkg1")
    bkg2 = Hist1D(edges, 20 * np.exp(-edges[:-1] / 120), name="bkg2")
    sig = Hist1D(edges, 5 * np.exp(-((edges[:-1] - 100) ** 2) / 400), name="sig")
    total = bkg1.values + bkg2.values
    data = Hist1D(edges, np.round(total), name="data")
    return {
        "DY": (bkg1, "DY #rightarrow ll", "kAzure-9", "backgrounds"),
        "TT": (bkg2, "t#bar{t}", "kSpring+5", "backgrounds"),
        "HH": (sig, "HH (x10)", "kRed", "signals"),
        "data": (data, "data", "kBlack", "data"),
    }


def test_stacked_render_pdf(tmp_path):
    out = tmp_path / "v.pdf"
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG).plot(
        "v",
        _synthetic(),
        str(out),
        want_data=True,
        custom={"datasim_text": "CMS Preliminary"},
        scale=10.0,
    )
    assert out.exists() and out.stat().st_size > 0


def test_stacked_render_blinded_no_ratio(tmp_path):
    out = tmp_path / "v_blind.png"
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG).plot(
        "v",
        _synthetic(),
        str(out),
        want_data=False,
        custom={"datasim_text": "CMS Simulation"},
    )
    assert out.exists() and out.stat().st_size > 0


def _total_unc(histograms, rel=0.2):
    """Summed background with an inflated (stat + syst -like) per-bin uncertainty."""
    bkgs = [h for h, _, _, group in histograms.values() if group == "backgrounds"]
    values = sum(h.values for h in bkgs)
    return Hist1D(
        bkgs[0].edges, values, variances=(rel * values) ** 2, name="total_unc"
    )


def test_total_unc_drives_band_and_ratio(tmp_path):
    from PlotKit.config import PlotConfig
    from PlotKit.plotters.stacked import StackedPlotter

    histograms = _synthetic()
    spec = StackedPlotter(PlotConfig(PAGE_CFG, hist_cfg=HIST_CFG), None).build_spec(
        "v", histograms, True, {}, None, _total_unc(histograms)
    )
    # The band histogram carries the full uncertainty, not the stat-only stack error.
    assert spec.bkg_total_unc is not None
    assert np.allclose(spec.bkg_total_unc.values, spec.bkg_total.values)
    assert np.allclose(spec.bkg_total_unc.errors, 0.2 * spec.bkg_total.values)
    assert not np.allclose(spec.bkg_total_unc.errors, spec.bkg_total.errors)
    assert "stat + syst" in spec.unc_band.label
    assert spec.draw_ratio

    out = tmp_path / "v_unc.pdf"
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG).plot(
        "v",
        histograms,
        str(out),
        want_data=True,
        custom={"datasim_text": "CMS Preliminary"},
        total_unc=_total_unc(histograms),
    )
    assert out.exists() and out.stat().st_size > 0


def test_total_unc_gives_ratio_panel_when_blinded(tmp_path):
    from PlotKit.config import PlotConfig
    from PlotKit.plotters.stacked import StackedPlotter

    histograms = _synthetic()
    config = PlotConfig(PAGE_CFG, hist_cfg=HIST_CFG)
    # Blinded and without the full uncertainty there is nothing to put in a ratio panel.
    assert (
        not StackedPlotter(config, None)
        .build_spec("v", histograms, False, {}, None)
        .draw_ratio
    )
    # With it, the panel shows the relative uncertainty band around 1.
    spec = StackedPlotter(config, None).build_spec(
        "v", histograms, False, {}, None, _total_unc(histograms)
    )
    assert spec.draw_ratio and spec.data is None
    assert spec.ratio_title == "Unc./Bkg"

    out = tmp_path / "v_blind_unc.png"
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG).plot(
        "v",
        histograms,
        str(out),
        want_data=False,
        custom={"datasim_text": "CMS Simulation"},
        total_unc=_total_unc(histograms),
    )
    assert out.exists() and out.stat().st_size > 0


def test_string_backend_name_is_resolved():
    # A backend passed as a name string (e.g. CLI --backend mplhep) must be resolved to a
    # backend instance, not stored verbatim (which would crash in render_stacked).
    from PlotKit.config import PlotConfig
    from PlotKit.plotters.stacked import StackedPlotter

    plotter = StackedPlotter(PlotConfig(PAGE_CFG, hist_cfg=HIST_CFG), "mplhep")
    assert hasattr(plotter.backend, "render_stacked")


def test_signal_scaled_to_background_integral():
    from PlotKit.config import PlotConfig
    from PlotKit.plotters.stacked import StackedPlotter

    config = PlotConfig(PAGE_CFG, hist_cfg=HIST_CFG)
    spec = StackedPlotter(config, None).build_spec(
        "v", _synthetic(), want_data=True, custom={}, scale="bkg"
    )

    bkg_total = sum(e.hist.integral() for e in spec.backgrounds)
    assert bkg_total > 0
    # Each signal is normalised so its integral equals the summed background.
    for sig in spec.signals:
        assert sig.hist.integral() == pytest.approx(bkg_total, rel=1e-9)
    # The hardcoded "(x10)" suffix is replaced by the normalisation note.
    assert spec.signals[0].label == "HH (norm. to bkg)"


def test_cmsstyle_backend_optional(tmp_path):
    pytest.importorskip("ROOT")
    pytest.importorskip("cmsstyle")
    out = tmp_path / "v_root.pdf"
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG, backend="cmsstyle").plot(
        "v",
        _synthetic(),
        str(out),
        want_data=True,
        custom={"datasim_text": "CMS Preliminary"},
        scale=10.0,
    )
    assert out.exists() and out.stat().st_size > 0
