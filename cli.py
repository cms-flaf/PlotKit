"""Standalone command-line entry point.

Renders a plot from a ROOT file *without* FLAF or ROOT -- histograms are read with uproot.
There are two ways to map the histograms in the file to process groups, labels and colours:

1. An explicit process map (the legacy ``inputs.yaml`` the analyses already ship), e.g.::

       python -m PlotKit.cli --style stacked \\
           --page-cfg cms_stacked.yaml --page-cfg-custom Run3_2022.yaml \\
           --hist-cfg histograms.yaml --inputs-cfg inputs.yaml \\
           --input merged.root --hist-name tau1_pt --output tau1_pt.pdf

2. Auto-discovery from a real FLAF merged file, whose histograms are nested as
   ``<channel>/<region>/<category>/<process>``. Point ``--path`` at the directory holding
   the per-process histograms and PlotKit classifies them itself (data via ``--data-name``,
   signals via ``--signal-regex``, everything else stacked as background)::

       python -m PlotKit.cli \\
           --page-cfg cms_stacked.yaml --page-cfg-custom Run3_2023.yaml \\
           --hist-cfg histograms.yaml \\
           --input MT2_bb.root --hist-name MT2_bb --path eMu/SR/res2b \\
           --signal-regex 'XtoHHto2B2W_2L_(300|600|1000)$' --signal-scale 100 \\
           --output MT2_bb.pdf
"""

from __future__ import annotations

import argparse
import re
import sys

import yaml

from .config import PlotConfig
from .histogram import from_uproot
from .plotters import get_plotter

# Default process names treated as observed data (first match in the file wins).
_DEFAULT_DATA_NAMES = ("Data_Full", "data", "data_obs", "Data")

# ROOT colour names (understood by rootcompat) cycled through for auto-discovered
# processes when no explicit colour is given.
_BKG_PALETTE = (
    "kAzure+1",
    "kGreen-3",
    "kPink+2",
    "kViolet",
    "kOrange+1",
    "kTeal+3",
    "kRed-10",
    "kBlue-7",
    "kMagenta",
    "kSpring+5",
    "kYellow-9",
    "kGray+2",
)
_SGN_PALETTE = ("kBlack", "kBlue+1", "kRed", "kGreen+2", "kViolet+1", "kOrange+7")


def _classify(entry: dict) -> str:
    t = str(entry.get("type", "")).lower()
    if t == "signal":
        return "signals"
    if t == "data":
        return "data"
    return "backgrounds"


def _read_histograms_from_inputs(input_file, hist_name, inputs_cfg, path=None):
    """Build ``{name: (Hist1D, label, color, group)}`` from an explicit process map."""
    import uproot

    with open(inputs_cfg, "r") as f:
        inputs = yaml.safe_load(f)

    prefix = f"{path.strip('/')}/" if path else ""
    single_entry = len(inputs) == 1
    histograms = {}
    with uproot.open(input_file) as f:
        for entry in inputs:
            name = entry["name"]
            # Accept a nested "<path>/<name>", a "<name>/<hist_name>" layout, or a flat object.
            candidates = [f"{prefix}{name}", f"{name}/{hist_name}", name]
            # Only fall back to the bare "<hist_name>" object for a single-process map --
            # otherwise every process would map to the same shared TH1 (silent wrong stack).
            if single_entry:
                candidates.append(hist_name)
            for candidate in candidates:
                try:
                    obj = f[candidate]
                except Exception:
                    continue
                if not getattr(obj, "classname", "").startswith("TH1"):
                    continue
                histograms[name] = (
                    from_uproot(obj, name=name),
                    entry.get("title", name),
                    entry.get("color", "kBlack"),
                    _classify(entry),
                )
                break
    return histograms


def _discover_histograms(input_file, path, signal_regex, signal_select, data_names):
    """Auto-discover per-process TH1 histograms under ``path`` and classify them.

    The real FLAF merged file is per-variable and nested as
    ``<channel>/<region>/<category>/<process>``, so ``path`` is the category directory and
    each child TH1 is one process' histogram.

    ``signal_regex`` identifies the signal *family* (anything matching is a signal, never a
    background). ``signal_select`` optionally narrows which family members are actually
    drawn -- unselected signals are dropped (not promoted to background), which keeps the
    legend readable when a file ships dozens of mass points.
    """
    import uproot

    sig_re = re.compile(signal_regex) if signal_regex else None
    sel_re = re.compile(signal_select) if signal_select else None
    data_set = set(data_names)

    def kind(name):
        if name in data_set:
            return "data"
        if sig_re and sig_re.search(name):
            return "signals"
        return "backgrounds"

    histograms = {}
    bkg_i = sgn_i = 0
    with uproot.open(input_file) as f:
        directory = f[path] if path else f
        names = sorted(
            k.split(";")[0]
            for k in directory.keys(recursive=False)
            if getattr(directory[k], "classname", "").startswith("TH1")
        )
        # Drop signal-family members not picked by the optional selection.
        names = [
            n
            for n in names
            if kind(n) != "signals" or sel_re is None or sel_re.search(n)
        ]
        # Backgrounds first, then signals, then data -- a stable, readable legend order.
        order = {"backgrounds": 0, "signals": 1, "data": 2}
        for name in sorted(names, key=lambda n: (order[kind(n)], n)):
            H = from_uproot(directory[name], name=name)
            group = kind(name)
            # Process names carry underscores (mathtext subscripts); show them as spaces.
            label = name.replace("_", " ")
            if group == "data":
                histograms[name] = (H, "data", "kBlack", "data")
            elif group == "signals":
                histograms[name] = (
                    H,
                    label,
                    _SGN_PALETTE[sgn_i % len(_SGN_PALETTE)],
                    "signals",
                )
                sgn_i += 1
            else:
                histograms[name] = (
                    H,
                    label,
                    _BKG_PALETTE[bkg_i % len(_BKG_PALETTE)],
                    "backgrounds",
                )
                bkg_i += 1
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
    p.add_argument(
        "--inputs-cfg",
        default=None,
        help="Explicit process map (inputs.yaml). If omitted, processes under --path are "
        "auto-discovered.",
    )
    p.add_argument("--input", required=True, help="Input ROOT file.")
    p.add_argument(
        "--hist-name", required=True, help="Variable / histogram name to plot."
    )
    p.add_argument(
        "--path",
        default=None,
        help="In-file directory holding the per-process histograms, e.g. "
        "'eMu/SR/res2b' (FLAF merged-file layout: channel/region/category).",
    )
    p.add_argument(
        "--signal-regex",
        default=None,
        help="Regex identifying the signal family among discovered processes "
        "(auto-discovery); matches are signals, never backgrounds.",
    )
    p.add_argument(
        "--signal-select",
        default=None,
        help="Optional regex narrowing which signal-family members are drawn "
        "(e.g. a few mass points); unselected family members are dropped.",
    )
    p.add_argument(
        "--data-name",
        action="append",
        default=None,
        help="Process name(s) to treat as observed data (auto-discovery; repeatable). "
        f"Default tries {', '.join(_DEFAULT_DATA_NAMES)}.",
    )
    p.add_argument(
        "--signal-scale",
        default="1",
        help="Multiply signal histograms by this factor before overlaying, or 'bkg' to "
        "normalise each signal's integral to the summed background.",
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

    if args.inputs_cfg:
        histograms = _read_histograms_from_inputs(
            args.input, args.hist_name, args.inputs_cfg, path=args.path
        )
    else:
        data_names = args.data_name or list(_DEFAULT_DATA_NAMES)
        histograms = _discover_histograms(
            args.input,
            args.path,
            args.signal_regex,
            args.signal_select,
            data_names,
        )

    if not histograms:
        print(
            "No histograms matched. Provide --inputs-cfg or a --path pointing at the "
            "per-process directory in the file.",
            file=sys.stderr,
        )
        return 1

    # "bkg" passes through as a string (normalise to background); anything else is a factor.
    try:
        scale = float(args.signal_scale)
    except (TypeError, ValueError):
        scale = args.signal_scale

    plotter.plot(
        args.hist_name,
        histograms,
        args.output,
        want_data=not args.no_data,
        scale=scale,
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
