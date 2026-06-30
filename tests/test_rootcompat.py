import numpy as np

from PlotKit import rootcompat as rc


def test_root_colors():
    assert rc.root_color_to_rgba("kBlack") == (0.0, 0.0, 0.0)
    assert rc.root_color_to_rgba("kWhite") == (1.0, 1.0, 1.0)
    assert rc.root_color_to_rgba("kAzure-9") == (0.6, 0.8, 1.0)
    assert rc.root_color_to_rgba("kSpring+5") == (0.6, 0.8, 0.2)
    # hex / matplotlib names pass straight through
    assert rc.root_color_to_rgba("#ff0000") == "#ff0000"
    # unknown -> default
    assert rc.root_color_to_rgba("kNotAColor", default=(0.1, 0.2, 0.3)) == (
        0.1,
        0.2,
        0.3,
    )


def test_tlatex_plain_passthrough():
    assert rc.tlatex_to_mpl("Events") == "Events"
    assert rc.tlatex_to_mpl("") == ""


def test_tlatex_markup():
    out = rc.tlatex_to_mpl("p_{T} (GeV)")
    assert out.startswith("$") and out.endswith("$")
    assert r"\mathrm{p}" in out and "_{" in out
    assert r"\tau" in rc.tlatex_to_mpl("#tau")
    assert r"\rightarrow" in rc.tlatex_to_mpl("hh#rightarrowbb")
    assert r"\bar" in rc.tlatex_to_mpl("t#bar{t}")


def test_tlatex_native_mathtext_passthrough():
    # Some analyses (e.g. H_mumu) write titles already as matplotlib mathtext.
    # These must be passed through unchanged -- re-converting them double-wraps
    # ``$...$`` and makes matplotlib raise "Double subscript".
    for s in (
        r"$p_{T}(\mu_1) (\mathrm{GeV})$",
        r"$\frac{\mathrm{Events}}{\mathrm{bin\ width}}$",
        r"cos($\theta_{CS}$)",  # mixed literal + math
    ):
        assert rc.tlatex_to_mpl(s) == s


def test_parse_bins():
    np.testing.assert_allclose(rc.parse_bins("5|0:10"), [0, 2, 4, 6, 8, 10])
    np.testing.assert_allclose(rc.parse_bins([0, 1, 4, 9]), [0, 1, 4, 9])


def test_line_and_fill_styles():
    assert rc.line_style_to_mpl(2) == "--"
    assert rc.line_style_to_mpl(1) == "-"
    assert rc.fill_style_to_hatch(3013) is not None
    assert rc.fill_style_to_hatch(1001) is None


def test_font_codes():
    assert rc.font_to_mpl(62).get("weight") == "bold"
    assert rc.font_to_mpl(52).get("style") == "italic"
    assert rc.font_to_mpl(42) == {}


# Real TLatex strings pulled from the analysis config/plot/*.yaml files. The command
# vocabulary is *not* separated from following text (``#rightarrowbb``), which is exactly
# the case that must convert to mathtext matplotlib can actually parse.
REAL_LABELS = [
    "hh#rightarrowbb#tau#tau",
    "p_{T}(lep_{1}) (GeV)",
    "#frac{Events}{bin width} #left(#frac{1}{GeV}#right) ",
    "m_{T}(lep_{1}, MET-#mu) (GeV)",
    r"\eta(lep_{1})",
    r"\Delta(\phi_{lep_{1}}, \phi_{MET-\mu})",
    "7.9804 fb^{-1} (13.6 TeV)",
    "bb#tau_{h}#tau_{h}",
    "t#bar{t}",
    "DY #rightarrow ll + jets",
    "W #rightarrow l#nu + jets",
    # Native matplotlib mathtext, as written in H_mumu/config/plot/histograms.yaml.
    r"$p_{T}(\mu_1) (\mathrm{GeV})$",
    r"$\sigma_{m_{\mu\mu}}/m_{\mu\mu}$",
    r"$\frac{\mathrm{Events}}{\mathrm{bin\ width}}\, \left(\frac{1}{\mathrm{GeV}}\right)$",
]


def test_converted_labels_parse_in_mathtext():
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.mathtext import MathTextParser

    parser = MathTextParser("agg")
    for raw in REAL_LABELS:
        converted = rc.tlatex_to_mpl(raw)
        if converted.startswith("$"):
            # Must not raise -- this is what caught the greedy-command bug.
            parser.parse(converted)
