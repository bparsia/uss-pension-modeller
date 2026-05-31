"""Page 3 — Projections: stochastic simulation from 2023.

View C: bootstrap. Resamples historical (equity_real, gilt_yield, cpi) tuples
with a fixed seed to generate 500 possible 20-year futures. Runs the fund model
forward from the 2023 valuation under the current soft cap scheme. Shows the
distribution of funding ratio, indexation, and pensioner outcomes.

Three sampling modes:
  - Joint (default): resample (equity, gilt, cpi) tuples together — preserves
    within-year correlations as observed historically.
  - Independent: resample each variable from its own pool independently — breaks
    historical correlations but avoids embedding the unusual 2008–2021 regime.
  - Two-regime: split pool at 2022; draw from pre- and post-2022 pools with a
    user-controlled weight. Allows exploring a persistent high-rate/high-CPI world.

Paths are pre-generated with a fixed seed — same result every reload.
"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from data.shared import (bootstrap_tuples, USS_2023_VALUATION,
                          USS_CONTRIB_EMPLOYER, USS_CONTRIB_EMPLOYEE,
                          USS_VALUATION_YEARS, HE_WAGE_GROWTH_NOM,
                          CPI, cpi_rate)
from data.fund_model import FundParams, simulate, soft_cap_indexation
from styles import placeholder

st.title("Projections: what might happen next?")

placeholder(
    "So far we have looked at what actually happened — using the historical record as "
    "given. But the future will not be identical to the past. Equity markets might "
    "perform better or worse; inflation might stay elevated or fall back; gilt yields "
    "might rise or fall. To get a sense of how *robust* the fund and its indexation "
    "commitments are across a range of plausible futures, we resample the historical "
    "record to generate many possible 20-year paths and run the fund model forward "
    "from the 2023 valuation on each one."
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_PATHS    = 500
N_YEARS    = 20
SEED       = 42
START_YEAR = 2023
REGIME_SPLIT_YEAR = 2022  # post-2022 = normalised rate era

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Parameters")

STARTING_BASIS_OPTIONS = {
    "USS TP (111%)":            ("uss_tp",       1.11, 1.38),
    "UCU Prudent (105%)":       ("ucu_prudent",  1.05, 1.38),
    "UCU Best Estimate (138%)": ("ucu_best_est", 1.38, 1.38),
}
starting_basis_label = st.sidebar.selectbox(
    "Starting valuation basis",
    list(STARTING_BASIS_OPTIONS),
    help="Sets the initial TP and BE funding ratios for the simulation.",
)
_, tp_fr_start, be_fr_start = STARTING_BASIS_OPTIONS[starting_basis_label]

target_label = st.sidebar.radio(
    "Indexation target", ["Soft cap (current)", "Full CPI"], horizontal=True,
)
use_soft_cap = (target_label == "Soft cap (current)")

starting_pension = st.sidebar.number_input(
    "Starting monthly pension (£)", min_value=100, max_value=10000, value=1000, step=100,
)

st.sidebar.divider()
st.sidebar.subheader("Advanced: sampling method")
SAMPLING_OPTIONS = {
    "Joint (default)":   "joint",
    "Independent draws": "independent",
    "Two-regime split":  "two_regime",
}
sampling_label = st.sidebar.radio(
    "Sampling method", list(SAMPLING_OPTIONS),
    help=(
        "Joint: resample (equity, gilt, CPI) tuples together. "
        "Independent: each variable drawn from its own pool. "
        "Two-regime: split at 2022; weight pre/post pools."
    ),
)
sampling_mode = SAMPLING_OPTIONS[sampling_label]

post_regime_pct = 50
if sampling_mode == "two_regime":
    post_regime_pct = st.sidebar.slider(
        "% of years from post-2022 regime", 0, 100, 50, 5,
        help="0% = all draws from 2006–2021; 100% = all draws from 2022–2025.",
    )

# ---------------------------------------------------------------------------
# Bootstrap pool construction
# ---------------------------------------------------------------------------
_all_tuples = bootstrap_tuples()  # (year, equity_real, gilt_yield, cpi)

# Pre-2022 and post-2022 pools
_pre  = [(t[1], t[2], t[3]) for t in _all_tuples if t[0] <  REGIME_SPLIT_YEAR]
_post = [(t[1], t[2], t[3]) for t in _all_tuples if t[0] >= REGIME_SPLIT_YEAR]
_all  = [(t[1], t[2], t[3]) for t in _all_tuples]

pool_pre  = np.array(_pre)   # (16, 3)
pool_post = np.array(_post)  # (4, 3)
pool_all  = np.array(_all)   # (20, 3)

# Separate pools for independent draws
pool_eq   = pool_all[:, 0]
pool_gilt = pool_all[:, 1]
pool_cpi  = pool_all[:, 2]


# ---------------------------------------------------------------------------
# Path generation (cached — same result for same inputs)
# ---------------------------------------------------------------------------
@st.cache_data
def generate_paths(
    n_paths: int,
    n_years: int,
    seed: int,
    mode: str,
    post_pct: int,
) -> np.ndarray:
    """Return array (n_paths, n_years, 3): equity_real, gilt_yield, cpi."""
    rng = np.random.default_rng(seed)

    if mode == "joint":
        idx = rng.integers(0, len(pool_all), size=(n_paths, n_years))
        return pool_all[idx]

    elif mode == "independent":
        eq   = pool_eq  [rng.integers(0, len(pool_eq),   size=(n_paths, n_years))]
        gilt = pool_gilt[rng.integers(0, len(pool_gilt), size=(n_paths, n_years))]
        cpi  = pool_cpi [rng.integers(0, len(pool_cpi),  size=(n_paths, n_years))]
        return np.stack([eq, gilt, cpi], axis=2)

    else:  # two_regime
        # For each of the n_paths × n_years draws, choose regime by weight
        use_post = rng.random(size=(n_paths, n_years)) < (post_pct / 100.0)
        pre_idx  = rng.integers(0, len(pool_pre),  size=(n_paths, n_years))
        post_idx = rng.integers(0, len(pool_post), size=(n_paths, n_years))
        pre_draw  = pool_pre [pre_idx]   # (n_paths, n_years, 3)
        post_draw = pool_post[post_idx]
        return np.where(use_post[:, :, np.newaxis], post_draw, pre_draw)


paths = generate_paths(N_PATHS, N_YEARS, SEED, sampling_mode, post_regime_pct)


# ---------------------------------------------------------------------------
# Run simulations
# ---------------------------------------------------------------------------
@st.cache_data
def run_simulations(
    paths_bytes: bytes,
    tp_fr: float,
    be_fr: float,
    use_soft_cap: bool,
) -> dict:
    _paths = np.frombuffer(paths_bytes, dtype=np.float64).reshape(N_PATHS, N_YEARS, 3)

    params = FundParams(
        assets_bn=USS_2023_VALUATION["assets_bn"],
        tp_fr=tp_fr,
        be_fr=be_fr,
    )

    fr_tp   = np.zeros((N_PATHS, N_YEARS))
    fr_be   = np.zeros((N_PATHS, N_YEARS))
    fr_pr   = np.zeros((N_PATHS, N_YEARS))
    idx_pct = np.zeros((N_PATHS, N_YEARS))
    cpi_arr = np.zeros((N_PATHS, N_YEARS))
    # Max affordable indexation = entire surplus as % of liabilities, per basis
    max_idx_tp = np.zeros((N_PATHS, N_YEARS))
    max_idx_be = np.zeros((N_PATHS, N_YEARS))
    max_idx_pr = np.zeros((N_PATHS, N_YEARS))

    for p in range(N_PATHS):
        shocks = [
            (float(_paths[p, t, 0]), float(_paths[p, t, 1]), float(_paths[p, t, 2]))
            for t in range(N_YEARS)
        ]
        states = simulate(shocks, params, ci_scheme="guaranteed")
        for t, s in enumerate(states):
            fr_tp[p, t]  = s.fr_tp
            fr_be[p, t]  = s.fr_be
            fr_pr[p, t]  = s.fr_pr
            cpi_val       = shocks[t][2]
            cpi_arr[p, t] = cpi_val
            idx_pct[p, t] = soft_cap_indexation(cpi_val) if use_soft_cap else cpi_val
            # Max affordable = surplus as % of liabilities (floored at 0)
            # FR = A/L, so surplus/L = FR - 1; indexation affordable = (FR-1)*100%
            max_idx_tp[p, t] = max(0.0, (s.fr_tp - 1.0) * 100)
            max_idx_be[p, t] = max(0.0, (s.fr_be - 1.0) * 100)
            max_idx_pr[p, t] = max(0.0, (s.fr_pr - 1.0) * 100)

    # Pension path (normalised to £1,000 start)
    pension = np.full((N_PATHS, N_YEARS), 1000.0)
    for t in range(1, N_YEARS):
        pension[:, t] = pension[:, t-1] * (1 + idx_pct[:, t] / 100)

    # Real pension: deflate by cumulative CPI from year 1
    cum_cpi = np.ones((N_PATHS, N_YEARS))
    for t in range(1, N_YEARS):
        cum_cpi[:, t] = cum_cpi[:, t-1] * (1 + cpi_arr[:, t] / 100)
    real_pension = pension / cum_cpi

    return dict(
        fr_tp=fr_tp, fr_be=fr_be, fr_pr=fr_pr,
        idx_pct=idx_pct, cpi_arr=cpi_arr,
        pension=pension, real_pension=real_pension,
        max_idx_tp=max_idx_tp, max_idx_be=max_idx_be, max_idx_pr=max_idx_pr,
    )


results      = run_simulations(paths.tobytes(), tp_fr_start, be_fr_start, use_soft_cap)
fr_tp        = results["fr_tp"]
fr_be        = results["fr_be"]
fr_pr        = results["fr_pr"]
max_idx_tp   = results["max_idx_tp"]
max_idx_be   = results["max_idx_be"]
max_idx_pr   = results["max_idx_pr"]
idx_pct      = results["idx_pct"]
cpi_arr      = results["cpi_arr"]
real_pension = results["real_pension"] * (starting_pension / 1000.0)

proj_years = list(range(START_YEAR + 1, START_YEAR + N_YEARS + 1))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pct(arr, p): return np.percentile(arr, p, axis=0)

BLUE  = "#4C78A8"
RED   = "#E45756"
DARK  = "#444444"
AMBER = "#F58518"

# Quartile colours: Q1 (worst) → red, Q2 → amber, Q3 → blue, Q4 (best) → green
Q_COLOURS = ["#E45756", "#F58518", "#4C78A8", "#54A24B"]
Q_LABELS  = ["Q1 — poor growth", "Q2 — below average", "Q3 — above average", "Q4 — strong growth"]

def rgba(hex_col: str, alpha: float) -> str:
    r, g, b = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"

def fan_traces(arr, years, colour, name):
    p10, p25, p75, p90 = pct(arr, 10), pct(arr, 25), pct(arr, 75), pct(arr, 90)
    med = pct(arr, 50)
    return [
        go.Scatter(
            x=years + years[::-1], y=list(p90) + list(p10[::-1]),
            fill="toself", fillcolor=rgba(colour, 0.10),
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ),
        go.Scatter(
            x=years + years[::-1], y=list(p75) + list(p25[::-1]),
            fill="toself", fillcolor=rgba(colour, 0.20),
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ),
        go.Scatter(
            x=years, y=med, name=name,
            line=dict(color=colour, width=2.5),
            hovertemplate=f"{name} median<br>%{{x}}: %{{y:.1f}}<extra></extra>",
        ),
    ]

# ---------------------------------------------------------------------------
# Rank paths by mean equity real return — used for quartiles + path selector
# ---------------------------------------------------------------------------
mean_eq = paths[:, :, 0].mean(axis=1)           # (N_PATHS,) mean equity return per path
rank    = np.argsort(mean_eq)                    # indices sorted worst→best
quartile_edges = np.array_split(rank, 4)         # Q1..Q4

# Fixed random example path from each quartile (same seed, stable)
_rng_q = np.random.default_rng(99)
quartile_examples = [
    int(_rng_q.choice(q)) for q in quartile_edges
]

# Named paths for the selector
_named_paths = {
    "Worst equity path (extreme)":      int(rank[0]),
    "Poor growth — example":            quartile_examples[0],
    "Below average — example":          quartile_examples[1],
    "Median path":                      int(rank[N_PATHS // 2]),
    "Above average — example":          quartile_examples[2],
    "Strong growth — example":          quartile_examples[3],
    "Best equity path (extreme)":       int(rank[-1]),
}


# ---------------------------------------------------------------------------
# Horizon selector (main page, affects all charts)
# ---------------------------------------------------------------------------
horizon_years = st.select_slider(
    "Display horizon (years)",
    options=[5, 10, 15, 20],
    value=20,
    help="Slice all charts to show only the first N projection years.",
)
# Apply horizon slice — _h used inline at each chart
_h = horizon_years
proj_years = proj_years[:_h]

# ---------------------------------------------------------------------------
# Section 1: Sampling method explanation
# ---------------------------------------------------------------------------
st.subheader("How the projections work")

_method_text = {
    "joint": (
        "Each projected path draws 20 years independently at random (with replacement) "
        "from the 20 historical years 2006–2025. Each draw picks up the equity return, "
        "gilt yield, and CPI that actually co-occurred in that year, preserving the "
        "real-world correlations between variables within a year. However, serial "
        "correlation across years is not preserved — a run of bad years cannot occur "
        "as a block, only as isolated draws. The same 500 paths are used every reload."
    ),
    "independent": (
        "Each of the three variables — equity return, gilt yield, and CPI — is drawn "
        "independently from its own historical pool. This breaks the within-year "
        "correlations observed historically (e.g. the 2022 equity crash + high CPI "
        "combination cannot occur together). The advantage is that the unusual "
        "post-2008 low-rate regime is not embedded as a correlated block."
    ),
    "two_regime": (
        f"The historical record is split at {REGIME_SPLIT_YEAR}: a pre-{REGIME_SPLIT_YEAR} "
        f"pool (2006–{REGIME_SPLIT_YEAR-1}: low gilt yields, subdued CPI) and a "
        f"post-{REGIME_SPLIT_YEAR} pool (2022–2025: normalised rates, elevated CPI). "
        "Each draw is taken from one pool or the other according to the weight set "
        "by the slider. This lets you explore how outcomes change if the high-rate "
        "era persists vs reverts to the 2010s pattern."
    ),
}
placeholder(_method_text[sampling_mode])

# --- Figure 1: sample paths with selector + quartile averages ---
st.subheader("Equity real return paths")

highlight_labels = st.multiselect(
    "Highlight paths",
    options=list(_named_paths.keys()),
    default=["Worst equity path (extreme)", "Median path", "Best equity path (extreme)"],
)
highlighted = {label: _named_paths[label] for label in highlight_labels}

fig_sample = go.Figure()

# Overall mean
overall_mean = paths[:, :_h, 0].mean(axis=0)
fig_sample.add_trace(go.Scatter(
    x=proj_years, y=overall_mean, name="Overall mean",
    line=dict(color=DARK, width=2, dash="dash"),
    hovertemplate="Overall mean<br>%{x}: %{y:.1f}%<extra></extra>",
))

# Highlighted paths
HIGHLIGHT_COLOURS = ["#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#C77DFF", "#FF9F1C", "#2EC4B6"]
for i, (label, pidx) in enumerate(highlighted.items()):
    col = HIGHLIGHT_COLOURS[i % len(HIGHLIGHT_COLOURS)]
    mean_val = mean_eq[pidx]
    fig_sample.add_trace(go.Scatter(
        x=proj_years, y=paths[pidx, :_h, 0],
        name=f"{label} (mean {mean_val:+.1f}%)",
        line=dict(color=col, width=2, dash="dot"),
        hovertemplate=f"{label}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
    ))

fig_sample.update_layout(
    xaxis_title="Year", yaxis_title="Equity real return (%)",
    yaxis=dict(ticksuffix="%"), hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_sample, use_container_width=True)
st.caption("Figure 1. Equity real return paths. Paths ranked by mean return across the 20-year horizon.")

st.caption("Mean and median of drawn variables across all 500 paths:")
c1, c2, c3 = st.columns(3)
for col, var, label in [
    (c1, paths[:,:,0], "Equity real return"),
    (c2, paths[:,:,1], "Gilt yield"),
    (c3, paths[:,:,2], "CPI"),
]:
    col.metric(label, f"Mean {np.mean(var):.1f}%", f"Median {np.median(var):.1f}%")

# ---------------------------------------------------------------------------
# Section 2: Funding ratio fan charts
# ---------------------------------------------------------------------------
st.subheader("Funding ratio distribution")

placeholder(
    "All three valuation bases are shown on a single chart. Median lines are always "
    "visible. Select a basis to highlight its uncertainty fan (10th–90th and 25th–75th "
    "percentile bands). The three medians diverge over time because each basis uses a "
    "different discount rate — the same assets look very different depending on how "
    "liabilities are valued."
)

FR_BASES = {
    "USS TP":           (fr_tp[:, :_h] * 100, DARK,  tp_fr_start * 100),
    "UCU Prudent":      (fr_pr[:, :_h] * 100, RED,   USS_2023_VALUATION["ucu_prudent_fr"] * 100),
    "UCU Best Estimate":(fr_be[:, :_h] * 100, BLUE,  be_fr_start * 100),
}

fan_col, cap_col = st.columns([2, 1])
fan_basis = fan_col.radio(
    "Show uncertainty fan for", list(FR_BASES.keys()), horizontal=True, index=0,
)
y_cap = cap_col.slider("Display cap (%)", min_value=150, max_value=500, value=300, step=25)

x_anchor = [START_YEAR] + proj_years

fig_fr = go.Figure()
fig_fr.add_hline(y=100, line_dash="solid", line_color="#E45756", line_width=2,
                 annotation_text="100% — deficit below this line",
                 annotation_position="bottom right",
                 annotation_font=dict(color="#E45756", size=12))

# Collect all percentiles to set y range
all_p10, all_p90 = [], []

for basis_name, (arr, colour, start_fr) in FR_BASES.items():
    p10, p25, p75, p90 = pct(arr, 10), pct(arr, 25), pct(arr, 75), pct(arr, 90)
    med = pct(arr, 50)
    all_p10.append(float(p10.min()))
    all_p90.append(float(p90.max()))

    if basis_name == fan_basis:
        # Clip fan values to display cap
        p10c = np.minimum(p10, y_cap)
        p25c = np.minimum(p25, y_cap)
        p75c = np.minimum(p75, y_cap)
        p90c = np.minimum(p90, y_cap)
        x_rev = proj_years[::-1] + [START_YEAR]
        fig_fr.add_trace(go.Scatter(
            x=x_anchor + x_rev,
            y=[start_fr] + list(p90c) + list(p10c[::-1]) + [start_fr],
            fill="toself", fillcolor=rgba(colour, 0.12),
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig_fr.add_trace(go.Scatter(
            x=x_anchor + x_rev,
            y=[start_fr] + list(p75c) + list(p25c[::-1]) + [start_fr],
            fill="toself", fillcolor=rgba(colour, 0.25),
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))

    # Median always solid, full width, own colour
    med_clipped = np.minimum(med, y_cap)
    fig_fr.add_trace(go.Scatter(
        x=x_anchor, y=[start_fr] + list(med_clipped),
        name=basis_name,
        line=dict(color=colour, width=2.5, dash="solid"),
        hovertemplate=f"{basis_name} median<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
    ))

y_min = max(0, min(all_p10) - 10)
y_max = y_cap
fig_fr.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Funding ratio (%)", ticksuffix="%", range=[y_min, y_max]),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_fr, use_container_width=True)
st.caption("Figure 3. Projected funding ratio under three valuation bases, 500 bootstrap paths. Median lines always shown; fan shows selected basis.")

# Summary table
import pandas as pd
TABLE_YEARS = [y for y in [2028, 2033, 2038, 2043] if y <= START_YEAR + _h]
rows = []
for basis_name, (arr, colour, start_fr) in FR_BASES.items():
    for yr in TABLE_YEARS:
        t = yr - START_YEAR - 1
        if 0 <= t < N_YEARS:
            col_data = arr[:, t]
            rows.append({
                "Basis": basis_name,
                "Year": yr,
                "10th %ile": f"{np.percentile(col_data, 10):.0f}%",
                "25th %ile": f"{np.percentile(col_data, 25):.0f}%",
                "Median":    f"{np.median(col_data):.0f}%",
                "75th %ile": f"{np.percentile(col_data, 75):.0f}%",
                "90th %ile": f"{np.percentile(col_data, 90):.0f}%",
            })

df_fr = pd.DataFrame(rows).set_index(["Basis", "Year"])
with st.expander("Summary table — funding ratio by basis and year"):
    st.dataframe(df_fr, use_container_width=True)


# ---------------------------------------------------------------------------
# Section 3: Annual indexation distribution
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# CPI fan chart
# ---------------------------------------------------------------------------
st.subheader("Simulated inflation paths")

placeholder(
    "CPI is drawn from the same historical pool as equity returns and gilt yields. "
    "Most paths stay in the 1–4% range familiar from the pre-2021 era, but the pool "
    "includes the 2022 and 2023 spikes — so some paths see sustained high inflation. "
    "The inflation environment matters directly for indexation: high CPI years are "
    "where the soft cap diverges from full protection."
)

fig_cpi = go.Figure()
for trace in fan_traces(paths[:, :_h, 2], proj_years, AMBER, "CPI"):
    if trace.name == "CPI":
        trace.name = "CPI — median"
    fig_cpi.add_trace(trace)
fig_cpi.add_hline(y=2.0, line_dash="dot", line_color="lightgray", line_width=1,
                  annotation_text="2% target", annotation_position="top left")
fig_cpi.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="CPI (%)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_cpi, use_container_width=True)
st.caption("Figure 5. Simulated CPI paths across 500 bootstrap draws. Bands show 25th–75th (dark) and 10th–90th (light) percentiles.")

# ---------------------------------------------------------------------------
# Section 3: Real pension purchasing power
# ---------------------------------------------------------------------------
st.subheader("Real pension purchasing power")

placeholder(
    "Compounding indexation over 20 years and deflating by cumulative CPI gives the "
    "real purchasing power of the pension at each point. The dotted line shows "
    "full purchasing power maintained (full CPI). The soft cap fan shows what "
    "actually happens under the current scheme. The dark line is the median; "
    "bands show the 25th–75th and 10th–90th percentile ranges."
)

# Always compute full-CPI real pension for comparison
pension_full_cpi = np.full((N_PATHS, N_YEARS), 1000.0)
for t in range(1, N_YEARS):
    pension_full_cpi[:, t] = pension_full_cpi[:, t-1] * (1 + cpi_arr[:, t] / 100)
cum_cpi = np.ones((N_PATHS, N_YEARS))
for t in range(1, N_YEARS):
    cum_cpi[:, t] = cum_cpi[:, t-1] * (1 + cpi_arr[:, t] / 100)
real_full_cpi = pension_full_cpi / cum_cpi * (starting_pension / 1000.0)

pension_sc_only = np.full((N_PATHS, N_YEARS), 1000.0)
sc_idx_arr = np.array([[soft_cap_indexation(cpi_arr[p, t]) for t in range(N_YEARS)] for p in range(N_PATHS)])
for t in range(1, N_YEARS):
    pension_sc_only[:, t] = pension_sc_only[:, t-1] * (1 + sc_idx_arr[:, t] / 100)
real_sc_only = pension_sc_only / cum_cpi * (starting_pension / 1000.0)

fig_real = go.Figure()
fig_real.add_hline(
    y=starting_pension, line_dash="solid", line_color="lightgray", line_width=1.5,
    annotation_text="Full purchasing power", annotation_position="top left",
)

# Full CPI: flat reference line (real value is always starting_pension by construction)
fig_real.add_trace(go.Scatter(
    x=[START_YEAR] + proj_years,
    y=[starting_pension] * (_h + 1),
    name="Full CPI (purchasing power preserved)",
    line=dict(color="#54A24B", width=2, dash="dot"),
    hovertemplate="Full CPI<br>%{x}: £%{y:,.0f}<extra></extra>",
))

# Soft cap fan
for trace in fan_traces(real_sc_only[:, :_h], proj_years, BLUE, "Soft cap"):
    if trace.name == "Soft cap":
        trace.name = "Soft cap — median"
    fig_real.add_trace(trace)

fig_real.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Real monthly pension (£, 2023 prices)",
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_real, use_container_width=True)
st.caption(f"Figure 6. Real pension purchasing power, 2023 prices. Starting pension £{starting_pension:,}/month. Dotted green = full CPI reference. Blue fan = soft cap outcomes across 500 paths.")

ep_sc = real_sc_only[:, _h - 1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Full CPI (2043)",           f"£{starting_pension:,}")
c2.metric("Soft cap median (2043)",    f"£{np.median(ep_sc):,.0f}")
c3.metric("Soft cap 10th pct (2043)",  f"£{np.percentile(ep_sc, 10):,.0f}")
c4.metric("Soft cap 90th pct (2043)",  f"£{np.percentile(ep_sc, 90):,.0f}")

placeholder(
    "Full CPI always preserves purchasing power by construction. Under the soft cap, "
    "high-inflation draws permanently erode purchasing power — the cap is never made "
    "up in later years. The spread shows the range of outcomes depending on how many "
    "high-inflation years are drawn."
)

# ---------------------------------------------------------------------------
# Section 4: Annual headroom — max affordable vs soft cap
# ---------------------------------------------------------------------------
st.subheader("Annual indexation headroom")

placeholder(
    "The soft cap pays a fixed formula regardless of the fund's position. But on "
    "the UCU Best Estimate basis, the fund has substantial surplus in most paths — "
    "enough to have afforded considerably more than the soft cap. The chart below "
    "shows the maximum indexation affordable each year (entire surplus converted to "
    "indexation) vs what the soft cap actually pays. The gap is the upside that "
    "currently goes nowhere — it sits in the fund, is used to reduce contributions, "
    "or is subject to negotiation. This is the resource that conditional indexation "
    "schemes would distribute."
)

max_basis_options = {
    "USS TP":            max_idx_tp[:, :_h],
    "UCU Prudent":       max_idx_pr[:, :_h],
    "UCU Best Estimate": max_idx_be[:, :_h],
}
max_basis = st.radio(
    "Max affordable basis", list(max_basis_options.keys()), horizontal=True, index=2,
    help="Which valuation basis to use when computing maximum affordable indexation.",
)
_max_idx = max_basis_options[max_basis]

fig_head = go.Figure()

# Soft cap rates fan
for trace in fan_traces(sc_idx_arr[:, :_h], proj_years, BLUE, "Soft cap"):
    if trace.name == "Soft cap":
        trace.name = "Soft cap — median"
    fig_head.add_trace(trace)

# Max affordable fan — cap display at 30% to keep readable
_max_idx_display = np.minimum(_max_idx, 30.0)
for trace in fan_traces(_max_idx_display, proj_years, AMBER, f"Max affordable ({max_basis})"):
    if trace.name == f"Max affordable ({max_basis})":
        trace.name = f"Max affordable ({max_basis}) — median"
    fig_head.add_trace(trace)

# Full CPI median for reference
fig_head.add_trace(go.Scatter(
    x=proj_years, y=pct(cpi_arr[:, :_h], 50),
    name="Median CPI", line=dict(color="#54A24B", width=1.5, dash="dot"),
    hovertemplate="Median CPI<br>%{x}: %{y:.1f}%<extra></extra>",
))

fig_head.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Annual indexation rate (%)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_head, use_container_width=True)
st.caption(f"Figure 7. Annual indexation rates across 500 paths. Blue = soft cap. Amber = maximum affordable on {max_basis} basis (capped at 30% for readability). Dotted green = median CPI.")

placeholder(
    "The next page explores how conditional indexation schemes could systematically "
    "distribute this headroom — linking indexation to what the fund can actually afford "
    "rather than a fixed formula."
)

# ---------------------------------------------------------------------------
# Section 5: Contributions — history, wages, and the triennial lock
# ---------------------------------------------------------------------------
st.subheader("Contributions, wages, and the triennial lock")

placeholder(
    "Indexation is only one side of the equation. The fund's long-run health also "
    "depends on contribution income — which is the contribution rate multiplied by "
    "the salary roll. Both have moved significantly since 2008. Contribution rates "
    "were raised sharply after the 2017 and 2020 valuations, then cut back after the "
    "2023 surplus. Meanwhile HE sector wages have grown below CPI in most years since "
    "2009, permanently reducing the real value of the contribution base."
)

# --- Chart 1: Contribution rate history ---
_contrib_years = sorted(USS_CONTRIB_EMPLOYER.keys())
_emp  = [USS_CONTRIB_EMPLOYER[y] for y in _contrib_years]
_ee   = [USS_CONTRIB_EMPLOYEE[y] for y in _contrib_years]
_tot  = [e + ee for e, ee in zip(_emp, _ee)]

fig_contrib = go.Figure()
fig_contrib.add_trace(go.Bar(
    x=_contrib_years, y=_emp, name="Employer",
    marker_color=BLUE, opacity=0.85,
    hovertemplate="%{x}<br>Employer: %{y:.1f}%<extra></extra>",
))
fig_contrib.add_trace(go.Bar(
    x=_contrib_years, y=_ee, name="Employee",
    marker_color=AMBER, opacity=0.85,
    hovertemplate="%{x}<br>Employee: %{y:.1f}%<extra></extra>",
))
# Mark triennial valuation years
for vyr in USS_VALUATION_YEARS:
    fig_contrib.add_vline(
        x=vyr, line_dash="dot", line_color="lightgray", line_width=1,
        annotation_text=str(vyr), annotation_position="top",
        annotation_font=dict(size=10, color="gray"),
    )
fig_contrib.update_layout(
    barmode="stack",
    xaxis_title="Year",
    yaxis=dict(title="Contribution rate (% of salary)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_contrib, use_container_width=True)
st.caption("Figure 8. USS contribution rates (% of salary), employer and employee stacked. Dotted verticals mark triennial valuation years.")

placeholder(
    "Rates are set at each triennial valuation and held fixed until the next one — "
    "typically a three-year lag between the fund's position and the rates members pay. "
    "The sharp rise in 2019 and 2021 reflected the 2017 and 2020 valuations respectively, "
    "both of which showed large deficits on the USS TP basis. The 2023 cut — from 34.7% "
    "combined to 20.6% — came only after the 2023 valuation confirmed a surplus. "
    "Members on both sides paid elevated rates throughout the intervening years, "
    "despite the UCU Best Estimate showing the fund comfortably in surplus throughout."
)

# --- Chart 2: Real wage index + contribution real value ---
_wage_years_hist = sorted(HE_WAGE_GROWTH_NOM.keys())

# Cumulative nominal wage index (2008 = 100)
_cum_wage_nom = [100.0]
_cum_cpi_hist = [100.0]
for y in _wage_years_hist[1:]:
    nom_g = HE_WAGE_GROWTH_NOM.get(y, 0.0)
    cpi_g = cpi_rate(y)
    _cum_wage_nom.append(_cum_wage_nom[-1] * (1 + nom_g / 100))
    _cum_cpi_hist.append(_cum_cpi_hist[-1] * (1 + cpi_g / 100))

_real_wage_idx = [w / c * 100 for w, c in zip(_cum_wage_nom, _cum_cpi_hist)]

# Real contribution value = (rate/100) × real wage index (arbitrary units, 2008=rate×100)
_real_contrib_val = [
    (USS_CONTRIB_EMPLOYER.get(y, 0) + USS_CONTRIB_EMPLOYEE.get(y, 0)) / 100 * rw
    for y, rw in zip(_wage_years_hist, _real_wage_idx)
]
# Normalise to 2008=100 for comparability
_rc0 = _real_contrib_val[0]
_real_contrib_norm = [v / _rc0 * 100 for v in _real_contrib_val]

fig_wages = go.Figure()
fig_wages.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                    annotation_text="2008 baseline", annotation_position="top left")
fig_wages.add_trace(go.Scatter(
    x=_wage_years_hist, y=_real_wage_idx, name="Real wage index",
    line=dict(color=RED, width=2),
    hovertemplate="%{x}<br>Real wage index: %{y:.1f}<extra></extra>",
))
fig_wages.add_trace(go.Scatter(
    x=_wage_years_hist, y=_real_contrib_norm, name="Real contribution value",
    line=dict(color=BLUE, width=2, dash="dash"),
    hovertemplate="%{x}<br>Real contribution value: %{y:.1f}<extra></extra>",
))
for vyr in USS_VALUATION_YEARS:
    fig_wages.add_vline(
        x=vyr, line_dash="dot", line_color="lightgray", line_width=1,
    )
fig_wages.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Index (2008 = 100)"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_wages, use_container_width=True)
st.caption(
    "Figure 9. Real wage index (red) and real contribution value (blue dashed, = rate × real wage, 2008=100). "
    "When real wages fall, higher nominal contribution rates are needed just to maintain the same real income to the fund."
)

placeholder(
    "Even with the contribution rate rises of 2019–2022, the real value of contributions "
    "barely recovered to 2008 levels — because HE wages had fallen so far behind CPI. "
    "The 2023 rate cut, while welcome for members, dropped the real contribution value "
    "sharply. The fund's current surplus provides a buffer, but a return to below-CPI "
    "wages combined with a market downturn could quickly erode it. The projections above "
    "use the current 20.6% combined rate and carry forward real wage growth as a parameter."
)

# --- Chart 3: Triennial lock — what happens between valuations ---
st.markdown("#### The triennial lock")

placeholder(
    "Because rates are only reset at triennial valuations, there is always a lag between "
    "the fund's true position and what members are paying. The chart below illustrates "
    "this for the period 2017–2023: the USS TP funding ratio is shown alongside the "
    "contribution rate in force. Note how the rate stayed elevated even as the FR "
    "recovered strongly in 2022–2023 — members continued paying the high 2020-valuation "
    "rates until January 2023. Under a UCU Best Estimate basis, the fund was never "
    "in the deficit that justified those rates."
)

_lock_years = list(range(2017, 2026))
_lock_fr_tp = []
try:
    from data.uss_valuation_bases import get_fr_histories as _get_fr
    _fr_h = _get_fr(_lock_years)
    _lock_fr_tp = [float(_fr_h.loc[y, "uss_tp"]) for y in _lock_years]
except Exception:
    _lock_fr_tp = []

if _lock_fr_tp:
    _lock_rate = [USS_CONTRIB_EMPLOYER.get(y, 0) + USS_CONTRIB_EMPLOYEE.get(y, 0)
                  for y in _lock_years]

    fig_lock = go.Figure()
    fig_lock.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                       annotation_text="100% — break-even", annotation_position="top left")
    fig_lock.add_trace(go.Scatter(
        x=_lock_years, y=_lock_fr_tp, name="USS TP funding ratio",
        line=dict(color=DARK, width=2.5),
        hovertemplate="%{x}<br>USS TP FR: %{y:.0f}%<extra></extra>",
    ))
    for vyr in [y for y in USS_VALUATION_YEARS if y in _lock_years]:
        fig_lock.add_vline(
            x=vyr, line_dash="dot", line_color="lightgray", line_width=1,
            annotation_text=f"Valuation {vyr}", annotation_position="top",
            annotation_font=dict(size=10, color="gray"),
        )
    fig_lock.add_trace(go.Bar(
        x=_lock_years, y=_lock_rate, name="Combined contribution rate",
        marker_color=AMBER, opacity=0.5, yaxis="y2",
        hovertemplate="%{x}<br>Combined rate: %{y:.1f}%<extra></extra>",
    ))
    fig_lock.update_layout(
        xaxis_title="Year",
        yaxis =dict(title="USS TP funding ratio (%)", ticksuffix="%"),
        yaxis2=dict(title="Combined contribution rate (%)", ticksuffix="%",
                    overlaying="y", side="right", showgrid=False),
        hovermode="x unified", legend_title="",
    )
    st.plotly_chart(fig_lock, use_container_width=True)
    st.caption(
        "Figure 10. USS TP funding ratio (dark line) vs combined contribution rate in force (amber bars). "
        "Dotted verticals mark triennial valuations. The lag between FR recovery and rate reduction is visible: "
        "members paid peak rates through 2022 despite the FR recovering strongly."
    )
