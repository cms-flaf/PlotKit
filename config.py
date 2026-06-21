"""Loading and access helpers for the legacy plot configuration.

PlotKit reads exactly the three config objects the FLAF plotting task already uses:

* ``page_cfg``        -- canvas/page style + per-process histogram styles (``cms_stacked.yaml``)
* ``page_cfg_custom`` -- era-specific overrides: lumi, channel and region labels (``<era>.yaml``)
* ``hist_cfg``        -- per-variable binning, titles, log/blind flags (``histograms.yaml``)

Each argument may be a path to a YAML file or an already-loaded ``dict`` (matching the old
``Plotter`` behaviour), so nothing in the analysis configs needs to change.
"""

from __future__ import annotations

import os
from typing import Optional

import yaml


def load_mapping(cfg) -> dict:
    """Return a dict from a YAML path or pass an existing dict/list through."""
    if cfg is None:
        return {}
    if isinstance(cfg, str):
        with open(cfg, "r") as f:
            return yaml.safe_load(f)
    if isinstance(cfg, (dict, list)):
        return cfg
    raise TypeError(f"Unsupported config type: {type(cfg)!r}")


# Which legacy style block describes each process group.
_GROUP_STYLE_KEY = {
    "backgrounds": "bkg_hist",
    "signals": "sgn_hist",
    "data": "data_hist",
}


class PlotConfig:
    """Normalised, read-only view over the merged legacy configuration."""

    def __init__(self, page_cfg, page_cfg_custom=None, hist_cfg=None):
        self.page = dict(load_mapping(page_cfg))
        if page_cfg_custom:
            # Legacy semantics: the era file shallow-updates the page config.
            self.page.update(load_mapping(page_cfg_custom))
        self.hist = load_mapping(hist_cfg)

    # -- page-level accessors ----------------------------------------------
    @property
    def page_setup(self) -> dict:
        return self.page.get("page_setup", {}) or {}

    @property
    def legend_cfg(self) -> dict:
        legend_key = self.page_setup.get("legend", "legend")
        return self.page.get(legend_key, {}) or {}

    def text_box_names(self):
        return list(self.page_setup.get("text_boxes", []) or [])

    def text_box(self, name: str) -> dict:
        return self.page.get(name, {}) or {}

    def group_style(self, group: str) -> dict:
        return self.page.get(_GROUP_STYLE_KEY.get(group, ""), {}) or {}

    @property
    def bkg_unc_style(self) -> dict:
        # The bkg histogram references its uncertainty block by name.
        unc_key = self.page.get("bkg_hist", {}).get("unc_hist", "bkg_unc_hist")
        return self.page.get(unc_key, {}) or {}

    # -- per-variable accessors --------------------------------------------
    def hist_desc(self, hist_name: str) -> dict:
        return self.hist.get(hist_name, {}) or {}

    # -- backend selection --------------------------------------------------
    def backend_name(self) -> str:
        """Resolve the style backend: env var > config > default ('mplhep')."""
        env = os.environ.get("PLOTKIT_BACKEND")
        if env:
            return env.strip().lower()
        return str(self.page_setup.get("backend", "mplhep")).strip().lower()

    # -- labels from the era custom file -----------------------------------
    def channel_label(self, channel: str) -> str:
        return (self.page.get("channel_text", {}) or {}).get(channel, channel)

    def region_label(self, region: str) -> str:
        return (self.page.get("customregion_text", {}) or {}).get(region, "")
