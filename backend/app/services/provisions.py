"""Monthly labour provisions accrued on top of an employee's salary.

Source: the client's "Planilha de Custo de Funcionário" workbook.

Three provisions are accrued at one twelfth of the corresponding yearly
obligation, and each one carries its own accessory charges — the FGTS deposit
that will be due when the event is paid, plus, outside Simples Nacional, the
employer social security load. Accruing the provision without its accessories
would under-provision the actual cash outflow.

    base (férias + 1/3 + 13º)      7/36 of salary        19.4444%
    + FGTS 8% over the base        7/36 * 0.08            1.5556%
    + INSS/RAT/Terceiros 28.8%     7/36 * 0.288           5.6000%  (Regime Normal only)

    Simples Nacional   7/36 * 1.080 = 21.0000% of salary
    Regime Normal      7/36 * 1.368 = 26.6000% of salary

Two divergences in the workbook were corrected, per the client's request:

* The Simples Nacional tab had the 13º provision hard-coded to 0 instead of
  salary/12, understating the monthly cost by 8.33% of payroll.
* FGTS over the vacation bonus used salary/454.5; the arithmetic is
  (salary/36) * 8% = salary/450.

With both fixed the workbook's own total lands on exactly 40.00% of salary
(68.80% under Regime Normal), which is the round target it was built around.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Optional, Tuple

# One twelfth of a month's salary, accrued monthly.
VACATION_RATE = Decimal(1) / Decimal(12)          # férias 1/12       — 8.333%
VACATION_BONUS_RATE = Decimal(1) / Decimal(36)    # 1/3 férias 1/12   — 2.778%
THIRTEENTH_RATE = Decimal(1) / Decimal(12)        # 13º salário 1/12  — 8.333%

BASE_RATE = VACATION_RATE + VACATION_BONUS_RATE + THIRTEENTH_RATE  # 19.444%

FGTS_RATE = Decimal("0.08")

# INSS (20%) + Terceiros (5.8%) + RAT (3%), as used by the workbook's
# "Planilha de Custo de Funcionário" tabs. Its other pair of tabs uses 29.8%,
# adding 1% of FAP — the FAP is company-specific and the 28.8% model is the
# internally consistent one, so that is what is applied here.
EMPLOYER_SOCIAL_SECURITY_RATE = Decimal("0.288")

# Tax regimes.
REGIME_NORMAL = "NORMAL"
REGIME_SIMPLES = "SIMPLES_NACIONAL"
REGIME_LABELS = {
    REGIME_NORMAL: "Regime Normal",
    REGIME_SIMPLES: "Simples Nacional",
}
DEFAULT_REGIME = REGIME_NORMAL

# Simples Nacional companies are exempt from the employer social security
# contribution on payroll (it is already inside the DAS), but never from FGTS.
SOCIAL_SECURITY_BY_REGIME = {
    REGIME_NORMAL: EMPLOYER_SOCIAL_SECURITY_RATE,
    REGIME_SIMPLES: Decimal(0),
}


def total_rate(regime: str) -> Decimal:
    """Everything provisioned monthly, as a fraction of salary."""
    social = SOCIAL_SECURITY_BY_REGIME.get(regime, EMPLOYER_SOCIAL_SECURITY_RATE)
    return BASE_RATE * (Decimal(1) + FGTS_RATE + social)


def rate_breakdown(regime: str) -> Dict[str, float]:
    """The rates behind every number, for display alongside the values."""
    social = SOCIAL_SECURITY_BY_REGIME.get(regime, EMPLOYER_SOCIAL_SECURITY_RATE)
    return {
        "vacation": float(VACATION_RATE),
        "vacation_bonus": float(VACATION_BONUS_RATE),
        "thirteenth": float(THIRTEENTH_RATE),
        "base": float(BASE_RATE),
        "fgts": float(BASE_RATE * FGTS_RATE),
        "social_security": float(BASE_RATE * social),
        "total": float(total_rate(regime)),
        "fgts_rate": float(FGTS_RATE),
        "social_security_rate": float(social),
    }


def _round(value: Decimal) -> float:
    """Money is rounded to cents at the point it is reported, never during the
    arithmetic, so a sum of provisions matches the provision of a sum."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _components(base: Decimal, regime: str) -> Dict[str, Decimal]:
    social_rate = SOCIAL_SECURITY_BY_REGIME.get(regime, EMPLOYER_SOCIAL_SECURITY_RATE)

    vacation = base * VACATION_RATE
    vacation_bonus = base * VACATION_BONUS_RATE
    thirteenth = base * THIRTEENTH_RATE
    provisions = vacation + vacation_bonus + thirteenth

    return {
        "vacation": vacation,
        "vacation_bonus": vacation_bonus,
        "thirteenth": thirteenth,
        "provisions_base": provisions,
        "fgts_vacation": vacation * FGTS_RATE,
        "fgts_vacation_bonus": vacation_bonus * FGTS_RATE,
        "fgts_thirteenth": thirteenth * FGTS_RATE,
        "fgts": provisions * FGTS_RATE,
        "social_security": provisions * social_rate,
        "total": provisions * (Decimal(1) + FGTS_RATE + social_rate),
    }


def compute_provisions(salary: Optional[float], regime: str = DEFAULT_REGIME) -> Dict[str, Optional[float]]:
    """The monthly provisions for one employee, accessories included.

    Returns None for every field when the salary is unknown — a salary-less
    row must not be reported as costing zero.
    """
    keys = (
        "vacation", "vacation_bonus", "thirteenth", "provisions_base",
        "fgts_vacation", "fgts_vacation_bonus", "fgts_thirteenth",
        "fgts", "social_security", "total",
    )
    if salary is None or salary <= 0:
        return {key: None for key in keys}

    values = _components(Decimal(str(salary)), regime)
    return {key: _round(values[key]) for key in keys}


def sum_provisions(items: Iterable[Tuple[Optional[float], str]]) -> Dict[str, float]:
    """Aggregate provisions over many employees, each with its company's regime.

    Rows without a salary are skipped rather than counted as zero, and
    `salary_base` reports how much payroll the numbers actually cover. Payroll
    is bucketed per regime before the rates are applied, so a mixed portfolio
    of Simples and Regime Normal companies aggregates correctly.
    """
    payroll_by_regime: Dict[str, Decimal] = {}
    for salary, regime in items:
        if salary is None or salary <= 0:
            continue
        key = regime or DEFAULT_REGIME
        payroll_by_regime[key] = payroll_by_regime.get(key, Decimal(0)) + Decimal(str(salary))

    totals: Dict[str, Decimal] = {}
    salary_base = Decimal(0)
    for regime, payroll in payroll_by_regime.items():
        salary_base += payroll
        for key, value in _components(payroll, regime).items():
            totals[key] = totals.get(key, Decimal(0)) + value

    result = {key: _round(value) for key, value in totals.items()}
    result["salary_base"] = _round(salary_base)
    result["total_cost"] = _round(salary_base + totals.get("total", Decimal(0)))
    # An empty set still answers with zeros rather than missing keys.
    for key in ("vacation", "vacation_bonus", "thirteenth", "provisions_base",
                "fgts_vacation", "fgts_vacation_bonus", "fgts_thirteenth",
                "fgts", "social_security", "total"):
        result.setdefault(key, 0.0)
    return result
