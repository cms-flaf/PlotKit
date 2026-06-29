"""Base class shared by all plot styles."""

from __future__ import annotations

from typing import Optional, Union

from ..backends import StyleBackend, get_backend
from ..config import PlotConfig


class BasePlotter:
    """Holds the configuration and the chosen rendering backend.

    A concrete plotter implements ``plot(...)``: it assembles an engine-neutral spec
    (see :mod:`PlotKit.spec`) and hands it to ``self.backend``.  Keeping spec-building
    here (engine independent) and drawing in the backend is what lets the same plotter
    render through either mplhep or cmsstyle.
    """

    def __init__(
        self, config: PlotConfig, backend: Optional[Union[StyleBackend, str]] = None
    ):
        self.config = config
        # ``backend`` may be a ready instance, a name string (e.g. "cmsstyle" from the
        # CLI), or None (use the configured default) -- resolve all three here.
        if backend is None:
            backend = get_backend(config.backend_name())
        elif isinstance(backend, str):
            backend = get_backend(backend)
        self.backend = backend

    @classmethod
    def from_files(cls, page_cfg, page_cfg_custom=None, hist_cfg=None, backend=None):
        """Convenience constructor from config paths/dicts."""
        config = PlotConfig(page_cfg, page_cfg_custom, hist_cfg)
        return cls(config, backend)

    def plot(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError
