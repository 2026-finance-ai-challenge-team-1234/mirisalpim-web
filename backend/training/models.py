from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
import uuid

#: 연령 트랙. 시나리오 하나가 여러 트랙에 제공될 수 있어 Scenario.target_tracks 는 배열이다.
#: (구 Scenario.track 은 이제 scenario.md 분류 코드를 담는다 — 의미가 다르다)
TARGET_TRACK_CHOICES = [
    ("teen", "청소년"),
    ("young", "청년"),
    ("middle_age", "중장년"),
    ("senior", "노년"),
]
TARGET_TRACK_VALUES = {value for value, _ in TARGET_TRACK_CHOICES}

#: scenario.md 의 시나리오 분류 코드. T=보이스피싱 S=스미싱, 대분류 2자리 + 세부번호
track_code_validator = RegexValidator(
    r"^[TS]\d{2}-\d{1,2}$", "scenario.md 의 분류 코드여야 합니다 (예: T01-5)"
)


def validate_target_tracks(value):
    if not isinstance(value, list) or not value:
        raise ValidationError("target_tracks 는 비어 있지 않은 배열이어야 합니다")
    bad = [v for v in value if v not in TARGET_TRACK_VALUES]
    if bad:
        raise ValidationError(f"허용되지 않는 연령 트랙: {bad}")


class Scenario(models.Model):
    CATEGORY_CHOICES = [
        ("voice", "보이스피싱"),
        ("smishing", "스미싱"),
        ("phishing", "피싱"),
    ]

    REVIEW_STATUS_CHOICES = [
        ("human_reviewed", "사람 검수됨"),
        ("auto_labeled", "자동 라벨 기반"),
    ]

    scenario_id = models.CharField(max_length=100, primary_key=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    #: 전달 채널이 아니라 사기 유형 분류 코드 (T01-5 등). 시나리오 추천이 이 값을 쓴다
    track = models.CharField(max_length=10, validators=[track_code_validator])
    #: 이 시나리오를 제공할 연령 트랙들
    target_tracks = models.JSONField(default=list, validators=[validate_target_tracks])
    title = models.CharField(max_length=200)
    #: 마지막 훈련 결과 리포트에 표시할 짧은 출처명. 분석 메모나 내부 경로는 넣지 않는다
    source = models.TextField()
    #: 결과 리포트의 공식 자료 링크. 공식 HTTPS URL 문자열 1~2개만 저장한다
    source_refs = models.JSONField(default=list, blank=True)
    #: 출처 검수 상태이며 내부 관리용이다. 결과 리포트에는 노출하지 않는다
    source_review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS_CHOICES, default="human_reviewed"
    )
    is_scam = models.BooleanField(default=True)
    difficulty = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    #: 상대 역할이 달성하려는 최종 목적(문장). 평가 항목은 learning_objectives 에 둔다
    goal = models.TextField()
    learning_objectives = models.JSONField(default=list, blank=True)
    max_turns = models.PositiveSmallIntegerField(default=20)
    persona_display_name = models.CharField(max_length=100)
    persona_name = models.CharField(max_length=100, blank=True)
    #: 자녀 사칭·신변 위협형은 사칭할 기관이 없다
    persona_org = models.CharField(max_length=200, blank=True)
    persona_role = models.CharField(max_length=100, blank=True)
    persona_tone = models.TextField()
    persona_rules = models.JSONField(default=list, blank=True)
    persona_resistance_strategy = models.JSONField(default=list, blank=True)
    persona_voice_preset = models.CharField(max_length=50)
    forbidden = models.JSONField(default=list)
    #: 종료 조건. 판정기가 충족을 제안하고 최종 승인은 코드가 한다
    end_conditions = models.JSONField(default=list, blank=True)
    debrief_points = models.JSONField(default=list, blank=True)

    @property
    def track_group(self):
        """추천 가중치가 집계되는 대분류 (T01-5 → T01)."""
        return self.track.split("-")[0]

    def __str__(self):
        return f"[{self.track}] {self.title}"

class Stage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="stages")
    stage_key = models.CharField(max_length=50)
    order_index = models.PositiveSmallIntegerField()
    objective = models.TextField()
    opening = models.TextField(null=True, blank=True)
    min_turns = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    tactics = models.JSONField(default=list)
    #: 판정기가 advance_stage 를 제안할 때 보는 기준 (ai_core.prompts.advance_criteria_block)
    advance_when = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("scenario", "stage_key")]
        ordering = ["scenario", "order_index"]

class TellPoint(models.Model):
    SIGNAL_TYPE = [
        ("risk", "위험 신호"),
        ("legitimacy", "정상 신호"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="tell_points")
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="tell_points")
    tp_key = models.CharField(max_length=20)
    signal_type = models.CharField(max_length=12, choices=SIGNAL_TYPE, default="risk")
    trigger = models.TextField()
    why = models.TextField()
    #: 판별 결정력 1=약한 보조 신호 3=결정적 신호
    weight = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    first_detectable_turn = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = [("scenario", "tp_key")]

class Session(models.Model):
    ENTRY_PATH = [
        ("recommended", "AI 추천"),
        ("direct", "직접 선택")
    ]

    STATUS = [
        ("active", "진행 중"),
        ("ended", "종료")
    ]

    #: scenario.md §4·§5 — 난이도는 카테고리와 독립된 축이고 Q4(대응 습관)로 정해진다.
    #: 시나리오가 아니라 세션이 갖는다 (같은 시나리오를 난이도만 바꿔 진행한다)
    DIFFICULTY = [
        ("easy", "쉬움"),
        ("normal", "보통"),
        ("hard", "어려움"),
    ]

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT, related_name="sessions")
    anon_client_id = models.CharField(max_length=100)
    entry_path = models.CharField(max_length=20, choices=ENTRY_PATH)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY, default="normal")
    #: ai_core.SessionState 에는 있지만 다른 테이블에서 복원할 수 없는 두 값.
    #: turns_in_stage 는 min_turns 게이트가, resistance_count 는 사기꾼 프롬프트가 쓴다.
    turns_in_stage = models.PositiveSmallIntegerField(default=0)
    resistance_count = models.PositiveSmallIntegerField(default=0)
    turn = models.PositiveSmallIntegerField(default=0)
    current_stage = models.ForeignKey(Stage, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")    
    status = models.CharField(max_length=10, choices=STATUS)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

class Turn(models.Model):
    ROLE =[
        ("scammer", "사기범"),
        ("user", "훈련생")
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="turns")
    turn_no = models.PositiveSmallIntegerField()
    role = models.CharField(max_length=10, choices=ROLE)
    text = models.TextField()
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT, related_name="+")
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class RiskyAction(models.Model):
    ACTION_TYPE = [
        ("personal_info", "개인정보제공"),
        ("link_click", "링크클릭"),
        ("app_install", "앱설치동의"),
        ("transfer_consent", "송금동의"),
        ("isolation_accepted", "고립수용"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="risky_actions")
    turn_no = models.PositiveSmallIntegerField()
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE)
    created_at = models.DateTimeField(auto_now_add=True)

class SessionTellPointHit(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="tell_point_hits")
    tell_point = models.ForeignKey(TellPoint, on_delete=models.CASCADE, related_name="+")
    hit_turn = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = [("session", "tell_point")]

class UserJudgment(models.Model):
    GRADE = [
        ("S", "S"),
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
        ("오탐", "오탐")
    ]
    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True, related_name="judgment")
    judged_turn = models.PositiveSmallIntegerField(null=True, blank=True)
    is_scam_guess = models.BooleanField()
    grade = models.CharField(max_length=4, choices=GRADE)
    created_at = models.DateTimeField(auto_now_add=True)

class DiagnosisReport(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True, related_name="diagnosis")
    #: Cialdini 5유형으로 고정할지 자유 문구로 둘지 팀 미확정이라 아직 비워둘 수 있게 한다
    vulnerability_type = models.CharField(max_length=30, blank=True)
    #: tp_key 스냅샷. 종료 후 원문을 지워도 타임라인을 다시 그릴 수 있게 남긴다
    missed_tell_points = models.JSONField(default=list)
    guidance_text = models.TextField()
    #: 리포트 문서 §4 진단 LLM 출력 3종. LLM 없이도 규칙 기반 문장으로 채운다
    summary = models.TextField(blank=True)
    strength = models.TextField(blank=True)
    weakness = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class EvalResult(models.Model):
    PHASE = [
        ("pre", "사전"),
        ("post", "사후")
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anon_client_id = models.CharField(max_length=100)
    phase = models.CharField(max_length=4, choices=PHASE)
    score = models.PositiveSmallIntegerField()
    total_questions = models.PositiveSmallIntegerField()
    taken_at = models.DateTimeField(auto_now_add=True)
