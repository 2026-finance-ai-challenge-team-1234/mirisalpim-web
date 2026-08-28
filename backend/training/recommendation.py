"""P-02 추천 — 팀 추천 엔진에 "훈련 가능한 것만" 제약을 씌운다.

recommendation_engine.py 는 프론트와 함께 확정한 규칙표이고 이 파일에서 수정하지
않는다. 다만 그 엔진은 순수 함수라 어떤 시나리오가 실제로 적재돼 있는지 모른다.
분류표는 소분류 109개인데 시나리오는 12개 트랙에만 있어서, 엔진 결과를 그대로
쓰면 3000건 시뮬레이션 기준 81.7% 가 훈련할 수 없는 소분류를 가리킨다
(그대로 훈련을 시작하면 409 SCENARIO_NOT_AVAILABLE).

그래서 순서대로 물러난다.
  1. 엔진이 고른 소분류가 훈련 가능하면 그대로 쓴다.
  2. 아니면 같은 중분류 안에서 훈련 가능한 소분류로 바꾼다.
  3. 중분류째 비어 있으면 엔진 점수가 높은 순으로 다음 중분류를 찾는다.
     이유·제목·적합도도 그 중분류 기준으로 다시 만든다.

시나리오가 늘어날수록 1번에서 끝나는 비율이 올라간다.
"""

import random

from .recommendation_engine import (
    CATEGORY_META,
    _build_reasons,
    _compute_category_scores,
    _compute_match_percent,
    recommend as engine_recommend,
)

#: 엔진의 channel 값과 Scenario.category 값이 다르다 (sms ↔ smishing).
CHANNEL_TO_CATEGORY = {"voice": "voice", "sms": "smishing"}


def recommend(survey, trainable_tracks):
    """엔진 결과를 훈련 가능한 범위로 좁혀서 돌려준다.

    trainable_tracks 가 비어 있으면 None (적재된 시나리오가 하나도 없는 상태).
    """
    if not trainable_tracks:
        return None

    result = engine_recommend(survey)
    group = result["recommendedCategory"]

    # 1. 엔진이 고른 그대로 훈련 가능한 경우
    if result["recommendedSubcategory"] in trainable_tracks:
        return _to_api(result, group, result["recommendedSubcategory"])

    # 2. 같은 중분류 안에서 대체
    same_group = sorted(t for t in trainable_tracks if t.startswith(group + "-"))
    if same_group:
        return _to_api(result, group, random.choice(same_group))

    # 3. 중분류째 비어 있으면 점수 순으로 다음 중분류
    scores = _compute_category_scores(survey)
    for next_group, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        candidates = sorted(t for t in trainable_tracks if t.startswith(next_group + "-"))
        if not candidates:
            continue
        meta = CATEGORY_META[next_group]
        rebuilt = {
            "channel": meta["channel"],
            "title": meta["title"],
            "description": meta["description"],
            "difficulty": result["difficulty"],
            "match": _compute_match_percent(scores, next_group),
            "reasons": _build_reasons(scores, survey, next_group),
        }
        return _to_api(rebuilt, next_group, random.choice(candidates))

    return None


def _to_api(result, group, track):
    """엔진 결과 → API 응답 형태.

    프론트가 이미 쓰고 있는 이름(category/track/suitability)을 유지한다.
    엔진 쪽 이름(channel/recommendedSubcategory/match)과 다르므로 주의.
    """
    return {
        "category": CHANNEL_TO_CATEGORY[result["channel"]],
        "categoryGroup": group,
        "track": track,
        "title": result["title"],
        "description": result["description"],
        "difficulty": result["difficulty"],
        "reasons": result["reasons"],
        "suitability": str(result["match"]),
    }
