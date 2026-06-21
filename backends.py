"""Rendering backends.

A backend takes an engine-neutral :class:`~PlotKit.spec.StackSpec` and draws it.  Two are
provided, matching issue #171's requirement to "support both mplhep and cmsstyle":

* :class:`MplhepBackend` -- matplotlib + mplhep.  The **default**; pure Python, no ROOT, so
  it works standalone and is the transparent replacement for the legacy ROOT renderer.
* :class:`CmsstyleBackend` -- ROOT + the official ``cmsstyle`` package.  Selected with
  ``backend: cmsstyle`` (or ``PLOTKIT_BACKEND=cmsstyle``).  ``cmsstyle`` is imported lazily;
  if it (or ROOT) is unavailable the backend warns and falls back to mplhep.

New plot styles add a ``render_<style>`` method here (and a plotter that builds the spec).
"""

from __future__ import annotations

import re
import warnings

import numpy as np

from . import rootcompat as rc
from .spec import StackSpec

# Text in a StackSpec is kept as raw ROOT TLatex; ``_t`` converts it for matplotlib.
_t = rc.tlatex_to_mpl


def _parse_lumi_energy(lumi_text):
    """Extract ``(lumi, energy)`` numbers from a legacy lumi string for cmsstyle."""
    lumi = re.search(r"([\d.]+)\s*fb", str(lumi_text))
    energy = re.search(r"([\d.]+)\s*TeV", str(lumi_text))
    return (
        float(lumi.group(1)) if lumi else None,
        float(energy.group(1)) if energy else None,
    )


class StyleBackend:
    """Abstract backend.  Subclasses implement ``render_stacked`` (and future styles)."""

    name = "base"

    def render_stacked(
        self, spec: StackSpec, output_file: str
    ) -> None:  # pragma: no cover
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# matplotlib / mplhep
# --------------------------------------------------------------------------- #
class MplhepBackend(StyleBackend):
    name = "mplhep"

    def _new_figure(self, spec):
        import matplotlib

        if matplotlib.get_backend().lower() not in ("agg", "pdf", "svg", "ps"):
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import mplhep as hep

        plt.style.use(hep.style.CMS)
        want_ratio = (
            spec.draw_ratio and spec.data is not None and spec.bkg_total is not None
        )
        if want_ratio:
            fig, (ax, rax) = plt.subplots(
                2,
                1,
                figsize=spec.canvas_size,
                sharex=True,
                gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06},
            )
        else:
            fig, ax = plt.subplots(figsize=spec.canvas_size)
            rax = None
        return plt, hep, fig, ax, rax

    @staticmethod
    def _step_band(ax, edges, lo, hi, band):
        ax.fill_between(
            edges,
            np.append(lo, lo[-1]),
            np.append(hi, hi[-1]),
            step="post",
            facecolor="none" if band.hatch else band.color,
            hatch=band.hatch,
            edgecolor=band.color,
            linewidth=0.0,
            alpha=band.alpha,
        )

    def _cms_label(self, hep, ax, spec):
        try:
            hep.cms.label(
                ax=ax,
                data=spec.is_data,
                label=spec.scope_text,
                rlabel=_t(spec.lumi_text),
                loc=0,
            )
        except TypeError:
            # Older mplhep without rlabel: draw CMS text + manual lumi.
            hep.cms.text(spec.scope_text or "", ax=ax)
            if spec.lumi_text:
                ax.text(
                    1.0,
                    1.005,
                    _t(spec.lumi_text),
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                )

    def render_stacked(self, spec: StackSpec, output_file: str) -> None:
        plt, hep, fig, ax, rax = self._new_figure(spec)

        ymax_candidates = [1e-9]

        # stacked backgrounds
        if spec.backgrounds:
            edges = spec.backgrounds[0].hist.edges
            hep.histplot(
                [e.hist.values for e in spec.backgrounds],
                bins=edges,
                stack=True,
                histtype="fill",
                label=[_t(e.label) for e in spec.backgrounds],
                color=[e.color for e in spec.backgrounds],
                edgecolor="black",
                linewidth=0.5,
                ax=ax,
            )
        if spec.bkg_total is not None:
            ymax_candidates.append(
                float(np.max(spec.bkg_total.values + spec.bkg_total.errors))
            )
            if spec.unc_band is not None:
                t = spec.bkg_total
                self._step_band(
                    ax, t.edges, t.values - t.errors, t.values + t.errors, spec.unc_band
                )
                # legend proxy for the band
                ax.fill(
                    np.nan,
                    np.nan,
                    facecolor="none",
                    hatch=spec.unc_band.hatch,
                    edgecolor=spec.unc_band.color,
                    label=_t(spec.unc_band.label),
                )

        # signal overlays (already scaled by the plotter)
        for e in spec.signals:
            hep.histplot(
                e.hist.values,
                bins=e.hist.edges,
                histtype="step",
                color=e.line_color or e.color,
                linewidth=e.line_width,
                linestyle=e.line_style,
                label=_t(e.label),
                ax=ax,
            )
            ymax_candidates.append(float(np.max(e.hist.values)))

        # data points
        if spec.data is not None:
            d = spec.data
            hep.histplot(
                d.hist.values,
                bins=d.hist.edges,
                yerr=d.hist.errors,
                histtype="errorbar",
                color=d.color,
                marker=d.marker or "o",
                markersize=d.marker_size,
                label=_t(d.label),
                ax=ax,
            )
            ymax_candidates.append(float(np.max(d.hist.values + d.hist.errors)))

        # axes ranges / scales
        edges = self._any_edges(spec)
        self._set_xrange(ax, edges)
        ax.set_ylabel(_t(spec.y_title))
        if spec.log_x:
            ax.set_xscale("log")
        if spec.log_y:
            ax.set_yscale("log")
            ax.set_ylim(spec.y_min_log, max(ymax_candidates) * spec.max_y_sf)
        else:
            ax.set_ylim(spec.y_min, max(ymax_candidates) * spec.max_y_sf)

        # CMS + auxiliary labels
        self._cms_label(hep, ax, spec)
        for i, lab in enumerate(spec.extra_labels):
            ax.text(
                0.05,
                0.92 - 0.06 * i,
                _t(lab),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=spec.legend_fontsize or 16,
            )
        ax.legend(loc=spec.legend_loc, frameon=False, fontsize=spec.legend_fontsize)

        # ratio panel
        if rax is not None:
            self._draw_ratio(rax, spec)
            rax.set_xlabel(_t(spec.x_title))
            self._set_xrange(rax, edges)
            if spec.log_x:
                rax.set_xscale("log")
        else:
            ax.set_xlabel(_t(spec.x_title))

        fig.savefig(output_file, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _set_xrange(ax, edges):
        if edges is None:
            return
        lo, hi = float(edges[0]), float(edges[-1])
        if hi > lo:
            ax.set_xlim(lo, hi)

    @staticmethod
    def _any_edges(spec):
        for src in (spec.backgrounds, spec.signals):
            if src:
                return src[0].hist.edges
        if spec.data is not None:
            return spec.data.hist.edges
        if spec.bkg_total is not None:
            return spec.bkg_total.edges
        return None

    def _draw_ratio(self, rax, spec):
        total, d = spec.bkg_total, spec.data
        with np.errstate(divide="ignore", invalid="ignore"):
            safe = total.values > 0
            ratio = np.where(safe, d.hist.values / total.values, np.nan)
            ratio_err = np.where(
                safe, d.hist.errors / np.where(safe, total.values, 1), np.nan
            )
            rel = np.where(safe, total.errors / np.where(safe, total.values, 1), 0.0)
        if spec.unc_band is not None:
            self._step_band(rax, total.edges, 1 - rel, 1 + rel, spec.unc_band)
        rax.axhline(1.0, color="black", linewidth=1.0, linestyle="--")
        rax.errorbar(
            d.hist.centers,
            ratio,
            yerr=ratio_err,
            fmt="o",
            color=d.color,
            markersize=d.marker_size,
        )
        rax.set_ylim(spec.ratio_min, spec.ratio_max)
        rax.set_ylabel(_t(spec.ratio_title))


# --------------------------------------------------------------------------- #
# ROOT / cmsstyle
# --------------------------------------------------------------------------- #
class CmsstyleBackend(StyleBackend):
    name = "cmsstyle"

    def _to_th1(self, ROOT, hist, name):
        th = ROOT.TH1D(
            name, name, len(hist.values), np.asarray(hist.edges, dtype="float64")
        )
        for i, (v, e) in enumerate(zip(hist.values, hist.errors), start=1):
            th.SetBinContent(i, float(v))
            th.SetBinError(i, float(e))
        th.SetDirectory(0)
        return th

    @staticmethod
    def _root_color(ROOT, rgb):
        if isinstance(rgb, str):
            return ROOT.TColor.GetColor(rgb)
        return ROOT.TColor.GetColor(float(rgb[0]), float(rgb[1]), float(rgb[2]))

    def render_stacked(self, spec: StackSpec, output_file: str) -> None:
        try:
            import ROOT
            import cmsstyle as CMS
        except Exception as exc:  # ROOT or cmsstyle missing
            warnings.warn(
                f"cmsstyle backend unavailable ({exc}); falling back to mplhep.",
                RuntimeWarning,
            )
            return MplhepBackend().render_stacked(spec, output_file)

        ROOT.gROOT.SetBatch(True)
        CMS.setCMSStyle()
        CMS.ResetAdditionalInfo()
        for lab in spec.extra_labels:
            CMS.AppendAdditionalInfo(lab)  # raw ROOT TLatex -- rendered natively
        # cmsstyle wants numeric lumi/energy; recover them from the legacy string.
        lumi_val, energy_val = _parse_lumi_energy(spec.lumi_text)
        if energy_val is not None:
            CMS.SetEnergy(energy_val)
        CMS.SetLumi(lumi_val if lumi_val is not None else None, run="")
        CMS.SetExtraText(spec.scope_text)

        edges = MplhepBackend._any_edges(spec)
        x_min, x_max = float(edges[0]), float(edges[-1])
        ymax = 1e-9
        keep = []  # keep python refs alive

        stack = ROOT.THStack("stack", "")
        for i, e in enumerate(spec.backgrounds):
            th = self._to_th1(ROOT, e.hist, f"bkg_{i}")
            th.SetFillColor(self._root_color(ROOT, e.color))
            th.SetLineColor(ROOT.kBlack)
            th.SetLineWidth(1)
            stack.Add(th)
            keep.append(th)
        if spec.bkg_total is not None:
            ymax = max(
                ymax, float(np.max(spec.bkg_total.values + spec.bkg_total.errors))
            )
        if spec.data is not None:
            ymax = max(
                ymax, float(np.max(spec.data.hist.values + spec.data.hist.errors))
            )

        y_min = spec.y_min_log if spec.log_y else spec.y_min
        y_max = ymax * spec.max_y_sf

        if spec.draw_ratio and spec.data is not None and spec.bkg_total is not None:
            canv = CMS.cmsDiCanvas(
                "c",
                x_min,
                x_max,
                y_min,
                y_max,
                spec.ratio_min,
                spec.ratio_max,
                spec.x_title,
                spec.y_title,
                spec.ratio_title,
                square=True,
            )
            canv.cd(1)
        else:
            canv = CMS.cmsCanvas(
                "c",
                x_min,
                x_max,
                y_min,
                y_max,
                spec.x_title,
                spec.y_title,
                square=True,
            )
        if spec.log_y:
            ROOT.gPad.SetLogy(True)
        if spec.log_x:
            ROOT.gPad.SetLogx(True)

        leg = CMS.cmsLeg(0.55, 0.6, 0.92, 0.9)
        stack.Draw("HIST SAME")
        keep.append(stack)
        for i, e in enumerate(spec.backgrounds):
            leg.AddEntry(keep[i], e.label, "f")

        # background uncertainty band
        if spec.bkg_total is not None and spec.unc_band is not None:
            band = self._to_th1(ROOT, spec.bkg_total, "bkg_unc")
            band.SetFillColor(self._root_color(ROOT, spec.unc_band.color))
            band.SetFillStyle(3013)
            band.SetMarkerSize(0)
            band.Draw("E2 SAME")
            keep.append(band)
            leg.AddEntry(band, spec.unc_band.label, "f")

        for i, e in enumerate(spec.signals):
            th = self._to_th1(ROOT, e.hist, f"sig_{i}")
            th.SetLineColor(self._root_color(ROOT, e.line_color or e.color))
            th.SetLineWidth(int(e.line_width))
            th.SetLineStyle(2 if e.line_style == "--" else 1)
            th.SetFillStyle(0)
            th.Draw("HIST SAME")
            keep.append(th)
            leg.AddEntry(th, e.label, "l")

        if spec.data is not None:
            d = self._to_th1(ROOT, spec.data.hist, "data")
            d.SetMarkerStyle(20)
            d.SetLineColor(ROOT.kBlack)
            d.Draw("PE SAME")
            keep.append(d)
            leg.AddEntry(d, spec.data.label, "pe")

        CMS.CMS_lumi(ROOT.gPad)  # draw CMS + lumi on the active (main) pad

        # ratio panel
        if spec.draw_ratio and spec.data is not None and spec.bkg_total is not None:
            canv.cd(2)
            ratio = self._to_th1(ROOT, spec.data.hist, "ratio")
            total = self._to_th1(ROOT, spec.bkg_total, "ratio_den")
            ratio.Divide(total)
            ratio.SetMarkerStyle(20)
            ratio.Draw("PE SAME")
            keep.append(ratio)
            keep.append(total)

        CMS.SaveCanvas(canv, output_file)


_BACKENDS = {
    "mplhep": MplhepBackend,
    "matplotlib": MplhepBackend,
    "cmsstyle": CmsstyleBackend,
    "root": CmsstyleBackend,
}


def get_backend(name: str) -> StyleBackend:
    """Return a backend instance by name (default mplhep; unknown names warn)."""
    cls = _BACKENDS.get((name or "mplhep").strip().lower())
    if cls is None:
        warnings.warn(f"Unknown backend {name!r}; using mplhep.", RuntimeWarning)
        cls = MplhepBackend
    return cls()
