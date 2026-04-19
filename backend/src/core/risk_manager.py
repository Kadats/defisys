"""
Compatibility wrapper for risk management.

Canonical implementation now lives in the domain layer:
`backend.src.domain.risk.manager`.
"""

from backend.src.domain.risk.manager import (  # noqa: F401
    EMERGENCY_GAS_MULTIPLIER,
    HF_CRITICAL_THRESHOLD,
    HF_REFINANCE_THRESHOLD,
    HF_WARNING_THRESHOLD,
    LIQUIDATION_PENALTY,
    LIQUIDATION_THRESHOLD,
    HealthStatus,
    RiskManager,
)

__all__ = [
    "RiskManager",
    "HealthStatus",
    "HF_WARNING_THRESHOLD",
    "HF_CRITICAL_THRESHOLD",
    "HF_REFINANCE_THRESHOLD",
    "LIQUIDATION_THRESHOLD",
    "LIQUIDATION_PENALTY",
    "EMERGENCY_GAS_MULTIPLIER",
]

