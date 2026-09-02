"""API 키 없이 돌아가는 스모크 테스트.

시나리오 스키마와 상태머신의 전환 승인 로직만 검증한다 (판정기 LLM 호출 없음).
"전환 조건 회귀 테스트" — 판정기를 engine.step() 에 연결하면서 try_advance_stage() 의
게이트 로직이 바뀌었으므로(관련 커밋: proposed 기본값 True→AND-게이트), 그 경계 조건을
전부 이 파일에서 결정론적으로 검증한다.

사용법: python -m ai_core.smoke   (mirisalpim-web/ 에서 실행)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ⚠️ Windows 콘솔 기본 인코딩(cp949)에서 한글/기호 출력이 UnicodeEncodeError 로 죽는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

import ai_core.agents.scammer as scammer_module  # noqa: E402
from ai_core.config import model_for, scammer_fallback_for  # noqa: E402

# ⚠️ llm 은 import 만으로 API 키를 요구하지 않는다 (설정 검사는 raise_for_config()
# 안에 있고 chat() 이 부른다). 아래 폴백 검증은 chat() 을 가짜로 갈아끼우므로
# 이 파일은 여전히 키 없이 돌아간다.
from ai_core.llm import ChatResult, is_transient_model_error  # noqa: E402
from ai_core.state import create_session, current_stage, try_advance_stage  # noqa: E402
from ai_core.streaming import split_sentences, strip_mask_chars  # noqa: E402
from ai_core.types import Scenario  # noqa: E402

failed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global failed
    mark = "✓" if cond else "✗"
    tail = f" {detail}" if detail else ""
    print(f"  {mark} {label}{tail}")
    if not cond:
        failed += 1


path = Path(__file__).resolve().parent.parent / "data" / "scenarios" / "sc-02.json"
scenario = Scenario.from_dict(json.loads(path.read_text(encoding="utf-8")))

print("\n시나리오 스키마")
check("로드 성공", bool(scenario.scenario_id), scenario.scenario_id)
check("단계 4개", len(scenario.stages) == 4, f"{len(scenario.stages)}개")
check("첫 단계에 opening 존재", bool(scenario.stages[0].opening))
check("tellPoint 3개 이상", len(scenario.tell_points) >= 3, f"{len(scenario.tell_points)}개")
stage_ids = {s.id for s in scenario.stages}
check(
    "tellPoint 의 stage 가 모두 실재",
    all(t.stage in stage_ids for t in scenario.tell_points),
)
check("모든 tellPoint 에 why 존재", all(len(t.why) > 10 for t in scenario.tell_points))
check("forbidden 정의됨", len(scenario.forbidden) > 0, f"{len(scenario.forbidden)}개")

print("\n상태머신 — 전환은 코드가 승인한다 (판정기 미연결 기본 동작)")
state = create_session(scenario)
check("초기 단계", current_stage(scenario, state).id == "trust_building")

early = try_advance_stage(scenario, state)
check("최소 턴 미달 시 전환 거부 (판정기 기본값)", not early.advanced, early.reason)

proposed_early = try_advance_stage(scenario, state, proposed=True)
check("판정기가 제안해도 조건 미달이면 거부", not proposed_early.advanced, proposed_early.reason)

state.turns_in_stage = scenario.stages[0].min_turns
ok = try_advance_stage(scenario, state)
check("조건 충족 + 판정기 미연결(기본 True) 시 전환", ok.advanced, ok.reason)
check("전환 후 단계 카운터 초기화", state.turns_in_stage == 0)

print("\n판정기 연결 시 AND-게이트 (신규)")
state2 = create_session(scenario)
state2.turns_in_stage = scenario.stages[0].min_turns
rejected_by_judge = try_advance_stage(scenario, state2, proposed=False)
check(
    "최소 턴 충족해도 판정기가 반대(False)하면 전환 안 함",
    not rejected_by_judge.advanced,
    rejected_by_judge.reason,
)
check("전환 안 됐으니 단계는 그대로", current_stage(scenario, state2).id == "trust_building")

approved_by_judge = try_advance_stage(scenario, state2, proposed=True)
check("같은 상태에서 판정기가 찬성(True)하면 전환됨", approved_by_judge.advanced, approved_by_judge.reason)

# 마지막 단계까지 밀어서 경계 확인
state3 = create_session(scenario)
while state3.stage_index < len(scenario.stages) - 1:
    state3.turns_in_stage = scenario.stages[state3.stage_index].min_turns
    try_advance_stage(scenario, state3)
state3.turns_in_stage = 99
last = try_advance_stage(scenario, state3, proposed=True)
check("마지막 단계에서는 판정기가 찬성해도 전환 안 함", not last.advanced, last.reason)

print("\n문장 분리 — split_sentences() (스트리밍 x 안전 필터)")

sentences, rest = split_sentences("괜찮으세요? 확인이 필요합니다.")
check("일반 문장 2개로 분리", sentences == ["괜찮으세요?", "확인이 필요합니다."], str(sentences))
check("잔여 버퍼 없음", rest == "", repr(rest))

sentences, rest = split_sentences("salpim-secure.example 로 접속하세요.")
check(
    "더미 도메인 마침표는 경계로 안 잡힘",
    sentences == ["salpim-secure.example 로 접속하세요."],
    str(sentences),
)

sentences, rest = split_sentences("본인 확인이 필요합니다. 성함이")
check("완성된 문장만 반환", sentences == ["본인 확인이 필요합니다."], str(sentences))
check("종결부호 없는 잔여분은 버퍼에 남음", rest == " 성함이", repr(rest))

print("\n마스킹 문자 제거 — strip_mask_chars() (TTS 가 '빈 원'으로 읽는 것을 막는다)")

check(
    "기관명의 ○○ 제거",
    strip_mask_chars("○○지방검찰청 강윤재 수사관입니다.") == "지방검찰청 강윤재 수사관입니다.",
    strip_mask_chars("○○지방검찰청 강윤재 수사관입니다."),
)
check(
    "인물명의 ○○ 제거 후 공백 정리",
    strip_mask_chars("최○○ 수사관입니다.") == "최 수사관입니다.",
    strip_mask_chars("최○○ 수사관입니다."),
)
clean = "한양지방검찰청 강윤재 수사관입니다."
check("마스킹 문자가 없으면 원문 그대로", strip_mask_chars(clean) is clean, clean)

print("\n사기범 일시 장애 폴백 (LLM 호출 없이 chat() 을 가짜로 대체)")


class _FakeApiError(Exception):
    """google-genai APIError 처럼 code 를 들고 오는 예외."""

    def __init__(self, code: int) -> None:
        super().__init__(f"{code} 오류")
        self.code = code


check("503 은 일시 장애로 본다", is_transient_model_error(_FakeApiError(503)))
check("429 은 일시 장애로 본다", is_transient_model_error(_FakeApiError(429)))
check("400 은 재시도 대상이 아니다", not is_transient_model_error(_FakeApiError(400)))
check("403 은 재시도 대상이 아니다", not is_transient_model_error(_FakeApiError(403)))
check("일반 예외는 재시도 대상이 아니다", not is_transient_model_error(ValueError("boom")))


#: 폴백 재시도 "로직" 검증용 가짜 모델명.
#: ⚠️ 실제 설정(scammer_fallback_for())을 쓰면 안 된다 - CI 에는 .env 도
#: LLM_PROVIDER 도 없어 PROVIDER 가 기본값 ollama 가 되고, ollama 는 폴백이 비어 있어
#: 재시도가 일어나지 않는다. 로컬(.env 에 gemini)에서만 통과하는 테스트가 된다.
_FALLBACK = "test-fallback-model"


def _run_scammer(side_effect, on_delta=None, fallback=_FALLBACK):
    """chat() 과 폴백 설정을 가로채고 (호출된 모델 목록, 예외이름) 을 돌려준다."""
    used: list[str | None] = []

    def fake_chat(role, req, delta=None, model=None):
        used.append(model)
        result = side_effect(len(used), delta)
        if isinstance(result, BaseException):
            raise result
        return result

    original_chat = scammer_module.chat
    original_fallback = scammer_module.scammer_fallback_for
    scammer_module.chat = fake_chat
    scammer_module.scammer_fallback_for = lambda: fallback
    try:
        scammer_module.generate_scammer_turn(scenario, create_session(scenario), on_delta)
        return used, None
    except BaseException as exc:  # noqa: BLE001 - 종류만 확인한다
        return used, type(exc).__name__
    finally:
        scammer_module.chat = original_chat
        scammer_module.scammer_fallback_for = original_fallback


_OK = ChatResult(text="네, 확인되었습니다.", model="m", latency_ms=10, first_token_ms=5)

# 설정 해석은 프로바이더를 명시해 확인한다 (주변 환경에 좌우되지 않게).
_gemini_fallback = scammer_fallback_for("gemini")
check(
    "gemini 폴백이 설정돼 있고 기본 사기범 모델과 다르다",
    bool(_gemini_fallback) and _gemini_fallback != model_for("scammer", "gemini"),
    f"{model_for('scammer', 'gemini')} → {_gemini_fallback}",
)
check(
    "ollama 는 폴백을 두지 않는다",
    scammer_fallback_for("ollama") is None,
    str(scammer_fallback_for("ollama")),
)

used, err = _run_scammer(lambda n, d: _FakeApiError(503) if n == 1 else _OK)
check(
    "일시 장애 + 아직 방출 전이면 폴백 모델로 한 번 재시도",
    used == [None, _FALLBACK] and err is None,
    f"{used} {err}",
)


def _emit_then_fail(n, delta):
    if n == 1:
        if delta:
            delta("첫 문장입니다.")  # 안전 게이트를 통해 이미 나간 상태
        return _FakeApiError(503)
    return _OK


used, err = _run_scammer(_emit_then_fail, on_delta=lambda s: None)
check(
    "이미 문장을 내보냈으면 재시도하지 않는다 (같은 말이 두 번 들리면 안 된다)",
    used == [None] and err == "_FakeApiError",
    f"{used} {err}",
)

used, err = _run_scammer(lambda n, d: _FakeApiError(400))
check(
    "비일시 오류는 폴백 없이 그대로 올린다",
    used == [None] and err == "_FakeApiError",
    f"{used} {err}",
)

used, err = _run_scammer(lambda n, d: _FakeApiError(503))
check(
    "폴백도 실패하면 예외가 올라온다",
    used == [None, _FALLBACK] and err == "_FakeApiError",
    f"{used} {err}",
)

used, err = _run_scammer(lambda n, d: _FakeApiError(503), fallback=None)
check(
    "폴백 설정이 없으면(ollama 등) 재시도하지 않는다",
    used == [None] and err == "_FakeApiError",
    f"{used} {err}",
)

if failed == 0:
    print("\n스모크 테스트 통과 — 결정론적 코어는 정상입니다.\n")
else:
    print(f"\n{failed}건 실패\n")
sys.exit(0 if failed == 0 else 1)
