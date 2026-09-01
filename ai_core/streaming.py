"""문장 단위 스트리밍 안전 게이트.

Controlled Streaming Cascade(idea-plan.md §7.5) 준비: 완성된 텍스트를 사후 검사하는
대신, 문장이 완성되는 즉시 안전 필터를 통과한 문장만 downstream(TTS 등)으로 흘려보낸다.
한 문장이라도 차단되면 그 뒤는 흘려보내지 않고 대체 문구로 마무리한다 - 이미 승인돼
downstream 으로 나간 문장은 그 자체로 안전 검사를 통과했으므로 그대로 유지한다
(기존 사후 검사처럼 전체 턴을 통째로 대체하지 않는다).

안전 검사(check_safety)는 백그라운드 스레드 하나가 큐에서 순서대로 꺼내 처리한다.
feed() 는 문장을 큐에 넣기만 하고 바로 반환한다 - 2026-08-25 실측: feed() 안에서
check_safety() 를 동기 호출하면 llm.py 의 스트림 소비 루프(on_delta 호출부)가 그
네트워크 왕복만큼 그대로 멈춰서, 문장이 2개면 안전검사 지연이 고스란히 두 번
더해졌다(한 턴에 최대 20초+). 백그라운드 스레드로 분리하면 다음 문장을 계속
받아오는 동안 이전 문장의 안전검사가 병행되어 이 지연이 상당 부분 가려진다.
큐가 FIFO 단일 워커라 승인 순서·차단 시 즉시 중단 의미는 그대로 유지된다.

스트림 자체를 조기 중단하지는 않는다(스코프 제한) - 차단 후에도 LLM 응답 생성은
끝까지 받되, 남은 문장은 안전 검사도 하지 않고 버린다. llm.py 의 프로바이더별
스트리밍 루프를 고쳐야 하는 조기 중단은 별도 과제다.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
from dataclasses import dataclass, field
from typing import Callable

from .agents.safety import check_safety
from .cost import Usage
from .prompts import SAFETY_FALLBACK_TEXT

logger = logging.getLogger(__name__)

#: 문장 종결부호(.!?…) 뒤에 공백 또는 문자열 끝이 와야 경계로 본다.
#: "salpim-secure.example" 같은 더미 도메인의 마침표는 뒤에 공백 없이 문자가
#: 바로 붙으므로 경계로 잡히지 않는다.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])(?=\s|$)")

#: TTS 가 글자 그대로 읽어버리는 마스킹 문자. "○○지방검찰청" 은 훈련생 귀에
#: "빈 원 빈 원 지방검찰청" 으로 들린다. 카드 데이터와 SCAMMER_CORE 에서 ○ 를 모두
#: 걷어냈지만, 모델이 스스로 만들어내는 경우가 남는다.
_MASK_CHARS = re.compile(r"[○◯◦●□■]+")


def strip_mask_chars(text: str) -> str:
    """마스킹 문자를 걷어낸 발화를 돌려준다.

    자막과 음성이 반드시 같은 문자열이어야 하므로, 발화가 확정되는 한 지점에서만
    적용한다. TTS 직전에 적용하면 화면에는 ○ 가 남고 소리에서만 사라져 어긋난다.
    """
    if not _MASK_CHARS.search(text):
        return text
    cleaned = _MASK_CHARS.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    logger.warning("발화에서 마스킹 문자를 제거했습니다 - 프롬프트·카드 회귀 가능성")
    return cleaned


#: 워커 종료 신호
_DONE = object()


def split_sentences(buf: str) -> tuple[list[str], str]:
    """완성된 문장 리스트와 아직 안 끝난 나머지 버퍼를 분리한다."""
    parts = _SENTENCE_BOUNDARY.split(buf)
    *complete, rest = parts
    sentences = [s.strip() for s in complete if s.strip()]
    return sentences, rest


@dataclass
class StreamingSafetyGate:
    """generate_scammer_turn(scenario, state, on_delta=gate.feed) 로 꽂는다.

    스트림이 끝난 뒤 반드시 finish() 를 호출해야 한다 - 잔여 버퍼를 마저 검사하고,
    백그라운드 워커가 큐를 다 처리할 때까지 기다린 뒤 반환한다(join). finish() 가
    반환한 시점부터 display_text/blocked/violations/usage 를 읽어도 안전하다.
    """

    #: 승인된 문장이 나올 때마다 호출할 실제 콜백(TTS 등). None 이면 그냥 버린다.
    downstream: Callable[[str], None] | None = None

    _buf: str = ""
    approved: list[str] = field(default_factory=list)
    blocked: bool = False
    violations: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    _queue: queue.Queue = field(default_factory=queue.Queue, init=False, repr=False)
    _worker: threading.Thread = field(init=False, repr=False)
    #: close() 로 중단된 상태. 남은 문장을 검사 없이 버리기 위한 표시다.
    _aborted: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    def feed(self, delta: str) -> None:
        """llm.py 의 스트림 소비 루프에서 매 청크마다 호출된다 - 절대 블로킹하면 안 된다."""
        if self.blocked:
            return
        self._buf += delta
        sentences, self._buf = split_sentences(self._buf)
        for s in sentences:
            self._queue.put(s)

    def finish(self) -> None:
        """스트림 종료 후 호출. 잔여 버퍼를 큐에 넣고 워커가 다 처리할 때까지 기다린다."""
        tail = self._buf.strip()
        self._buf = ""
        if tail:
            self._queue.put(tail)
        self._queue.put(_DONE)
        self._worker.join()

    def close(self) -> None:
        """턴이 중간에 실패했을 때 워커만 정리한다 (남은 문장은 검사하지 않는다).

        finish() 와 달리 결과를 만들지 않는다 - 예외로 턴이 깨진 상황이라 남은 문장에
        LLM 비용을 더 쓸 이유가 없다. 이걸 부르지 않으면 워커가 큐에서 영원히 대기해
        실패한 턴마다 스레드가 하나씩 새어 나간다(daemon 이라 종료는 막지 않지만,
        장시간 떠 있는 서버에서는 계속 쌓인다).
        """
        self._aborted = True
        self._queue.put(_DONE)
        self._worker.join()

    def _run_worker(self) -> None:
        """백그라운드에서 문장을 순서대로(FIFO) 안전 검사한다.

        단일 워커라 승인 순서와 "차단되면 그 뒤는 버림" 의미가 그대로 유지된다.
        self.blocked 를 feed() 가 읽는 것과 여기서 쓰는 것 사이에 락을 걸지 않았다 -
        bool 하나의 읽기/쓰기라 GIL 상 원자적이고, 최악의 경우도 feed() 가 차단 직후
        문장 한두 개를 더 큐에 넣는 정도인데 그 문장들은 아래에서 그대로 버려진다.
        """
        while True:
            sentence = self._queue.get()
            if sentence is _DONE:
                return
            if self.blocked or self._aborted:
                continue
            try:
                self._check_and_emit(sentence)
            except Exception:
                # 안전 필터 호출 자체가 실패(네트워크 오류 등)하면 판정 불가다.
                # agents/safety.py 의 파싱 실패 처리와 같은 원칙으로 차단 쪽에 선다 -
                # 여기서 예외를 흘리면 워커가 죽어 남은 문장이 조용히 사라진다.
                self.blocked = True
                self.violations = ["safety_check_failed"]

    def _check_and_emit(self, sentence: str) -> None:
        # 자막(downstream)·음성(TTS)·transcript 가 모두 이 한 문자열을 쓴다.
        # 여기서 걷어내야 셋이 어긋나지 않는다.
        sentence = strip_mask_chars(sentence)
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
