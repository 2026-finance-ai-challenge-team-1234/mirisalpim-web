"""진단 LLM — 이미 계산된 사실을 해석해 문장으로 만든다.

리포트 문서 §4 의 역할 분담을 그대로 지킨다.

  LLM 이 하는 것   : summary / vulnerability_pattern / strength / weakness
  LLM 이 안 하는 것: 등급·점수 결정, tell point 발생 여부, 위험행동 발생 여부

등급과 단서 목록은 grading.py 가 이미 정했고, 여기서 나온 문장으로 덮어쓰지 않는다.
호출이 실패하거나 늦으면 diagnosis.py 의 규칙 기반 문장을 그대로 쓴다 - fallback 이
빈약한 게 아니라 덜 개인화됐을 뿐이라 서비스는 그대로 돌아간다 (API 설계 9절).

⚠️ 전용 role 이 없어 판정기(judge) 설정을 빌려 쓴다. gemini-3.7-flash, 구조화 출력,
   roleplay 튜닝 없음 - 진단에도 맞는 조합이다. ai_core/config.py 의 AGENTS 에
   diagnosis role 이 추가되면 그쪽으로 옮기는 게 맞다.
"""

import json
import logging
import threading

from ai_core.llm import ChatRequest, chat_json

logger = logging.getLogger(__name__)

#: 이 시간을 넘기면 규칙 기반 문장으로 간다. API 설계 9절은 180초까지 허용하지만,
#: fallback 이 완성된 리포트라 로딩 화면을 그만큼 붙잡아 둘 이유가 없다.
DIAGNOSIS_TIMEOUT_SECONDS = 60

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "vulnerability_pattern": {"type": "string"},
        "strength": {"type": "string"},
        "weakness": {"type": "string"},
    },
    "required": ["summary", "vulnerability_pattern", "strength", "weakness"],
}

SYSTEM = """당신은 보이스피싱·스미싱 모의훈련의 진단 작성자입니다.
훈련이 끝난 뒤, 이미 계산된 사실을 받아 훈련생에게 보여줄 문장을 씁니다.

지켜야 할 것
- 등급, 점수, 놓친 단서 목록, 위험행동 목록을 새로 판단하지 마세요. 이미 정해져 있습니다.
- 주어진 사실에 없는 내용을 지어내지 마세요.
- 훈련생을 비난하지 마세요. 속은 것은 흔한 일이라는 태도를 유지합니다.
- 잘한 점(strength)은 반드시 하나 이상 찾아서 씁니다. 대화를 끝까지 이어간 것도 경험입니다.
- 실제 URL, 계좌번호, 기관 전화번호를 쓰지 마세요.
- 존댓말로, 각 항목은 1~2문장으로 씁니다.

항목
- summary: 이번 훈련이 어떻게 흘러갔는지 요약합니다.
- vulnerability_pattern: 이번 훈련에서 드러난 경향을 20자 이내 짧은 구로 씁니다.
  (예: "긴급성 압박에 반응하는 경향") 사람의 고정된 성격으로 단정하지 마세요.
- strength: 훈련생이 실제로 잘한 행동을 씁니다.
- weakness: 아쉬웠던 지점을 씁니다."""


def interpret(scenario, state, result, report):
    """LLM 해석 4문장. 실패하면 None."""
    box = {}

    def run():
        try:
            box["value"] = _call(scenario, state, result, report)
        except Exception as exc:  # 모델 오류·설정 오류·파싱 실패
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(DIAGNOSIS_TIMEOUT_SECONDS)

    if worker.is_alive():
        logger.warning("diagnosis_llm timeout - 규칙 기반 문장을 사용합니다")
        return None
    if "error" in box:
        logger.warning("diagnosis_llm 실패(%s) - 규칙 기반 문장을 사용합니다",
                       type(box["error"]).__name__)
        return None
    return box.get("value")


def _call(scenario, state, result, report):
    facts = {
        "카테고리": scenario.category,
        "실제로_사기였는가": scenario.is_scam,
        "등급": result.grade,
        "판단이_맞았는가": result.is_correct,
        "훈련생이_판단한_턴": result.judged_turn,
        "가장_빠른_판별_가능_턴": result.first_detectable_turn,
        "놓친_단서": [
            {"턴": m["turn"], "신호": m["trigger"], "이유": m["why"]}
            for m in report["missedTellPoints"]
        ],
        "훈련생이_한_위험행동": result.risky_actions,
        "훈련생이_되묻거나_거절한_횟수": state.resistance_count,
        "대화": [
            {"화자": "사기범" if t.role == "scammer" else "훈련생", "말": t.text}
            for t in state.transcript
        ],
    }

    payload, _ = chat_json(
        "judge",
        ChatRequest(
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": json.dumps(facts, ensure_ascii=False, indent=1),
            }],
            response_schema=DIAGNOSIS_SCHEMA,
        ),
    )
    if not payload:
        return None

    return {
        "summary": payload["summary"].strip(),
        "vulnerabilityPattern": payload["vulnerability_pattern"].strip(),
        "strength": payload["strength"].strip(),
        "weakness": payload["weakness"].strip(),
    }
