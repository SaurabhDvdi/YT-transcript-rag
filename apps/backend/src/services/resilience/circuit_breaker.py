"""Circuit breaker and provider health monitoring."""

import time
from typing import Literal

CircuitState = Literal["CLOSED", "OPEN", "HALF_OPEN"]


class CircuitBreaker:
    """Stateful circuit breaker preventing cascading downstream failures."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: CircuitState = "CLOSED"
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.success_count: int = 0

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if now - self.last_failure_time >= self.cooldown_seconds:
                self.state = "HALF_OPEN"
                self.success_count = 0
                return True
            return False

        return self.state == "HALF_OPEN"

    def record_success(self) -> None:
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state in ("CLOSED", "HALF_OPEN") and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def get_status(self) -> dict[str, str | int | float]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "cooldown_seconds": self.cooldown_seconds,
        }

    def reset(self) -> None:
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0


class ProviderHealthTracker:
    """Central registry tracking circuit breakers and health across all AI providers."""

    _instance: "ProviderHealthTracker | None" = None

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get_instance(cls) -> "ProviderHealthTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "ProviderHealthTracker | None") -> None:
        cls._instance = instance

    def _get_breaker(self, provider_name: str) -> CircuitBreaker:
        if provider_name not in self._breakers:
            self._breakers[provider_name] = CircuitBreaker(
                self.failure_threshold, self.cooldown_seconds
            )
        return self._breakers[provider_name]

    def is_available(self, provider_name: str) -> bool:
        breaker = self._get_breaker(provider_name)
        return breaker.allow_request()

    def record_outcome(self, provider_name: str, success: bool) -> None:
        breaker = self._get_breaker(provider_name)
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def get_provider_status(self, provider_name: str) -> dict[str, str | int | float]:
        breaker = self._get_breaker(provider_name)
        return breaker.get_status()

    def get_all_health(self) -> dict[str, dict[str, str | int | float]]:
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}

    def reset(self) -> None:
        for breaker in self._breakers.values():
            breaker.reset()
