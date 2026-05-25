"""USS fund accounting model.

Core simulation engine. Given a sequence of annual shocks (equity real returns %,
gilt yield %, CPI rate %), evolves assets and liabilities forward and computes the
CI factor and catch-up indexation at each step.

Two liability measures run simultaneously (following USS CI second report):
  1. Best Estimate / sustainability test  — discount rate = gilt + be_spread
  2. Technical Provisions / affordability test — discount rate = gilt + tp_spread

The CI factor (0–1) is determined by whether the fund can *afford* target indexation
after granting it — i.e. whether the post-grant surplus is non-negative on both tests.
When it cannot, the CI factor is solved such that granting (factor × target) leaves
the surplus at zero. This matches the USS report's mechanism.

The CI factor feedback loop: a lower CI factor reduces ΔL_idx, which improves
the post-grant FR, which may allow a higher factor next year.

Catch-up uses the implicit surplus approach: no separate reserve; catch-up is paid
from scheme surplus when CI factor = 1 and surplus remains after in-year indexation.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@dataclass
class FundParams:
    """All parameters governing one simulation run."""

    # Starting conditions (from 2023 valuation by default)
    assets_bn: float = 73.1
    tp_fr: float = 1.11        # TP funding ratio at start
    be_fr: float = 1.38        # BE funding ratio at start
    pr_fr: float = 1.05        # UCU Prudent funding ratio at start

    # Liability discount rate spreads over 10yr gilt yield (percentage points)
    be_spread: float = 3.23    # Best estimate: Gilts + 3.23% (USS CI report)
    tp_spread: float = 1.75    # TP: Gilts + 1.75% (USS CI report)
    pr_spread: float = 0.75    # UCU Prudent: Gilts + 0.75% (approx CPI+1.5%)

    # Investment strategy
    equity_share: float = 0.67
    bond_return_real: float = 0.0   # real bond return % p.a.

    # Contributions
    contribution_rate: float = 0.20
    salary_roll_bn: float = 2.5     # £bn p.a.
    wage_growth_real: float = -0.5  # real wage growth % p.a. (below CPI)

    # Payouts: pensions paid as fraction of assets p.a.
    payout_rate: float = 0.045

    # CI target: real enhancement above CPI (post-retirement target = CPI + 0%)
    target_real: float = 0.0       # % above CPI; e.g. 1.0 for CPI+1%

    # Statutory minimum post-retirement (CPI capped at this)
    statutory_min_cap: float = 2.5

    # Surplus distribution
    surplus_distribution_frac: float = 0.0
    indexation_share: float = 0.5
    employer_contribution_share: float = 0.65
    be_buffer: float = 1.15    # Min BE FR before surplus distribution

    # Catch-up
    catchup_window: int = 0    # 0 = indefinite


# ---------------------------------------------------------------------------
# Annual state
# ---------------------------------------------------------------------------

@dataclass
class FundState:
    year: int
    assets_bn: float
    liabilities_be_bn: float
    liabilities_tp_bn: float
    liabilities_pr_bn: float
    fr_be: float
    fr_tp: float
    fr_pr: float
    ci_factor: float           # 0–1
    indexation_pct: float      # total indexation granted this year (%)
    target_pct: float          # what full target would have been
    catchup_gap: float         # cumulative gap below target
    catchup_paid: float
    contribution_rate: float
    contribution_relief: float
    surplus_distributed: float


# ---------------------------------------------------------------------------
# Liability uplift from an indexation grant
# ---------------------------------------------------------------------------

def _delta_L(L: float, indexation_pct: float) -> float:
    """Increase in liability stock from granting indexation_pct% this year.

    An indexation grant of i% uplifts all future benefit cashflows by i%,
    so the PV of liabilities rises by i% × L (first-order approximation).
    This is the correct simple model; no duration adjustment needed here
    since the cashflow schedule already embeds the timing.
    """
    return L * indexation_pct / 100.0


# ---------------------------------------------------------------------------
# CI factor: solve for the factor that leaves post-grant surplus = 0
# ---------------------------------------------------------------------------

def _solve_ci_factor(
    A: float,
    L_be: float,
    L_tp: float,
    target_pct: float,
    stat_min_pct: float,
    ci_scheme: str,
) -> float:
    """Return the CI factor (0–1) such that indexation is affordable.

    Affordability means: after granting (factor × target_pct)%, the surplus
    on *both* tests remains ≥ 0.

    If both tests pass at factor=1, return 1.0.
    If both fail at factor=0 (even stat min unaffordable), return 0.0
    and let the caller apply the statutory minimum floor separately.

    For binary CI: return 1.0 if factor=1 is affordable, else 0.0.
    For guaranteed/soft_cap: always return 1.0 (cost borne externally).
    """
    if ci_scheme in ("guaranteed", "soft_cap"):
        return 1.0

    # Check if full target is affordable on both tests
    dL_be_full = _delta_L(L_be, target_pct)
    dL_tp_full = _delta_L(L_tp, target_pct)
    if A >= L_be + dL_be_full and A >= L_tp + dL_tp_full:
        return 1.0

    # Not fully affordable. Find the largest factor in [0,1] such that
    # A >= L_be + factor×ΔL_be_full  AND  A >= L_tp + factor×ΔL_tp_full
    # => factor <= (A - L_be) / dL_be_full  [if dL_be_full > 0]
    # => factor <= (A - L_tp) / dL_tp_full
    # Take the binding (minimum) constraint.
    if target_pct <= 0:
        return 1.0

    be_surplus = A - L_be
    tp_surplus = A - L_tp
    factor = min(
        be_surplus / dL_be_full if dL_be_full > 0 else 1.0,
        tp_surplus / dL_tp_full if dL_tp_full > 0 else 1.0,
    )
    factor = max(0.0, min(1.0, factor))

    if ci_scheme == "binary":
        # Binary: only pay if full indexation is affordable
        return 1.0 if factor >= 1.0 else 0.0

    return factor


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def simulate(
    shocks: list[tuple[float, float, float]],
    params: FundParams,
    ci_scheme: str = "proportional",
) -> list[FundState]:
    """Run the fund model for a sequence of annual shocks.

    Parameters
    ----------
    shocks : list of (equity_real_ret_pct, gilt_yield_pct, cpi_rate_pct)
    params : FundParams
    ci_scheme : "guaranteed" | "binary" | "proportional" | "soft_cap" |
                "soft_cap_plus" | "hybrid"

    Returns
    -------
    List of FundState, one per year.
    """
    L_be = params.assets_bn / params.be_fr
    L_tp = params.assets_bn / params.tp_fr
    L_pr = params.assets_bn / params.pr_fr
    A = params.assets_bn
    salary_roll = params.salary_roll_bn

    catchup_gap = 0.0
    gap_history: list[float] = []

    states: list[FundState] = []
    start_year = 2023

    for t, (eq_ret_real, gilt_yield, cpi) in enumerate(shocks):
        year = start_year + t

        # --- Nominal portfolio return ---
        # eq_ret_real is real return above CPI; convert to nominal
        eq_ret_nom  = (1 + eq_ret_real / 100) * (1 + cpi / 100) - 1
        bond_ret_nom = (1 + params.bond_return_real / 100) * (1 + cpi / 100) - 1
        port_ret_nom = (params.equity_share * eq_ret_nom
                        + (1 - params.equity_share) * bond_ret_nom)

        # --- Contributions (nominal) ---
        wage_nom = (1 + (params.wage_growth_real + cpi) / 100)
        salary_roll *= wage_nom
        C = params.contribution_rate * salary_roll

        # --- Payouts ---
        P = params.payout_rate * A

        # --- Evolve assets ---
        A_new = A * (1 + port_ret_nom) + C - P

        # --- Liability discount rates ---
        be_disc = (gilt_yield + params.be_spread) / 100
        tp_disc = (gilt_yield + params.tp_spread) / 100
        pr_disc = (gilt_yield + params.pr_spread) / 100

        # Evolve liabilities before indexation grant:
        # L grows at discount rate (unwinding of discounting as we step forward),
        # plus new accrual, minus payouts already made.
        accrual = C * 0.8
        L_be_pre = L_be * (1 + be_disc) + accrual - P
        L_tp_pre = L_tp * (1 + tp_disc) + accrual - P
        L_pr_pre = L_pr * (1 + pr_disc) + accrual - P
        # Floor at small positive to avoid numerical issues
        L_be_pre = max(L_be_pre, 1e-6)
        L_tp_pre = max(L_tp_pre, 1e-6)
        L_pr_pre = max(L_pr_pre, 1e-6)

        # --- Target indexation ---
        target_pct = cpi + params.target_real
        stat_min   = min(cpi, params.statutory_min_cap)
        stat_min   = max(stat_min, 0.0)

        # --- CI factor (solves affordability, not just FR threshold) ---
        ci_factor = _solve_ci_factor(
            A=A_new,
            L_be=L_be_pre,
            L_tp=L_tp_pre,
            target_pct=target_pct,
            stat_min_pct=stat_min,
            ci_scheme=ci_scheme,
        )

        # Scheme-specific floor adjustments
        if ci_scheme == "soft_cap":
            indexation = soft_cap_indexation(cpi)
        elif ci_scheme == "soft_cap_plus":
            # Floor = soft cap; CI factor adds upside above that
            floor = soft_cap_indexation(cpi)
            indexation = floor + ci_factor * max(0.0, target_pct - floor)
        elif ci_scheme == "hybrid":
            # Floor = params.hybrid_floor_frac × target, always paid
            floor = getattr(params, "hybrid_floor_frac", 0.5) * target_pct
            indexation = floor + ci_factor * max(0.0, target_pct - floor)
        else:
            indexation = ci_factor * target_pct

        # Statutory minimum floor
        indexation = max(indexation, stat_min)

        # --- Apply indexation to liabilities ---
        dL_be = _delta_L(L_be_pre, indexation)
        dL_tp = _delta_L(L_tp_pre, indexation)
        dL_pr = _delta_L(L_pr_pre, indexation)
        L_be_new = L_be_pre + dL_be
        L_tp_new = L_tp_pre + dL_tp
        L_pr_new = L_pr_pre + dL_pr

        fr_be_new = A_new / L_be_new
        fr_tp_new = A_new / L_tp_new
        fr_pr_new = A_new / L_pr_new

        # --- Catch-up ---
        gap_this_year = max(0.0, target_pct - indexation)
        gap_history.append(gap_this_year)
        window = gap_history[-params.catchup_window:] if params.catchup_window > 0 else gap_history
        catchup_gap = sum(window)
        catchup_paid = 0.0

        if ci_factor >= 1.0 and catchup_gap > 0:
            # Budget: remaining surplus after in-year indexation on both tests
            be_surplus = max(0.0, A_new - L_be_new)
            tp_surplus = max(0.0, A_new - L_tp_new)
            budget_bn = min(be_surplus, tp_surplus)
            # Convert £bn to indexation %: ΔL = L × i/100, so i = 100 × budget / L
            catchup_capacity = 100.0 * budget_bn / L_be_new if L_be_new > 0 else 0.0
            catchup_paid = min(catchup_gap, catchup_capacity)
            catchup_gap = max(0.0, catchup_gap - catchup_paid)
            # Reduce last entry in gap_history to reflect partial payment
            gap_history[-1] = max(0.0, gap_history[-1] - catchup_paid)

        # --- Surplus distribution ---
        contribution_relief = 0.0
        surplus_distributed = 0.0
        if params.surplus_distribution_frac > 0 and ci_factor >= 1.0:
            be_surplus = max(0.0, A_new / L_be_new - params.be_buffer) * L_be_new
            if be_surplus > 0:
                distributable = be_surplus * params.surplus_distribution_frac
                surplus_distributed = distributable
                contrib_share = distributable * (1 - params.indexation_share)
                contribution_relief = contrib_share / salary_roll * 100

        states.append(FundState(
            year=year,
            assets_bn=A_new,
            liabilities_be_bn=L_be_new,
            liabilities_tp_bn=L_tp_new,
            liabilities_pr_bn=L_pr_new,
            fr_be=fr_be_new,
            fr_tp=fr_tp_new,
            fr_pr=fr_pr_new,
            ci_factor=ci_factor,
            indexation_pct=indexation + catchup_paid,
            target_pct=target_pct,
            catchup_gap=catchup_gap,
            catchup_paid=catchup_paid,
            contribution_rate=params.contribution_rate,
            contribution_relief=contribution_relief,
            surplus_distributed=surplus_distributed,
        ))

        A = A_new
        L_be = L_be_new
        L_tp = L_tp_new
        L_pr = L_pr_new

    return states


# ---------------------------------------------------------------------------
# Soft cap formula
# ---------------------------------------------------------------------------

def soft_cap_indexation(cpi: float) -> float:
    """Current USS DB soft cap formula (always CPI-based)."""
    if cpi <= 5.0:
        return cpi
    elif cpi <= 15.0:
        return 5.0 + 0.5 * (cpi - 5.0)
    else:
        return 10.0
