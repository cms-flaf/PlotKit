from PlotKit.config import PlotConfig


def make_config():
    page = {
        "page_setup": {"draw_ratio": True, "max_ratio": 1.5, "legend": "legend"},
        "legend": {"text_size": 0.03},
        "bkg_hist": {"fill_style": 1001, "unc_hist": "bkg_unc_hist"},
        "bkg_unc_hist": {"fill_style": 3013, "fill_color": "kCyan-5"},
        "sgn_hist": {"line_width": 3},
        "data_hist": {"marker_color": "kBlack"},
    }
    era = {
        "channel_text": {"tauTau": "bb#tau#tau"},
        "customregion_text": {"OS_Iso": "OS, Isolated"},
    }
    hist = {"tau1_pt": {"x_title": "p_{T}", "divide_by_bin_width": True}}
    return PlotConfig(page, era, hist)


def test_merge_and_accessors():
    cfg = make_config()
    assert cfg.group_style("backgrounds")["fill_style"] == 1001
    assert cfg.group_style("signals")["line_width"] == 3
    assert cfg.bkg_unc_style["fill_color"] == "kCyan-5"
    assert cfg.hist_desc("tau1_pt")["divide_by_bin_width"] is True
    # era file merged into the page config
    assert cfg.channel_label("tauTau") == "bb#tau#tau"
    assert cfg.region_label("OS_Iso") == "OS, Isolated"


def test_backend_default_and_env(monkeypatch):
    cfg = make_config()
    monkeypatch.delenv("PLOTKIT_BACKEND", raising=False)
    assert cfg.backend_name() == "mplhep"
    monkeypatch.setenv("PLOTKIT_BACKEND", "cmsstyle")
    assert cfg.backend_name() == "cmsstyle"
