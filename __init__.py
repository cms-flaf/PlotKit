"""PlotKit -- CMS analysis plotting toolkit.

A from-scratch redesign of the FLAF plotting code (issue cms-flaf/FLAF#171).  It renders CMS
stacked plots with **matplotlib + mplhep** by default (no ROOT required) and can optionally
render through **ROOT + cmsstyle**.  It reads the existing analysis ``config/plot/*.yaml``
files unchanged, runs standalone or embedded in FLAF, and is structured so new plot styles
(dataset comparison, 2D, ...) and backends can be added without disrupting callers.
"""

from __future__ import annotations

from .config import PlotConfig
from .histogram import Hist1D, to_hist1d
from .plotters.stacked import StackedPlotter

# NOTE: the legacy facade is the *module* ``PlotKit.Plotter`` exposing class ``Plotter``.
# It is deliberately NOT re-exported here: FLAF does ``import FLAF.PlotKit.Plotter as Plotter``
# and then ``Plotter.Plotter(...)``, so the submodule name must not be shadowed by the class.
# Import the class explicitly with ``from PlotKit.Plotter import Plotter``.

__version__ = "1.0.0"

__all__ = [
    "StackedPlotter",
    "PlotConfig",
    "Hist1D",
    "to_hist1d",
    "__version__",
]
