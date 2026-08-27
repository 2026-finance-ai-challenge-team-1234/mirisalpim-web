import asyncio
import json
import random
import threading
import uuid

from ai_core.engine import Engine, load_scenario, start_session, step
from ai_core.llm import ConfigError
from asgiref.sync import sync_to_async
from ai_core.types import UserJudgment as EngineJudgment
from django.db import IntegrityError, connections, transaction
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .diagnosis import build_report
from .diagnosis_llm import interpret
from .engine_state import load_state, save_state
from .grading import grade
from .http import error_response, json_response, parse_json_body
from .models import DiagnosisReport, Scenario, Session, UserJudgment
from .pii import mask_pii
from .recommendation import recommend
from .selection import get_selection, store_selection
from .throttle import (
    idempotency_cache_key,
    remember_turn,
    remembered_turn,
    turn_rate_exceeded,
)
from .tracks import TAXONOMY

#: 익명 식별자를 담는 세션 키로 원본 쿠키 값이 아니라 서버가 만든 파생 식별자를 넣음
#: 응답으로는 노출 X
ANON_CLIENT_ID_KEY = "anon_client_id"

#: 사용자 입력 길이 상한
MAX_INPUT_CHARS = 200

#: 한 턴 처리 제한 시간 (API 설계 9절). 넘으면 AI_TIMEOUT.
TURN_TIMEOUT_SECONDS = 60


def ensure_anon_client_id(session):
    """익명 세션에 파생 식별자를 보장하고 그 값을 돌려줌"""
    anon_client_id = session.get(ANON_CLIENT_ID_KEY)
    if not anon_client_id:
        anon_client_id = uuid.uuid4().hex
        session[ANON_CLIENT_ID_KEY] = anon_client_id
    return anon_client_id


@require_GET
@ensure_csrf_cookie
def bootstrap(request):
    """P-01. 익명 세션 쿠키와 csrftoken 쿠키를 발급

    사용자 ID 는 반환하지 않는다. features 는 실제로 적재된 시나리오를 근거로
    계산하므로, 시나리오가 없는 카테고리는 자동으로 false
    """
    ensure_anon_client_id(request.session)

    available = set(Scenario.objects.values_list("category", flat=True).distinct())

    return json_response(
        {
            "apiVersion": "v1",
            "features": {
                "voice": "voice" in available,
                "smishing": "smishing" in available,
                "phishing": False,
            },
            "limits": {"maxInputChars": MAX_INPUT_CHARS},
        }
    )


@require_GET
def all_scenarios(request):
    """P-03-01. 훈련 유형 분류표.

    분류표 전체를 내려보내되, 각 소분류에 시나리오 적재 현황을 붙임
    프론트는 available=false 를 비활성 처리해서 "눌렀는데 훈련할 게 없는" 경우를
    화면 단계에서 막음

    시나리오 카드 내부(is_scam / stages / tell_points / forbidden)는 절대 내보내지
    않는다. is_scam 이 새어나가면 훈련 자체가 무의미
    """
    # track 코드는 T=voice / S=smishing 으로 접두사가 갈려 카테고리 없이도 안 겹친다.
    counts = {}
    for track in Scenario.objects.values_list("track", flat=True):
        counts[track] = counts.get(track, 0) + 1

    payload = {}
    for category, groups in TAXONOMY.items():
        payload[category] = [
            {
                "id": group["id"],
                "code": group["id"],
                "title": group["title"],
                "badge": group["badge"],
                "desc": group["desc"],
                "subItems": [
                    {
                        "id": sub["id"],
                        "code": sub["code"],
                        "name": sub["name"],
                        "available": counts.get(sub["id"], 0) > 0,
                        "scenarioCount": counts.get(sub["id"], 0),
                    }
                    for sub in group["subItems"]
                ],
            }
            for group in groups
        ]

    return json_response(payload)


def _trainable_tracks():
    """시나리오가 실제로 적재된 track 코드 집합."""
    return set(Scenario.objects.values_list("track", flat=True))


@require_POST
def user_info(request):
    """P-03-02. 직접 선택한 훈련을 세션에 기록한다.

    이름/나이/주소는 받기만 하고 저장하지 않는다. ERD 에 담을 테이블이 없고,
    기획서의 '개인정보 수집·저장 없음' 이 심사 방어 논리이기 때문이다.
    (팀 결정이 뒤집히면 그때 모델을 추가한다.)
    """
    body = parse_json_body(request)
    if body is None:
        return error_response("INVALID_BODY", "요청 형식이 올바르지 않습니다.", 400)

    category = body.get("category")
    track = body.get("trackId")

    if category not in TAXONOMY:
        return error_response("INVALID_CATEGORY", "지원하지 않는 카테고리입니다.", 400)

    known = {
        sub["id"]
        for group in TAXONOMY[category]
        for sub in group["subItems"]
    }
    if track not in known:
        return error_response("INVALID_TRACK", "지원하지 않는 훈련 유형입니다.", 400)

    # 클라이언트가 보낸 available 을 믿지 않고 서버가 다시 확인한다.
    if track not in _trainable_tracks():
        return error_response(
            "SCENARIO_NOT_AVAILABLE", "아직 준비되지 않은 훈련 유형입니다.", 409
        )

    store_selection(request.session, category, track, entry_path="direct")

    return json_response({"category": category, "track": track})


def _find_track(track):
    """분류표에서 track 코드가 속한 (카테고리, 대분류, 소분류) 를 찾는다."""
    for category, groups in TAXONOMY.items():
        for group in groups:
            for sub in group["subItems"]:
                if sub["id"] == track:
                    return category, group, sub
    return None, None, None


@require_POST
def recommendations(request):
    """P-02. 문진 응답으로 훈련 1개를 추천하고 세션에 기록한다.

    추천 결과도 직접 선택과 같은 자리에 저장한다 - 프론트가 '설문 다시하기' 를
    덮어쓰기로 처리하기 때문이다.
    """
    body = parse_json_body(request)
    if body is None:
        return error_response("INVALID_BODY", "요청 형식이 올바르지 않습니다.", 400)

    result = recommend(body, _trainable_tracks())
    if result is None:
        return error_response(
            "SCENARIO_NOT_AVAILABLE", "훈련 가능한 시나리오가 없습니다.", 503
        )

    category, group, sub = _find_track(result["track"])
    if category is None:
        # 매핑표가 분류표에 없는 코드를 가리키는 상태 - 데이터 정합성 문제다.
        return error_response(
            "SCENARIO_NOT_AVAILABLE", "훈련 가능한 시나리오가 없습니다.", 503
        )

    store_selection(
        request.session,
        category,
        result["track"],
        entry_path="recommended",
        difficulty=result["difficulty"],
    )

    reasons = result["matched"] or ["평소 활동과 대응 습관을 기준으로 골랐습니다"]

    return json_response(
        {
            "category": category,
            "track": result["track"],
            "title": f"{sub['name']} 대응 훈련",
            "description": group["desc"],
            "reasons": reasons,
            "suitability": str(min(97, 78 + 7 * len(result["matched"]))),
        }
    )


@require_POST
def start_training(request):
    """P-04 / P-05-01. 고른 훈련으로 세션을 만들고 사기범의 첫 발화를 돌려준다.

    LLM 을 호출하지 않는다 - 첫 발화는 시나리오 카드의 opening 을 그대로 쓴다
    (ai_core.start_session: "결정적이고, 지연이 0이고, 반드시 각본 위에서 시작한다").

    ⚠️ 응답에 시나리오 제목·페르소나·목표를 담지 않는다. 제목이 "검찰 사칭 —",
    "경찰 민원 회신 —" 처럼 is_scam 을 그대로 누설하고, 페르소나 표기도 시나리오마다
    "가상 위협 발신자"처럼 정답을 알려준다. 훈련생은 지금 상황이 사기인지 알면 안 된다.
    """
    selection = get_selection(request.session)
    if not selection:
        return error_response(
            "NO_SELECTION", "먼저 훈련 유형을 선택해 주세요.", 400
        )

    candidates = list(
        Scenario.objects.filter(
            category=selection["category"], track=selection["track"]
        ).values_list("scenario_id", flat=True)
    )
    if not candidates:
        return error_response(
            "SCENARIO_NOT_AVAILABLE", "아직 준비되지 않은 훈련 유형입니다.", 409
        )

    # 같은 유형 안에 사기·정상 시나리오가 섞여 있고 무작위로 고른다 (기능명세 F-05).
    # 훈련생은 지금 고른 것이 사기인지 사전에 알 수 없어야 한다.
    scenario = load_scenario(random.choice(candidates))
    engine = start_session(scenario, difficulty=selection.get("difficulty"))

    with transaction.atomic():
        session = Session.objects.create(
            session_id=engine.state.session_id,
            scenario_id=scenario.scenario_id,
            anon_client_id=ensure_anon_client_id(request.session),
            entry_path=selection["entry_path"],
            status="active",
            difficulty=engine.state.difficulty,
        )
        save_state(session, engine.state)

    opening = engine.state.transcript[-1]

    return json_response(
        {
            "sessionId": str(session.session_id),
            "category": scenario.category,
            "maxTurns": scenario.max_turns,
            "turnNo": opening.turn,
            "opening": opening.text,
        },
        status=201,
    )


#: 위험 신호를 프론트 계약(camelCase)으로 옮기고 개입 문구를 붙인다 (기능명세 F-14).
#: 앞의 5종은 판정기가 관찰한 위험행동(RiskyAction.ACTION_TYPE), 뒤는 입력에서
#: 정규식으로 곧바로 잡은 개인정보다.
RISK_WARNINGS = {
    "personal_info": ("personalInfo", "방금 개인정보를 알려주셨습니다. 실제였다면 그대로 도용될 수 있습니다."),
    "link_click": ("linkClick", "문자 속 링크를 눌렀습니다. 실제였다면 악성 앱이 설치될 수 있습니다."),
    "app_install": ("appInstall", "앱 설치에 동의하셨습니다. 실제였다면 인증번호와 화면이 통째로 넘어갑니다."),
    "transfer_consent": ("transferConsent", "송금에 동의하셨습니다. 실제였다면 돈이 즉시 빠져나갑니다."),
    "isolation_accepted": ("isolationAcceptance", "가족·주변과 연락하지 않기로 하셨습니다. 고립 유도는 사기의 결정적 신호입니다."),
    "resident_registration_number": ("personalInfo", "방금 주민등록번호를 알려주셨습니다. 실제였다면 이 정보로 지금 대출이 실행됩니다."),
    "account_number": ("personalInfo", "방금 계좌번호를 알려주셨습니다. 실제였다면 대포통장으로 쓰일 수 있습니다."),
    "card_number": ("personalInfo", "방금 카드번호를 알려주셨습니다. 실제였다면 즉시 결제에 쓰입니다."),
    "phone_number": ("personalInfo", "방금 전화번호를 알려주셨습니다. 실제였다면 추가 사기 표적이 됩니다."),
}


#: 정규식(pii.py)이 값의 종류까지 특정해서 잡아낸 항목들. 판정기의 포괄적인
#: personal_info 와 같은 사실을 가리킨다.
SPECIFIC_PII_KINDS = {
    "resident_registration_number",
    "account_number",
    "card_number",
    "phone_number",
}


def _risk_warnings(kinds):
    """같은 신호가 반복되면 한 번만 내보낸다.

    ⚠️ 매핑된 type 이 아니라 원래 신호 기준으로 묶는다. 주민등록번호와 계좌번호는
    둘 다 personalInfo 로 나가지만 알려줘야 할 내용이 다르다("이 정보로 대출이
    실행됩니다" vs "대포통장으로 쓰일 수 있습니다"). type 으로 묶으면 훈련생이
    한 문장에서 둘을 같이 말했을 때 뒤엣것이 통째로 사라진다.

    다만 정규식이 종류까지 특정해 알린 경우, 판정기의 포괄적인 personal_info 는
    같은 말을 한 번 더 하는 것이라 생략한다.
    """
    kinds = list(kinds)
    has_specific_pii = SPECIFIC_PII_KINDS.intersection(kinds)

    warnings = []
    seen = set()
    for kind in kinds:
        if kind == "personal_info" and has_specific_pii:
            continue
        mapped = RISK_WARNINGS.get(kind)
        if mapped is None or kind in seen:
            continue
        seen.add(kind)
        warnings.append({"type": mapped[0], "message": mapped[1]})
    return warnings


def _check_turn_request(request, session_id):
    """두 턴 경로가 공유하는 앞단 검사.

    반환: (본문 텍스트, 익명 ID, 오류응답). 오류가 있으면 앞의 둘은 None 이다.
    """
    body = parse_json_body(request)
    if body is None:
        return None, None, error_response(
            "INVALID_BODY", "요청 형식이 올바르지 않습니다.", 400
        )

    text = (body.get("text") or "").strip()
    if not text:
        return None, None, error_response("EMPTY_INPUT", "입력이 비어 있습니다.", 400)
    if len(text) > MAX_INPUT_CHARS:
        return None, None, error_response(
            "INPUT_TOO_LARGE", f"{MAX_INPUT_CHARS}자 이내로 입력해 주세요.", 413
        )

    anon_client_id = ensure_anon_client_id(request.session)

    retry_after = turn_rate_exceeded(anon_client_id)
    if retry_after is not None:
        return None, None, error_response(
            "RATE_LIMITED",
            "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
            429,
            headers={"Retry-After": str(retry_after)},
        )

    return text, anon_client_id, None


def _run_step(scenario, state, masked_text):
    """step() 을 시간 제한과 함께 돌린다.

    step() 은 LLM 을 세 번 부르고 취소할 방법이 없다. 제한 시간이 지나면 스레드는
    그대로 두고(daemon) 요청만 끝낸다 - 상태를 저장하지 않으므로 세션은 그대로다.

    반환: (결과, 오류코드). 둘 중 하나만 값이 있다.

    ConfigError 는 삼키지 않고 그대로 올린다. 모델 호출 실패(502)와 달리 우리
    설정이 잘못된 것이라 운영자가 고쳐야 하고, 500 으로 드러나야 눈에 띈다.
    """
    box = {}

    def run():
        try:
            box["outcome"] = step(Engine(scenario=scenario, state=state), masked_text)
        except Exception as exc:  # 모델 오류·설정 오류 등
            box["error"] = exc
        finally:
            connections.close_all()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(TURN_TIMEOUT_SECONDS)

    if worker.is_alive():
        return None, "AI_TIMEOUT"
    if "error" in box:
        if isinstance(box["error"], ConfigError):
            raise box["error"]
        return None, "AI_ERROR"
    return box["outcome"], None


def _open_turn(session_id, anon_client_id):
    """턴 시작에 필요한 것만 짧은 트랜잭션에서 읽는다.

    ⚠️ LLM 호출은 반드시 이 트랜잭션 밖에서 한다. 예전 구현은 step() 을 통째로
    atomic + select_for_update 안에 두어서, 턴당 4~20초 동안 DB 커넥션과 행 잠금을
    붙들고 있었다. 동시 사용자가 몇 명만 돼도 커넥션 풀이 마른다.

    잠금 대신 _commit_turn() 의 낙관적 검사(turn 번호 비교)로 턴 겹침을 막는다.

    반환: (컨텍스트, 오류응답). 둘 중 하나만 값이 있다.
    """
    with transaction.atomic():
        session = (
            Session.objects.select_for_update()
            .filter(pk=session_id, anon_client_id=anon_client_id)
            .first()
        )
        # 남의 익명 쿠키로 접근하면 존재 여부도 알려주지 않는다 (403 이 아니라 404).
        if session is None:
            return None, error_response(
                "SESSION_NOT_FOUND", "훈련을 찾을 수 없습니다.", 404
            )
        if session.status != "active":
            return None, error_response("SESSION_ENDED", "이미 종료된 훈련입니다.", 409)

        return (load_scenario(session.scenario_id), load_state(session), session.turn), None


@require_POST
def submit_turn(request, session_id):
    """P-05-02. 훈련생 발화 1턴을 처리하고 사기범의 다음 발화를 돌려준다.

    처리 순서는 API 설계 4-6 을 따른다:
      입력 검증 → PII 마스킹 → 판정기 → 코드 상태 승인 → 사기범 생성 → 안전 필터
    뒤의 네 단계는 ai_core.step() 안에서 일어난다.

    LLM 호출은 트랜잭션 밖에서 한다. 턴 겹침은 저장 시점의 낙관적 검사로 막는다
    (_open_turn / _commit_turn 참고) - SSE 경로와 같은 방식이다.
    """
    text, anon_client_id, failure = _check_turn_request(request, session_id)
    if failure is not None:
        return failure

    # 같은 Idempotency-Key 로 다시 왔다면 턴을 또 진행하지 않고 첫 응답을 돌려준다.
    idem_key = idempotency_cache_key(request, session_id)
    replayed = remembered_turn(idem_key)
    if replayed is not None:
        return json_response(replayed)

    context, failure = _open_turn(session_id, anon_client_id)
    if failure is not None:
        return failure
    scenario, state, loaded_turn = context

    masked_text, detected_pii = mask_pii(text)

    # 트랜잭션 밖 - 여기가 4~20초 걸린다.
    outcome, error_code = _run_step(scenario, state, masked_text)
    if error_code == "AI_TIMEOUT":
        return error_response(
            "AI_TIMEOUT", "응답이 지연되고 있습니다. 다시 시도해 주세요.", 504
        )
    if error_code is not None:
        return error_response("AI_ERROR", "응답 생성에 실패했습니다.", 502)

    try:
        _commit_turn(session_id, anon_client_id, loaded_turn, state, outcome)
    except ConcurrentTurnError:
        return error_response(
            "TURN_CONFLICT", "이전 턴이 아직 처리 중입니다.", 409
        )

    payload = {
        "turnNo": state.turn,
        "scammerText": outcome.scammer_text,
        "riskWarnings": _risk_warnings(detected_pii + outcome.risky_actions),
        "ended": outcome.ended,
        "endReason": outcome.end_reason,
    }
    remember_turn(idem_key, payload)
    return json_response(payload)


@require_POST
def submit_judgment(request, session_id):
    """P-06. 판단 제출 = 종료 + 채점 + 진단을 한 번에 처리한다.

    API 설계 1절이 "판단 없이 finish 만 호출하는 계약은 F-11 과 불일치"라고 정해서
    별도 종료 API 를 두지 않는다. 최대 턴 도달로 이미 종료된 세션도 판단은 받는다
    (화면이 종료 시점에 자동으로 물어본다).

    응답 후 대화 원문을 지운다 - 리포트에 필요한 값은 이미 스냅샷으로 옮겼다.

    진단 LLM 호출은 트랜잭션 밖에서 한다. 턴 처리와 같은 이유로, 수십 초 걸리는
    모델 호출을 트랜잭션 + 행 잠금 안에 두면 커넥션이 그동안 묶인다.
    """
    body = parse_json_body(request)
    if body is None:
        return error_response("INVALID_BODY", "요청 형식이 올바르지 않습니다.", 400)

    is_scam_guess = body.get("isScamGuess")
    if not isinstance(is_scam_guess, bool):
        return error_response(
            "INVALID_JUDGMENT", "사기 여부 판단을 보내주세요.", 400
        )

    anon_client_id = ensure_anon_client_id(request.session)

    with transaction.atomic():
        session = (
            Session.objects.select_for_update()
            .filter(pk=session_id, anon_client_id=anon_client_id)
            .first()
        )
        if session is None:
            return error_response("SESSION_NOT_FOUND", "훈련을 찾을 수 없습니다.", 404)
        if UserJudgment.objects.filter(session=session).exists():
            return error_response("ALREADY_JUDGED", "이미 판단을 제출했습니다.", 409)

        scenario = load_scenario(session.scenario_id)
        state = load_state(session)

    state.user_judgment = EngineJudgment(turn=state.turn, is_scam_guess=is_scam_guess)

    # 등급·놓친 단서·행동 가이드는 코드가 정한다 (리포트 문서 §8).
    result = grade(scenario, state)
    report = build_report(scenario, state, result)

    # 트랜잭션 밖 - 실패하거나 늦으면 규칙 기반 문장을 그대로 쓴다.
    interpreted = interpret(scenario, state, result, report)
    if interpreted:
        report.update(interpreted)

    try:
        _finish_session(session_id, is_scam_guess, result, report)
    except IntegrityError:
        # 준비하는 사이에 다른 요청이 먼저 판단을 저장했다.
        return error_response("ALREADY_JUDGED", "이미 판단을 제출했습니다.", 409)

    return json_response(report)


def _finish_session(session_id, is_scam_guess, result, report):
    """채점 결과를 저장하고 세션을 닫는다. 원문은 여기서 지운다."""
    with transaction.atomic():
        session = Session.objects.select_for_update().get(pk=session_id)

        UserJudgment.objects.create(
            session=session,
            judged_turn=result.judged_turn,
            is_scam_guess=is_scam_guess,
            grade=result.grade,
        )
        DiagnosisReport.objects.create(
            session=session,
            # 분류 체계(Cialdini 5유형 고정 여부)가 미확정이라 LLM 이 준 짧은 구를
            # 그대로 넣는다. 고정 목록으로 정해지면 매핑을 추가해야 한다.
            vulnerability_type=report["vulnerabilityPattern"][:30],
            missed_tell_points=report["missedTellPoints"],
            guidance_text="\n".join(report["guidance"]),
            summary=report["summary"],
            strength=report["strength"],
            weakness=report["weakness"],
        )

        session.status = "ended"
        session.ended_at = session.ended_at or timezone.now()
        session.save(update_fields=["status", "ended_at"])

        _discard_transcript(session)


def _discard_transcript(session):
    """대화 원문 파기.

    행 자체는 남긴다 - 턴 번호·화자·단계는 타임라인에 쓰이고 개인정보가 아니다.
    지우는 것은 발화 내용뿐이다 (기획서 10절: "대화는 세션 종료 시 파기").
    """
    session.turns.update(text="")


#: 워커 스레드가 스트림 끝을 알리는 표식.
_STREAM_END = object()


class ConcurrentTurnError(Exception):
    """스트리밍 중 같은 세션의 다른 턴이 먼저 저장된 경우."""


def _sse(event, payload):
    body = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {body}\n\n"


@require_POST
def turn_stream(request, session_id):
    """P-05-02 (SSE). 승인된 문장이 나오는 즉시 흘려보낸다.

    동기 버전(submit_turn)과 처리 순서는 같다. 다른 점은 사기범 발화를 다 기다리지
    않고 안전 필터를 통과한 문장부터 내보낸다는 것뿐이다 - 체감 지연이 여기서 줄어든다.

    ai_core.step() 은 동기 함수이고 on_delta 는 StreamingSafetyGate 의 워커 스레드에서
    불린다(poc/server.py 와 같은 구조). 그래서 step() 을 별도 스레드에 넘기고 이 쪽은
    큐를 비우며 yield 한다.

    ⚠️ 생성기가 도는 동안에는 DB 트랜잭션을 열어두지 않는다. 대신 저장 시점에 불러온
    턴 번호가 그대로인지 확인해서(낙관적 잠금) 턴이 겹치면 저장을 포기한다.

    ⚠️ _turn_events 는 반드시 async 생성기여야 한다. 동기 생성기를 넘기면 ASGI 경로가
    이벤트 루프를 막으며 소진해서, 문장이 하나씩 나가지 않고 턴이 끝난 뒤 한꺼번에
    도착한다 - 스트리밍의 이점이 통째로 사라진다.
    """
    text, anon_client_id, failure = _check_turn_request(request, session_id)
    if failure is not None:
        return failure

    context, failure = _open_turn(session_id, anon_client_id)
    if failure is not None:
        return failure
    scenario, state, loaded_turn = context

    masked_text, detected_pii = mask_pii(text)

    response = StreamingHttpResponse(
        _turn_events(
            session_id, anon_client_id, scenario, state, loaded_turn,
            masked_text, detected_pii,
        ),
        content_type="text/event-stream; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    # Railway 등 리버스 프록시가 응답을 모아두면 스트리밍 이점이 사라진다.
    response["X-Accel-Buffering"] = "no"
    return response


async def _turn_events(
    session_id, anon_client_id, scenario, state, loaded_turn, masked_text, detected_pii
):
    yield _sse("accepted", {"turnNo": loaded_turn + 1})

    # 정규식으로 잡은 개인정보는 LLM 을 기다릴 필요가 없다 - 즉시 개입한다 (F-14).
    pii_warnings = _risk_warnings(detected_pii)
    for warning in pii_warnings:
        yield _sse("riskWarning", warning)

    # 판정기가 먼저 끝나야 사기범 생성이 시작된다. 화면이 대기 상태를 표시할 수
    # 있도록 지금 단계를 알린다 (API 설계 4-6 의 status 이벤트).
    yield _sse("status", {"phase": "judging"})

    # step() 은 동기 함수라 스레드에서 돌리고, 결과 문장은 이벤트 루프로 넘겨받는다.
    loop = asyncio.get_running_loop()
    deltas = asyncio.Queue()
    box = {}

    def hand_off(sentence):
        loop.call_soon_threadsafe(deltas.put_nowait, sentence)

    def run_turn():
        try:
            box["outcome"] = step(
                Engine(scenario=scenario, state=state), masked_text, on_delta=hand_off
            )
        except Exception as exc:  # 모델 오류·타임아웃 등
            box["error"] = exc
        finally:
            # 이 스레드가 DB 를 쓸 일은 없지만, 썼다면 커넥션을 여기서 반납한다.
            connections.close_all()
            loop.call_soon_threadsafe(deltas.put_nowait, _STREAM_END)

    worker = threading.Thread(target=run_turn, daemon=True)
    worker.start()

    deadline = loop.time() + TURN_TIMEOUT_SECONDS
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            yield _sse("error", {"code": "AI_TIMEOUT", "message": "응답이 지연되고 있습니다."})
            return
        try:
            item = await asyncio.wait_for(deltas.get(), timeout=remaining)
        except (asyncio.TimeoutError, TimeoutError):
            # 워커는 daemon 이라 두고 끝낸다. 저장하지 않으므로 세션은 그대로다.
            yield _sse("error", {"code": "AI_TIMEOUT", "message": "응답이 지연되고 있습니다."})
            return
        if item is _STREAM_END:
            break
        # 안전 필터를 통과한 문장만 여기 도착한다 (StreamingSafetyGate).
        yield _sse("delta", {"text": item})
    await asyncio.to_thread(worker.join)

    if "error" in box:
        yield _sse("error", {"code": "AI_ERROR", "message": "응답 생성에 실패했습니다."})
        return

    outcome = box["outcome"]

    # 판정기 결과는 step() 이 끝나야 알 수 있어서 여기서 내보낸다. 동기 경로
    # (submit_turn)와 같은 결과가 되도록 두 신호를 합쳐서 계산한 뒤, 앞에서 이미
    # 보낸 것만 뺀다.
    already_sent = {warning["message"] for warning in pii_warnings}
    for warning in _risk_warnings(detected_pii + outcome.risky_actions):
        if warning["message"] not in already_sent:
            yield _sse("riskWarning", warning)

    try:
        await sync_to_async(_commit_turn)(
            session_id, anon_client_id, loaded_turn, state, outcome
        )
    except ConcurrentTurnError:
        yield _sse(
            "error", {"code": "TURN_CONFLICT", "message": "이전 턴이 아직 처리 중입니다."}
        )
        return

    yield _sse(
        "done",
        {
            "turnNo": state.turn,
            "text": outcome.scammer_text,
            "ended": outcome.ended,
            "endReason": outcome.end_reason,
        },
    )


def _commit_turn(session_id, anon_client_id, loaded_turn, state, outcome):
    """스트리밍이 끝난 뒤 상태를 저장한다.

    생성기가 도는 동안 다른 요청이 같은 세션의 턴을 진행했다면 turn 이 움직여 있다.
    그 경우 저장하면 두 턴이 섞이므로 포기한다.
    """
    with transaction.atomic():
        session = (
            Session.objects.select_for_update()
            .filter(pk=session_id, anon_client_id=anon_client_id)
            .first()
        )
        if session is None or session.turn != loaded_turn:
            raise ConcurrentTurnError

        save_state(session, state)
        if outcome.ended:
            session.status = "ended"
            session.ended_at = timezone.now()
            session.save(update_fields=["status", "ended_at"])
