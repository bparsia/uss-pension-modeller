"""Chart renderer for the Bluffer's Guide.

Takes a spec dict (parsed from a ```chart block in the markdown) and returns
a (fig, caption) tuple. The spec always has a `type` key; other keys are
optional with sensible defaults.

Chart types:
  real_pension_path   — historical real pension paths, one line per scheme
  fr_history          — funding ratio history, all three bases + CPI overlay
  indexation_rates    — soft cap vs full CPI annual rates
  residual_surplus    — surplus remaining after indexation, per basis
  ci_mechanism        — indexation granted as function of FR (illustrative)
  ci_replay           — historical CI scheme comparison (real pension)
  outcome_boxplot     — final-year real pension distribution, horizontal box per scheme
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent

def _load_fr_histories():
    p = _ROOT / "data" / "uss_valuation_bases.py"
    spec = importlib.util.spec_from_file_location("uss_valuation_bases", p)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.get_fr_histories(list(range(2008, 2026)))

from data.shared import cpi_rate, bootstrap_tuples, USS_2023_VALUATION, EQUITY_REAL_RETURN, GILT_YIELD_10Y
from data.fund_model import FundParams, simulate, soft_cap_indexation

# ---------------------------------------------------------------------------
# Colour palette (consistent with rest of app)
# ---------------------------------------------------------------------------
C = dict(
    uss_tp       = "#444444",
    ucu_prudent  = "#E45756",
    ucu_best_est = "#4C78A8",
    cpi          = "#FFA15A",
    soft_cap     = "#636EFA",
    full_cpi     = "#00CC96",
    proportional = "#4C78A8",
    hybrid       = "#F58518",
    binary       = "#E45756",
)
BASIS_LABEL = {
    "uss_tp":       "USS TP",
    "ucu_prudent":  "UCU Prudent",
    "ucu_best_est": "UCU Best Estimate",
}
SCHEME_LABEL = {
    "soft_cap":     "Soft cap (current USS)",
    "full_cpi":     "Full CPI",
    "proportional": "Proportional CI",
    "hybrid":       "Hybrid CI (soft cap+)",
    "binary":       "Binary CI",
    "none":         "No indexation",
    "statutory":    "Statutory minimum (2.5% cap)",
}
SCHEME_COLOUR = {
    "soft_cap":     C["soft_cap"],
    "full_cpi":     C["full_cpi"],
    "proportional": C["proportional"],
    "hybrid":       C["hybrid"],
    "binary":       C["binary"],
    "none":         "#888888",
    "statutory":    "#BBBBBB",
}
SCHEME_DASH = {
    "soft_cap":     "dot",
    "full_cpi":     "dot",
    "proportional": "solid",
    "hybrid":       "solid",
    "binary":       "dash",
    "none":         "dot",
    "statutory":    "dash",
}

STAT_MIN_CAP = 2.5

def _rgba(h: str, a: float) -> str:
    r, g, b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return f"rgba({r},{g},{b},{a})"

def _ci_indexation(fr: float, cpi: float, scheme: str, target: float) -> float:
    stat_min = min(max(cpi, 0.0), STAT_MIN_CAP)
    surplus  = (fr - 1.0) * 100.0
    if scheme == "soft_cap":   return soft_cap_indexation(cpi)
    if scheme == "full_cpi":   return target
    if scheme == "none":       return 0.0
    if scheme == "statutory":  return min(cpi, STAT_MIN_CAP)
    factor = min(1.0, max(0.0, surplus / target)) if target > 0 else 1.0
    if scheme == "binary":
        idx = target if factor >= 1.0 else 0.0
    elif scheme == "proportional":
        idx = factor * target
    elif scheme == "hybrid":
        floor = soft_cap_indexation(cpi)
        idx   = max(floor, factor * target)
    else:
        idx = factor * target
    return max(idx, stat_min)

# ---------------------------------------------------------------------------
# render(spec) — main entry point
# ---------------------------------------------------------------------------
def render(spec: dict) -> tuple[go.Figure, str]:
    """Return (fig, caption) for the given spec dict."""
    t = spec.get("type", "")
    if t == "real_pension_path":       return _real_pension_path(spec)
    if t == "fr_history":              return _fr_history(spec)
    if t == "indexation_rates":        return _indexation_rates(spec)
    if t == "residual_surplus":        return _residual_surplus(spec)
    if t == "ci_mechanism":            return _ci_mechanism(spec)
    if t == "ci_replay":               return _ci_replay(spec)
    if t == "ci_replay_cumulative":    return _ci_replay_cumulative(spec)
    if t == "outcome_boxplot":         return _outcome_boxplot(spec)
    if t == "fr_affordability":        return _fr_affordability(spec)
    raise ValueError(f"Unknown chart type: {t!r}")

# ---------------------------------------------------------------------------
# 1. real_pension_path
# ---------------------------------------------------------------------------
def _real_pension_path(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      schemes      : comma-separated list of scheme names (default: full_cpi, soft_cap, none)
      start_year   : int (default: 2017)
      pension      : float, starting monthly pension £ (default: 1000)
      show_nominal : bool (default: false) — show nominal £ instead of real
      caption      : str
    """
    schemes      = [s.strip() for s in spec.get("schemes", "full_cpi,soft_cap,none").split(",")]
    start_year   = int(spec.get("start_year", 2017))
    pension0     = float(spec.get("pension", 1000))
    show_nominal = str(spec.get("show_nominal", "false")).lower() == "true"
    caption      = spec.get("caption", "Real pension purchasing power under different indexation approaches.")

    all_years = list(range(start_year, 2026))
    cpi_idx   = {start_year: 1.0}
    for y in all_years[1:]:
        cpi_idx[y] = cpi_idx[y-1] * (1 + cpi_rate(y) / 100)

    fig = go.Figure()
    ref_line = pension0 * cpi_idx[all_years[-1]] if show_nominal else pension0
    label = "Starting pension (nominal)" if show_nominal else "Full purchasing power"
    fig.add_hline(y=ref_line if not show_nominal else pension0,
                  line_dash="dash", line_color="lightgray", line_width=1,
                  annotation_text=label, annotation_position="top left")

    for scheme in schemes:
        p = pension0
        nom_vals = [pension0]
        for y in all_years[1:]:
            idx = _ci_indexation(1.5, cpi_rate(y), scheme, cpi_rate(y))
            p  *= (1 + idx / 100)
            nom_vals.append(p)
        y_vals = nom_vals if show_nominal else [n / cpi_idx[y] for n, y in zip(nom_vals, all_years)]
        fig.add_trace(go.Scatter(
            x=all_years, y=y_vals,
            name=SCHEME_LABEL.get(scheme, scheme),
            line=dict(color=SCHEME_COLOUR.get(scheme, "#888"), width=2,
                      dash=SCHEME_DASH.get(scheme, "solid")),
            hovertemplate=f"{SCHEME_LABEL.get(scheme,scheme)}<br>%{{x}}: £%{{y:,.0f}}<extra></extra>",
        ))

    ylabel = f"Nominal monthly pension (£)" if show_nominal else f"Real monthly pension (£, {start_year} prices)"
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title=ylabel,
        hovermode="x unified", legend_title="",
    )
    return fig, caption

# ---------------------------------------------------------------------------
# 2. fr_history
# ---------------------------------------------------------------------------
def _fr_history(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      bases        : comma-separated (default: uss_tp,ucu_prudent,ucu_best_est)
      highlight    : one basis to bold (default: ucu_best_est)
      show_cpi     : bool (default: true)
      caption      : str
    """
    fr  = _load_fr_histories()
    bases     = [b.strip() for b in spec.get("bases", "uss_tp,ucu_prudent,ucu_best_est").split(",")]
    highlight = spec.get("highlight", "ucu_best_est")
    show_cpi  = spec.get("show_cpi", "true").lower() != "false"
    caption   = spec.get("caption", "USS funding ratio 2008–2025 under three valuation bases.")

    years = [y for y in range(2008, 2026) if y in fr.index]
    fig   = go.Figure()
    fig.add_hline(y=100, line_dash="solid", line_color="black", line_width=2,
                  annotation_text="Fully funded (100%)", annotation_position="top right")

    for b in bases:
        yrs  = [y for y in years if not np.isnan(float(fr.loc[y, b]))]
        vals = [float(fr.loc[y, b]) for y in yrs]
        bold = (b == highlight)
        fig.add_trace(go.Scatter(
            x=yrs, y=vals, name=BASIS_LABEL[b],
            line=dict(color=C[b], width=3 if bold else 1.5,
                      dash="solid" if bold else "dot"),
            hovertemplate=f"{BASIS_LABEL[b]}<br>%{{x}}: %{{y:.0f}}%<extra></extra>",
        ))

    if show_cpi:
        cpis = [cpi_rate(y) for y in years]
        fig.add_trace(go.Bar(
            x=years, y=cpis, name="CPI", marker_color=C["cpi"], opacity=0.35,
            yaxis="y2", hovertemplate="%{x}<br>CPI: %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            yaxis2=dict(title="CPI (%)", ticksuffix="%", overlaying="y",
                        side="right", range=[0, 15], showgrid=False),
        )

    fig.update_layout(
        xaxis_title="Year",
        yaxis=dict(title="Funding ratio (%)", ticksuffix="%"),
        hovermode="x unified", legend_title="",
    )
    return fig, caption

# ---------------------------------------------------------------------------
# 3. indexation_rates
# ---------------------------------------------------------------------------
def _indexation_rates(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      show_cost_diff : bool (default: false) — add bar chart of full-soft gap
      caption        : str
    """
    show_diff = spec.get("show_cost_diff", "false").lower() == "true"
    caption   = spec.get("caption", "Annual indexation rate: soft cap vs full CPI, 2008–2025.")

    years = list(range(2008, 2026))
    cpis  = [cpi_rate(y) for y in years]
    scs   = [soft_cap_indexation(cpi_rate(y)) for y in years]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=cpis, name="Full CPI",
        marker_color=C["cpi"], opacity=0.5,
        hovertemplate="%{x}<br>Full CPI: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=scs, name="Soft cap",
        line=dict(color=C["soft_cap"], width=2.5),
        hovertemplate="%{x}<br>Soft cap: %{y:.1f}%<extra></extra>",
    ))
    if show_diff:
        diffs = [c - s for c, s in zip(cpis, scs)]
        fig.add_trace(go.Bar(
            x=years, y=diffs, name="Gap (full − soft cap)",
            marker_color="#EF553B", opacity=0.7, yaxis="y2",
            hovertemplate="%{x}<br>Gap: %{y:.2f}%<extra></extra>",
        ))
        fig.update_layout(
            yaxis2=dict(title="Gap (%)", ticksuffix="%", overlaying="y",
                        side="right", showgrid=False),
        )
    fig.update_layout(
        xaxis_title="Year", yaxis=dict(title="Indexation rate (%)", ticksuffix="%"),
        hovermode="x unified", legend_title="",
    )
    return fig, caption

# ---------------------------------------------------------------------------
# 4. residual_surplus
# ---------------------------------------------------------------------------
def _residual_surplus(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      bases     : comma-separated (default: uss_tp,ucu_prudent,ucu_best_est)
      scheme    : soft_cap or full_cpi (default: full_cpi)
      highlight : basis to fill (default: ucu_best_est)
      caption   : str
    """
    fr        = _load_fr_histories()
    bases     = [b.strip() for b in spec.get("bases", "uss_tp,ucu_prudent,ucu_best_est").split(",")]
    scheme    = spec.get("scheme", "full_cpi")
    highlight = spec.get("highlight", "ucu_best_est")
    caption   = spec.get("caption", "Residual surplus after indexation as % of liabilities.")

    years = [y for y in range(2008, 2026) if y in fr.index]
    fig   = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="lightgray", line_width=1)

    for b in bases:
        yrs  = [y for y in years if not np.isnan(float(fr.loc[y, b]))]
        rate = soft_cap_indexation if scheme == "soft_cap" else lambda c: c
        vals = [float(fr.loc[y, b]) / (1 + rate(cpi_rate(y)) / 100) - 100 for y in yrs]
        bold = (b == highlight)
        col  = C[b]
        fig.add_trace(go.Scatter(
            x=yrs, y=vals, name=BASIS_LABEL[b],
            line=dict(color=col, width=3 if bold else 1.5,
                      dash="solid" if bold else "dot"),
            fill="tozeroy" if bold else None,
            fillcolor=_rgba(col, 0.10) if bold else None,
            hovertemplate=f"{BASIS_LABEL[b]}<br>%{{x}}: %{{y:+.1f}}% of liabilities<extra></extra>",
        ))

    label = "soft cap" if scheme == "soft_cap" else "full CPI"
    fig.update_layout(
        xaxis_title="Year",
        yaxis=dict(title=f"Residual surplus after {label} (% of liabilities)", ticksuffix="%"),
        hovermode="x unified", legend_title="",
    )
    return fig, caption

# ---------------------------------------------------------------------------
# 5. ci_mechanism
# ---------------------------------------------------------------------------
def _ci_mechanism(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      cpi      : float, illustrative CPI % (default: 5.0)
      schemes  : comma-separated (default: full_cpi,soft_cap,proportional,hybrid,binary)
      caption  : str
    """
    cpi_val = float(spec.get("cpi", 5.0))
    schemes = [s.strip() for s in spec.get("schemes", "full_cpi,soft_cap,proportional,hybrid,binary").split(",")]
    caption = spec.get("caption",
        f"Indexation granted as a function of funding ratio at CPI = {cpi_val:.1f}%.")

    fr_range = np.linspace(0.80, 1.60, 200)
    fig = go.Figure()
    fig.add_vline(x=100, line_dash="dash", line_color="lightgray", line_width=1,
                  annotation_text="100%", annotation_position="top")

    for scheme in schemes:
        y_vals = [_ci_indexation(fr, cpi_val, scheme, cpi_val) for fr in fr_range]
        fig.add_trace(go.Scatter(
            x=fr_range * 100, y=y_vals,
            name=SCHEME_LABEL.get(scheme, scheme),
            line=dict(color=SCHEME_COLOUR.get(scheme, "#888"), width=2,
                      dash=SCHEME_DASH.get(scheme, "solid")),
            hovertemplate=f"{SCHEME_LABEL.get(scheme,scheme)}<br>FR %{{x:.0f}}%: %{{y:.2f}}%<extra></extra>",
        ))
    fig.add_hline(y=min(cpi_val, STAT_MIN_CAP), line_dash="dot", line_color="gray", line_width=1,
                  annotation_text=f"Statutory min ({min(cpi_val,STAT_MIN_CAP):.1f}%)",
                  annotation_position="bottom right")
    fig.update_layout(
        xaxis_title="Funding ratio (%)", xaxis=dict(ticksuffix="%"),
        yaxis_title="Indexation granted (%)", yaxis=dict(ticksuffix="%"),
        hovermode="x unified", legend_title="",
    )
    return fig, caption

# ---------------------------------------------------------------------------
# Shared helper: compute real pension paths for ci_replay and ci_replay_cumulative
# ---------------------------------------------------------------------------
def _replay_paths(
    fr_hist, schemes, basis, start_year, pension0, do_catchup
) -> tuple[list[int], dict[str, list[float]]]:
    """Return (pension_years, {scheme: real_vals}) for all schemes."""
    all_years   = [y for y in range(start_year, 2026) if y in fr_hist.index]
    index_years = all_years[1:]
    cpi_idx = {start_year: 1.0}
    for y in index_years:
        cpi_idx[y] = cpi_idx[y-1] * (1 + cpi_rate(y) / 100)

    pension_years = [start_year] + index_years
    paths = {}
    for scheme in schemes:
        p           = pension0
        pens        = [pension0]
        catchup_gap = 0.0
        for y in index_years:
            fr_val = float(fr_hist.loc[y, basis]) / 100.0 if not np.isnan(float(fr_hist.loc[y, basis])) else 1.5
            cpi_y  = cpi_rate(y)
            target = cpi_y
            idx    = _ci_indexation(fr_val, cpi_y, scheme, target)
            if do_catchup and scheme not in ("full_cpi", "soft_cap", "none"):
                gap_this_year = max(0.0, target - idx)
                catchup_gap  += gap_this_year
                if idx >= target and catchup_gap > 0:
                    surplus_pct = max(0.0, (fr_val - 1.0) * 100.0)
                    budget = max(0.0, surplus_pct - idx)
                    paid = min(catchup_gap, budget)
                    catchup_gap = max(0.0, catchup_gap - paid)
                    idx += paid
            p *= (1 + idx / 100)
            pens.append(p)
        paths[scheme] = [pv / cpi_idx[y] for pv, y in zip(pens, pension_years)]
    return pension_years, paths


# ---------------------------------------------------------------------------
# 6. ci_replay  — historical replay using actual FR data + catch-up tracking
# ---------------------------------------------------------------------------
def _ci_replay(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      schemes    : comma-separated (default: full_cpi,soft_cap,proportional,hybrid)
      basis      : which FR to use for CI affordability (default: ucu_best_est)
      start_year : int (default: 2017)
      pension    : float (default: 1000)
      catchup    : bool (default: true) — apply USS catch-up mechanism
      caption    : str
    """
    fr_hist    = _load_fr_histories()
    schemes    = [s.strip() for s in spec.get("schemes", "full_cpi,soft_cap,proportional,hybrid").split(",")]
    basis      = spec.get("basis", "ucu_best_est")
    start_year = int(spec.get("start_year", 2017))
    pension0   = float(spec.get("pension", 1000))
    do_catchup = spec.get("catchup", "true").lower() != "false"
    caption    = spec.get("caption",
        f"Real pension from {start_year} under each scheme ({BASIS_LABEL.get(basis, basis)} basis).")

    pension_years, paths = _replay_paths(fr_hist, schemes, basis, start_year, pension0, do_catchup)

    fig = go.Figure()
    fig.add_hline(y=pension0, line_dash="dash", line_color="lightgray", line_width=1,
                  annotation_text="Full purchasing power", annotation_position="top left")

    for scheme in schemes:
        fig.add_trace(go.Scatter(
            x=pension_years, y=paths[scheme],
            name=SCHEME_LABEL.get(scheme, scheme),
            line=dict(color=SCHEME_COLOUR.get(scheme, "#888"), width=2,
                      dash=SCHEME_DASH.get(scheme, "solid")),
            hovertemplate=f"{SCHEME_LABEL.get(scheme,scheme)}<br>%{{x}}: £%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title=f"Real monthly pension (£, {start_year} prices)",
        hovermode="x unified", legend_title="",
    )
    return fig, caption


# ---------------------------------------------------------------------------
# 6b. ci_replay_cumulative — total real pension received over the period
# ---------------------------------------------------------------------------
def _ci_replay_cumulative(spec: dict):
    """Same parameters as ci_replay. Returns a summary DataFrame instead of a figure."""
    import pandas as pd
    fr_hist    = _load_fr_histories()
    schemes    = [s.strip() for s in spec.get("schemes", "full_cpi,soft_cap,proportional,hybrid").split(",")]
    basis      = spec.get("basis", "ucu_best_est")
    start_year = int(spec.get("start_year", 2017))
    pension0   = float(spec.get("pension", 1000))
    do_catchup = spec.get("catchup", "true").lower() != "false"
    caption    = spec.get("caption",
        f"Total real pension received {start_year}–2025, starting pension £{pension0:,.0f}/yr ({BASIS_LABEL.get(basis, basis)} basis).")

    pension_years, paths = _replay_paths(fr_hist, schemes, basis, start_year, pension0, do_catchup)
    n_years = len(pension_years)
    full_cpi_total = sum(paths.get("full_cpi", [pension0] * n_years))

    rows = []
    for scheme in schemes:
        total    = sum(paths[scheme])
        shortfall = full_cpi_total - total
        rows.append({
            "Scheme":           SCHEME_LABEL.get(scheme, scheme),
            "Total real £":     f"£{total:,.0f}",
            "vs Full CPI":      f"−£{shortfall:,.0f}" if shortfall > 0 else "—",
            "Avg/yr":           f"£{total/n_years:,.0f}",
        })

    df = pd.DataFrame(rows).set_index("Scheme")
    return df, caption

# ---------------------------------------------------------------------------
# 7. outcome_boxplot — final-year distribution, horizontal boxes
# ---------------------------------------------------------------------------
def _outcome_boxplot(spec: dict) -> tuple[go.Figure, str]:
    """
    spec keys:
      schemes  : comma-separated (default: full_cpi,soft_cap,proportional,hybrid)
      basis    : starting FR basis (default: ucu_best_est) OR "all" for three sub-charts
      pension  : float starting pension (default: 1000)
      n_years  : int projection horizon (default: 20)
      caption  : str
    """
    schemes  = [s.strip() for s in spec.get("schemes", "full_cpi,soft_cap,proportional,hybrid").split(",")]
    basis    = spec.get("basis", "ucu_best_est")
    pension0 = float(spec.get("pension", 1000))
    n_years  = int(spec.get("n_years", 20))
    caption  = spec.get("caption",
        f"Distribution of real pension at year {n_years} across 500 paths.")

    BASIS_FR = {
        "uss_tp":       (1.11, 1.38, 1.05),
        "ucu_prudent":  (1.05, 1.38, 1.05),
        "ucu_best_est": (1.38, 1.38, 1.38),
    }

    # Generate bootstrap paths (same seed as rest of app)
    _all_tuples = bootstrap_tuples()
    _pool = np.array([(t[1], t[2], t[3]) for t in _all_tuples])
    rng   = np.random.default_rng(42)
    idx   = rng.integers(0, len(_pool), size=(500, n_years))
    paths = _pool[idx]  # (500, n_years, 3)

    def _run_basis(b):
        tp_fr, be_fr, pr_fr = BASIS_FR[b]
        results = {}
        for scheme in schemes:
            ci_str = "soft_cap" if scheme == "soft_cap" else \
                     "guaranteed" if scheme == "full_cpi" else \
                     "soft_cap_plus" if scheme == "hybrid" else scheme
            finals = []
            for p_idx in range(500):
                shocks = [(float(paths[p_idx,t,0]),
                           float(paths[p_idx,t,1]),
                           float(paths[p_idx,t,2])) for t in range(n_years)]
                params = FundParams(
                    assets_bn=USS_2023_VALUATION["assets_bn"],
                    tp_fr=tp_fr, be_fr=be_fr, pr_fr=pr_fr,
                )
                states  = simulate(shocks, params, ci_scheme=ci_str)
                pension = pension0
                cum_cpi = 1.0
                for t, s in enumerate(states):
                    pension *= (1 + s.indexation_pct / 100)
                    cum_cpi *= (1 + shocks[t][2] / 100)
                finals.append(pension / cum_cpi)
            results[scheme] = np.array(finals)
        return results

    fig = go.Figure()

    if basis == "all":
        # Three groups of boxes, one per basis
        for b in ["uss_tp", "ucu_prudent", "ucu_best_est"]:
            res = _run_basis(b)
            for scheme in schemes:
                fig.add_trace(go.Box(
                    x=res[scheme],
                    name=f"{SCHEME_LABEL.get(scheme,scheme)} — {BASIS_LABEL[b]}",
                    orientation="h",
                    marker_color=SCHEME_COLOUR.get(scheme, "#888"),
                    boxmean=True,
                    hovertemplate=f"{SCHEME_LABEL.get(scheme,scheme)} ({BASIS_LABEL[b]})<br>%{{x:,.0f}}<extra></extra>",
                ))
    else:
        res = _run_basis(basis)
        for scheme in schemes:
            fig.add_trace(go.Box(
                x=res[scheme],
                name=SCHEME_LABEL.get(scheme, scheme),
                orientation="h",
                marker_color=SCHEME_COLOUR.get(scheme, "#888"),
                boxmean=True,
                hovertemplate=f"{SCHEME_LABEL.get(scheme,scheme)}<br>£%{{x:,.0f}}<extra></extra>",
            ))
        fig.add_vline(x=pension0, line_dash="dash", line_color="lightgray", line_width=1,
                      annotation_text="Starting pension", annotation_position="top right")

    fig.update_layout(
        xaxis_title=f"Real monthly pension at year {n_years} (£, 2023 prices)",
        yaxis_title="",
        showlegend=False,
        height=max(250, 80 * len(schemes) * (3 if basis == "all" else 1)),
    )
    return fig, caption


# ---------------------------------------------------------------------------
# 8. fr_affordability — FR history + cost-of-indexation thresholds
# ---------------------------------------------------------------------------
def _fr_affordability(spec: dict) -> tuple[go.Figure, str]:
    """
    Plots FR lines for each valuation basis alongside the FR level required to
    afford soft-cap and full-CPI indexation each year (i.e. 1 + rate/100 × 100).
    Where the FR line is above the cost line the scheme can afford that indexation.

    spec keys:
      bases       : comma-separated (default: uss_tp, ucu_prudent, ucu_best_est)
      schemes     : comma-separated cost lines (default: soft_cap, full_cpi)
      show_cpi    : bool (default: true) — CPI bars on secondary axis
      start_year  : int (default: 2008)
      caption     : str
    """
    fr      = _load_fr_histories()
    bases      = [b.strip() for b in spec.get("bases", "uss_tp,ucu_prudent,ucu_best_est").split(",")]
    schemes    = [s.strip() for s in spec.get("schemes", "soft_cap,full_cpi").split(",")]
    show_cpi   = spec.get("show_cpi", "true").lower() != "false"
    start_year = int(spec.get("start_year", 2008))
    caption    = spec.get("caption", "USS funding ratio vs cost of indexation.")

    years = [y for y in range(start_year, 2026) if y in fr.index]

    fig = go.Figure()

    # 100% reference line
    fig.add_hline(y=100, line_dash="solid", line_color="black", line_width=2,
                  annotation_text="Fully funded (100%)", annotation_position="top right")

    # FR lines per basis
    for b in bases:
        yrs  = [y for y in years if not np.isnan(float(fr.loc[y, b]))]
        vals = [float(fr.loc[y, b]) for y in yrs]
        fig.add_trace(go.Scatter(
            x=yrs, y=vals, name=BASIS_LABEL[b],
            line=dict(color=C[b], width=2, dash="solid"),
            hovertemplate=f"{BASIS_LABEL[b]}<br>%{{x}}: %{{y:.0f}}%<extra></extra>",
        ))

    # Cost-of-indexation threshold lines
    # "Cost" = FR needed to pay indexation without reducing the FR
    # = current FR × (1 + indexation_rate/100) — simplified: just the indexation uplift as % of assets
    # More precisely: to afford indexation i%, liabilities grow by i%, so you need FR >= 100*(1+i/100)
    COST_COLOUR = {"soft_cap": C["soft_cap"], "full_cpi": C["full_cpi"]}
    for scheme in schemes:
        cost_vals = [100 * (1 + soft_cap_indexation(cpi_rate(y)) / 100)
                     if scheme == "soft_cap"
                     else 100 * (1 + cpi_rate(y) / 100)
                     for y in years]
        fig.add_trace(go.Scatter(
            x=years, y=cost_vals,
            name=f"Cost: {SCHEME_LABEL.get(scheme, scheme)}",
            line=dict(color=COST_COLOUR.get(scheme, "#888"), width=2.5, dash="dash"),
            hovertemplate=f"Cost of {SCHEME_LABEL.get(scheme,scheme)}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    if show_cpi:
        cpis = [cpi_rate(y) for y in years]
        fig.add_trace(go.Bar(
            x=years, y=cpis, name="CPI", marker_color=C["cpi"], opacity=0.25,
            yaxis="y2", hovertemplate="%{x}<br>CPI: %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            yaxis2=dict(title="CPI (%)", ticksuffix="%", overlaying="y",
                        side="right", range=[0, 15], showgrid=False),
        )

    fig.update_layout(
        xaxis_title="Year",
        yaxis=dict(title="Funding ratio / cost threshold (%)", ticksuffix="%"),
        hovermode="x unified", legend_title="",
    )
    return fig, caption
