# ai_core

미리살핌의 AI 핵심 로직 — 사기범 에이전트 + 판정기 + 상태머신. Django 의존이 없다.
Django 앱(`backend/training/`)은 이 패키지를 import 만 한다.

`ai-test/`(별도 저장소, PoC 전용)에서 검증한 뒤 이관한 코드다. `ai-test/cli/`와
`agents/victim.py`(자동 대화 테스트 하네스)는 PoC 전용이라 이관하지 않았다.

## 빠른 확인 (LLM 호출 없음)

```bash
cd mirisalpim-web
python -m ai_core.smoke
```

## 설정

`config.py` 한 곳에서 프로바이더(`ollama`/`anthropic`/`gemini`)와 역할별 모델을 결정한다.
`.env`는 `backend/.env`를 그대로 읽는다(Django와 환경변수를 공유). 필요한 키:

```bash
LLM_PROVIDER=gemini          # 기본값 ollama(무과금)
GEMINI_API_KEY=...           # PROVIDER=gemini 일 때
ANTHROPIC_API_KEY=...        # PROVIDER=anthropic 일 때
```

## 판정기 제안 → 코드 승인

`engine.step()`이 매 훈련생 턴마다 판정기를 호출해 `advance_stage`를 제안받고,
`state.try_advance_stage(scenario, state, proposed=...)`가 최소 턴 수 조건과 함께
최종 승인한다. 판정기가 반대하면 최소 턴을 채웠어도 전환하지 않는다
(`ai_core/smoke.py`의 "판정기 연결 시 AND-게이트" 항목이 이 경계를 검증한다).

`risky_actions`/`resisted`는 판정기가 관찰한 사실이라 그대로 상태에 반영한다
(`state.apply_judgment`). `risky_actions` 값은 `training.RiskyAction.ACTION_TYPE`
(Django 모델)과 동일한 5종 enum이라 그대로 `RiskyAction` 행으로 저장할 수 있다.

⚠️ 구조화 출력(판정기)은 지금 **gemini 전용**이다. `PROVIDER=anthropic`/`ollama`로
`use_judge=True`(기본값) 호출하면 `NotImplementedError`가 난다 — `use_judge=False`로
호출하거나(min_turns만으로 전환, 기존 PoC-1 방식) gemini로 전환할 것.
