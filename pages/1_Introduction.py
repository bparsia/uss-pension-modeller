"""Page 1 — Introduction to indexation."""
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from data.shared import CPI, RPI, cpi_rate, rpi_rate, GILT_YIELD_10Y
from data.fund_model import soft_cap_indexation
from styles import placeholder

st.title("What is pension indexation?")

placeholder(
    "Your USS pension is paid monthly for the rest of your life after retirement. "
    "The amount you receive is fixed in pounds — but pounds buy less over time as "
    "prices rise. **Indexation** is the annual uprating of your pension to protect "
    "its purchasing power. The question is: how much uprating, and who pays for it?"
)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
st.sidebar.header("Parameters")
start_year = st.sidebar.selectbox(
    "Retirement year",
    options=list(range(2005, 2024)),
    index=list(range(2005, 2024)).index(2009),
)
starting_pension = st.sidebar.number_input(
    "Starting monthly pension (£)", min_value=100, max_value=10000, value=1000, step=100,
)
inflation_measure = st.sidebar.radio(
    "Inflation measure", ["CPI", "RPI"], horizontal=True,
    help="CPI is the official USS indexation target. RPI is typically 0.5–1pp higher.",
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
_index = CPI if inflation_measure == "CPI" else RPI
_rate_fn = cpi_rate if inflation_measure == "CPI" else rpi_rate

years = [y for y in sorted(_index) if y >= start_year]
n = len(years)

inf_rates  = np.array([_rate_fn(y) for y in years])
# Soft cap is always CPI-based — that is what USS actually pays
sc_rates   = np.array([soft_cap_indexation(cpi_rate(y)) for y in years])
full_rates = inf_rates.copy()

def pension_path(annual_rates_pct: np.ndarray) -> np.ndarray:
    p = np.empty(n)
    p[0] = starting_pension
    for i in range(1, n):
        p[i] = p[i - 1] * (1 + annual_rates_pct[i] / 100)
    return p

pension_none = np.full(n, float(starting_pension))
pension_full = pension_path(full_rates)
pension_sc   = pension_path(sc_rates)

idx_index = np.array([_index[y] for y in years])
deflator  = _index[start_year] / idx_index

real_none = pension_none * deflator
real_full = pension_full * deflator
real_sc   = pension_sc   * deflator

# ---------------------------------------------------------------------------
# Chart 1: Nominal pension value
# ---------------------------------------------------------------------------
st.subheader("Nominal monthly pension over time")
st.caption("In pounds, not adjusted for inflation.")

fig_nom = go.Figure()
fig_nom.add_trace(go.Scatter(
    x=years, y=pension_none, name="No indexation",
    line=dict(color="#888888", width=2, dash="dot"),
    hovertemplate="%{x}<br>£%{y:,.0f}<extra>No indexation</extra>",
))
fig_nom.add_trace(go.Scatter(
    x=years, y=pension_sc, name="Soft cap (current USS DB)",
    line=dict(color="#636EFA", width=2.5),
    hovertemplate="%{x}<br>£%{y:,.0f}<extra>Soft cap</extra>",
))
fig_nom.add_trace(go.Scatter(
    x=years, y=pension_full, name=f"Full {inflation_measure} indexation",
    line=dict(color="#00CC96", width=2),
    hovertemplate=f"%{{x}}<br>£%{{y:,.0f}}<extra>Full {inflation_measure}</extra>",
))
fig_nom.update_layout(
    xaxis_title="Year", yaxis_title="Monthly pension (£)",
    hovermode="x unified", legend_title="Scheme",
)
st.plotly_chart(fig_nom, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 2: Real pension value
# ---------------------------------------------------------------------------
st.subheader("Real monthly pension (purchasing power)")
st.caption(
    f"{inflation_measure}-adjusted to {start_year} prices. "
    f"£{starting_pension:,} = full purchasing power maintained."
)

fig_real = go.Figure()
fig_real.add_hline(
    y=starting_pension, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power", annotation_position="top left",
)
fig_real.add_trace(go.Scatter(
    x=years, y=real_none, name="No indexation",
    line=dict(color="#888888", width=2, dash="dot"),
    hovertemplate="%{x}<br>£%{y:,.0f}<extra>No indexation</extra>",
))
fig_real.add_trace(go.Scatter(
    x=years, y=real_sc, name="Soft cap (current USS DB)",
    line=dict(color="#636EFA", width=2.5),
    hovertemplate="%{x}<br>£%{y:,.0f}<extra>Soft cap</extra>",
))
fig_real.add_trace(go.Scatter(
    x=years, y=real_full, name=f"Full {inflation_measure} indexation",
    line=dict(color="#00CC96", width=2),
    hovertemplate=f"%{{x}}<br>£%{{y:,.0f}}<extra>Full {inflation_measure}</extra>",
))
fig_real.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Monthly pension (£, {start_year} prices, {inflation_measure}-deflated)",
    hovermode="x unified", legend_title="Scheme",
)
st.plotly_chart(fig_real, use_container_width=True)

# ---------------------------------------------------------------------------
# Key numbers
# ---------------------------------------------------------------------------
end_year = years[-1]
loss_none = 100 * (1 - real_none[-1] / starting_pension)
loss_sc   = 100 * (1 - real_sc[-1]   / starting_pension)
loss_full = 100 * (1 - real_full[-1] / starting_pension)

col1, col2, col3 = st.columns(3)
col1.metric("No indexation", f"£{real_none[-1]:,.0f}/month",
            f"{loss_none:+.1f}% real ({end_year})", delta_color="inverse")
col2.metric("Soft cap", f"£{real_sc[-1]:,.0f}/month",
            f"{loss_sc:+.1f}% real ({end_year})", delta_color="inverse")
col3.metric(f"Full {inflation_measure}", f"£{real_full[-1]:,.0f}/month",
            f"{loss_full:+.1f}% real ({end_year})", delta_color="inverse")

# ---------------------------------------------------------------------------
# Chart 3: Annual rates
# ---------------------------------------------------------------------------
st.subheader("What the soft cap actually pays each year")

placeholder(
    "The soft cap pays CPI in full up to 5%, then half of anything above 5%, up to a "
    "maximum of 10%. In most years CPI was below 5% so the soft cap paid in full. "
    "In 2022–2023 it diverged significantly."
)

fig_rates = go.Figure()
fig_rates.add_trace(go.Bar(
    x=years[1:], y=inf_rates[1:], name=f"{inflation_measure} rate",
    marker_color="#FFA15A", opacity=0.7,
    hovertemplate=f"%{{x}}<br>{inflation_measure}: %{{y:.1f}}%<extra></extra>",
))
fig_rates.add_trace(go.Scatter(
    x=years[1:], y=sc_rates[1:], name="Soft cap rate",
    line=dict(color="#636EFA", width=2.5),
    hovertemplate="%{x}<br>Soft cap: %{y:.1f}%<extra></extra>",
))
fig_rates.update_layout(
    xaxis_title="Year", yaxis_title="Annual rate (%)",
    hovermode="x unified", legend_title="Rate", yaxis=dict(ticksuffix="%"),
)
st.plotly_chart(fig_rates, use_container_width=True)

# ---------------------------------------------------------------------------
# Where does the money come from?
# ---------------------------------------------------------------------------
st.subheader("Where does the money come from?")

placeholder(
    "Indexation is not free. Every percentage point of annual increase means the scheme "
    "owes higher payments for the rest of every pensioner's life. That obligation has to "
    "be funded from somewhere: investment returns, contributions, or — if neither covers "
    "the cost — a shortfall that someone has to bear. Under the current USS DB structure, "
    "that means higher contributions from employers *and* members, or reduced future "
    "benefit accrual, or both. Under conditional indexation, some of that risk shifts "
    "differently. The next page explains how."
)

# ---------------------------------------------------------------------------
# Gilt yield context
# ---------------------------------------------------------------------------
with st.expander("Why gilt yields matter"):
    gilts = [(y, GILT_YIELD_10Y[y]) for y in years if y in GILT_YIELD_10Y]
    g_years, g_vals = zip(*gilts)
    fig_gilts = go.Figure()
    fig_gilts.add_trace(go.Scatter(
        x=g_years, y=g_vals, mode="lines+markers",
        line=dict(color="#EF553B", width=2),
        hovertemplate="%{x}<br>10yr gilt yield: %{y:.2f}%<extra></extra>",
    ))
    fig_gilts.update_layout(
        xaxis_title="Year", yaxis_title="10-year gilt yield (%)",
        yaxis=dict(ticksuffix="%"),
    )
    st.plotly_chart(fig_gilts, use_container_width=True)

    placeholder(
        "USS values its liabilities using a discount rate linked to long-dated gilt yields. "
        "When gilt yields fall, liabilities appear larger and the scheme looks less "
        "well-funded — even if assets grew. When gilt yields rose sharply in 2022, "
        "liabilities fell and the funding ratio jumped from 83% to 111% almost overnight. "
        "This is why the valuation methodology matters as much as actual investment returns."
    )
