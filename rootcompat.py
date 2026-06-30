"""Translate the legacy ROOT-flavoured config vocabulary into matplotlib equivalents.

The analysis ``config/plot/*.yaml`` files were written for a ROOT renderer and use ROOT
colour names (``kAzure-9``), ROOT ``TLatex`` markup (``p_{T}``, ``#tau``), ROOT font codes
(``42``/``62``) and ROOT draw options (``HIST``/``e2``/``0pe``).  Keeping those files
untouched is a hard requirement of issue #171, so this module does the on-the-fly
translation.  Everything here is pure Python (no ROOT import required) so the renderer
works standalone; when ROOT *is* importable it is used as the authoritative source for any
colour not already in the baked table.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

# Exact RGB values ROOT assigns to every colour used across the three analyses' plot
# configs (generated from ROOT's colour table).  Lets the standalone path reproduce the
# colours faithfully without importing ROOT.
_ROOT_COLORS = {
    "kWhite": (1.0, 1.0, 1.0),
    "kBlack": (0.0, 0.0, 0.0),
    "kGray": (0.8, 0.8, 0.8),
    "kGray+1": (0.6, 0.6, 0.6),
    "kGray+2": (0.4, 0.4, 0.4),
    "kGray+3": (0.2, 0.2, 0.2),
    "kRed": (1.0, 0.0, 0.0),
    "kRed+1": (0.8, 0.0, 0.0),
    "kRed+2": (0.6, 0.0, 0.0),
    "kRed-10": (1.0, 0.8, 0.8),
    "kGreen": (0.0, 1.0, 0.0),
    "kGreen+2": (0.0, 0.6, 0.0),
    "kGreen-3": (0.2, 0.8, 0.2),
    "kBlue": (0.0, 0.0, 1.0),
    "kBlue+1": (0.0, 0.0, 0.8),
    "kBlue-7": (0.4, 0.4, 1.0),
    "kBlue-10": (0.8, 0.8, 1.0),
    "kYellow": (1.0, 1.0, 0.0),
    "kYellow-9": (1.0, 1.0, 0.6),
    "kMagenta": (1.0, 0.0, 1.0),
    "kMagenta-10": (1.0, 0.8, 1.0),
    "kCyan": (0.0, 1.0, 1.0),
    "kCyan-5": (0.4, 0.6, 0.6),
    "kOrange": (1.0, 0.8, 0.0),
    "kOrange-4": (1.0, 0.8, 0.4),
    "kOrange+1": (1.0, 0.6, 0.2),
    "kOrange+7": (1.0, 0.4, 0.0),
    "kSpring": (0.2, 1.0, 0.0),
    "kSpring+5": (0.6, 0.8, 0.2),
    "kAzure": (0.0, 0.2, 1.0),
    "kAzure+1": (0.2, 0.6, 1.0),
    "kAzure-4": (0.4, 0.6, 1.0),
    "kAzure-9": (0.6, 0.8, 1.0),
    "kViolet": (0.8, 0.0, 1.0),
    "kViolet+1": (0.6, 0.2, 1.0),
    "kViolet-9": (0.8, 0.6, 1.0),
    "kPink": (1.0, 0.0, 0.2),
    "kPink+2": (0.8, 0.4, 0.6),
    "kTeal": (0.0, 1.0, 0.8),
    "kTeal+3": (0.0, 0.4, 0.2),
}

_COLOR_RE = re.compile(r"^(k[A-Za-z]+)\s*([+-]\s*\d+)?$")


def root_color_to_rgba(value, default=(0.5, 0.5, 0.5)):
    """Convert a ROOT colour name (or any matplotlib colour) into an RGB tuple."""
    if value is None:
        return default
    if isinstance(value, (tuple, list)):
        return tuple(value)
    s = str(value).strip()
    # Already a matplotlib-understood colour (hex, named, etc.).
    if s.startswith("#") or s.lower() in _MPL_NAMED:
        return s
    if s in _ROOT_COLORS:
        return _ROOT_COLORS[s]
    m = _COLOR_RE.match(s)
    if m:
        # Try ROOT as the authoritative source for colours not in the baked table.
        try:
            import ROOT  # noqa: PLC0415

            base = m.group(1)
            off = int(m.group(2).replace(" ", "")) if m.group(2) else 0
            c = ROOT.gROOT.GetColor(getattr(ROOT, base) + off)
            if c:
                return (
                    round(c.GetRed(), 4),
                    round(c.GetGreen(), 4),
                    round(c.GetBlue(), 4),
                )
        except Exception:
            pass
        # Last resort: the base colour without the shade modifier.
        if m.group(1) in _ROOT_COLORS:
            return _ROOT_COLORS[m.group(1)]
    return default


# A few matplotlib colour names we should pass straight through.
_MPL_NAMED = {
    "white",
    "black",
    "red",
    "green",
    "blue",
    "yellow",
    "magenta",
    "cyan",
    "orange",
    "gray",
    "grey",
    "none",
}


# --------------------------------------------------------------------------- #
# TLatex -> matplotlib mathtext
# --------------------------------------------------------------------------- #
# ROOT TLatex commands are NOT separated from following text (``#rightarrowbb``), so we must
# match a known command vocabulary (longest first) rather than greedily grabbing letters.
# This is the matplotlib-mathtext-supported subset relevant to physics labels.
_KNOWN_CMDS = [
    # structural
    "frac",
    "sqrt",
    "bar",
    "hat",
    "tilde",
    "vec",
    "dot",
    "ddot",
    "overline",
    "underline",
    "left",
    "right",
    "mathrm",
    "mathbf",
    "mathit",
    "mathcal",
    "sum",
    "prod",
    "int",
    "oint",
    # lower-case greek
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "varepsilon",
    "zeta",
    "eta",
    "theta",
    "vartheta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "omicron",
    "pi",
    "varpi",
    "rho",
    "varrho",
    "sigma",
    "varsigma",
    "tau",
    "upsilon",
    "phi",
    "varphi",
    "chi",
    "psi",
    "omega",
    # upper-case greek
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Pi",
    "Sigma",
    "Upsilon",
    "Phi",
    "Psi",
    "Omega",
    # arrows / relations / operators / misc symbols
    "rightarrow",
    "leftarrow",
    "Rightarrow",
    "Leftarrow",
    "leftrightarrow",
    "to",
    "times",
    "cdot",
    "pm",
    "mp",
    "div",
    "leq",
    "geq",
    "ll",
    "gg",
    "neq",
    "approx",
    "equiv",
    "sim",
    "simeq",
    "propto",
    "infty",
    "partial",
    "nabla",
    "forall",
    "exists",
    "in",
    "notin",
    "subset",
    "supset",
    "cup",
    "cap",
    "angle",
    "perp",
    "parallel",
    "prime",
    "circ",
    "bullet",
    "star",
    "dagger",
    "ell",
    "hbar",
    "deg",
]
# Longest first so e.g. ``rightarrow`` wins over ``right`` and ``Rightarrow`` over nothing.
_CMD_ALT = "|".join(sorted(_KNOWN_CMDS, key=len, reverse=True))
_MATH_TOKEN_RE = re.compile(r"\\(?:%s)|[A-Za-z]+|\s+|." % _CMD_ALT)


def _mathify(text: str) -> str:
    """Turn a LaTeX-ish string into mathtext, keeping latin words upright."""
    out = []
    for tok in _MATH_TOKEN_RE.findall(text):
        if tok.startswith("\\"):
            out.append(tok)  # a known command / greek letter -> keep as-is
        elif tok.isalpha():
            out.append(r"\mathrm{%s}" % tok)  # upright text run (ROOT default)
        elif tok.isspace():
            out.append(r"\ " * len(tok))  # explicit math space
        elif tok == "\\":
            continue  # stray backslash from an unknown command -> drop, keep the text
        else:
            out.append(tok)
    return "".join(out)


def tlatex_to_mpl(text) -> str:
    """Convert ROOT ``TLatex`` markup to a matplotlib mathtext string.

    Handles both ROOT ``#cmd`` markup and bare LaTeX ``\\cmd`` markup (the analysis
    configs mix the two).  Plain strings without markup are returned unchanged.
    A string already written as native matplotlib mathtext (delimited by ``$``) is
    passed through untouched.
    """
    if text is None:
        return ""
    s = str(text)
    # A string containing '$' is already native matplotlib mathtext -- ROOT TLatex
    # never uses '$'. Some analyses (e.g. H_mumu) write titles directly as mathtext
    # (``$p_{T}(\\mu_1)$``); re-converting them would double-wrap ``$...$`` and mangle
    # the markup, after which matplotlib raises "Double subscript". Pass them through.
    if "$" in s:
        return s
    if not any(c in s for c in "#\\^_{}"):
        return s
    # ROOT uses '#' where LaTeX uses '\'.
    s = s.replace("#", "\\")
    return "$%s$" % _mathify(s)


# --------------------------------------------------------------------------- #
# Fonts / draw options / binning
# --------------------------------------------------------------------------- #
def font_to_mpl(font_code) -> dict:
    """Map a ROOT font code (e.g. 42, 61, 52) to matplotlib weight/style kwargs."""
    try:
        font_id = int(font_code) // 10
    except (TypeError, ValueError):
        return {}
    kw = {}
    if font_id in (6, 7):
        kw["weight"] = "bold"
    if font_id in (5, 7, 1, 3):
        kw["style"] = "italic"
    return kw


def draw_opt_kind(draw_opt) -> str:
    """Classify a ROOT draw option into one of: ``band``, ``points``, ``hist``."""
    o = str(draw_opt or "").lower()
    if "e2" in o:
        return "band"
    if "pe" in o or "ple" in o or o.startswith("p"):
        return "points"
    return "hist"


def line_style_to_mpl(line_style) -> str:
    """Map a ROOT line style index to a matplotlib linestyle."""
    mapping = {1: "-", 2: "--", 3: ":", 4: "-.", 7: (0, (5, 2)), 9: (0, (8, 3))}
    try:
        return mapping.get(int(line_style), "-")
    except (TypeError, ValueError):
        return "-"


def fill_style_to_hatch(fill_style) -> Optional[str]:
    """Map a ROOT fill style (e.g. 3013) to a matplotlib hatch pattern, else ``None``.

    ROOT fill styles 3001-3025 are hatch patterns; 1001 is solid and 0 is hollow.
    """
    try:
        fs = int(fill_style)
    except (TypeError, ValueError):
        return None
    if 3000 <= fs < 4000:
        density = fs % 100
        if density <= 4:
            return "///"
        if density <= 7:
            return "\\\\\\"
        if density <= 16:
            return "xxx"
        return "...."
    return None


_BIN_RE = re.compile(r"^\s*(\d+)\s*\|\s*([-\d.eE+]+)\s*:\s*([-\d.eE+]+)\s*$")


def parse_bins(spec) -> np.ndarray:
    """Parse a bin specification into an array of bin edges.

    Accepts the legacy ``"n|lo:hi"`` string (n uniform bins) or an explicit list of edges.
    """
    if isinstance(spec, (list, tuple, np.ndarray)):
        return np.asarray(spec, dtype=float)
    m = _BIN_RE.match(str(spec))
    if not m:
        raise ValueError(f"Cannot parse bin specification: {spec!r}")
    n, lo, hi = int(m.group(1)), float(m.group(2)), float(m.group(3))
    return np.linspace(lo, hi, n + 1)


# --------------------------------------------------------------------------- #
# Text-box positioning
# --------------------------------------------------------------------------- #
# Anchor points expressed in axes fraction coordinates, keyed by the legacy ROOT
# position-reference names.  Used to place the auxiliary text boxes.
_POS_REF = {
    "inner_left_top": (0.05, 0.95, "left", "top"),
    "inner_right_top": (0.95, 0.95, "right", "top"),
    "inner_left_bottom": (0.05, 0.05, "left", "bottom"),
    "inner_right_bottom": (0.95, 0.05, "right", "bottom"),
    "left_top": (0.05, 0.95, "left", "top"),
    "right_top": (0.95, 0.95, "right", "top"),
}


def pos_ref_anchor(name: str):
    """Return ``(x, y, ha, va)`` in axes fraction for a known position reference."""
    return _POS_REF.get(name, (0.05, 0.95, "left", "top"))
