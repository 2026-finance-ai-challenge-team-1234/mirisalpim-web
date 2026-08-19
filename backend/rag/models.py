"""RAG 전용 모델 — **INSTALLED_APPS 에 등록되어 있지 않다.**

RAG 는 MVP 필수 계층이 아니라 후순위 확장이다(CLAUDE.md 확정 결정). 그런데 이 모델을
training 앱에 두면 초기 migration 이 `CREATE EXTENSION vector` 를 실행하게 되고,
첫 배포가 배포 환경의 pgvector 제공 여부에 걸린다. 배포 실패는 대회 기준 0점이라
그 의존을 초기 경로에서 뺐다.

도입할 때:
  1. config/settings.py 의 INSTALLED_APPS 에 "rag" 추가
  2. requirements.txt 에 pgvector 유지 확인
  3. python manage.py migrate rag
"""

from django.db import models
from pgvector.django import VectorField


class Utterance(models.Model):
    utterance_id = models.CharField(max_length=100, primary_key=True)
    text = models.TextField()
    category = models.CharField(max_length=20)
    #: Scenario.track 과 같은 분류 코드를 쓴다 (T01-5 등) — 시나리오와 안정적으로 연결된다
    scam_type = models.CharField(max_length=100)
    stage = models.CharField(max_length=50)
    tactic = models.CharField(max_length=100)
    context = models.TextField(blank=True)
    source = models.CharField(max_length=200)
    embedding = VectorField(dimensions=1536)
