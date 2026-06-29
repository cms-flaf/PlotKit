"""Plot-style registry.

Each plot *style* is a :class:`~PlotKit.plotters.base.BasePlotter` subclass that turns
histograms + config into an engine-neutral spec.  v1 ships the backward-compatible
``stacked`` style; new styles (e.g. dataset ``comparison`` or ``2d``) register here and add a
matching ``render_<style>`` to the backends -- this is the extension point foreseen by
issue #171.
"""

from __future__ import annotations

from .base import BasePlotter
from .stacked import StackedPlotter

STYLES = {
    "stacked": StackedPlotter,
}


def get_plotter(style: str):
    """Return the plotter class for ``style`` (default ``stacked``)."""
    try:
        return STYLES[(style or "stacked").strip().lower()]
    except KeyError as exc:
        raise KeyError(
            f"Unknown plot style {style!r}; available: {sorted(STYLES)}"
        ) from exc


__all__ = ["BasePlotter", "StackedPlotter", "STYLES", "get_plotter"]
