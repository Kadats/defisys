"""In-memory paper trading runtime with auditable events and alerts."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal
import uuid

RuntimeState = Literal["healthy", "degraded", "restricted", "halted"]
AlertSeverity = Literal["info", "warning", "critical"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeAlert:
    alert_id: str
    severity: AlertSeverity
    code: str
    message: str
    occurred_at: str
    session_id: str | None
    blocking: bool
    active: bool = True


@dataclass
class PaperRuntimeSession:
    session_id: str
    strategy_name: str
    environment: str
    started_at: str
    ended_at: str | None = None
    status: RuntimeState = "healthy"
    open_orders_count: int = 0
    open_positions_count: int = 0
    portfolio_equity_usd: float = 0.0
    cash_usd: float = 0.0
    net_btc_exposure: float = 0.0
    risk_state: str = "SAFE"
    runtime_health: str = "healthy"
    llm_fallback_count: int = 0
    kill_switch_active: bool = False


@dataclass
class RuntimeEvent:
    event_id: str
    session_id: str
    event_type: str
    occurred_at: str
    correlation_id: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)


class PaperTradingRuntime:
    def __init__(self):
        self._lock = Lock()
        self._events: deque[RuntimeEvent] = deque(maxlen=1000)
        self._alerts: deque[RuntimeAlert] = deque(maxlen=500)
        self._session: PaperRuntimeSession | None = None

    def start_session(self, strategy_name: str, environment: str = "paper") -> PaperRuntimeSession:
        with self._lock:
            session_id = str(uuid.uuid4())
            self._session = PaperRuntimeSession(
                session_id=session_id,
                strategy_name=strategy_name,
                environment=environment,
                started_at=_utc_now_iso(),
                status="healthy",
                runtime_health="healthy",
            )
            self._emit(
                event_type="runtime_state_changed",
                correlation_id=str(uuid.uuid4()),
                source="paper_runtime",
                payload={"runtime_status": "healthy", "reason": "session_started"},
            )
            return self._session

    def stop_session(self) -> PaperRuntimeSession | None:
        with self._lock:
            if self._session is None:
                return None

            self._session.status = "halted"
            self._session.runtime_health = "halted"
            self._session.ended_at = _utc_now_iso()
            self._emit(
                event_type="runtime_state_changed",
                correlation_id=str(uuid.uuid4()),
                source="paper_runtime",
                payload={"runtime_status": "halted", "reason": "session_stopped"},
            )
            return self._session

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            if self._session is None:
                return {
                    "running": False,
                    "runtime_status": "halted",
                    "session": None,
                    "active_alerts": [a.__dict__ for a in self._active_alerts()],
                    "last_event": self._events[-1].__dict__ if self._events else None,
                }
            return {
                "running": self._session.ended_at is None,
                "runtime_status": self._session.status,
                "session": self._session.__dict__,
                "active_alerts": [a.__dict__ for a in self._active_alerts()],
                "last_event": self._events[-1].__dict__ if self._events else None,
            }

    def ingest_market_snapshot(
        self,
        symbol: str,
        price: float,
        source_status: str = "real",
        ml_confidence: float = 0.5,
        health_factor: float = 2.0,
        kill_switch_active: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            if self._session is None or self._session.ended_at is not None:
                raise RuntimeError("Paper runtime session is not active")

            correlation_id = str(uuid.uuid4())
            self._session.kill_switch_active = bool(kill_switch_active)
            self._emit(
                event_type="market_snapshot_received",
                correlation_id=correlation_id,
                source="market_feed",
                payload={
                    "symbol": symbol,
                    "price": float(price),
                    "source_status": source_status,
                },
            )

            runtime_state: RuntimeState = "healthy"
            decision_action = "HOLD"
            blocking_reason = None

            if kill_switch_active:
                runtime_state = "halted"
                blocking_reason = "kill_switch_active"
                self._raise_alert(
                    severity="critical",
                    code="KILL_SWITCH_ACTIVATED",
                    message="Kill switch active. New orders are blocked.",
                    blocking=True,
                )
                self._emit(
                    event_type="kill_switch_activated",
                    correlation_id=correlation_id,
                    source="risk_guardrail",
                    payload={"blocking": True},
                )
            elif health_factor < 1.2:
                runtime_state = "restricted"
                blocking_reason = "health_factor_critical"
                self._raise_alert(
                    severity="critical",
                    code="HEALTH_FACTOR_CRITICAL",
                    message=f"Health factor {health_factor:.2f} is below critical threshold.",
                    blocking=True,
                )
            elif source_status in {"degraded", "offline"}:
                runtime_state = "degraded"
                self._raise_alert(
                    severity="warning",
                    code="MARKET_FEED_DEGRADED",
                    message=f"Market feed status is {source_status}.",
                    blocking=False,
                )

            if runtime_state in {"healthy", "degraded"} and ml_confidence >= 0.70:
                decision_action = "BUY"

            if runtime_state in {"restricted", "halted"}:
                decision_action = "BLOCKED"

            self._session.status = runtime_state
            self._session.runtime_health = runtime_state
            self._session.risk_state = "KILL_SWITCH" if kill_switch_active else "SAFE"

            self._emit(
                event_type="strategy_decision_generated"
                if decision_action != "BLOCKED"
                else "strategy_decision_blocked",
                correlation_id=correlation_id,
                source="strategy_engine",
                payload={
                    "strategy_name": self._session.strategy_name,
                    "decision_action": decision_action,
                    "decision_source": "rules",
                    "ml_confidence": float(ml_confidence),
                    "health_factor": float(health_factor),
                    "source_status": source_status,
                    "blocking_reason": blocking_reason,
                },
            )

            if decision_action == "BUY":
                order_id = str(uuid.uuid4())
                fill_id = str(uuid.uuid4())
                fill_price = float(price) * 1.0005

                self._emit(
                    event_type="paper_order_proposed",
                    correlation_id=correlation_id,
                    source="paper_engine",
                    payload={
                        "order_id": order_id,
                        "action": "BUY",
                        "quantity": 1.0,
                        "reference_price": float(price),
                        "reason": "ml_confidence_signal",
                    },
                )
                self._emit(
                    event_type="paper_order_accepted",
                    correlation_id=correlation_id,
                    source="paper_engine",
                    payload={"order_id": order_id},
                )
                self._emit(
                    event_type="paper_fill_simulated",
                    correlation_id=correlation_id,
                    source="paper_engine",
                    payload={
                        "fill_id": fill_id,
                        "order_id": order_id,
                        "fill_price": fill_price,
                        "fill_quantity": 1.0,
                        "slippage_bps": 5.0,
                    },
                )

            self._emit(
                event_type="runtime_snapshot_emitted",
                correlation_id=correlation_id,
                source="paper_runtime",
                payload={
                    "portfolio_equity_usd": self._session.portfolio_equity_usd,
                    "cash_usd": self._session.cash_usd,
                    "net_btc_exposure": self._session.net_btc_exposure,
                    "risk_state": self._session.risk_state,
                    "runtime_health": self._session.runtime_health,
                    "runtime_status": self._session.status,
                    "kill_switch_active": self._session.kill_switch_active,
                    "source_status": source_status,
                },
            )
            return {
                "runtime_status": runtime_state,
                "decision_action": decision_action,
                "blocking_reason": blocking_reason,
                "correlation_id": correlation_id,
            }

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            tail = list(self._events)[-max(1, limit) :]
            return [e.__dict__ for e in tail]

    def list_alerts(self, active_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            alerts = self._active_alerts() if active_only else list(self._alerts)
            return [a.__dict__ for a in alerts[-max(1, limit) :]]

    def _active_alerts(self) -> list[RuntimeAlert]:
        return [a for a in self._alerts if a.active]

    def _raise_alert(
        self,
        severity: AlertSeverity,
        code: str,
        message: str,
        blocking: bool,
    ) -> None:
        alert = RuntimeAlert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            code=code,
            message=message,
            occurred_at=_utc_now_iso(),
            session_id=self._session.session_id if self._session else None,
            blocking=blocking,
        )
        self._alerts.append(alert)
        self._emit(
            event_type="runtime_alert_emitted",
            correlation_id=str(uuid.uuid4()),
            source="paper_runtime",
            payload={
                "severity": severity,
                "code": code,
                "message": message,
                "blocking": blocking,
                "alert_id": alert.alert_id,
            },
        )

    def _emit(
        self,
        event_type: str,
        correlation_id: str,
        source: str,
        payload: dict[str, Any],
    ) -> None:
        if self._session is None:
            return
        event = RuntimeEvent(
            event_id=str(uuid.uuid4()),
            session_id=self._session.session_id,
            event_type=event_type,
            occurred_at=_utc_now_iso(),
            correlation_id=correlation_id,
            source=source,
            payload=payload,
        )
        self._events.append(event)


paper_runtime = PaperTradingRuntime()
