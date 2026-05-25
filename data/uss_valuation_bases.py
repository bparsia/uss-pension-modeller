"""USS funding ratio histories under three valuation bases.

Three named bases derived from UCU valuation methodology (Shapland et al.):

  USS_TP        — published triennial valuations (Technical Provisions basis,
                  gilt-linked self-sufficiency discount rate). Volatile; the
                  old contested approach.

  UCU_PRUDENT   — CPI + ~1.5% real discount rate. FR 102–109% at all four
                  anchor dates. A conservative but stable approach.

  UCU_BEST_EST  — CPI + ~3.2% real discount rate. FR 135–146% at all four
                  anchor dates. Best estimate; USS moving toward this.

Method (from the UCU valuation methodology):

    liabilities(UCU basis) = liabilities(USS basis)
                           × PV(cash flows, UCU discount rate)
                           / PV(cash flows, USS discount rate)

The 2020 cash flow schedule (USS_CashFlows.xlsx) is used as the basis.
The USS TP implied flat real discount rate is back-calibrated from the four
known anchor points and interpolated for inter-valuation years.

Inter-valuation years use log-linear interpolation of the USS TP rate,
which maps to smooth (but plausible) FR paths consistent with the anchors.
Stochasticity is handled by the caller (USS_Scenarios page), not here.
"""

from pathlib import Path
import numpy as np
import pandas as pd

_SOURCES = Path(__file__).parent.parent / "sources"
_CASHFLOWS = _SOURCES / "USS_CashFlows.xlsx"

# ---------------------------------------------------------------------------
# Anchor data (from UCU valuation methodology report + USS published figures)
# ---------------------------------------------------------------------------
# (year, assets_bn, uss_tp_fr, ucu_be_fr, ucu_pr_fr, ucu_be_rate, ucu_pr_rate)
_ANCHORS = [
    # year  assets   USS TP  UCU BE  UCU PR  be_rate  pr_rate
    # USS TP FR: triennial valuations + monitoring reports
    # UCU BE/PR: from UCU valuation methodology (Shapland et al.), anchor years only
    (2008,  None,    1.03,   None,   None,   None,    None),
    (2009,  None,    0.74,   None,   None,   None,    None),   # post-Lehman monitoring est.
    (2011,  None,    0.92,   None,   None,   None,    None),
    (2014,  None,    0.89,   None,   None,   None,    None),
    (2017,  60.0,    0.89,   1.36,   1.02,   0.030,   0.014),
    (2018,  63.7,    0.87,   1.46,   1.09,   0.033,   0.016),
    (2020,  66.5,    0.83,   1.35,   1.04,   0.030,   0.014),
    (2021,  None,    0.87,   None,   None,   None,    None),   # equity recovery estimate
    (2022,  None,    1.02,   None,   None,   None,    None),   # gilt yield surge
    (2023,  73.1,    1.11,   1.38,   1.05,   0.035,   0.019),
    (2024,  74.8,    1.14,   None,   None,   None,    None),   # monitoring Mar 2024
    (2025,  None,    1.16,   None,   None,   None,    None),   # monitoring Mar 2025
]

# Calibrated USS TP implied flat real discount rates (back-calculated from anchors)
# These track long gilt yields; used to interpolate FR for non-anchor years.
_USS_REAL_RATES = {
    2008:  0.015,   # pre-GFC: positive real gilt yields ~1-2%
    2009: -0.005,   # post-Lehman: yields fell
    2010:  0.010,   # recovery
    2011:  0.008,   # 2011 valuation implied ~0.7-0.9%; using calibrated anchor below
    2017:  0.695,   # calibrated (average of BE/PR implied: 0.681, 0.709)
    2018:  0.461,   # calibrated
    2020:  0.331,   # calibrated (average: 0.381, 0.281)
    2023:  2.198,   # calibrated (average: 2.184, 2.211)
    2024:  2.300,   # estimated: gilt yields remained elevated
    2025:  2.200,   # estimated: modest decline from 2024 peak
}

# ---------------------------------------------------------------------------
# Cash flow loading
# ---------------------------------------------------------------------------

def _load_real_cashflows() -> np.ndarray:
    """Load real cash flows from USS_CashFlows.xlsx QuickCalcs sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(_CASHFLOWS, data_only=True)
    ws = wb["QuickCalcs"]
    rows = list(ws.iter_rows(values_only=True))
    # Real cash flows are in column J (index 9), rows 2..83 (years 1..82)
    cf = [rows[i][9] for i in range(2, 84)]
    cf = [c if (c is not None and isinstance(c, (int, float))) else 0.0 for c in cf]
    return np.array(cf)


def _pv(r: float, cash_flows: np.ndarray) -> float:
    """PV of cash_flows at flat annual real discount rate r."""
    t = np.arange(1, len(cash_flows) + 1)
    return float(np.sum(cash_flows / (1 + r) ** t))


# ---------------------------------------------------------------------------
# Core FR computation
# ---------------------------------------------------------------------------

def _ucu_fr(assets: float, uss_tp_liabs: float, ucu_rate: float,
             uss_rate: float, cf: np.ndarray) -> float:
    """FR under a UCU basis, given the USS TP liability and conversion rates."""
    ratio = _pv(ucu_rate, cf) / _pv(uss_rate, cf)
    ucu_liabs = uss_tp_liabs * ratio
    return assets / ucu_liabs


def build_fr_histories(years: list[int]) -> pd.DataFrame:
    """Return a DataFrame with columns [year, uss_tp, ucu_prudent, ucu_best_est].

    For anchor years with published data, values are taken directly.
    For inter-anchor years, the USS TP rate is interpolated and UCU FRs
    are derived from the same conversion formula.

    ``years`` should cover 2008–2025 or whatever range is needed.
    """
    if not _CASHFLOWS.exists():
        raise FileNotFoundError(
            f"Cash flow data not found at {_CASHFLOWS}. "
            "This file is not in the repo (non-shareable). "
            "FR history will fall back to the CSV-based approach."
        )

    cf = _load_real_cashflows()

    # Build a lookup of anchor USS TP rates
    anchor_rates = {yr: r for yr, r in _USS_REAL_RATES.items()}

    # Known anchors as lookup
    anchor_lookup = {a[0]: a for a in _ANCHORS}

    # Interpolate USS TP rate for every year using log-linear interpolation
    # (rates can be negative so use linear, not log)
    known_years = sorted(anchor_rates.keys())
    known_vals  = [anchor_rates[y] / 100 for y in known_years]  # convert % to decimal

    all_rates = np.interp(years, known_years, known_vals)
    year_rate = dict(zip(years, all_rates))

    # Asset interpolation: only anchors with known assets
    asset_years = [a[0] for a in _ANCHORS if a[1] is not None]
    asset_vals  = [a[1] for a in _ANCHORS if a[1] is not None]
    all_assets  = np.interp(years, asset_years, asset_vals)
    year_assets = dict(zip(years, all_assets))

    # USS TP FR: all anchors have a value
    uss_tp_years = [a[0] for a in _ANCHORS]
    uss_tp_vals  = [a[2] * 100 for a in _ANCHORS]
    all_uss_tp   = np.interp(years, uss_tp_years, uss_tp_vals)
    year_uss_tp  = dict(zip(years, all_uss_tp))

    # UCU rates: interpolate from anchor years that have them (2017–2023)
    ucu_anchor_years = [a[0] for a in _ANCHORS if a[5] is not None]
    be_rates = [a[5] for a in _ANCHORS if a[5] is not None]
    pr_rates = [a[6] for a in _ANCHORS if a[6] is not None]
    ucu_min_year = min(ucu_anchor_years)

    rows = []
    for yr in years:
        r_uss   = year_rate[yr]
        assets  = year_assets[yr]
        uss_tp_fr = year_uss_tp[yr]
        uss_liabs = assets / (uss_tp_fr / 100)

        if yr >= ucu_min_year:
            r_be = float(np.interp(yr, ucu_anchor_years, be_rates))
            r_pr = float(np.interp(yr, ucu_anchor_years, pr_rates))
            be_fr = _ucu_fr(assets, uss_liabs, r_be, r_uss, cf) * 100
            pr_fr = _ucu_fr(assets, uss_liabs, r_pr, r_uss, cf) * 100
        else:
            be_fr = None
            pr_fr = None

        rows.append(dict(
            year=yr,
            uss_tp=round(uss_tp_fr, 1),
            ucu_prudent=round(pr_fr, 1) if pr_fr is not None else None,
            ucu_best_est=round(be_fr, 1) if be_fr is not None else None,
        ))

    return pd.DataFrame(rows).set_index("year")


# ---------------------------------------------------------------------------
# Convenience: cached singleton
# ---------------------------------------------------------------------------

_cache: pd.DataFrame | None = None


def get_fr_histories(years: list[int] | None = None) -> pd.DataFrame:
    """Cached FR histories for the standard 2008–2025 range."""
    global _cache
    if years is None:
        years = list(range(2008, 2026))
    if _cache is None or list(_cache.index) != years:
        _cache = build_fr_histories(years)
    return _cache
