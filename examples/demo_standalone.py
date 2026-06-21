"""Minimal standalone demo: render a stacked plot from synthetic histograms.

Run (no ROOT or FLAF needed)::

    python examples/demo_standalone.py /tmp/demo.pdf
"""

from __future__ import annotations

import os
import sys

import numpy as np

# Allow running this example directly from a checkout (python examples/demo_standalone.py).
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from PlotKit.Plotter import Plotter  # noqa: E402
from PlotKit.histogram import Hist1D  # noqa: E402

# A minimal page config in the legacy (ROOT-flavoured) vocabulary.
PAGE_CFG = {
    "page_setup": {
        "draw_ratio": True,
        "max_ratio": 1.5,
        "text_boxes": [],
        "legend": "legend",
    },
    "legend": {"text_size": 0.03},
    "cms_text": {"text": "CMS"},
    "scope_text": {"text": "Preliminary"},
    "lumi_text": {"text": "X fb^{-1} (13.6 TeV)"},
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
HIST_CFG = {"demo_var": {"x_title": "m_{T} (GeV)", "y_title": "Events"}}


def main(output="demo.pdf"):
    edges = np.linspace(0, 200, 21)
    rng = np.random.default_rng(1)
    bkg1 = Hist1D(edges, 40 * np.exp(-edges[:-1] / 80), name="bkg1")
    bkg2 = Hist1D(edges, 20 * np.exp(-edges[:-1] / 120), name="bkg2")
    sig = Hist1D(edges, 6 * np.exp(-((edges[:-1] - 100) ** 2) / 400), name="sig")
    total = bkg1.values + bkg2.values
    data = Hist1D(edges, rng.poisson(total).astype(float), name="data")

    histograms = {
        "DY": (bkg1, "DY #rightarrow ll", "kAzure-9", "backgrounds"),
        "TT": (bkg2, "t#bar{t}", "kSpring+5", "backgrounds"),
        "HH": (sig, "HH signal (x20)", "kRed", "signals"),
        "data": (data, "data", "kBlack", "data"),
    }
    Plotter(PAGE_CFG, hist_cfg=HIST_CFG).plot(
        "demo_var",
        histograms,
        output,
        want_data=True,
        custom={"datasim_text": "CMS Preliminary"},
        scale=20.0,
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo.pdf")
