"""Backend-neutral 1D histogram representation and adapters.

``Hist1D`` is a tiny container around three numpy arrays (bin edges, bin values and
per-bin variances). It deliberately knows nothing about ROOT or matplotlib so that the
plotting code can stay framework agnostic and run standalone.

Adapters are provided to build a :class:`Hist1D` from the objects PlotKit is most often
handed: a ROOT ``TH1`` (the FLAF path), an ``uproot`` histogram (the standalone path) or
raw numpy arrays.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

import numpy as np


@dataclasses.dataclass
class Hist1D:
    """A 1D histogram: ``edges`` has ``len(values) + 1`` entries.

    ``variances`` (the squared per-bin uncertainties) is optional; when missing it is
    assumed to equal ``values`` (Poisson), matching the usual ROOT default.
    """

    edges: np.ndarray
    values: np.ndarray
    variances: Optional[np.ndarray] = None
    name: str = ""

    def __post_init__(self):
        self.edges = np.asarray(self.edges, dtype=float)
        self.values = np.asarray(self.values, dtype=float)
        if self.variances is None:
            self.variances = np.abs(self.values).copy()
        else:
            self.variances = np.asarray(self.variances, dtype=float)
        if len(self.edges) != len(self.values) + 1:
            raise ValueError(
                f"edges ({len(self.edges)}) must have one more entry than "
                f"values ({len(self.values)})"
            )

    # -- derived quantities -------------------------------------------------
    @property
    def widths(self) -> np.ndarray:
        return np.diff(self.edges)

    @property
    def centers(self) -> np.ndarray:
        return 0.5 * (self.edges[1:] + self.edges[:-1])

    @property
    def errors(self) -> np.ndarray:
        return np.sqrt(self.variances)

    def integral(self) -> float:
        return float(np.sum(self.values))

    def copy(self) -> "Hist1D":
        return Hist1D(
            self.edges.copy(), self.values.copy(), self.variances.copy(), self.name
        )

    def scaled(self, factor: float) -> "Hist1D":
        """Return a copy multiplied by ``factor`` (variance scales as ``factor**2``)."""
        return Hist1D(
            self.edges.copy(),
            self.values * factor,
            self.variances * (factor**2),
            self.name,
        )

    def divided_by_width(self) -> "Hist1D":
        """Return a copy with each bin divided by its width (the ``dN/dx`` form)."""
        w = self.widths
        return Hist1D(
            self.edges.copy(),
            self.values / w,
            self.variances / (w**2),
            self.name,
        )


def from_numpy(values, edges, variances=None, name="") -> Hist1D:
    return Hist1D(edges=edges, values=values, variances=variances, name=name)


def from_th1(th1, name: Optional[str] = None) -> Hist1D:
    """Build a :class:`Hist1D` from a ROOT ``TH1`` (overflow/underflow dropped)."""
    n = th1.GetNbinsX()
    edges = np.array([th1.GetBinLowEdge(i) for i in range(1, n + 2)], dtype=float)
    values = np.array([th1.GetBinContent(i) for i in range(1, n + 1)], dtype=float)
    errors = np.array([th1.GetBinError(i) for i in range(1, n + 1)], dtype=float)
    return Hist1D(
        edges=edges,
        values=values,
        variances=errors**2,
        name=name if name is not None else th1.GetName(),
    )


def from_uproot(obj, name: str = "") -> Hist1D:
    """Build a :class:`Hist1D` from an uproot histogram object."""
    values, edges = obj.to_numpy(flow=False)
    variances = None
    try:
        variances = obj.variances(flow=False)
    except Exception:
        try:
            errs = obj.errors(flow=False)
            variances = np.asarray(errs, dtype=float) ** 2
        except Exception:
            variances = None
    return Hist1D(edges=edges, values=values, variances=variances, name=name)


def to_hist1d(obj, name: Optional[str] = None) -> Hist1D:
    """Best-effort coercion of ``obj`` into a :class:`Hist1D`.

    Accepts an existing :class:`Hist1D`, a ROOT ``TH1`` (anything exposing
    ``GetNbinsX``) or an uproot histogram (anything exposing ``to_numpy``).
    """
    if isinstance(obj, Hist1D):
        return obj if name is None else dataclasses.replace(obj, name=name)
    if hasattr(obj, "GetNbinsX"):
        return from_th1(obj, name=name)
    if hasattr(obj, "to_numpy"):
        return from_uproot(obj, name=name or "")
    raise TypeError(f"Cannot convert {type(obj)!r} into a Hist1D")


def stack_total(hists) -> Optional[Hist1D]:
    """Sum a list of :class:`Hist1D` sharing the same binning (or return ``None``)."""
    hists = list(hists)
    if not hists:
        return None
    total = hists[0].copy()
    total.name = "total"
    for h in hists[1:]:
        total.values += h.values
        total.variances += h.variances
    return total
