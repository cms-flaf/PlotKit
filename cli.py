"""Standalone command-line entry point.

Renders a plot from a ROOT file *without* FLAF or ROOT -- histograms are read with uproot.
A legacy ``inputs.yaml`` (the ``name``/``title``/``color``/``type`` list the analyses already
ship) maps the histograms in the file to process groups, labels and colours::

    python -m PlotKit.cli --style stacked \\
        --page-cfg cms_stacked.yaml --page-cfg-custom Run3_2022.yaml \\
        --hist-cfg histograms.yaml --inputs-cfg inputs.yaml \\
        --input merged.root --hist-name tau1_pt --output tau1_pt.pdf
"""

from __future__ import annotations

import argparse
import sys

import yaml

from .config import PlotConfig
from .histogram import from_uproot
from .plotters import get_plotter


def _classify(entry: dict) -> str:
    t = str(entry.get("type", "")).lower()
    if t == "signal":
        return "signals"
    if t == "data":
        return "data"
    return "backgrounds"


def _read_histograms(input_file, hist_name, inputs_cfg):
    """Build the ``{key: (Hist1D, label, color, group)}`` dict from a ROOT file."""
    import uproot

    with open(inputs_cfg, "r") as f:
        inputs = yaml.safe_load(f)

    histograms = {}
    with uproot.open(input_file) as f:
        for entry in inputs:
            name = entry["name"]
            # Allow either a flat "<name>" object or a "<name>/<hist_name>" layout.
            for candidate in (f"{name}/{hist_name}", name, hist_name):
                try:
                    obj = f[candidate]
                except Exception:
                    continue
                histograms[name] = (
                    from_uproot(obj, name=name),
                    entry.get("title", name),
                    entry.get("color", "kBlack"),
                    _classify(entry),
                )
                break
    return histograms


def build_parser():
    p = argparse.ArgumentParser(
        prog="PlotKit", description="Standalone CMS plot rendering."
    )
    p.add_argument("--style", default="stacked", help="Plot style (default: stacked).")
    p.add_argument(
        "--page-cfg", required=True, help="Page style config (cms_stacked.yaml)."
    )
    p.add_argument(
        "--page-cfg-custom", default=None, help="Era overrides (<era>.yaml)."
    )
    p.add_argument(
        "--hist-cfg", required=True, help="Per-variable config (histograms.yaml)."
    )
    p.add_argument("--inputs-cfg", required=True, help="Process map (inputs.yaml).")
    p.add_argument("--input", required=True, help="Input ROOT file.")
    p.add_argument(
        "--hist-name", required=True, help="Variable / histogram name to plot."
    )
    p.add_argument("--output", required=True, help="Output file (.pdf/.png).")
    p.add_argument("--backend", default=None, help="mplhep (default) or cmsstyle.")
    p.add_argument(
        "--no-data", action="store_true", help="Do not draw the data points."
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    config = PlotConfig(args.page_cfg, args.page_cfg_custom, args.hist_cfg)
    plotter = get_plotter(args.style)(config, args.backend)
    histograms = _read_histograms(args.input, args.hist_name, args.inputs_cfg)
    if not histograms:
        print("No histograms matched the inputs config.", file=sys.stderr)
        return 1
    plotter.plot(args.hist_name, histograms, args.output, want_data=not args.no_data)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
