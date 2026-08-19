"""토큰·비용 집계. 단가는 config.py 에서 관리한다."""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    MODEL_PRICE,
    PROVIDER,
    USD_TO_KRW,
)


@dataclass
class Usage:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0

    def add(self, other: Usage) -> None:
        self.input += other.input
        self.output += other.output
        self.cache_read += other.cache_read
        self.cache_write += other.cache_write

    @property
    def total(self) -> int:
        return self.input + self.output + self.cache_read + self.cache_write


def _price_for(model: str) -> dict[str, float]:
    for k, v in MODEL_PRICE.items():
        if model.startswith(k):
            return v
    return {"input": 5.0, "output": 25.0}  # 모르는 모델은 Opus 단가로 보수적 추정


def cost_usd_for(u: Usage, model: str) -> float:
    """모델별 단가를 적용한 비용. Ollama 는 항상 0"""
    if PROVIDER == "ollama":
        return 0.0
    p = _price_for(model)
    m = 1_000_000
    return (
        u.input * p["input"] / m
        + u.output * p["output"] / m
        + u.cache_write * p["input"] * CACHE_WRITE_MULTIPLIER / m
        + u.cache_read * p["input"] * CACHE_READ_MULTIPLIER / m
    )


def krw(usd: float) -> str:
    return f"약 {round(usd * USD_TO_KRW):,}원"
