"""Engine-neutral description of a plot.

A *plotter* (e.g. :class:`~PlotKit.plotters.stacked.StackedPlotter`) turns histograms and
config into one of these specs; a *backend* (mplhep/matplotlib or cmsstyle/ROOT) renders it.
Keeping the description independent of any drawing engine is what lets PlotKit support both
``mplhep`` and ``cmsstyle`` (issue #171) and makes adding new plot styles a matter of
producing a new spec rather than touching every backend.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional, Tuple, Union

from .histogram import Hist1D

# A colour as produced by ``rootcompat.root_color_to_rgba``: either an RGB(A) tuple or a
# matplotlib-understood colour string (hex / named).
Color = Union[Tuple[float, ...], str]


@dataclasses.dataclass
class HistEntry:
    """One histogram to draw, with its already-resolved (engine-neutral) style."""

    hist: Hist1D
    label: str
    color: Color = (0.5, 0.5, 0.5)
    filled: bool = True
    line_style: str = "-"
    line_width: float = 1.0
    line_color: Optional[Color] = None
    marker: Optional[str] = None
    marker_size: float = 6.0
    legend: bool = True


@dataclasses.dataclass
class UncBand:
    """Style for the background-uncertainty band (drawn from the stack total)."""

    hatch: Optional[str] = "///"
    color: Color = (0.4, 0.6, 0.6)
    label: str = "Bkg. uncertainty"
    alpha: float = 1.0


@dataclasses.dataclass
class StackSpec:
    """Everything a backend needs to render a stacked CMS plot."""

    # data series
    backgrounds: List[HistEntry] = dataclasses.field(default_factory=list)
    signals: List[HistEntry] = dataclasses.field(default_factory=list)
    data: Optional[HistEntry] = None
    bkg_total: Optional[Hist1D] = None
    # Same values as ``bkg_total``, but with the *full* per-bin uncertainty (stat + syst
    # from the up/down variations) in place of the stat-only one.  When set it drives both
    # the uncertainty band on the main pad and the band in the ratio panel.
    bkg_total_unc: Optional[Hist1D] = None
    unc_band: Optional[UncBand] = None

    # axes
    x_title: str = ""
    y_title: str = "Events"
    log_x: bool = False
    log_y: bool = False
    y_min: float = 0.0
    y_min_log: float = 1e-2
    max_y_sf: float = 1.5

    # ratio panel
    draw_ratio: bool = True
    ratio_title: str = "Obs/Bkg"
    ratio_min: float = 0.5
    ratio_max: float = 1.5

    # labels
    cms_text: str = "CMS"
    scope_text: str = "Preliminary"
    is_data: bool = True
    lumi_text: str = ""
    extra_labels: List[str] = dataclasses.field(default_factory=list)

    # legend / canvas
    legend_loc: str = "upper right"
    legend_fontsize: Optional[float] = None
    canvas_size: Tuple[float, float] = (10.0, 10.0)
