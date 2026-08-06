"""Backward-compatible ``Plotter`` facade.

FLAF imports this module as ``FLAF.PlotKit.Plotter`` and uses exactly this class, so keeping
its signature identical to the legacy ROOT implementation makes the new (matplotlib/mplhep)
renderer a transparent drop-in -- no change is required in the analysis configs or in the
FLAF plotting task beyond the submodule swap.

Legacy usage (unchanged)::

    import FLAF.PlotKit.Plotter as Plotter
    plotter = Plotter.Plotter(page_cfg, page_cfg_custom, hist_cfg=hist_cfg_dict)
    plotter.plot(hist_name, {proc: (TH1, name, color, group)}, out_pdf,
                 want_data=..., custom=..., scale=...)
"""

from __future__ import annotations

from typing import Optional

from .config import PlotConfig
from .plotters.stacked import StackedPlotter


class Plotter:
    def __init__(
        self,
        page_cfg,
        page_cfg_custom=None,
        hist_cfg=None,
        inputs_cfg=None,  # accepted for legacy signature compatibility; unused
        backend=None,
    ):
        self.config = PlotConfig(page_cfg, page_cfg_custom, hist_cfg)
        self._plotter = StackedPlotter(self.config, _as_backend(backend))

    def plot(
        self,
        hist_name: str,
        histograms: dict,
        output_file: str,
        want_data: bool = True,
        custom: Optional[dict] = None,
        scale=None,
        total_unc=None,
    ) -> None:
        """``scale`` is a fixed factor (number, or per-signal dict), or the string ``"bkg"``
        to normalise each signal's integral to the summed background (for shape comparison).

        ``total_unc`` optionally carries the summed background with its full (stat + syst)
        per-bin uncertainty; when given it is shown as the band and as a ratio panel below
        the plot.
        """
        self._plotter.plot(
            hist_name,
            histograms,
            output_file,
            want_data=want_data,
            custom=custom,
            scale=scale,
            total_unc=total_unc,
        )


def _as_backend(backend):
    if backend is None or hasattr(backend, "render_stacked"):
        return backend
    from .backends import get_backend

    return get_backend(backend)
