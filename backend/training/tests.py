import asyncio
import json
import time
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from ai_core.engine import Engine, TurnOutcome, load_scenario, start_session
from ai_core.llm import ConfigError
from ai_core.types import RiskyAction as EngineRiskyAction
from ai_core.types import UserJudgment as EngineJudgment
from ai_core.state import (
    apply_judgment,
    current_stage,
    mark_tell_points,
    record_turn,
    try_advance_stage,
)
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, TransactionTestCase

from .engine_state import load_state, save_state
from .grading import first_detectable_turn, grade
from .models import Scenario, Session, Stage, TellPoint
from .throttle import TURN_RATE_LIMIT, TURN_RATE_WINDOW_SECONDS
from .selection import SELECTION_KEY
from .views import ANON_CLIENT_ID_KEY, ConcurrentTurnError, _commit_turn


class BootstrapTests(TestCase):
    """P-01. 익명 세션 쿠키 + CSRF 쿠키 발급"""

    def test_issues_session_and_csrf_cookies(self):
        response = self.client.get("/api/v1/bootstrap")

        self.assertEqual(response.status_code, 200)
        self.assertIn("sessionid", response.cookies)
        self.assertIn("csrftoken", response.cookies)

    def test_csrf_cookie_is_readable_by_frontend(self):
        """client.js 가 document.cookie 로 csrftoken 을 읽어 헤더에 붙임"""
        response = self.client.get("/api/v1/bootstrap")

        self.assertFalse(response.cookies["csrftoken"]["httponly"])

    def test_session_cookie_is_not_readable_by_script(self):
        response = self.client.get("/api/v1/bootstrap")

        self.assertTrue(response.cookies["sessionid"]["httponly"])

    def test_does_not_expose_anon_client_id(self):
        response = self.client.get("/api/v1/bootstrap")

        self.assertNotIn("anonClientId", response.json())
        self.assertIn(ANON_CLIENT_ID_KEY, self.client.session)

    def test_anon_client_id_is_stable_across_requests(self):
        self.client.get("/api/v1/bootstrap")
        first = self.client.session[ANON_CLIENT_ID_KEY]

        self.client.get("/api/v1/bootstrap")

        self.assertEqual(self.client.session[ANON_CLIENT_ID_KEY], first)

    def test_response_is_not_cached(self):
        response = self.client.get("/api/v1/bootstrap")

        self.assertEqual(response["Cache-Control"], "no-store")

    def test_features_follow_seeded_scenarios(self):
        """시나리오가 없는 카테고리는 false 로 내려간다."""
        response = self.client.get("/api/v1/bootstrap")

        features = response.json()["features"]
        self.assertFalse(features["voice"])
        self.assertFalse(features["smishing"])

    def test_features_voice_true_when_voice_scenario_exists(self):
        Scenario.objects.create(
            scenario_id="sc-test",
            category="voice",
            track="T01-1",
            target_tracks=["senior"],
            title="테스트",
            source="테스트",
            difficulty=1,
            goal="테스트",
            max_turns=10,
            persona_display_name="테스트",
            persona_tone="테스트",
            persona_voice_preset="male_40s_formal",
        )

        response = self.client.get("/api/v1/bootstrap")

        self.assertTrue(response.json()["features"]["voice"])


class AllScenariosTests(TestCase):
    """P-03-01. 분류표 + 시나리오 적재 현황 (API 설계 8절 체크리스트)"""

    @classmethod
    def setUpTestData(cls):
        Scenario.objects.create(
            scenario_id="sc-test",
            category="voice",
            track="T01-1",
            target_tracks=["senior"],
            title="검찰 사칭 테스트",
            source="테스트",
            is_scam=True,
            difficulty=2,
            goal="테스트",
            max_turns=20,
            persona_display_name="테스트",
            persona_tone="테스트",
            persona_voice_preset="male_40s_formal",
            forbidden=["실제 계좌번호"],
        )

    def test_returns_frontend_shape(self):
        """client.js 는 voice/smishing 이 배열인지로 응답 유효성을 판단한다."""
        payload = self.client.get("/api/v1/all-scenarios").json()

        self.assertIsInstance(payload["voice"], list)
        self.assertIsInstance(payload["smishing"], list)
        group = payload["voice"][0]
        self.assertEqual(
            set(group), {"id", "code", "title", "badge", "desc", "subItems"}
        )

    def test_marks_available_only_where_scenario_exists(self):
        payload = self.client.get("/api/v1/all-scenarios").json()

        subs = {s["id"]: s for g in payload["voice"] for s in g["subItems"]}
        self.assertTrue(subs["T01-1"]["available"])
        self.assertEqual(subs["T01-1"]["scenarioCount"], 1)
        self.assertFalse(subs["T01-2"]["available"])
        self.assertEqual(subs["T01-2"]["scenarioCount"], 0)

    def test_never_exposes_scenario_internals(self):
        """is_scam이 새면 훈련이 무의미해지며, stages/tellPoints/forbidden 또한 마찬가지

        부분 문자열 검사는 오탐이 나기에(코드값 personal_info_input 이 'persona' 를
        포함한다) 노출된 키 집합 자체를 고정
        """
        payload = self.client.get("/api/v1/all-scenarios").json()

        for groups in payload.values():
            for group in groups:
                self.assertEqual(
                    set(group), {"id", "code", "title", "badge", "desc", "subItems"}
                )
                for sub in group["subItems"]:
                    self.assertEqual(
                        set(sub),
                        {"id", "code", "name", "available", "scenarioCount"},
                    )

    def test_response_is_not_cached(self):
        response = self.client.get("/api/v1/all-scenarios")

        self.assertEqual(response["Cache-Control"], "no-store")


class ScenarioFactory:
    """테스트용 시나리오 생성 헬퍼."""

    @staticmethod
    def create(scenario_id, track, category="voice", **kwargs):
        defaults = {
            "target_tracks": ["senior"],
            "title": f"{track} 테스트",
            "source": "테스트",
            "is_scam": True,
            "difficulty": 2,
            "goal": "테스트",
            "max_turns": 20,
            "persona_display_name": "테스트",
            "persona_tone": "테스트",
            "persona_voice_preset": "male_40s_formal",
        }
        defaults.update(kwargs)
        return Scenario.objects.create(
            scenario_id=scenario_id, category=category, track=track, **defaults
        )


class UserInfoTests(TestCase):
    """P-03-02. 직접 선택 결과를 세션에 기록한다."""

    @classmethod
    def setUpTestData(cls):
        ScenarioFactory.create("sc-a", "T01-1")

    def post(self, **body):
        return self.client.post(
            "/api/v1/user-info", data=body, content_type="application/json"
        )

    def test_stores_selection_in_session(self):
        response = self.post(category="voice", trackId="T01-1", name="홍길동")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session[SELECTION_KEY],
            {
                "category": "voice",
                "track": "T01-1",
                "entry_path": "direct",
                "difficulty": None,  # 직접 선택은 문진이 없어 시나리오 기본값을 쓴다
            },
        )

    def test_does_not_store_personal_info(self):
        """이름·나이·주소는 받기만 하고 저장하지 않는다."""
        self.post(
            category="voice", trackId="T01-1",
            name="홍길동", age="60대 이상", address="서울시 성북구",
        )

        stored = str(dict(self.client.session))
        for pii in ("홍길동", "60대 이상", "서울시 성북구"):
            self.assertNotIn(pii, stored)

    def test_rejects_unknown_track(self):
        response = self.post(category="voice", trackId="T99-9")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_TRACK")

    def test_rejects_track_without_scenario(self):
        """클라이언트가 보낸 available 을 믿지 않는다."""
        response = self.post(category="voice", trackId="T01-2")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "SCENARIO_NOT_AVAILABLE")

    def test_rejects_malformed_body(self):
        response = self.client.post(
            "/api/v1/user-info", data="not json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)


class RecommendationTests(TestCase):
    """P-02. 문진 → 추천. 훈련 불가능한 track 은 반환하지 않는다."""

    @classmethod
    def setUpTestData(cls):
        ScenarioFactory.create("sc-a", "T01-1")
        ScenarioFactory.create("sc-b", "T05-1")

    def post(self, **body):
        return self.client.post(
            "/api/v1/recommendations", data=body, content_type="application/json"
        )

    def test_returns_fields_frontend_needs(self):
        payload = self.post(
            age="AGE_60", activities=[], concerns=["CONCERN_01"], habit="HABIT_LISTEN"
        ).json()

        self.assertEqual(
            set(payload),
            {"category", "track", "title", "description", "reasons", "suitability"},
        )
        self.assertEqual(payload["track"], "T01-1")
        self.assertEqual(payload["category"], "voice")

    def test_never_recommends_track_without_scenario(self):
        """CONCERN_09 는 T06-2/T06-1 을 가리키지만 둘 다 시나리오가 없다."""
        payload = self.post(
            age="AGE_30", activities=["ACT_LOAN_INSURANCE"],
            concerns=["CONCERN_09"], habit="HABIT_HANGUP",
        ).json()

        self.assertIn(payload["track"], {"T01-1", "T05-1"})

    def test_stores_selection_as_recommended(self):
        self.post(age="AGE_60", concerns=["CONCERN_01"], habit="HABIT_LISTEN")

        self.assertEqual(
            self.client.session[SELECTION_KEY]["entry_path"], "recommended"
        )

    def test_direct_selection_overwrites_recommendation(self):
        """프론트가 '설문 다시하기'와 '직접 선택하기'를 덮어쓰기로 처리한다."""
        self.post(age="AGE_60", concerns=["CONCERN_01"], habit="HABIT_LISTEN")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T05-1"},
            content_type="application/json",
        )

        selection = self.client.session[SELECTION_KEY]
        self.assertEqual(selection["track"], "T05-1")
        self.assertEqual(selection["entry_path"], "direct")

    def test_empty_survey_still_returns_trainable_track(self):
        payload = self.post().json()

        self.assertIn(payload["track"], {"T01-1", "T05-1"})

    def test_returns_503_when_no_scenarios_seeded(self):
        Scenario.objects.all().delete()

        response = self.post(age="AGE_60", concerns=["CONCERN_01"])

        self.assertEqual(response.status_code, 503)


class EngineStateAdapterTests(TestCase):
    """Step 7. ai_core.SessionState 를 DB 에 저장했다가 그대로 복원한다.

    LLM 을 호출하지 않는다 - start_session 은 시나리오의 opening 을 쓰고,
    record_turn/apply_judgment/mark_tell_points 는 순수 함수다.
    """

    SCENARIO_ID = "sc-02"

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def build_engine(self):
        scenario = load_scenario(self.SCENARIO_ID)
        return scenario, start_session(scenario, difficulty="normal")

    def create_session_row(self, state):
        return Session.objects.create(
            session_id=state.session_id,
            scenario_id=self.SCENARIO_ID,
            anon_client_id="anon-test",
            entry_path="direct",
            status="active",
            difficulty=state.difficulty,
        )

    def advance_one_user_turn(self, scenario, state):
        """LLM 없이 훈련생 턴 1회분 상태 변화를 만든다."""
        state.turn += 1
        record_turn(state, "user", "저 그런 적 없는데요", current_stage(scenario, state).id)
        apply_judgment(state, ["personal_info"], resisted=True)
        mark_tell_points(scenario, state)

    def test_round_trip_preserves_every_field(self):
        scenario, engine = self.build_engine()
        self.advance_one_user_turn(scenario, engine.state)
        session = self.create_session_row(engine.state)

        save_state(session, engine.state)
        restored = load_state(Session.objects.get(pk=session.pk))

        original = engine.state
        self.assertEqual(restored.scenario_id, original.scenario_id)
        self.assertEqual(restored.session_id, original.session_id)
        self.assertEqual(restored.difficulty, original.difficulty)
        self.assertEqual(restored.turn, original.turn)
        self.assertEqual(restored.stage_index, original.stage_index)
        self.assertEqual(restored.turns_in_stage, original.turns_in_stage)
        self.assertEqual(restored.resistance_count, original.resistance_count)
        self.assertEqual(restored.hit_tell_points, original.hit_tell_points)
        self.assertEqual(
            [(t.role, t.text, t.turn, t.stage) for t in restored.transcript],
            [(t.role, t.text, t.turn, t.stage) for t in original.transcript],
        )
        self.assertEqual(
            [(a.turn, a.type) for a in restored.risky_actions],
            [(a.turn, a.type) for a in original.risky_actions],
        )

    def test_restored_state_keeps_working_in_ai_core(self):
        """복원한 상태로 상태머신을 계속 돌릴 수 있어야 한다."""
        scenario, engine = self.build_engine()
        session = self.create_session_row(engine.state)
        save_state(session, engine.state)

        restored = load_state(Session.objects.get(pk=session.pk))
        self.advance_one_user_turn(scenario, restored)
        result = try_advance_stage(scenario, restored, proposed=True)

        self.assertIsInstance(result.advanced, bool)
        self.assertEqual(current_stage(scenario, restored).id, scenario.stages[restored.stage_index].id)

    def test_saving_twice_does_not_duplicate_rows(self):
        """증분 저장이라 같은 상태를 두 번 저장해도 행이 늘지 않는다."""
        scenario, engine = self.build_engine()
        self.advance_one_user_turn(scenario, engine.state)
        session = self.create_session_row(engine.state)

        save_state(session, engine.state)
        counts = (
            session.turns.count(),
            session.risky_actions.count(),
            session.tell_point_hits.count(),
        )
        save_state(session, engine.state)

        self.assertEqual(
            counts,
            (
                session.turns.count(),
                session.risky_actions.count(),
                session.tell_point_hits.count(),
            ),
        )

    def test_stage_advance_is_persisted(self):
        scenario, engine = self.build_engine()
        session = self.create_session_row(engine.state)
        save_state(session, engine.state)

        state = load_state(Session.objects.get(pk=session.pk))
        while not try_advance_stage(scenario, state, proposed=True).advanced:
            state.turn += 1
            state.turns_in_stage += 1
            record_turn(state, "user", "네", current_stage(scenario, state).id)
        save_state(session, state)

        session.refresh_from_db()
        self.assertEqual(session.current_stage.order_index, 1)
        self.assertEqual(session.turns_in_stage, 0)
        self.assertEqual(load_state(session).stage_index, 1)

    def test_tell_point_hits_are_recorded(self):
        scenario, engine = self.build_engine()
        session = self.create_session_row(engine.state)

        save_state(session, engine.state)

        self.assertGreater(session.tell_point_hits.count(), 0)
        self.assertEqual(
            sorted(load_state(session).hit_tell_points),
            sorted(engine.state.hit_tell_points),
        )


class StartTrainingTests(TestCase):
    """Step 8. 훈련 세션 생성 + 첫 발화 (LLM 호출 없음)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def select(self, track="T01-1", category="voice"):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": category, "trackId": track},
            content_type="application/json",
        )

    def start(self):
        return self.client.post("/api/v1/training-sessions")

    def test_creates_session_and_returns_opening(self):
        self.select()

        response = self.start()

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(
            set(payload), {"sessionId", "category", "maxTurns", "turnNo", "opening"}
        )
        self.assertEqual(payload["turnNo"], 1)
        self.assertTrue(payload["opening"])

    def test_persists_first_turn(self):
        self.select()

        session_id = self.start().json()["sessionId"]

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.status, "active")
        self.assertEqual(session.turn, 1)
        self.assertEqual(session.turns.count(), 1)
        self.assertEqual(session.turns.first().role, "scammer")

    def test_opening_matches_stored_turn(self):
        self.select()

        payload = self.start().json()

        stored = Session.objects.get(pk=payload["sessionId"]).turns.first()
        self.assertEqual(stored.text, payload["opening"])

    def test_never_leaks_whether_scenario_is_scam(self):
        """제목·페르소나·목표가 새면 훈련이 무의미해진다."""
        self.select(track="T01-2")  # sc-03(사기) + nm-01(정상) 이 함께 있는 유형

        payload = self.start().json()

        scenario = Scenario.objects.get(
            pk=Session.objects.get(pk=payload["sessionId"]).scenario_id
        )
        raw = str(payload)
        self.assertNotIn(scenario.title, raw)
        self.assertNotIn(scenario.goal, raw)
        self.assertNotIn(scenario.persona_display_name, raw)
        self.assertNotIn("isScam", raw)

    def test_mixes_normal_scenarios_into_the_same_track(self):
        """F-05. T01-2 는 사기 1 + 정상 1 이라 반복하면 둘 다 나와야 한다."""
        self.select(track="T01-2")

        picked = set()
        for _ in range(30):
            payload = self.start().json()
            picked.add(Session.objects.get(pk=payload["sessionId"]).scenario_id)

        self.assertEqual(picked, {"sc-03", "nm-01"})

    def test_requires_a_selection_first(self):
        self.client.get("/api/v1/bootstrap")

        response = self.start()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "NO_SELECTION")

    def test_records_entry_path_and_difficulty_from_survey(self):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/recommendations",
            data={"age": "AGE_60", "concerns": ["CONCERN_01"], "habit": "HABIT_HANGUP"},
            content_type="application/json",
        )

        session_id = self.start().json()["sessionId"]

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.entry_path, "recommended")
        self.assertEqual(session.difficulty, "hard")

    def test_session_is_owned_by_the_anonymous_client(self):
        self.select()

        session_id = self.start().json()["sessionId"]

        session = Session.objects.get(pk=session_id)
        self.assertEqual(
            session.anon_client_id, self.client.session[ANON_CLIENT_ID_KEY]
        )


def fake_step(engine, user_text, risky_actions=(), **kwargs):
    """LLM 없이 ai_core.step() 과 같은 상태 변화를 만든다.

    실제 step() 은 판정기·사기범·안전필터로 3번 LLM 을 호출한다. 뷰의 계약을
    검증하는 데는 상태 변화와 반환값만 있으면 되므로 그 부분만 흉내낸다.
    """
    scenario, state = engine.scenario, engine.state

    state.turn += 1
    record_turn(state, "user", user_text, current_stage(scenario, state).id)
    apply_judgment(state, list(risky_actions), resisted=False)
    try_advance_stage(scenario, state, proposed=False)

    if state.turn >= scenario.max_turns:
        return TurnOutcome(
            scammer_text="", latency_ms=0, first_token_ms=0, stage_changed=None,
            ended=True, end_reason=f"최대 턴({scenario.max_turns}) 도달",
            risky_actions=list(risky_actions),
        )

    state.turn += 1
    state.turns_in_stage += 1
    record_turn(state, "scammer", "가상 사기범 응답입니다.",
                current_stage(scenario, state).id, 12)
    mark_tell_points(scenario, state)

    return TurnOutcome(
        scammer_text="가상 사기범 응답입니다.", latency_ms=12, first_token_ms=5,
        stage_changed=None, ended=False, risky_actions=list(risky_actions),
    )


class SubmitTurnTests(TestCase):
    """Step 9a. 턴 처리 (동기). LLM 은 호출하지 않는다."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def start_training(self):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )
        return self.client.post("/api/v1/training-sessions").json()["sessionId"]

    def turn(self, session_id, text, risky_actions=()):
        with patch(
            "training.views.step",
            side_effect=lambda e, t, **kw: fake_step(e, t, risky_actions=risky_actions),
        ):
            return self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": text},
                content_type="application/json",
            )

    def test_returns_reply_and_persists_both_turns(self):
        session_id = self.start_training()

        response = self.turn(session_id, "저 그런 적 없는데요")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {"turnNo", "scammerText", "riskWarnings", "ended", "endReason"},
        )
        self.assertEqual(payload["scammerText"], "가상 사기범 응답입니다.")
        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.turns.count(), 3)  # opening + user + scammer
        self.assertEqual(session.turn, payload["turnNo"])

    def test_masks_pii_before_llm_and_before_db(self):
        """마스킹은 LLM 전달 전에 일어나야 하고 DB 에도 원문이 남으면 안 된다."""
        session_id = self.start_training()
        seen = {}

        def capture(engine, text, **kwargs):
            seen["text"] = text
            return fake_step(engine, text)

        with patch("training.views.step", side_effect=capture):
            self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": "제 주민번호는 900101-1234567입니다"},
                content_type="application/json",
            )

        self.assertNotIn("900101-1234567", seen["text"])
        self.assertIn("[주민등록번호]", seen["text"])
        stored = Session.objects.get(pk=session_id).turns.filter(role="user").first()
        self.assertNotIn("900101-1234567", stored.text)

    def test_masking_keeps_the_behaviour_visible_to_the_judge(self):
        """값은 지우되 '개인정보를 말했다'는 사실은 남겨야 판정기가 잡는다."""
        session_id = self.start_training()
        seen = {}

        def capture(engine, text, **kwargs):
            seen["text"] = text
            return fake_step(engine, text)

        with patch("training.views.step", side_effect=capture):
            self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": "계좌는 110-234-567890 입니다"},
                content_type="application/json",
            )

        self.assertIn("[계좌번호]", seen["text"])

    def test_warns_immediately_on_pii(self):
        session_id = self.start_training()

        payload = self.turn(session_id, "제 주민번호는 900101-1234567입니다").json()

        self.assertEqual(
            payload["riskWarnings"][0]["type"], "personalInfo"
        )
        self.assertIn("주민등록번호", payload["riskWarnings"][0]["message"])

    def test_warns_on_judge_detected_risky_action(self):
        session_id = self.start_training()

        payload = self.turn(
            session_id, "네 앱 설치할게요", risky_actions=["app_install"]
        ).json()

        self.assertEqual(payload["riskWarnings"][0]["type"], "appInstall")
        self.assertEqual(
            Session.objects.get(pk=session_id).risky_actions.count(), 1
        )

    def test_warns_about_each_kind_of_personal_info(self):
        """주민번호와 계좌번호는 알려줄 내용이 달라 둘 다 나가야 한다."""
        session_id = self.start_training()

        payload = self.turn(
            session_id,
            "주민번호 900101-1234567 이고 계좌는 110-234-567890 입니다",
            risky_actions=["personal_info"],
        ).json()

        messages = " / ".join(w["message"] for w in payload["riskWarnings"])
        self.assertIn("주민등록번호", messages)
        self.assertIn("계좌번호", messages)

    def test_judge_does_not_repeat_what_the_regex_already_said(self):
        """정규식이 종류까지 특정했으면 판정기의 포괄적 personal_info 는 생략한다."""
        session_id = self.start_training()

        payload = self.turn(
            session_id,
            "주민번호 900101-1234567 입니다",
            risky_actions=["personal_info"],
        ).json()

        self.assertEqual(len(payload["riskWarnings"]), 1)
        self.assertIn("주민등록번호", payload["riskWarnings"][0]["message"])

    def test_does_not_repeat_an_identical_signal(self):
        session_id = self.start_training()

        payload = self.turn(
            session_id,
            "네 설치할게요",
            risky_actions=["app_install", "app_install"],
        ).json()

        self.assertEqual(len(payload["riskWarnings"]), 1)

    def test_another_anonymous_client_gets_404(self):
        session_id = self.start_training()
        other = Client()
        other.get("/api/v1/bootstrap")

        response = other.post(
            f"/api/v1/training-sessions/{session_id}/turns",
            data={"text": "안녕하세요"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "SESSION_NOT_FOUND")

    def test_ended_session_is_rejected(self):
        session_id = self.start_training()
        Session.objects.filter(pk=session_id).update(status="ended")

        response = self.turn(session_id, "안녕하세요")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "SESSION_ENDED")

    def test_input_longer_than_limit_is_rejected(self):
        session_id = self.start_training()

        response = self.turn(session_id, "가" * 201)

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "INPUT_TOO_LARGE")

    def test_empty_input_is_rejected(self):
        session_id = self.start_training()

        response = self.turn(session_id, "   ")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "EMPTY_INPUT")

    def test_session_ends_at_max_turns(self):
        session_id = self.start_training()
        session = Session.objects.get(pk=session_id)
        Session.objects.filter(pk=session_id).update(
            turn=session.scenario.max_turns - 1
        )

        payload = self.turn(session_id, "네").json()

        self.assertTrue(payload["ended"])
        self.assertIn("최대 턴", payload["endReason"])
        session.refresh_from_db()
        self.assertEqual(session.status, "ended")
        self.assertIsNotNone(session.ended_at)

    def test_unknown_session_id_is_404(self):
        self.client.get("/api/v1/bootstrap")

        response = self.turn("11111111-1111-1111-1111-111111111111", "안녕")

        self.assertEqual(response.status_code, 404)


class GradingTests(TestCase):
    """Step 10. 채점 - DB 도 LLM 도 타지 않는 순수 함수."""

    def make(self, scenario_id, judged_turn, is_scam_guess, risky=(), resistance=0):
        scenario = load_scenario(scenario_id)
        state = start_session(scenario).state
        state.turn = judged_turn
        state.resistance_count = resistance
        state.risky_actions = [EngineRiskyAction(turn=judged_turn, type=r) for r in risky]
        state.user_judgment = EngineJudgment(turn=judged_turn, is_scam_guess=is_scam_guess)
        return scenario, state

    def test_immediate_detection_is_S(self):
        scenario, state = self.make("sc-02", judged_turn=1, is_scam_guess=True)

        result = grade(scenario, state)

        self.assertEqual(result.grade, "S")
        self.assertEqual(result.delta, 0)

    def test_early_detection_is_A(self):
        scenario, state = self.make("sc-02", judged_turn=4, is_scam_guess=True)

        self.assertEqual(grade(scenario, state).grade, "A")

    def test_minor_risky_action_drops_to_B(self):
        scenario, state = self.make(
            "sc-02", judged_turn=2, is_scam_guess=True, risky=["link_click"]
        )

        self.assertEqual(grade(scenario, state).grade, "B")

    def test_critical_risky_action_is_C(self):
        scenario, state = self.make(
            "sc-02", judged_turn=2, is_scam_guess=True, risky=["transfer_consent"]
        )

        result = grade(scenario, state)
        self.assertEqual(result.grade, "C")
        self.assertTrue(result.has_critical_action)

    def test_never_recognising_the_scam_is_D(self):
        scenario, state = self.make("sc-02", judged_turn=20, is_scam_guess=False)

        result = grade(scenario, state)
        self.assertEqual(result.grade, "D")
        self.assertFalse(result.is_correct)

    def test_reporting_a_normal_scenario_is_false_alarm(self):
        """F-21. 정상 시나리오를 사기로 신고하면 오탐."""
        scenario, state = self.make("nm-01", judged_turn=3, is_scam_guess=True)

        result = grade(scenario, state)
        self.assertEqual(result.grade, "오탐")
        self.assertFalse(result.is_correct)

    def test_correctly_trusting_a_normal_scenario_is_S(self):
        scenario, state = self.make("nm-01", judged_turn=8, is_scam_guess=False)

        result = grade(scenario, state)
        self.assertEqual(result.grade, "S")
        self.assertTrue(result.is_correct)

    def test_first_detectable_turn_uses_matching_signal_type(self):
        """사기는 risk 신호, 정상은 legitimacy 신호를 기준으로 삼는다."""
        self.assertEqual(first_detectable_turn(load_scenario("sc-02")), 1)
        self.assertEqual(first_detectable_turn(load_scenario("nm-01")), 1)

    def test_missed_tell_points_stop_at_the_judgment_turn(self):
        scenario, state = self.make("sc-02", judged_turn=3, is_scam_guess=True)

        missed = grade(scenario, state).missed_tell_points

        turns = {tp.id: tp.first_detectable_turn for tp in scenario.tell_points}
        self.assertTrue(all(turns[tp] < 3 for tp in missed))
        self.assertIn("tp1", missed)
        self.assertNotIn("tp5", missed)

    def test_immediate_detection_missed_nothing(self):
        """S 등급인데 리포트가 '신호를 지나쳤다'고 말하면 안 된다."""
        scenario, state = self.make("sc-02", judged_turn=1, is_scam_guess=True)

        result = grade(scenario, state)

        self.assertEqual(result.grade, "S")
        self.assertEqual(result.missed_tell_points, [])

    def test_late_detection_still_lists_missed_tell_points(self):
        scenario, state = self.make("sc-02", judged_turn=10, is_scam_guess=True)

        self.assertIn("tp1", grade(scenario, state).missed_tell_points)


class SubmitJudgmentTests(TestCase):
    """Step 10. 판단 제출 = 종료 + 채점 + 진단 + 원문 파기."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def start_training(self, track="T01-1"):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": track},
            content_type="application/json",
        )
        return self.client.post("/api/v1/training-sessions").json()["sessionId"]

    def judge(self, session_id, is_scam_guess=True):
        return self.client.post(
            f"/api/v1/training-sessions/{session_id}/judgment",
            data={"isScamGuess": is_scam_guess},
            content_type="application/json",
        )

    def delay_judgment_to_turn(self, session_id, turn):
        """LLM 없이 판단 시점만 뒤로 민다.

        채점은 session.turn 을 판단 턴으로 삼는다. 시작 직후(1턴)에 제출하면
        최초 판별 가능 시점과 같아 '지나친 단서 없음'이 되므로, 놓친 단서가
        실리는 경로를 보려면 턴이 진행된 상태를 만들어야 한다.
        """
        Session.objects.filter(pk=session_id).update(turn=turn)

    def test_returns_a_complete_report(self):
        session_id = self.start_training()

        payload = self.judge(session_id).json()

        self.assertEqual(
            set(payload),
            {"grade", "isCorrect", "judgedTurn", "firstDetectableTurn", "summary",
             "strength", "weakness", "missedTellPoints", "riskyActions",
             "guidance", "timeline"},
        )
        self.assertTrue(payload["summary"])
        self.assertTrue(payload["guidance"])

    def test_always_includes_a_strength(self):
        """리포트 문서 §8: 잘한 점을 반드시 1개 이상 포함한다."""
        session_id = self.start_training()

        self.assertTrue(self.judge(session_id).json()["strength"])

    def test_missed_tell_points_carry_their_explanation(self):
        """설명은 시나리오의 why 를 그대로 쓴다 - LLM 생성이 필요 없다."""
        session_id = self.start_training()
        self.delay_judgment_to_turn(session_id, 10)

        missed = self.judge(session_id).json()["missedTellPoints"]

        self.assertTrue(missed)
        self.assertEqual(set(missed[0]), {"id", "turn", "trigger", "why", "weight"})

    def test_ends_the_session(self):
        session_id = self.start_training()

        self.judge(session_id)

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.status, "ended")
        self.assertIsNotNone(session.ended_at)

    def test_discards_the_transcript(self):
        """기획서 10절: 대화는 세션 종료 시 파기."""
        session_id = self.start_training()
        self.assertTrue(Session.objects.get(pk=session_id).turns.first().text)

        self.judge(session_id)

        texts = Session.objects.get(pk=session_id).turns.values_list("text", flat=True)
        self.assertEqual(set(texts), {""})

    def test_keeps_turn_rows_for_the_timeline(self):
        """원문만 지우고 턴 번호·화자·단계는 남긴다."""
        session_id = self.start_training()

        self.judge(session_id)

        turns = Session.objects.get(pk=session_id).turns.all()
        self.assertTrue(turns.exists())
        self.assertTrue(all(t.turn_no and t.role and t.stage_id for t in turns))

    def test_persists_grade_and_report(self):
        session_id = self.start_training()
        self.delay_judgment_to_turn(session_id, 10)

        payload = self.judge(session_id).json()

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.judgment.grade, payload["grade"])
        self.assertEqual(session.diagnosis.summary, payload["summary"])
        self.assertTrue(session.diagnosis.missed_tell_points)

    def test_second_judgment_is_rejected(self):
        session_id = self.start_training()
        self.judge(session_id)

        response = self.judge(session_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ALREADY_JUDGED")

    def test_another_anonymous_client_gets_404(self):
        session_id = self.start_training()
        other = Client()
        other.get("/api/v1/bootstrap")

        response = other.post(
            f"/api/v1/training-sessions/{session_id}/judgment",
            data={"isScamGuess": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_missing_judgment_field_is_rejected(self):
        session_id = self.start_training()

        response = self.client.post(
            f"/api/v1/training-sessions/{session_id}/judgment",
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_JUDGMENT")


def fake_streaming_step(engine, user_text, on_delta=None, risky_actions=(), **kwargs):
    """문장 단위로 on_delta 를 부르는 fake. 실제 StreamingSafetyGate 와 같은 모양."""
    scenario, state = engine.scenario, engine.state

    state.turn += 1
    record_turn(state, "user", user_text, current_stage(scenario, state).id)
    apply_judgment(state, list(risky_actions), resisted=False)
    try_advance_stage(scenario, state, proposed=False)

    sentences = ["첫 번째 문장입니다.", "두 번째 문장입니다."]
    for sentence in sentences:
        if on_delta:
            on_delta(sentence)

    full = "".join(sentences)
    state.turn += 1
    state.turns_in_stage += 1
    record_turn(state, "scammer", full, current_stage(scenario, state).id, 12)
    mark_tell_points(scenario, state)

    return TurnOutcome(
        scammer_text=full, latency_ms=12, first_token_ms=5, stage_changed=None,
        ended=False, risky_actions=list(risky_actions),
    )


def drain(response):
    """스트리밍 본문을 문자열로 모은다.

    뷰가 async 생성기를 넘기므로(ASGI 에서 실제로 문장 단위 전송이 되려면 필수)
    streaming_content 는 async 이터레이터다. 동기 테스트에서 읽으려면 루프를 돌려야 한다.

    생성기 안의 sync_to_async(_commit_turn) 는 별도 스레드·별도 커넥션에서 돈다.
    그래서 이 테스트들은 TransactionTestCase 여야 한다 - TestCase 의 롤백 트랜잭션은
    커밋되지 않아 그 커넥션에서 세션이 아예 보이지 않는다.
    """
    if response.is_async:
        async def collect():
            return b"".join([chunk async for chunk in response.streaming_content])
        return asyncio.run(collect()).decode("utf-8")
    return b"".join(response.streaming_content).decode("utf-8")


def parse_sse(body):
    """SSE 본문을 [(event, data), ...] 로 푼다."""
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((name, data))
    return events


class TurnStreamTests(TransactionTestCase):
    """Step 9b. SSE 턴 처리.

    TestCase 가 아니라 TransactionTestCase 다. 뷰가 async 생성기를 쓰고 그 안의
    저장이 별도 스레드에서 일어나므로, 롤백 트랜잭션 안에 갇힌 데이터는 그 스레드에
    보이지 않는다. 대신 매 테스트마다 시드를 다시 넣는다.
    """

    def setUp(self):
        call_command("seed_scenarios", verbosity=0)

    def start_training(self):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )
        return self.client.post("/api/v1/training-sessions").json()["sessionId"]

    def stream(self, session_id, text, risky_actions=()):
        with patch(
            "training.views.step",
            side_effect=lambda e, t, on_delta=None, **kw: fake_streaming_step(
                e, t, on_delta=on_delta, risky_actions=risky_actions
            ),
        ):
            response = self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns/stream",
                data={"text": text},
                content_type="application/json",
            )
            body = drain(response)
        return response, parse_sse(body)

    def test_streams_sentences_then_done(self):
        session_id = self.start_training()

        response, events = self.stream(session_id, "저 그런 적 없는데요")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream; charset=utf-8")
        names = [name for name, _ in events]
        self.assertEqual(names[0], "accepted")
        self.assertEqual(names[-1], "done")
        deltas = [data["text"] for name, data in events if name == "delta"]
        self.assertEqual(deltas, ["첫 번째 문장입니다.", "두 번째 문장입니다."])

    def test_done_carries_the_full_approved_text(self):
        session_id = self.start_training()

        _, events = self.stream(session_id, "네")

        done = dict(events)["done"]
        self.assertEqual(done["text"], "첫 번째 문장입니다.두 번째 문장입니다.")
        self.assertFalse(done["ended"])

    def test_disables_proxy_buffering(self):
        """Railway 프록시가 모아두면 스트리밍 이점이 사라진다."""
        session_id = self.start_training()

        response, _ = self.stream(session_id, "네")

        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_pii_warning_arrives_before_any_delta(self):
        """정규식으로 잡은 개인정보는 LLM 을 기다리지 않는다."""
        session_id = self.start_training()

        _, events = self.stream(session_id, "제 주민번호는 900101-1234567입니다")

        names = [name for name, _ in events]
        self.assertLess(names.index("riskWarning"), names.index("delta"))

    def test_judge_warning_arrives_after_the_stream(self):
        session_id = self.start_training()

        _, events = self.stream(session_id, "설치할게요", risky_actions=["app_install"])

        names = [name for name, _ in events]
        self.assertGreater(names.index("riskWarning"), names.index("delta"))
        warning = next(d for n, d in events if n == "riskWarning")
        self.assertEqual(warning["type"], "appInstall")

    def test_persists_the_turn(self):
        session_id = self.start_training()

        self.stream(session_id, "저 그런 적 없는데요")

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.turns.count(), 3)
        self.assertEqual(session.turns.filter(role="user").first().text, "저 그런 적 없는데요")

    def test_masks_pii_before_persisting(self):
        session_id = self.start_training()

        self.stream(session_id, "계좌는 110-234-567890 입니다")

        stored = Session.objects.get(pk=session_id).turns.filter(role="user").first()
        self.assertNotIn("110-234-567890", stored.text)

    def test_another_anonymous_client_gets_404(self):
        session_id = self.start_training()
        other = Client()
        other.get("/api/v1/bootstrap")

        response = other.post(
            f"/api/v1/training-sessions/{session_id}/turns/stream",
            data={"text": "안녕"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_model_failure_becomes_an_error_event(self):
        session_id = self.start_training()

        with patch("training.views.step", side_effect=RuntimeError("모델 오류")):
            response = self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns/stream",
                data={"text": "안녕"},
                content_type="application/json",
            )
            events = parse_sse(drain(response))

        self.assertEqual(events[-1][0], "error")
        self.assertEqual(events[-1][1]["code"], "AI_ERROR")
        self.assertEqual(Session.objects.get(pk=session_id).turns.count(), 1)

    def test_stale_turn_is_rejected_by_the_optimistic_lock(self):
        """스트리밍 도중 다른 턴이 먼저 저장되면 이 턴은 포기한다.

        스레드를 띄우면 Django 테스트 트랜잭션 밖의 커넥션이 생겨 검증이 어렵다.
        가드 자체는 _commit_turn 을 직접 불러 확인한다.
        """
        session_id = self.start_training()
        session = Session.objects.get(pk=session_id)
        scenario = load_scenario(session.scenario_id)
        state = load_state(session)
        outcome = fake_streaming_step(Engine(scenario=scenario, state=state), "안녕")

        with self.assertRaises(ConcurrentTurnError):
            _commit_turn(
                session_id,
                self.client.session[ANON_CLIENT_ID_KEY],
                session.turn - 1,  # 이미 움직인 뒤라 가정
                state,
                outcome,
            )

        self.assertEqual(Session.objects.get(pk=session_id).turns.count(), 1)


class SeedScenariosTests(TestCase):
    """시나리오 적재는 기동할 때마다 돌아도 안전해야 한다.

    Dockerfile CMD 가 컨테이너를 띄울 때마다 seed_scenarios 를 부른다. 진행됐던
    세션이 남아 있는 배포 DB 에서도 실패하지 않아야 재배포가 막히지 않는다.
    """

    CARD_ID = "sc-02"

    def counts(self):
        return (
            Scenario.objects.count(),
            Stage.objects.count(),
            TellPoint.objects.count(),
        )

    def seed(self, directory=None):
        args = ["seed_scenarios"]
        kwargs = {"verbosity": 0}
        if directory:
            kwargs["directory"] = str(directory)
        call_command(*args, **kwargs)

    def write_card(self, directory, mutate):
        """실제 카드 하나를 임시 디렉터리에 복사하면서 mutate 로 고친다."""
        source = Path(settings.SCENARIO_SEED_DIR) / f"{self.CARD_ID}.json"
        card = json.loads(source.read_text(encoding="utf-8"))
        mutate(card)
        (Path(directory) / f"{self.CARD_ID}.json").write_text(
            json.dumps(card, ensure_ascii=False), encoding="utf-8"
        )

    def test_reseeding_does_not_duplicate_rows(self):
        self.seed()
        first = self.counts()

        self.seed()

        self.assertEqual(self.counts(), first)

    def test_reseeding_survives_a_session_that_already_used_a_stage(self):
        """Turn.stage 가 PROTECT 라 예전 구현은 여기서 ProtectedError 로 죽었다."""
        self.seed()
        scenario = load_scenario(self.CARD_ID)
        engine = start_session(scenario, difficulty="normal")
        session = Session.objects.create(
            session_id=engine.state.session_id,
            scenario_id=self.CARD_ID,
            anon_client_id="anon-test",
            entry_path="direct",
            status="active",
            difficulty=engine.state.difficulty,
        )
        save_state(session, engine.state)
        self.assertEqual(session.turns.count(), 1)

        self.seed()  # 재배포 시점

        self.assertEqual(Session.objects.get(pk=session.pk).turns.count(), 1)
        self.assertTrue(Stage.objects.filter(scenario_id=self.CARD_ID).exists())

    def test_reseeding_applies_edited_card_content(self):
        self.seed()

        with tempfile.TemporaryDirectory() as directory:
            self.write_card(
                directory, lambda card: card["stages"][0].update(objective="바뀐 목표")
            )
            self.seed(directory)

        stage = Stage.objects.get(scenario_id=self.CARD_ID, order_index=0)
        self.assertEqual(stage.objective, "바뀐 목표")

    def test_stage_removed_from_the_card_is_deleted(self):
        self.seed()

        dropped = {}

        with tempfile.TemporaryDirectory() as directory:
            def drop_last_stage(card):
                key = card["stages"].pop()["id"]
                card["tell_points"] = [
                    tp for tp in card["tell_points"] if tp["stage"] != key
                ]
                dropped["key"] = key

            self.write_card(directory, drop_last_stage)
            self.seed(directory)

        self.assertFalse(
            Stage.objects.filter(
                scenario_id=self.CARD_ID, stage_key=dropped["key"]
            ).exists()
        )
        self.assertFalse(
            TellPoint.objects.filter(scenario_id=self.CARD_ID, tp_key="tp6").exists()
        )


class ApiErrorContractTests(TestCase):
    """API 하위의 오류는 항상 JSON 계약을 지킨다.

    기본 404 는 HTML 이라 프론트 client.js 의 res.json() 이 깨지고, 경로 오타든
    엔드포인트 누락이든 전부 code "UNKNOWN" 으로 뭉개진다.
    """

    def test_unknown_api_path_returns_json(self):
        response = self.client.get("/api/v1/there-is-no-such-endpoint")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_llm_config_failure_still_returns_json(self):
        """LLM 설정이 깨져 있어도 프론트가 읽을 수 있는 응답이어야 한다.

        ai_core.llm 은 예전에 import 시점에 sys.exit(1) 을 불러 워커째 죽었다.
        이제는 호출 시점에 ConfigError 가 나고, API 는 JSON 계약을 지킨다.
        """
        call_command("seed_scenarios", verbosity=0)
        client = Client(raise_request_exception=False)
        client.get("/api/v1/bootstrap")
        client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )
        session_id = client.post("/api/v1/training-sessions").json()["sessionId"]

        with patch("training.views.step", side_effect=ConfigError("키 없음")):
            response = client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": "여보세요"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["error"]["code"], "INTERNAL_ERROR")

    def test_api_error_carries_a_request_id(self):
        """응답의 requestId 를 서버 로그와 맞춰볼 수 있어야 한다."""
        response = self.client.get("/api/v1/there-is-no-such-endpoint")

        self.assertTrue(response.json()["error"]["requestId"].startswith("req_"))

    @skipUnless(settings.FRONTEND_DIST.exists(), "프론트 빌드 결과물이 있어야 확인 가능")
    def test_unknown_page_path_still_renders_the_spa(self):
        """SPA 라우트는 404 가 아니라 index.html 이어야 한다 (딥링크·새로고침).

        handler404 를 붙이면서 SPA 폴백까지 JSON 으로 덮지 않았는지 확인한다.
        """
        response = self.client.get("/report")

        self.assertEqual(response.status_code, 200)


class TurnThrottleTests(TestCase):
    """API 설계 9절 - 레이트 리밋, 4-6 - Idempotency-Key."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def setUp(self):
        cache.clear()

    def start_training(self):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )
        return self.client.post("/api/v1/training-sessions").json()["sessionId"]

    def turn(self, session_id, text="안녕하세요", headers=None):
        with patch(
            "training.views.step",
            side_effect=lambda e, t, **kw: fake_step(e, t),
        ):
            return self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": text},
                content_type="application/json",
                headers=headers or {},
            )

    def test_allows_requests_under_the_limit(self):
        """한도 안에서는 429 가 나오지 않는다.

        200 을 기대하지 않는 이유: fake_step 이 턴을 2씩 올려서 20회를 돌리면
        중간에 max_turns 에 닿아 SESSION_ENDED(409)가 난다. 여기서 확인할 것은
        레이트 리밋이 걸리지 않는다는 것뿐이다.
        """
        session_id = self.start_training()

        codes = [self.turn(session_id).status_code for _ in range(TURN_RATE_LIMIT)]

        self.assertNotIn(429, codes)

    def test_rejects_requests_over_the_limit(self):
        session_id = self.start_training()
        for _ in range(TURN_RATE_LIMIT):
            self.turn(session_id)

        response = self.turn(session_id)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "RATE_LIMITED")

    def test_rate_limit_tells_the_client_when_to_retry(self):
        session_id = self.start_training()
        for _ in range(TURN_RATE_LIMIT):
            self.turn(session_id)

        response = self.turn(session_id)

        self.assertEqual(response["Retry-After"], str(TURN_RATE_WINDOW_SECONDS))

    def test_limit_is_per_anonymous_client(self):
        """다른 사용자가 앞사람의 한도에 걸리면 안 된다."""
        session_id = self.start_training()
        for _ in range(TURN_RATE_LIMIT + 1):
            self.turn(session_id)

        other = Client()
        other.get("/api/v1/bootstrap")
        other.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )

        self.assertEqual(other.post("/api/v1/training-sessions").status_code, 201)

    def test_retry_with_same_idempotency_key_does_not_advance_the_turn(self):
        session_id = self.start_training()
        headers = {"Idempotency-Key": "abc-123"}

        first = self.turn(session_id, headers=headers).json()
        second = self.turn(session_id, headers=headers).json()

        self.assertEqual(first, second)
        # opening + user + scammer. 두 번째 요청이 턴을 진행시켰다면 5건이 된다.
        self.assertEqual(Session.objects.get(pk=session_id).turns.count(), 3)

    def test_different_idempotency_key_advances_the_turn(self):
        session_id = self.start_training()

        self.turn(session_id, headers={"Idempotency-Key": "key-1"})
        self.turn(session_id, headers={"Idempotency-Key": "key-2"})

        self.assertEqual(Session.objects.get(pk=session_id).turns.count(), 5)

    def test_without_the_header_each_request_is_a_new_turn(self):
        session_id = self.start_training()

        self.turn(session_id)
        self.turn(session_id)

        self.assertEqual(Session.objects.get(pk=session_id).turns.count(), 5)


class TurnTimeoutTests(TestCase):
    """API 설계 9절 - 턴 처리 제한 시간."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_scenarios", verbosity=0)

    def setUp(self):
        cache.clear()

    def start_training(self):
        self.client.get("/api/v1/bootstrap")
        self.client.post(
            "/api/v1/user-info",
            data={"category": "voice", "trackId": "T01-1"},
            content_type="application/json",
        )
        return self.client.post("/api/v1/training-sessions").json()["sessionId"]

    def test_slow_model_becomes_a_timeout(self):
        session_id = self.start_training()

        def never_returns(engine, user_text, **kwargs):
            time.sleep(5)

        with patch("training.views.TURN_TIMEOUT_SECONDS", 0.2):
            with patch("training.views.step", side_effect=never_returns):
                response = self.client.post(
                    f"/api/v1/training-sessions/{session_id}/turns",
                    data={"text": "안녕하세요"},
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["error"]["code"], "AI_TIMEOUT")

    def test_timeout_does_not_advance_the_session(self):
        session_id = self.start_training()

        def never_returns(engine, user_text, **kwargs):
            time.sleep(5)

        with patch("training.views.TURN_TIMEOUT_SECONDS", 0.2):
            with patch("training.views.step", side_effect=never_returns):
                self.client.post(
                    f"/api/v1/training-sessions/{session_id}/turns",
                    data={"text": "안녕하세요"},
                    content_type="application/json",
                )

        session = Session.objects.get(pk=session_id)
        self.assertEqual(session.turn, 1)
        self.assertEqual(session.turns.count(), 1)

    def test_model_failure_becomes_a_502(self):
        session_id = self.start_training()

        with patch("training.views.step", side_effect=RuntimeError("모델 오류")):
            response = self.client.post(
                f"/api/v1/training-sessions/{session_id}/turns",
                data={"text": "안녕하세요"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "AI_ERROR")
