"""Shared economic data for ussmodeller.

CPI and RPI sourced from ONS (same as jnchesvinflation/utils.py).
Gilt yield data (10-year nominal) sourced from BoE / DMO.
Equity returns (UK/global) sourced from Shapland et al. (2021) and MSCI.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# CPI (CPIH, ONS series D7BT), normalised 2015=100, annual averages
# ---------------------------------------------------------------------------
CPI = {
    2005: 74.9,
    2006: 76.8,
    2007: 79.0,
    2008: 82.7,
    2009: 83.5,
    2010: 86.4,
    2011: 90.4,
    2012: 93.5,
    2013: 96.1,
    2014: 97.9,
    2015: 100.0,
    2016: 101.0,
    2017: 103.6,
    2018: 106.0,
    2019: 108.0,
    2020: 108.7,
    2021: 111.5,
    2022: 121.3,
    2023: 131.4,
    2024: 135.3,
    2025: 138.0,  # estimate
}

# ---------------------------------------------------------------------------
# RPI (All Items, ONS series CHAW), normalised 2015=100
# ---------------------------------------------------------------------------
RPI = {
    2005: 74.3,
    2006: 76.6,
    2007: 79.9,
    2008: 83.1,
    2009: 82.7,
    2010: 86.5,
    2011: 91.0,
    2012: 93.9,
    2013: 96.7,
    2014: 98.9,
    2015: 100.0,
    2016: 101.8,
    2017: 105.1,
    2018: 108.3,
    2019: 111.4,
    2020: 113.2,
    2021: 120.2,
    2022: 136.8,
    2023: 146.3,
    2024: 152.0,
    2025: 156.7,  # estimate
}

# ---------------------------------------------------------------------------
# Annual CPI inflation rates (year-on-year %)
# Derived from CPI dict above.
# ---------------------------------------------------------------------------
def cpi_rate(year: int) -> float:
    if year - 1 not in CPI or year not in CPI:
        return 0.0
    return (CPI[year] - CPI[year - 1]) / CPI[year - 1] * 100.0

def rpi_rate(year: int) -> float:
    if year - 1 not in RPI or year not in RPI:
        return 0.0
    return (RPI[year] - RPI[year - 1]) / RPI[year - 1] * 100.0

# ---------------------------------------------------------------------------
# 10-year nominal gilt yields (% p.a., annual average)
# Source: BoE / DMO. Used as the base for liability discount rates.
# ---------------------------------------------------------------------------
GILT_YIELD_10Y = {
    2005: 4.39,
    2006: 4.50,
    2007: 5.01,
    2008: 4.61,
    2009: 3.63,
    2010: 3.61,
    2011: 3.10,
    2012: 1.84,
    2013: 2.44,
    2014: 2.54,
    2015: 1.87,
    2016: 1.37,
    2017: 1.24,
    2018: 1.42,
    2019: 0.87,
    2020: 0.32,
    2021: 0.85,
    2022: 2.74,
    2023: 4.07,
    2024: 4.24,
    2025: 4.60,  # estimate
}

# ---------------------------------------------------------------------------
# Real equity returns (% p.a., above CPI)
# Approximate global equity real returns; calibrated to Shapland et al. (2021)
# and MSCI World. USS asset mix was ~67% growth assets pre-2018.
# ---------------------------------------------------------------------------
EQUITY_REAL_RETURN = {
    2005: 20.9,
    2006: 10.0,
    2007: 4.5,
    2008: -42.1,
    2009: 26.6,
    2010: 11.8,
    2011: -7.6,
    2012: 13.4,
    2013: 24.0,
    2014: 4.2,
    2015: -0.9,
    2016: 7.5,
    2017: 20.1,
    2018: -10.4,
    2019: 26.6,
    2020: 14.1,
    2021: 19.6,
    2022: -19.8,
    2023: 20.7,
    2024: 16.3,
    2025: 5.0,   # estimate
}

# ---------------------------------------------------------------------------
# USS contribution rates (% of salary, total = employer + employee)
# Sources: USS annual reports, employer/employee rate schedules
# ---------------------------------------------------------------------------
# Employer rates
USS_CONTRIB_EMPLOYER = {
    2008: 16.0,
    2009: 16.0,
    2010: 16.0,
    2011: 16.0,
    2012: 16.0,
    2013: 16.0,
    2014: 16.0,
    2015: 18.0,   # Apr 2015 increase
    2016: 18.0,
    2017: 18.0,
    2018: 18.0,
    2019: 21.1,   # Apr 2019 increase (post-2017 valuation)
    2020: 21.1,
    2021: 23.7,   # Oct 2021 further increase
    2022: 23.7,
    2023: 14.5,   # Jan 2023 reduction (post-2020 revaluation + 2023 valuation)
    2024: 14.5,
    2025: 14.5,
}
# Employee rates
USS_CONTRIB_EMPLOYEE = {
    2008:  6.35,
    2009:  6.35,
    2010:  6.35,
    2011:  6.35,
    2012:  6.35,
    2013:  6.35,
    2014:  6.35,
    2015:  8.0,
    2016:  8.0,
    2017:  8.0,
    2018:  8.0,
    2019:  9.6,
    2020:  9.6,
    2021: 11.0,
    2022: 11.0,
    2023:  6.1,
    2024:  6.1,
    2025:  6.1,
}
# Triennial valuation years (markers)
USS_VALUATION_YEARS = [2008, 2011, 2014, 2017, 2020, 2023]

# ---------------------------------------------------------------------------
# HE sector wage growth (nominal % p.a.)
# Sources: UCEA pay spine settlements + ONS ASHE (HE sector).
# These are approximate annual averages for the whole HE pay spine.
# ---------------------------------------------------------------------------
HE_WAGE_GROWTH_NOM = {
    2008:  3.5,
    2009:  0.5,   # pay freeze begins
    2010:  0.4,
    2011:  0.0,   # pay freeze
    2012:  1.0,
    2013:  1.0,
    2014:  2.0,
    2015:  1.1,
    2016:  1.1,
    2017:  1.7,
    2018:  2.0,
    2019:  3.65,  # UCEA settlement
    2020:  1.8,
    2021:  1.5,
    2022:  3.0,   # below-CPI amid dispute
    2023:  5.0,   # improved settlement
    2024:  5.5,
    2025:  3.5,
}

# ---------------------------------------------------------------------------
# Historical tuples for bootstrap (View C)
# Each entry: (year, equity_real_ret, gilt_yield, cpi_rate)
# Only years where all three are available.
# ---------------------------------------------------------------------------
def bootstrap_tuples() -> list[tuple]:
    years = sorted(set(EQUITY_REAL_RETURN) & set(GILT_YIELD_10Y) & set(CPI))
    result = []
    for y in years:
        if y - 1 not in CPI:
            continue
        result.append((
            y,
            EQUITY_REAL_RETURN[y],
            GILT_YIELD_10Y[y],
            cpi_rate(y),
        ))
    return result

# ---------------------------------------------------------------------------
# USS valuation anchor data (for fund model initialisation)
# ---------------------------------------------------------------------------
USS_2023_VALUATION = {
    "year": 2023,
    "assets_bn": 73.1,
    "uss_tp_fr": 1.11,       # Technical Provisions funding ratio
    "ucu_prudent_fr": 1.05,  # UCU Prudent basis
    "ucu_be_fr": 1.38,       # UCU Best Estimate basis
    "tp_surplus_bn": 7.4,    # TP surplus
}
