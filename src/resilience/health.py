"""
Health management for resilience framework.

Implements FR-004 (Health File Convention) from the
015-error-recovery-resilience specification.

Subsystems maintain health files in `.watcher-state/` for
external watchdog integration (PM2, systemd, etc.).
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class HealthState(str, Enum):
    """
    Health state for subsystem status.

    Values:
        HEALTHY: All operations succeeding normally
        DEGRADED: Some failures occurring but still functional
        UNHEALTHY: Critical failures, needs intervention
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitState(str, Enum):
    """
    Circuit breaker state for external API protection.

    Values:
        CLOSED: Normal operation, requests allowed
        OPEN: Circuit tripped, requests blocked
        HALF_OPEN: Testing if service recovered
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthStatus:
    """
    Health status for a subsystem.

    Attributes:
        subsystem: Name of the subsystem
        status: Current health state
        last_heartbeat: ISO timestamp of last heartbeat
        last_success: ISO timestamp of last successful operation
        consecutive_failures: Count of consecutive failures
        degradation_reason: Why the subsystem is degraded (if applicable)
        circuit_state: Current circuit breaker state
        version: Version of the subsystem
    """
    subsystem: str
    status: HealthState = HealthState.HEALTHY
    last_heartbeat: Optional[str] = None
    last_success: Optional[str] = None
    consecutive_failures: int = 0
    degradation_reason: Optional[str] = None
    circuit_state: CircuitState = CircuitState.CLOSED
    version: str = "0.1.0"

    def to_json(self) -> str:
        """
        Serialize health status to JSON string.

        Returns:
            JSON string representation
        """
        data = {
            "subsystem": self.subsystem,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "last_success": self.last_success,
            "consecutive_failures": self.consecutive_failures,
            "degradation_reason": self.degradation_reason,
            "circuit_state": self.circuit_state.value,
            "version": self.version,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "HealthStatus":
        """
        Deserialize health status from JSON string.

        Args:
            json_str: JSON string to parse

        Returns:
            HealthStatus instance
        """
        data = json.loads(json_str)
        return cls(
            subsystem=data["subsystem"],
            status=HealthState(data["status"]),
            last_heartbeat=data.get("last_heartbeat"),
            last_success=data.get("last_success"),
            consecutive_failures=data.get("consecutive_failures", 0),
            degradation_reason=data.get("degradation_reason"),
            circuit_state=CircuitState(data.get("circuit_state", "closed")),
            version=data.get("version", "0.1.0"),
        )

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if the health status is stale (no recent heartbeat).

        Args:
            max_age_seconds: Maximum age in seconds (default: 5 minutes)

        Returns:
            True if heartbeat is older than max_age_seconds
        """
        if not self.last_heartbeat:
            return True

        try:
            heartbeat_time = datetime.fromisoformat(
                self.last_heartbeat.rstrip("Z")
            )
            age = (datetime.utcnow() - heartbeat_time).total_seconds()
            return age > max_age_seconds
        except ValueError:
            return True


class HealthManager:
    """
    Manages health status for a subsystem.

    Handles health file persistence, state transitions,
    and provides methods for recording success/failure.

    Example:
        health = HealthManager("gmail_watcher", state_dir=Path(".watcher-state"))

        try:
            result = poll_gmail()
            health.record_success()
        except Exception as e:
            health.record_failure(str(e))
        finally:
            health.heartbeat()

    Attributes:
        subsystem: Name of the subsystem
        state_dir: Directory for health files
        degraded_threshold: Consecutive failures before DEGRADED
        unhealthy_threshold: Consecutive failures before UNHEALTHY
    """

    def __init__(
        self,
        subsystem: str,
        state_dir: Path,
        degraded_threshold: int = 3,
        unhealthy_threshold: int = 5,
        version: str = "0.1.0",
    ):
        """
        Initialize health manager.

        Args:
            subsystem: Name of the subsystem
            state_dir: Directory for health files (e.g., .watcher-state)
            degraded_threshold: Failures before DEGRADED
            unhealthy_threshold: Failures before UNHEALTHY
            version: Subsystem version string
        """
        self.subsystem = subsystem
        self.state_dir = state_dir
        self.degraded_threshold = degraded_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.version = version

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load or create status
        self._status = self._load_status()

    @property
    def health_file(self) -> Path:
        """Path to the health file for this subsystem."""
        return self.state_dir / f"{self.subsystem}_health.json"

    def _load_status(self) -> HealthStatus:
        """Load status from file or create new."""
        if self.health_file.exists():
            try:
                content = self.health_file.read_text(encoding="utf-8")
                return HealthStatus.from_json(content)
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        return HealthStatus(
            subsystem=self.subsystem,
            version=self.version,
        )

    def _save_status(self) -> None:
        """Persist status to file."""
        self.health_file.write_text(
            self._status.to_json(),
            encoding="utf-8",
        )

    def _update_state(self) -> None:
        """Update health state based on consecutive failures."""
        if self._status.consecutive_failures >= self.unhealthy_threshold:
            self._status.status = HealthState.UNHEALTHY
        elif self._status.consecutive_failures >= self.degraded_threshold:
            self._status.status = HealthState.DEGRADED
        else:
            self._status.status = HealthState.HEALTHY
            self._status.degradation_reason = None

    def record_success(self) -> None:
        """
        Record a successful operation.

        Resets consecutive failures and updates last_success timestamp.
        """
        now = datetime.utcnow().isoformat() + "Z"
        self._status.consecutive_failures = 0
        self._status.last_success = now
        self._status.degradation_reason = None
        self._update_state()
        self._save_status()

    def record_failure(self, reason: str) -> None:
        """
        Record a failed operation.

        Increments consecutive failures and may transition state.

        Args:
            reason: Human-readable failure reason
        """
        self._status.consecutive_failures += 1
        self._status.degradation_reason = reason
        self._update_state()
        self._save_status()

    def heartbeat(self) -> None:
        """
        Record a heartbeat (subsystem is alive).

        Should be called at the end of each poll cycle,
        regardless of success or failure.
        """
        now = datetime.utcnow().isoformat() + "Z"
        self._status.last_heartbeat = now
        self._save_status()

    def get_status(self) -> HealthStatus:
        """
        Get the current health status.

        Returns:
            Current HealthStatus
        """
        return self._status

    def set_circuit_state(self, state: CircuitState) -> None:
        """
        Update the circuit breaker state.

        Args:
            state: New circuit state
        """
        self._status.circuit_state = state
        self._save_status()

    def reset(self) -> None:
        """
        Reset health status to healthy defaults.

        Useful for manual recovery or testing.
        """
        self._status = HealthStatus(
            subsystem=self.subsystem,
            status=HealthState.HEALTHY,
            consecutive_failures=0,
            circuit_state=CircuitState.CLOSED,
            version=self.version,
        )
        self._save_status()


def read_all_health_files(state_dir: Path) -> list[HealthStatus]:
    """
    Read all health files from a state directory.

    Args:
        state_dir: Directory containing health files

    Returns:
        List of HealthStatus for all subsystems found
    """
    if not state_dir.exists():
        return []

    statuses = []

    for health_file in state_dir.glob("*_health.json"):
        try:
            content = health_file.read_text(encoding="utf-8")
            status = HealthStatus.from_json(content)
            statuses.append(status)
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            continue

    return statuses


def compute_aggregate_status(statuses: list[HealthStatus]) -> HealthState:
    """
    Compute aggregate status from multiple subsystem statuses.

    Returns the worst status among all subsystems.

    Args:
        statuses: List of HealthStatus to aggregate

    Returns:
        HealthState: HEALTHY if all healthy, DEGRADED if any degraded,
                    UNHEALTHY if any unhealthy
    """
    if not statuses:
        return HealthState.HEALTHY

    # Priority: UNHEALTHY > DEGRADED > HEALTHY
    has_unhealthy = any(s.status == HealthState.UNHEALTHY for s in statuses)
    has_degraded = any(s.status == HealthState.DEGRADED for s in statuses)

    if has_unhealthy:
        return HealthState.UNHEALTHY
    if has_degraded:
        return HealthState.DEGRADED
    return HealthState.HEALTHY
