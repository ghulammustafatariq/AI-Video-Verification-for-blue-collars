"""
Economic Impact Model

Translates AI skill verification scores into projected marketplace earnings.
Based on the Fixly marketplace model:
  - Unverified workers get base rate + limited jobs
  - Verified workers get premium rates + more job offers
  - Score directly impacts earning potential per job
"""

from dataclasses import dataclass
from typing import Dict, Any


# ── Pakistan market baseline (PKR) ──
BASE_RATE_PER_JOB = 500      # Unverified plumber/electrician per job
MAX_JOBS_UNVERIFIED = 2      # Jobs per day without verification
MAX_JOBS_VERIFIED = 6        # Max jobs per day when verified
WORKING_DAYS_PER_MONTH = 22  # Average working days


# Premium multiplier by skill level
SKILL_PREMIUM = {
    "Master": 2.0,          # 100% more than base
    "Experienced": 1.5,     # 50% more
    "Competent": 1.2,       # 20% more
    "Developing": 1.0,      # base rate
    "Not Yet Ready": 0.7,  # 30% below base (needs improvement)
}

# Job multiplier by skill level (more jobs offered)
JOB_ALLOCATION = {
    "Master": 1.0,          # max jobs
    "Experienced": 0.85,
    "Competent": 0.65,
    "Developing": 0.4,
    "Not Yet Ready": 0.25,
}


@dataclass
class EconomicImpact:
    score: int
    skill_level: str
    rate_per_job: int              # PKR per job
    jobs_per_day: float            # Estimated jobs per day
    jobs_per_month: float
    monthly_income: int            # PKR
    premium_vs_unverified: int     # Extra PKR per month vs unverified peer
    premium_percentage: int        # % more than unverified
    annual_income: int
    annual_premium: int


def compute_economic_impact(score: int, skill_level: str) -> EconomicImpact:
    """
    Compute projected earnings based on verified skill score.

    Unverified baseline: Rs. 500/job, max 2 jobs/day = Rs. 22,000/month
    """
    premium = SKILL_PREMIUM.get(skill_level, 1.0)
    job_alloc = JOB_ALLOCATION.get(skill_level, 0.5)

    rate_per_job = int(BASE_RATE_PER_JOB * premium)
    jobs_per_day = MAX_JOBS_VERIFIED * job_alloc
    jobs_per_month = jobs_per_day * WORKING_DAYS_PER_MONTH
    monthly_income = int(rate_per_job * jobs_per_month)

    # Unverified baseline
    unverified_monthly = BASE_RATE_PER_JOB * MAX_JOBS_UNVERIFIED * WORKING_DAYS_PER_MONTH
    unverified_annual = unverified_monthly * 12

    premium_vs_unverified = monthly_income - unverified_monthly
    premium_percentage = int((premium_vs_unverified / unverified_monthly) * 100) if unverified_monthly > 0 else 0

    annual_income = monthly_income * 12
    annual_premium = premium_vs_unverified * 12

    return EconomicImpact(
        score=score,
        skill_level=skill_level,
        rate_per_job=rate_per_job,
        jobs_per_day=round(jobs_per_day, 1),
        jobs_per_month=round(jobs_per_month, 1),
        monthly_income=monthly_income,
        premium_vs_unverified=premium_vs_unverified,
        premium_percentage=premium_percentage,
        annual_income=annual_income,
        annual_premium=annual_premium,
    )


def compute_impact_if_improved(
    current_score: int,
    current_level: str,
    potential_score: int,
    potential_level: str,
) -> Dict[str, Any]:
    """
    Compare current earnings vs. potential earnings if skill improved.
    """
    current = compute_economic_impact(current_score, current_level)
    potential = compute_economic_impact(potential_score, potential_level)

    gain_per_month = potential.monthly_income - current.monthly_income
    gain_per_year = potential.annual_income - current.annual_income

    return {
        "current": current,
        "potential": potential,
        "monthly_gain": gain_per_month,
        "annual_gain": gain_per_year,
        "message": (
            f"Improving from {current_level} to {potential_level} would increase "
            f"monthly income by Rs. {gain_per_month:,} (+{potential.premium_percentage}%). "
            f"That is Rs. {gain_per_year:,} more per year."
        ),
    }
