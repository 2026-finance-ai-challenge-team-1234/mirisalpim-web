from django.db import models
from pgvector.django import VectorField
import uuid

class Scenario(models.Model):
    CATEGORY_CHOICES = [
        ("voice", "보이스피싱"),
        ("smishing", "스미싱"),
        ("phishing", "피싱"),
    ]

    TRACK_CHOICES = [
        ("teen", "청소년"),
        ("young", "청년"),
        ("parent", "중장년"),
        ("senior", "노년"),
    ]

    scenario_id = models.CharField(max_length=100, primary_key=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    track = models.CharField(max_length=20, choices=TRACK_CHOICES)
    title = models.CharField(max_length=200)
    source = models.TextField()
    is_scam = models.BooleanField(default=True)
    difficulty = models.PositiveSmallIntegerField()
    goal = models.TextField()
    max_turns = models.PositiveSmallIntegerField(default=20)
    persona_name = models.CharField(max_length=100)
    persona_org = models.CharField(max_length=200)
    persona_tone = models.TextField()
    persona_voice_preset = models.CharField(max_length=50)
    forbidden = models.JSONField(default=list)

class Stage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="stages")
    stage_key = models.CharField(max_length=50)
    order_index = models.PositiveSmallIntegerField()
    objective = models.TextField()
    opening = models.TextField(null=True, blank=True)
    min_turns = models.PositiveSmallIntegerField(default=1)
    tactics = models.JSONField(default=list)

    class Meta:
        unique_together = [("scenario", "stage_key")]

class TellPoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="tell_points")
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="tell_points")
    tp_key = models.CharField(max_length=20)
    trigger = models.TextField()
    why = models.TextField()
    weight = models.PositiveSmallIntegerField()
    first_detectable_turn = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = [("scenario", "tp_key")]

class Utterance(models.Model):
    utterance_id = models.CharField(max_length=100, primary_key=True)
    text = models.TextField()
    category = models.CharField(max_length=20)
    scam_type = models.CharField(max_length=100)
    stage = models.CharField(max_length=50)
    tactic = models.CharField(max_length=100)
    context = models.TextField(blank=True)
    source = models.CharField(max_length=200)
    embedding = VectorField(dimensions=1536)

class Session(models.Model):
    ENTRY_PATH = [
        ("recommended", "AI 추천"),
        ("direct", "직접 선택")
    ]

    STATUS = [
        ("active", "진행 중"),
        ("ended", "종료")
    ]

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT, related_name="sessions")
    anon_client_id = models.CharField(max_length=100)
    entry_path = models.CharField(max_length=20, choices=ENTRY_PATH)
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
    vulnerability_type = models.CharField(max_length=30)
    missed_tell_points = models.JSONField(default=list)
    guidance_text = models.TextField()
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