"""문장 단위 스트리밍 안전 게이트.

Controlled Streaming Cascade(idea-plan.md §7.5) 준비: 완성된 텍스트를 사후 검사하는
대신, 문장이 완성되는 즉시 안전 필터를 통과한 문장만 downstream(TTS 등)으로 흘려보낸다.
한 문장이라도 차단되면 그 뒤는 흘려보내지 않고 대체 문구로 마무리한다 - 이미 승인돼
downstream 으로 나간 문장은 그 자체로 안전 검사를 통과했으므로 그대로 유지한다
(기존 사후 검사처럼 전체 턴을 통째로 대체하지 않는다).

스트림 자체를 조기 중단하지는 않는다(스코프 제한) - 차단 후에도 LLM 응답 생성은
끝까지 받되, 남은 문장은 안전 검사도 하지 않고 버린다. llm.py 의 프로바이더별
스트리밍 루프를 고쳐야 하는 조기 중단은 별도 과제다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from .agents.safety import check_safety
from .cost import Usage
from .prompts import SAFETY_FALLBACK_TEXT

#: 문장 종결부호(.!?…) 뒤에 공백 또는 문자열 끝이 와야 경계로 본다.
#: "hanbit-secure.example" 같은 더미 도메인의 마침표는 뒤에 공백 없이 문자가
#: 바로 붙으므로 경계로 잡히지 않는다.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])(?=\s|$)")


def split_sentences(buf: str) -> tuple[list[str], str]:
    """완성된 문장 리스트와 아직 안 끝난 나머지 버퍼를 분리한다."""
    parts = _SENTENCE_BOUNDARY.split(buf)
    *complete, rest = parts
    sentences = [s.strip() for s in complete if s.strip()]
    return sentences, rest


@dataclass
class StreamingSafetyGate:
    """generate_scammer_turn(scenario, state, on_delta=gate.feed) 로 꽂는다.

    스트림이 끝난 뒤 반드시 finish() 를 호출해 잔여 버퍼(종결부호 없이 끝난
    마지막 문장)까지 검사해야 한다.
    """

    #: 승인된 문장이 나올 때마다 호출할 실제 콜백(TTS 등). None 이면 그냥 버린다.
    downstream: Callable[[str], None] | None = None

    _buf: str = ""
    approved: list[str] = field(default_factory=list)
    blocked: bool = False
    violations: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    def feed(self, delta: str) -> None:
        if self.blocked:
            return
        self._buf += delta
        sentences, self._buf = split_sentences(self._buf)
        for s in sentences:
            self._check_and_emit(s)
            if self.blocked:
                return

    def finish(self) -> None:
        if self.blocked:
            return
        tail = self._buf.strip()
        self._buf = ""
        if tail:
            self._check_and_emit(tail)

    def _check_and_emit(self, sentence: str) -> None:
        result = check_safety(sentence)
        self.usage.add(result.usage)
        if result.blocked:
            self.blocked = True
            self.violations = result.violations
            return
        self.approved.append(sentence)
        if self.downstream:
            self.downstream(sentence)

    @property
    def display_text(self) -> str:
        """transcript 에 기록할 최종 텍스트."""
        if self.blocked:
            return " ".join([*self.approved, SAFETY_FALLBACK_TEXT]).strip()
        return " ".join(self.approved).strip()
