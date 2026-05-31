"""Page 2 — Valuation, indexation cost, and the surplus question.

View A: retrospective. Uses historical FR series from uss_valuation_bases.py
(three valuation bases: USS TP, UCU Prudent, UCU Best Estimate) combined with
actual historical CPI to show what full indexation and the soft cap would have
cost, and what surplus would have remained.

No CI yet — this page sets up the surplus/deficit question that CI is a response to.
"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import importlib.util

from data.shared import CPI, RPI, cpi_rate, rpi_rate, HE_WAGE_GROWTH_NOM
from data.fund_model import soft_cap_indexation
from styles import placeholder

st.title("Valuation, indexation, and the surplus question")

placeholder(
    "The previous page showed that indexation costs money. This page asks: "
    "does the USS fund actually have that money — and if so, how much is left over? "
    "The answer depends critically on how you value the liabilities."
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Parameters")

inflation_measure = st.sidebar.radio(
    "Inflation measure", ["CPI", "RPI"], horizontal=True,
)
_index   = CPI if inflation_measure == "CPI" else RPI
_rate_fn = cpi_rate if inflation_measure == "CPI" else rpi_rate

start_year = st.sidebar.selectbox(
    "Retirement year (pension paths)",
    options=list(range(2008, 2024)),
    index=list(range(2008, 2024)).index(2017),
)
starting_pension = st.sidebar.number_input(
    "Starting monthly pension (£)", min_value=100, max_value=10000, value=1000, step=100,
)

st.sidebar.divider()
st.sidebar.subheader("Valuation basis")
BASIS_OPTIONS = {
    "USS TP (published)":           "uss_tp",
    "UCU Prudent (CPI+1.5%)":       "ucu_prudent",
    "UCU Best Estimate (CPI+3.2%)": "ucu_best_est",
}
BASIS_COLOURS = {
    "uss_tp":       "#444444",
    "ucu_prudent":  "#E45756",
    "ucu_best_est": "#4C78A8",
}
BASIS_LABELS = {v: k for k, v in BASIS_OPTIONS.items()}
selected_basis_label = st.sidebar.selectbox("Highlighted basis", list(BASIS_OPTIONS))
selected_basis = BASIS_OPTIONS[selected_basis_label]

# ---------------------------------------------------------------------------
# Load historical FR series
# ---------------------------------------------------------------------------
_vb_path = Path(__file__).parent.parent / "data" / "uss_valuation_bases.py"
_fr_histories = None
if _vb_path.exists():
    try:
        _spec = importlib.util.spec_from_file_location("uss_valuation_bases", _vb_path)
        _vb = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_vb)
        _fr_histories = _vb.get_fr_histories(list(range(2008, 2026)))
    except Exception as e:
        st.warning(f"Could not load valuation bases: {e}")

if _fr_histories is None:
    st.error("Historical FR data not available.")
    st.stop()

# All years with USS TP data (2008–2025); UCU bases only from 2017
ALL_YEARS = [y for y in range(2008, 2026) if y in _fr_histories.index]
UCU_YEARS = [y for y in ALL_YEARS if not np.isnan(float(_fr_histories.loc[y, "ucu_prudent"]))]

# CPI for all years
cpi_all  = {y: cpi_rate(y) for y in ALL_YEARS}
sc_all   = {y: soft_cap_indexation(cpi_rate(y)) for y in ALL_YEARS}

COLOURS = {
    "uss_tp":       "#444444",
    "ucu_prudent":  "#E45756",
    "ucu_best_est": "#4C78A8",
    "cpi":          "#FFA15A",
    "soft_cap":     "#636EFA",
    "full":         "#00CC96",
}

def fr_vals(basis, years=None):
    yrs = years or ALL_YEARS
    return [float(_fr_histories.loc[y, basis]) for y in yrs
            if not np.isnan(float(_fr_histories.loc[y, basis]))]

def fr_years(basis, years=None):
    yrs = years or ALL_YEARS
    return [y for y in yrs
            if not np.isnan(float(_fr_histories.loc[y, basis]))]


# ---------------------------------------------------------------------------
# Section 1: FR history + CPI overlay
# ---------------------------------------------------------------------------
st.subheader("Funding ratio and inflation, 2008–2025")

placeholder(
    "The funding ratio (FR) is assets divided by liabilities. Whether it is above or "
    "below 100% depends entirely on how liabilities are valued — and that depends on "
    "the discount rate chosen. All three lines below describe the same fund with the "
    "same assets. USS's published Technical Provisions basis (dark) is volatile because "
    "it is tied to gilt yields: low rates in the 2010s inflated liabilities and pushed "
    "the FR down; the 2022 rate shock reversed this almost overnight. The UCU bases use "
    "a higher, more stable discount rate and tell a very different story."
)

fig_fr = go.Figure()
fig_fr.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1)

for key, label in [("uss_tp", "USS TP"), ("ucu_prudent", "UCU Prudent"), ("ucu_best_est", "UCU Best Estimate")]:
    yrs  = fr_years(key)
    vals = fr_vals(key)
    is_selected = (key == selected_basis)
    fig_fr.add_trace(go.Scatter(
        x=yrs, y=vals, name=label,
        line=dict(color=COLOURS[key], width=3 if is_selected else 1.5,
                  dash="solid" if is_selected else "dot"),
        hovertemplate=f"{label}<br>%{{x}}: %{{y:.0f}}%<extra></extra>",
    ))

# CPI on secondary axis
fig_fr.add_trace(go.Bar(
    x=ALL_YEARS, y=[cpi_all[y] for y in ALL_YEARS],
    name="CPI", marker_color=COLOURS["cpi"], opacity=0.35,
    yaxis="y2",
    hovertemplate="%{x}<br>CPI: %{y:.1f}%<extra></extra>",
))

fig_fr.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Funding ratio (%)", ticksuffix="%"),
    yaxis2=dict(title="CPI (%)", ticksuffix="%", overlaying="y", side="right",
                range=[0, 15], showgrid=False),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_fr, use_container_width=True)

placeholder(
    "Key moments: 2009 — post-Lehman equity crash dropped USS TP to 74%. "
    "2011–2020 — persistent deficit on USS TP basis despite growing assets, driven by "
    "falling gilt yields. 2017–2018 — the basis for the industrial dispute: USS claimed "
    "a £5bn deficit; UCU's actuaries showed the fund was comfortably in surplus on a "
    "best-estimate basis. 2022 — gilt yields surged; USS TP FR jumped from 87% to 102% "
    "in a single year. 2023 — first triennial valuation showing a surplus on USS TP basis."
)

# ---------------------------------------------------------------------------
# Section 2: What indexation actually costs
# ---------------------------------------------------------------------------
st.subheader("What indexation costs — soft cap vs full CPI")

placeholder(
    "Every percentage point of indexation uplifts all future pension cashflows by that "
    "amount permanently. Granting i% of indexation raises liabilities by approximately "
    "i% — so a 5% grant on £70bn of liabilities costs around £3.5bn. The soft cap pays "
    "less than CPI when inflation exceeds 5%, which saves money but leaves pensioners "
    "with a real terms cut. The chart below shows annual indexation under each approach "
    "and the cost difference as a fraction of liabilities."
)

fig_rates = go.Figure()
fig_rates.add_trace(go.Bar(
    x=ALL_YEARS, y=[cpi_all[y] for y in ALL_YEARS],
    name="Full CPI", marker_color=COLOURS["cpi"], opacity=0.5,
    hovertemplate="%{x}<br>Full CPI: %{y:.1f}%<extra></extra>",
))
fig_rates.add_trace(go.Scatter(
    x=ALL_YEARS, y=[sc_all[y] for y in ALL_YEARS],
    name="Soft cap", line=dict(color=COLOURS["soft_cap"], width=2.5),
    hovertemplate="%{x}<br>Soft cap: %{y:.1f}%<extra></extra>",
))
fig_rates.update_layout(
    xaxis_title="Year", yaxis_title="Indexation rate (%)",
    yaxis=dict(ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_rates, use_container_width=True)

# Cost difference: full CPI minus soft cap, as % of liabilities
# ΔL = L × (full - sc) / 100; express as % of liabilities = (full - sc)
cost_diff = {y: cpi_all[y] - sc_all[y] for y in ALL_YEARS}

fig_cost = go.Figure()
fig_cost.add_trace(go.Bar(
    x=ALL_YEARS, y=[cost_diff[y] for y in ALL_YEARS],
    name="Extra cost of full CPI vs soft cap",
    marker_color="#EF553B", opacity=0.8,
    hovertemplate="%{x}<br>Extra cost: %{y:.2f}% of liabilities<extra></extra>",
))
fig_cost.update_layout(
    xaxis_title="Year",
    yaxis_title="Additional liability uplift (% of liabilities)",
    yaxis=dict(ticksuffix="%"),
    hovermode="x unified",
)
st.plotly_chart(fig_cost, use_container_width=True)

placeholder(
    "In most years the soft cap and full CPI are identical — CPI was below 5% so the "
    "cap never bit. The divergence in 2022–2023 is stark: the soft cap saved roughly "
    "2–3 percentage points of liabilities compared to full CPI. On £70bn of liabilities "
    "that is £1.4–2.1bn per year. Whether that saving was necessary depends on whether "
    "the fund could afford full indexation — which is what the next chart shows."
)

# ---------------------------------------------------------------------------
# Section 3: Post-indexation FR (affordability)
# ---------------------------------------------------------------------------
st.subheader("Could the fund afford full indexation?")

placeholder(
    "The chart below shows the funding ratio *after* granting full CPI indexation. "
    "A post-indexation FR above 100% means the fund could have afforded full CPI and "
    "still been in surplus. Below 100% means full indexation would have pushed the fund "
    "into deficit — someone would have had to make up the shortfall through higher "
    "contributions or reduced benefits."
)

fig_post = go.Figure()
fig_post.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                   annotation_text="Break-even after full CPI", annotation_position="top left")

for key, label in [("uss_tp", "USS TP"), ("ucu_prudent", "UCU Prudent"), ("ucu_best_est", "UCU Best Estimate")]:
    yrs  = fr_years(key)
    vals = [float(_fr_histories.loc[y, key]) / (1 + cpi_all[y] / 100) for y in yrs]
    is_selected = (key == selected_basis)
    fig_post.add_trace(go.Scatter(
        x=yrs, y=vals, name=label,
        line=dict(color=COLOURS[key], width=3 if is_selected else 1.5,
                  dash="solid" if is_selected else "dot"),
        hovertemplate=f"{label}<br>%{{x}}: post-idx FR %{{y:.1f}}%<extra></extra>",
    ))

fig_post.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Post-indexation funding ratio (%)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_post, use_container_width=True)

placeholder(
    "On the USS TP basis, full CPI indexation was unaffordable every year from 2009 to "
    "2022. Even in 2022 when the FR crossed 100%, granting full CPI (8.8%) would have "
    "pushed it back below 94%. On the UCU Best Estimate basis, the fund could have "
    "afforded full indexation throughout, with a large residual surplus every year. "
    "UCU Prudent is in between: affordable most years but tight in 2017 and 2021–2023 "
    "when inflation was high."
)

# ---------------------------------------------------------------------------
# Section 4: Residual surplus after full indexation
# ---------------------------------------------------------------------------
st.subheader("Residual surplus after full indexation")

placeholder(
    "If the fund is above break-even after full indexation, there is surplus left over. "
    "Under the UCU Best Estimate basis this surplus is substantial and persistent — "
    "equivalent to 25–40% of liabilities throughout the period. That raises a question "
    "the current scheme design does not fully answer: who should benefit from it?"
)

fig_residual = go.Figure()
fig_residual.add_hline(y=0, line_dash="dash", line_color="lightgray", line_width=1)

for key, label in [("uss_tp", "USS TP"), ("ucu_prudent", "UCU Prudent"), ("ucu_best_est", "UCU Best Estimate")]:
    yrs  = fr_years(key)
    # Residual surplus = post-indexation FR - 100, as % of liabilities
    vals = [float(_fr_histories.loc[y, key]) / (1 + cpi_all[y] / 100) - 100 for y in yrs]
    is_selected = (key == selected_basis)
    fig_residual.add_trace(go.Scatter(
        x=yrs, y=vals, name=label,
        line=dict(color=COLOURS[key], width=3 if is_selected else 1.5,
                  dash="solid" if is_selected else "dot"),
        fill="tozeroy" if is_selected else None,
        fillcolor=f"rgba({','.join(str(int(COLOURS[key].lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.1)" if is_selected else None,
        hovertemplate=f"{label}<br>%{{x}}: residual %{{y:+.1f}}% of liabilities<extra></extra>",
    ))

fig_residual.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="Residual surplus after full CPI (% of liabilities)", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_residual, use_container_width=True)

placeholder(
    "The UCU Best Estimate line shows a persistent residual surplus of 25–40% of "
    "liabilities — even after paying full CPI indexation every year. Under the soft cap "
    "the residual is even larger, because the cap saves money in high-inflation years. "
    "This surplus is not distributed to members or used to reduce contributions under "
    "current rules. The question of what to do with it — and what to do when there is "
    "a deficit instead — is what conditional indexation is designed to address."
)

# ---------------------------------------------------------------------------
# Section 5: Soft cap vs full CPI — post-indexation comparison
# ---------------------------------------------------------------------------
st.subheader("Soft cap vs full CPI: post-indexation funding ratio")

placeholder(
    "The soft cap is cheaper than full CPI in high-inflation years. The chart below "
    "compares the post-indexation FR under both approaches on the selected basis. "
    "In most years they are identical. In 2022–2023 the soft cap provides meaningful "
    "headroom — but only on bases that were already close to the affordability boundary."
)

fig_sc_vs_full = go.Figure()
fig_sc_vs_full.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                          annotation_text="Break-even", annotation_position="top left")

sel_yrs = fr_years(selected_basis)
sel_fr  = [float(_fr_histories.loc[y, selected_basis]) for y in sel_yrs]
post_full = [fr / (1 + cpi_all[y] / 100) for fr, y in zip(sel_fr, sel_yrs)]
post_sc   = [fr / (1 + sc_all[y]  / 100) for fr, y in zip(sel_fr, sel_yrs)]

fig_sc_vs_full.add_trace(go.Scatter(
    x=sel_yrs, y=post_full, name="After full CPI",
    line=dict(color=COLOURS["cpi"], width=2.5),
    hovertemplate="%{x}<br>After full CPI: %{y:.1f}%<extra></extra>",
))
fig_sc_vs_full.add_trace(go.Scatter(
    x=sel_yrs, y=post_sc, name="After soft cap",
    line=dict(color=COLOURS["soft_cap"], width=2.5),
    hovertemplate="%{x}<br>After soft cap: %{y:.1f}%<extra></extra>",
))
fig_sc_vs_full.update_layout(
    xaxis_title="Year",
    yaxis=dict(title=f"Post-indexation FR (%) — {selected_basis_label}", ticksuffix="%"),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_sc_vs_full, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 6: What this means for a pensioner
# ---------------------------------------------------------------------------
st.subheader("What this means for a pensioner")

placeholder(
    "The fund-level picture translates directly to individual outcomes. A pensioner "
    "who retired in 2017 on £1,000/month has received either the soft cap or full CPI "
    "each year. The gap between them is small in most years — but 2022–2023 matter a "
    "lot. Over the full period the cumulative difference is meaningful."
)

# Pension paths from start_year
idx_years = [y for y in sorted(_index.keys()) if y >= start_year]
n = len(idx_years)
idx_vals  = np.array([_index[y] for y in idx_years])
deflator  = _index[start_year] / idx_vals

def pension_path(rates_dict):
    p = np.empty(n)
    p[0] = float(starting_pension)
    for i in range(1, n):
        y = idx_years[i]
        r = rates_dict.get(y, 0.0)
        p[i] = p[i-1] * (1 + r / 100)
    return p

pension_sc   = pension_path(sc_all)
pension_full = pension_path(cpi_all)
pension_none = np.full(n, float(starting_pension))

real_sc   = pension_sc   * deflator
real_full = pension_full * deflator
real_none = pension_none * deflator

fig_pension = go.Figure()
fig_pension.add_hline(
    y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power", annotation_position="top left",
)
for pension, name, colour in [
    (real_none, "No indexation",   "#888888"),
    (real_sc,   "Soft cap",        COLOURS["soft_cap"]),
    (real_full, f"Full {inflation_measure}", COLOURS["cpi"]),
]:
    fig_pension.add_trace(go.Scatter(
        x=idx_years, y=pension, name=name,
        line=dict(color=colour, width=2),
        hovertemplate=f"%{{x}}<br>£%{{y:,.0f}}<extra>{name}</extra>",
    ))
fig_pension.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Monthly pension (£, {start_year} prices, {inflation_measure}-deflated)",
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_pension, use_container_width=True)

# Summary metrics
end_year = idx_years[-1]
chg_none = 100 * (real_none[-1] / starting_pension - 1)
chg_sc   = 100 * (real_sc[-1]   / starting_pension - 1)
chg_full = 100 * (real_full[-1] / starting_pension - 1)

col1, col2, col3 = st.columns(3)
col1.metric("No indexation",         f"£{real_none[-1]:,.0f}/month",
            f"{chg_none:+.1f}% real ({end_year})")
col2.metric("Soft cap",              f"£{real_sc[-1]:,.0f}/month",
            f"{chg_sc:+.1f}% real ({end_year})")
col3.metric(f"Full {inflation_measure}", f"£{real_full[-1]:,.0f}/month",
            f"{chg_full:+.1f}% real ({end_year})")

placeholder(
    "The soft cap and full CPI track each other closely until 2022. The two high-inflation "
    "years then drive a lasting gap in real purchasing power. A pensioner on the soft cap "
    "has permanently lower purchasing power than one on full CPI — the cap is not made up "
    "in later years. This is the core tension: the cap saves the fund money, but it does "
    "so by transferring inflation risk onto pensioners. The next page asks how the scheme "
    "could respond to a surplus or deficit more systematically."
)

# ---------------------------------------------------------------------------
# Section 7: HE real wages vs CPI
# ---------------------------------------------------------------------------
st.subheader("Wages and contributions: the other side of the equation")

placeholder(
    "The fund's contribution income depends on both the contribution rate and the "
    "size of the salary roll. HE sector wages have grown persistently below CPI since "
    "2009 — meaning the real value of the contribution stream has been eroding even "
    "when nominal rates were held constant. A pension scheme financed by a shrinking "
    "real wage base faces a structural headwind that higher contribution rates only "
    "partially offset."
)

_wage_years = sorted(HE_WAGE_GROWTH_NOM.keys())

# Build cumulative real wage index (base = 100 at first year)
_cum_wage  = [100.0]
_cum_cpi   = [100.0]
for y in _wage_years[1:]:
    prev_y = _wage_years[_wage_years.index(y) - 1]
    nom_g  = HE_WAGE_GROWTH_NOM.get(y, 0.0)
    cpi_g  = cpi_rate(y)
    _cum_wage.append(_cum_wage[-1] * (1 + nom_g / 100))
    _cum_cpi.append(_cum_cpi[-1]  * (1 + cpi_g  / 100))

_real_wage = [w / c * 100 for w, c in zip(_cum_wage, _cum_cpi)]

fig_wages = go.Figure()
fig_wages.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                    annotation_text="2008 real wage baseline",
                    annotation_position="top left")
fig_wages.add_trace(go.Scatter(
    x=_wage_years, y=_real_wage, name="HE real wage index",
    line=dict(color="#636EFA", width=2.5),
    hovertemplate="%{x}<br>Real wage index: %{y:.1f}<extra></extra>",
))
fig_wages.add_trace(go.Bar(
    x=_wage_years,
    y=[HE_WAGE_GROWTH_NOM[y] - cpi_rate(y) for y in _wage_years],
    name="Annual real wage growth",
    marker_color=["#54A24B" if HE_WAGE_GROWTH_NOM[y] - cpi_rate(y) >= 0 else "#E45756"
                  for y in _wage_years],
    opacity=0.5, yaxis="y2",
    hovertemplate="%{x}<br>Real wage growth: %{y:+.1f}%<extra></extra>",
))
fig_wages.update_layout(
    xaxis_title="Year",
    yaxis =dict(title="Real wage index (2008 = 100)"),
    yaxis2=dict(title="Annual real wage growth (%)", ticksuffix="%",
                overlaying="y", side="right", showgrid=False, zeroline=False),
    hovermode="x unified", legend_title="",
)
st.plotly_chart(fig_wages, use_container_width=True)

placeholder(
    "Cumulative real pay in HE fell by around 15–20% between 2009 and 2022. "
    "Each year of below-inflation settlement permanently reduces the base on which "
    "contributions are calculated. A 20% contribution rate applied to a salary roll "
    "that has shrunk 15% in real terms raises 15% less in real money than it did at "
    "the start — equivalent to a silent cut in the effective contribution rate. "
    "This matters for the projections on the next page, which carry this wage dynamic forward."
)

# ---------------------------------------------------------------------------
# Section 8: How surpluses and deficits are handled now
# ---------------------------------------------------------------------------
st.subheader("How surpluses and deficits are handled today")

placeholder(
    "PLACEHOLDER — explain the current USS mechanisms for responding to funding shortfalls "
    "and surpluses: triennial valuations set contribution rates, deficit recovery plans, "
    "the role of the employer covenant, and the fact that surpluses currently cannot be "
    "easily returned to members or used to enhance indexation. Explain why this means "
    "indexation is effectively a fixed commitment regardless of fund position — and why "
    "that creates the problem conditional indexation is designed to solve."
)
