"""Page 4 — Conditional Indexation: how schemes distribute surplus.

Historical replay uses actual FR data from uss_valuation_bases.py to compute
CI factors year by year — no forward fund simulation. This keeps the replay
grounded in actual history, exactly as Page 2 does.

Two steps:
  Step 1 — CI capped at CPI: schemes pay between stat min and full CPI depending
            on the fund's position. Valuation basis is the dominant driver.
  Step 2 — CI with upside: target above CPI; surplus above full CPI is
            distributed as additional real enhancement.

Stochastic projections follow the same two-step logic forward from 2023.
"""
import importlib.util
from pathlib import Path
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from data.shared import (bootstrap_tuples, USS_2023_VALUATION, cpi_rate)
from data.fund_model import FundParams, simulate, soft_cap_indexation
from styles import placeholder

st.title("Conditional indexation: linking pension increases to fund health")

placeholder(
    "The previous pages showed a tension: the soft cap protects the fund in high-inflation "
    "years but permanently cuts pensioners' purchasing power. Full indexation preserves "
    "purchasing power but is unaffordable when the fund is in deficit. Conditional "
    "indexation (CI) is the middle path — the grant is linked to what the fund can "
    "actually afford. This page works through that idea in two steps: first, how CI "
    "schemes behave when the target is simply CPI (replacing the soft cap); then, what "
    "happens when the target is set above CPI so that surplus is actively distributed "
    "back to pensioners."
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_PATHS    = 500
N_YEARS    = 20
SEED       = 42
START_YEAR = 2023

BLUE   = "#4C78A8"
RED    = "#E45756"
DARK   = "#444444"
AMBER  = "#F58518"
GREEN  = "#54A24B"
PURPLE = "#9D69C7"

BASIS_COLS = {
    "USS TP":            DARK,
    "UCU Prudent":       RED,
    "UCU Best Estimate": BLUE,
}
BASIS_KEYS = {
    "USS TP":            "uss_tp",
    "UCU Prudent":       "ucu_prudent",
    "UCU Best Estimate": "ucu_best_est",
}

def rgba(hex_col: str, alpha: float) -> str:
    r, g, b = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ---------------------------------------------------------------------------
# Load historical FR data (same source as Page 2)
# ---------------------------------------------------------------------------
_vb_path = Path(__file__).parent.parent / "data" / "uss_valuation_bases.py"
_fr_histories = None
if _vb_path.exists():
    try:
        _spec = importlib.util.spec_from_file_location("uss_valuation_bases", _vb_path)
        _vb   = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_vb)
        _fr_histories = _vb.get_fr_histories(list(range(2008, 2026)))
    except Exception as e:
        st.warning(f"Could not load valuation bases: {e}")

if _fr_histories is None:
    st.error("Historical FR data not available.")
    st.stop()

ALL_HIST_YEARS = [y for y in range(2008, 2026) if y in _fr_histories.index]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Parameters")

starting_pension = st.sidebar.number_input(
    "Starting monthly pension (£)", min_value=100, max_value=10000, value=1000, step=100,
)

replay_start = st.sidebar.selectbox(
    "Replay start year",
    options=list(range(2008, 2024)),
    index=list(range(2008, 2024)).index(2017),
)

ci_basis_label = st.sidebar.selectbox(
    "CI affordability basis",
    list(BASIS_KEYS.keys()),
    index=2,  # default: UCU Best Estimate
    help="Which funding ratio is used to determine how much CI the fund can afford.",
)
ci_basis_key = BASIS_KEYS[ci_basis_label]

st.sidebar.divider()
st.sidebar.subheader("Step 2: upside target")
target_real = st.sidebar.slider(
    "Real enhancement above CPI (%)",
    min_value=0.0, max_value=3.0, value=1.0, step=0.25,
    help="The indexation target above CPI when the fund has surplus to distribute.",
)

st.sidebar.divider()
st.sidebar.subheader("Hybrid floor")
FLOOR_OPTIONS = {
    "Soft cap+ (floor = soft cap formula)": "soft_cap_plus",
    "50% of target":                        "hybrid_50",
    "25% of target":                        "hybrid_25",
}
floor_label = st.sidebar.selectbox("Floor for hybrid CI", list(FLOOR_OPTIONS))
floor_mode  = FLOOR_OPTIONS[floor_label]

catchup_on = st.sidebar.checkbox(
    "Enable catch-up", value=True,
    help="Accumulate missed indexation and repay from surplus in good years.",
)

st.sidebar.divider()
st.sidebar.subheader("Projections starting basis")
PROJ_BASIS_OPTIONS = {
    "USS TP (111%)":            (1.11, 1.38, 1.05),
    "UCU Prudent (105%)":       (1.05, 1.38, 1.05),
    "UCU Best Estimate (138%)": (1.38, 1.38, 1.38),
}
proj_basis_label = st.sidebar.selectbox("Starting FR for projections", list(PROJ_BASIS_OPTIONS))
tp_fr_start, be_fr_start, pr_fr_start = PROJ_BASIS_OPTIONS[proj_basis_label]

# ---------------------------------------------------------------------------
# CI factor computation from FR (no fund simulation)
# ---------------------------------------------------------------------------
STAT_MIN_CAP = 2.5  # statutory minimum cap

def ci_indexation(fr: float, cpi: float, scheme: str, target_pct: float) -> float:
    """Compute indexation granted given funding ratio, CPI, scheme, and target."""
    stat_min = min(max(cpi, 0.0), STAT_MIN_CAP)
    surplus_pct = (fr - 1.0) * 100.0  # surplus as % of liabilities

    if scheme == "soft_cap":
        return soft_cap_indexation(cpi)

    if scheme == "guaranteed":
        return target_pct

    # Affordable factor: how much of target can surplus cover?
    if target_pct <= 0:
        factor = 1.0
    else:
        factor = min(1.0, max(0.0, surplus_pct / target_pct))

    if scheme == "binary":
        idx = target_pct if factor >= 1.0 else 0.0

    elif scheme == "proportional":
        idx = factor * target_pct

    elif scheme == "soft_cap_plus":
        floor = soft_cap_indexation(cpi)
        upside = max(0.0, target_pct - floor)
        upside_factor = min(1.0, max(0.0, surplus_pct / target_pct)) if target_pct > 0 else 1.0
        idx = floor + upside_factor * upside

    elif scheme in ("hybrid_50", "hybrid_25"):
        frac  = 0.5 if scheme == "hybrid_50" else 0.25
        floor = frac * target_pct
        upside = max(0.0, target_pct - floor)
        upside_factor = min(1.0, max(0.0, surplus_pct / target_pct)) if target_pct > 0 else 1.0
        idx = floor + upside_factor * upside
    else:
        idx = factor * target_pct

    return max(idx, stat_min)


def replay_pension(years: list, scheme: str, target_real_add: float,
                   basis_key: str, catchup: bool) -> tuple[list, list]:
    """
    Compute pension path and FR path for a given scheme over the replay years.
    Returns (pension_values, fr_values) both indexed to `years`.
    pension_values[0] = starting_pension at years[0].
    fr_values[i] = FR at years[i] (pre-indexation, i.e. the historical value).
    """
    pension = float(starting_pension)
    pensions = [pension]
    frs = []
    gap = 0.0  # catch-up gap

    for i, y in enumerate(years):
        fr_raw = _fr_histories.loc[y, basis_key]
        if np.isnan(float(fr_raw)):
            fr_raw = 1.0  # fallback for pre-2017 UCU years
        fr = float(fr_raw) / 100.0  # stored as %, convert to ratio

        cpi = cpi_rate(y)
        target = cpi + target_real_add

        idx = ci_indexation(fr, cpi, scheme, target)

        # Catch-up: if factor=1 and surplus remains, pay down gap
        if catchup and gap > 0:
            stat_min = min(max(cpi, 0.0), STAT_MIN_CAP)
            full_idx_fr = fr / (1 + idx / 100)  # post-indexation FR
            if full_idx_fr > 1.0:
                # remaining surplus as % of liabilities ≈ (full_idx_fr - 1) * 100
                extra_capacity = (full_idx_fr - 1.0) * 100.0
                catchup_paid = min(gap, extra_capacity)
                idx += catchup_paid
                gap = max(0.0, gap - catchup_paid)

        gap += max(0.0, target - idx)

        pension = pension * (1 + idx / 100)
        pensions.append(pension)
        frs.append(fr * 100.0)

    return pensions, frs


# Replay year range (filtered to years with data for the selected CI basis)
_replay_raw = [y for y in ALL_HIST_YEARS if y >= replay_start]
# UCU bases only available from 2017 — fall back to 1.0 if earlier (handled in replay_pension)
replay_years = _replay_raw

# CPI index for deflation
_cpi_index = {replay_years[0]: 1.0}
for y in replay_years[1:]:
    _cpi_index[y] = _cpi_index[replay_years[0]] * (
        _fr_histories.loc[y, "uss_tp"]  # just need CPI, not FR
    )
# Rebuild properly
_cpi_idx = {replay_years[0]: 1.0}
for y in replay_years[1:]:
    _cpi_idx[y] = _cpi_idx[y - 1] * (1 + cpi_rate(y) / 100) if y - 1 in _cpi_idx else 1.0

SCHEME_DEFS = {
    "Soft cap (current)": dict(scheme="soft_cap",    colour=DARK,   dash="dot"),
    "Full CPI":           dict(scheme="guaranteed",  colour=GREEN,  dash="dot"),
    "Proportional CI":    dict(scheme="proportional",colour=BLUE,   dash="solid"),
    "Hybrid CI":          dict(scheme=floor_mode,    colour=AMBER,  dash="solid"),
    "Binary CI":          dict(scheme="binary",      colour=RED,    dash="dash"),
}

# ---------------------------------------------------------------------------
# Section 1: The CI mechanism
# ---------------------------------------------------------------------------
st.subheader("How the CI factor works")

placeholder(
    "The core idea is simple: before granting indexation, the trustee checks whether "
    "the fund can afford it. The CI factor (0–1) is the fraction of the target that "
    "the fund's surplus can cover. If granting the full target leaves the fund in "
    "surplus, factor = 1. If the fund is exactly at break-even, factor = 0 and only "
    "the statutory minimum is paid. In between, the factor scales with the surplus."
)

_cpi_ex = st.slider("Illustrative CPI (%)", min_value=1.0, max_value=12.0, value=5.0, step=0.5)
_target_ex = _cpi_ex  # step 1: target = CPI
_fr_range = np.linspace(0.80, 1.60, 200)

fig_mech = go.Figure()
fig_mech.add_vline(x=100, line_dash="dash", line_color="lightgray", line_width=1,
                   annotation_text="100%", annotation_position="top")
for name, cfg in SCHEME_DEFS.items():
    y_vals = [ci_indexation(fr, _cpi_ex, cfg["scheme"], _target_ex) for fr in _fr_range]
    fig_mech.add_trace(go.Scatter(
        x=_fr_range * 100, y=y_vals,
        name=name, line=dict(color=cfg["colour"], width=2, dash=cfg["dash"]),
        hovertemplate=f"{name}<br>FR %{{x:.0f}}%: %{{y:.2f}}%<extra></extra>",
    ))
fig_mech.add_hline(y=min(_cpi_ex, 2.5), line_dash="dot", line_color="gray", line_width=1,
                   annotation_text=f"Statutory min ({min(_cpi_ex, 2.5):.1f}%)",
                   annotation_position="bottom right")
fig_mech.update_layout(
    xaxis_title="Funding ratio (%)", xaxis=dict(ticksuffix="%"),
    yaxis_title="Indexation granted (%)", yaxis=dict(ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_mech, use_container_width=True)
st.caption(
    f"Figure 1. Indexation granted as a function of funding ratio at CPI = {_cpi_ex:.1f}%. "
    "Proportional CI rises linearly from the statutory minimum. "
    "Hybrid CI guarantees a floor. Binary pays all or nothing at the affordability threshold."
)

# ---------------------------------------------------------------------------
# Section 2: Step 1 — CI schemes with target = CPI
# ---------------------------------------------------------------------------
st.subheader("Step 1: CI schemes replacing the soft cap (target = CPI)")

placeholder(
    "Here the CI target is simply full CPI — no upside. The schemes differ only in "
    "how they handle underfunding: proportional pays a fraction of CPI; hybrid guarantees "
    "a floor; binary pays all or nothing. Soft cap is shown for comparison. "
    "The key question is: does valuation methodology matter more than scheme design? "
    "Toggle the CI affordability basis in the sidebar to find out."
)

# Build pension + FR paths for each scheme under target = CPI
_step1_pensions = {}
_step1_frs      = {}
for name, cfg in SCHEME_DEFS.items():
    pvals, fvals = replay_pension(
        replay_years, cfg["scheme"], target_real_add=0.0,
        basis_key=ci_basis_key, catchup=catchup_on,
    )
    _step1_pensions[name] = pvals
    _step1_frs[name]      = fvals

# --- Real pension chart ---
fig_s1_real = go.Figure()
fig_s1_real.add_hline(
    y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power", annotation_position="top left",
)
pension_years = [replay_years[0]] + replay_years  # len = len(replay_years) + 1

for name, cfg in SCHEME_DEFS.items():
    pvals = _step1_pensions[name]
    real_vals = [p / _cpi_idx.get(y, 1.0) for p, y in zip(pvals, pension_years)]
    fig_s1_real.add_trace(go.Scatter(
        x=pension_years, y=real_vals, name=name,
        line=dict(color=cfg["colour"], width=2, dash=cfg["dash"]),
        hovertemplate=f"{name}<br>%{{x}}: £%{{y:,.0f}} real<extra></extra>",
    ))
fig_s1_real.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Monthly pension (£, {replay_years[0]} prices)",
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_s1_real, use_container_width=True)
st.caption(
    f"Figure 2. Real pension (CPI-deflated) under each scheme, {replay_years[0]}–{replay_years[-1]}. "
    f"CI affordability basis: {ci_basis_label}. Starting pension £{starting_pension:,}/month."
)

# --- FR chart: show the selected basis across schemes ---
placeholder(
    "The funding ratio below shows the selected basis across all schemes. Full CPI and "
    "guaranteed CI draw down the surplus fastest; proportional CI self-limits as the "
    "surplus shrinks. Switch the CI basis in the sidebar to see how different "
    "valuations change the picture."
)

fig_s1_fr = go.Figure()
fig_s1_fr.add_hline(y=100, line_dash="solid", line_color=RED, line_width=1.5,
                    annotation_text="100%", annotation_position="bottom right",
                    annotation_font=dict(color=RED))
for name, cfg in SCHEME_DEFS.items():
    fvals = _step1_frs[name]
    fig_s1_fr.add_trace(go.Scatter(
        x=replay_years, y=fvals, name=name,
        line=dict(color=cfg["colour"], width=2, dash=cfg["dash"]),
        hovertemplate=f"{name}<br>%{{x}}: FR %{{y:.0f}}%<extra></extra>",
    ))
fig_s1_fr.update_layout(
    xaxis_title="Year",
    yaxis=dict(title=f"Funding ratio — {ci_basis_label} (%)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_s1_fr, use_container_width=True)
st.caption(
    f"Figure 3. {ci_basis_label} funding ratio path under each scheme. "
    "Note: this uses the historical FR directly; it is not a forward simulation."
)

# Summary table step 1
_s1_rows = []
for name in SCHEME_DEFS:
    p_end  = _step1_pensions[name][-1]
    p_real = p_end / _cpi_idx.get(replay_years[-1], 1.0)
    chg    = 100 * (p_real / starting_pension - 1)
    _s1_rows.append({
        "Scheme": name,
        f"Nominal {replay_years[-1]}": f"£{p_end:,.0f}",
        f"Real {replay_years[-1]}":    f"£{p_real:,.0f}",
        "Real change":                 f"{chg:+.1f}%",
    })
st.dataframe(pd.DataFrame(_s1_rows).set_index("Scheme"), use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Valuation basis comparison — proportional CI
# ---------------------------------------------------------------------------
st.subheader("Does the valuation basis matter more than the scheme design?")

placeholder(
    "Under the UCU Best Estimate basis, proportional CI converges on full CPI almost "
    "every year — the fund is well enough capitalised that the CI factor is always 1. "
    "Under the USS TP basis, the CI factor is constrained in deficit years. This "
    "comparison isolates the valuation question: the same scheme can look very different "
    "depending on which FR number you use as the affordability gate."
)

fig_basis = go.Figure()
fig_basis.add_hline(
    y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power", annotation_position="top left",
)
for basis_name, basis_key in BASIS_KEYS.items():
    pvals, _ = replay_pension(
        replay_years, "proportional", target_real_add=0.0,
        basis_key=basis_key, catchup=catchup_on,
    )
    real_vals = [p / _cpi_idx.get(y, 1.0) for p, y in zip(pvals, pension_years)]
    col   = BASIS_COLS[basis_name]
    fig_basis.add_trace(go.Scatter(
        x=pension_years, y=real_vals, name=f"Prop. CI — {basis_name}",
        line=dict(color=col, width=2.5),
        hovertemplate=f"Prop. CI ({basis_name})<br>%{{x}}: £%{{y:,.0f}}<extra></extra>",
    ))
# Add soft cap for reference
sc_pvals, _ = replay_pension(replay_years, "soft_cap", 0.0, "uss_tp", False)
sc_real = [p / _cpi_idx.get(y, 1.0) for p, y in zip(sc_pvals, pension_years)]
fig_basis.add_trace(go.Scatter(
    x=pension_years, y=sc_real, name="Soft cap (reference)",
    line=dict(color=DARK, width=1.5, dash="dot"),
    hovertemplate="Soft cap<br>%{x}: £%{y:,.0f}<extra></extra>",
))
fig_basis.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Real monthly pension (£, {replay_years[0]} prices)",
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_basis, use_container_width=True)
st.caption(
    "Figure 4. Proportional CI real pension under all three valuation bases vs soft cap. "
    "The gap between bases shows how much the affordability determination depends on "
    "methodology, not fund performance."
)

# ---------------------------------------------------------------------------
# Section 4: Step 2 — CI with upside (target > CPI)
# ---------------------------------------------------------------------------
st.subheader(f"Step 2: using surplus to enhance indexation (target = CPI + {target_real:.2g}%)")

placeholder(
    f"The soft cap and full-CPI CI both cap the grant at CPI. But if the fund has "
    f"substantial surplus, why stop there? Setting the target above CPI — here CPI + "
    f"{target_real:.2g}% — allows the CI mechanism to distribute real gains to pensioners "
    f"when the fund can afford it. This is the 'upside' that the current soft cap "
    f"scheme does not capture. The same proportionality applies: if the surplus is "
    f"insufficient for the full enhanced target, the factor scales down."
) if target_real > 0 else placeholder(
    "Set the 'Real enhancement above CPI' slider in the sidebar above 0% to see "
    "how upside distribution works."
)

if target_real > 0:
    _step2_pensions = {}
    for name, cfg in SCHEME_DEFS.items():
        if cfg["scheme"] == "soft_cap":
            # Soft cap is unchanged by target setting
            pvals, _ = replay_pension(replay_years, "soft_cap", 0.0, ci_basis_key, catchup_on)
        else:
            pvals, _ = replay_pension(
                replay_years, cfg["scheme"], target_real_add=target_real,
                basis_key=ci_basis_key, catchup=catchup_on,
            )
        _step2_pensions[name] = pvals

    fig_s2 = go.Figure()
    fig_s2.add_hline(
        y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
        annotation_text="Full purchasing power", annotation_position="top left",
    )
    for name, cfg in SCHEME_DEFS.items():
        pvals = _step2_pensions[name]
        real_vals = [p / _cpi_idx.get(y, 1.0) for p, y in zip(pvals, pension_years)]
        fig_s2.add_trace(go.Scatter(
            x=pension_years, y=real_vals, name=name,
            line=dict(color=cfg["colour"], width=2, dash=cfg["dash"]),
            hovertemplate=f"{name}<br>%{{x}}: £%{{y:,.0f}} real<extra></extra>",
        ))
    # Add step 1 proportional for comparison
    pvals_s1, _ = replay_pension(replay_years, "proportional", 0.0, ci_basis_key, catchup_on)
    real_s1 = [p / _cpi_idx.get(y, 1.0) for p, y in zip(pvals_s1, pension_years)]
    fig_s2.add_trace(go.Scatter(
        x=pension_years, y=real_s1, name="Prop. CI — CPI only (step 1)",
        line=dict(color=BLUE, width=1.5, dash="dot"),
        hovertemplate="Prop. CI (CPI only)<br>%{x}: £%{y:,.0f}<extra></extra>",
    ))
    fig_s2.update_layout(
        xaxis_title="Year",
        yaxis_title=f"Real monthly pension (£, {replay_years[0]} prices)",
        hovermode="x unified", legend_title="",
    )
    st.plotly_chart(fig_s2, use_container_width=True)
    st.caption(
        f"Figure 5. Real pension with target = CPI + {target_real:.2g}% under each scheme. "
        f"CI basis: {ci_basis_label}. Dotted blue = proportional CI at CPI-only target for comparison."
    )

    _s2_rows = []
    for name in SCHEME_DEFS:
        p_end  = _step2_pensions[name][-1]
        p_real = p_end / _cpi_idx.get(replay_years[-1], 1.0)
        chg    = 100 * (p_real / starting_pension - 1)
        _s2_rows.append({
            "Scheme": name,
            f"Nominal {replay_years[-1]}": f"£{p_end:,.0f}",
            f"Real {replay_years[-1]}":    f"£{p_real:,.0f}",
            "Real change":                 f"{chg:+.1f}%",
        })
    st.dataframe(pd.DataFrame(_s2_rows).set_index("Scheme"), use_container_width=True)

    placeholder(
        f"With a CPI + {target_real:.2g}% target and a well-funded scheme (UCU BE basis), "
        "proportional CI can deliver genuine real gains to pensioners — the surplus is "
        "large enough to cover the enhanced target in most years. Under the TP basis, "
        "the fund's apparent deficit constrains even the enhanced grant. This again "
        "underscores that the choice of valuation methodology is not a technicality — "
        "it determines whether pensioners receive real benefit increases or real cuts."
    )

# ---------------------------------------------------------------------------
# Section 5: Stochastic projections
# ---------------------------------------------------------------------------
st.subheader("Forward projections: CI scheme outcomes from 2023")

placeholder(
    "Using the same 500 bootstrap paths as the previous page, we now run each CI scheme "
    "forward from the 2023 valuation. This shows the range of real pension outcomes "
    "and how each scheme's self-limiting or floor properties affect the distribution."
)

horizon_years = st.select_slider(
    "Display horizon (years)", options=[5, 10, 15, 20], value=20,
)
_h = horizon_years
proj_years_list = list(range(START_YEAR + 1, START_YEAR + N_YEARS + 1))[:_h]

# Generate paths
_all_tuples = bootstrap_tuples()
_all_pool   = np.array([(t[1], t[2], t[3]) for t in _all_tuples])

@st.cache_data
def _gen_paths(seed: int, n: int, ny: int) -> bytes:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(_all_pool), size=(n, ny))
    return _all_pool[idx].tobytes()

_paths_bytes = _gen_paths(SEED, N_PATHS, N_YEARS)
_paths = np.frombuffer(_paths_bytes, dtype=np.float64).reshape(N_PATHS, N_YEARS, 3)

PROJ_SCHEMES = {
    "Soft cap":        dict(ci_scheme="soft_cap",    colour=DARK,  dash="dot"),
    "Proportional CI": dict(ci_scheme="proportional",colour=BLUE,  dash="solid"),
    "Hybrid CI":       dict(ci_scheme="soft_cap_plus",colour=AMBER, dash="solid"),
    "Full CPI":        dict(ci_scheme="guaranteed",  colour=GREEN, dash="dot"),
}

@st.cache_data
def run_proj_schemes(paths_bytes: bytes, tp_fr: float, be_fr: float, pr_fr: float,
                     catchup: bool, t_real: float) -> dict:
    _p = np.frombuffer(paths_bytes, dtype=np.float64).reshape(N_PATHS, N_YEARS, 3)
    results = {}
    for name, cfg in PROJ_SCHEMES.items():
        real_pensions = np.zeros((N_PATHS, N_YEARS))
        fr_tp_arr     = np.zeros((N_PATHS, N_YEARS))

        for p_idx in range(N_PATHS):
            shocks = [(float(_p[p_idx, t, 0]),
                       float(_p[p_idx, t, 1]),
                       float(_p[p_idx, t, 2])) for t in range(N_YEARS)]
            params = FundParams(
                assets_bn=USS_2023_VALUATION["assets_bn"],
                tp_fr=tp_fr, be_fr=be_fr, pr_fr=pr_fr,
                target_real=t_real,
                catchup_window=0 if catchup else 999999,
            )
            states = simulate(shocks, params, ci_scheme=cfg["ci_scheme"])
            pension = 1000.0
            cum_cpi = 1.0
            for t, s in enumerate(states):
                pension *= (1 + s.indexation_pct / 100)
                cum_cpi *= (1 + shocks[t][2] / 100)
                real_pensions[p_idx, t] = pension / cum_cpi
                fr_tp_arr[p_idx, t]     = s.fr_tp * 100

        results[name] = dict(real_pension=real_pensions, fr_tp=fr_tp_arr)
    return results

proj_results = run_proj_schemes(
    _paths_bytes, tp_fr_start, be_fr_start, pr_fr_start, catchup_on, target_real,
)

def pct(arr, p): return np.percentile(arr, p, axis=0)

def fan_traces(arr, years, colour, name):
    p10, p25, p75, p90 = pct(arr, 10), pct(arr, 25), pct(arr, 75), pct(arr, 90)
    med = pct(arr, 50)
    return [
        go.Scatter(x=years + years[::-1], y=list(p90) + list(p10[::-1]),
                   fill="toself", fillcolor=rgba(colour, 0.10),
                   line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=years + years[::-1], y=list(p75) + list(p25[::-1]),
                   fill="toself", fillcolor=rgba(colour, 0.20),
                   line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=years, y=med, name=name,
                   line=dict(color=colour, width=2.5),
                   hovertemplate=f"{name} median<br>%{{x}}: %{{y:.1f}}<extra></extra>"),
    ]

fan_scheme = st.radio(
    "Show uncertainty fan for", list(PROJ_SCHEMES.keys()), horizontal=True, index=1,
)

fig_proj = go.Figure()
fig_proj.add_hline(
    y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power", annotation_position="top left",
)
for name, cfg in PROJ_SCHEMES.items():
    colour = cfg["colour"]
    arr    = proj_results[name]["real_pension"][:, :_h] * (starting_pension / 1000.0)
    if name == fan_scheme:
        for trace in fan_traces(arr, proj_years_list, colour, f"{name} — median"):
            fig_proj.add_trace(trace)
    else:
        fig_proj.add_trace(go.Scatter(
            x=[START_YEAR] + proj_years_list,
            y=[starting_pension] + list(pct(arr, 50)),
            name=name,
            line=dict(color=colour, width=2, dash=cfg["dash"]),
            hovertemplate=f"{name} median<br>%{{x}}: £%{{y:,.0f}}<extra></extra>",
        ))
fig_proj.update_layout(
    xaxis_title="Year",
    yaxis_title="Real monthly pension (£, 2023 prices)",
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_proj, use_container_width=True)
end_yr = START_YEAR + _h
target_label_str = f"CPI + {target_real:.2g}%" if target_real > 0 else "CPI"
st.caption(
    f"Figure 6. Projected real pension purchasing power, 2023–{end_yr}. "
    f"Target: {target_label_str}. Starting pension £{starting_pension:,}/month. "
    "Fan shows selected scheme's 10th–90th and 25th–75th percentile range."
)

_metric_cols = st.columns(len(PROJ_SCHEMES))
for col, (name, data) in zip(_metric_cols, proj_results.items()):
    arr = data["real_pension"][:, _h - 1] * (starting_pension / 1000.0)
    med = float(np.median(arr))
    chg = 100 * (med / starting_pension - 1)
    col.metric(name, f"£{med:,.0f}", f"{chg:+.1f}% real (median)")

placeholder(
    "In a well-funded scheme the CI schemes largely converge on full indexation in "
    "median paths — the surplus is sufficient to cover the target most of the time. "
    "The designs differ primarily in their tail behaviour: how much protection "
    "pensioners have in bad years (hybrid floor), and whether the fund retains "
    "more capital for future resilience (proportional self-limit)."
)
