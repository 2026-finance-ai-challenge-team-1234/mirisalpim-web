"""훈련 선택 결과를 익명 세션에 보관한다.

추천 경로(P-02)와 직접 선택 경로(P-03-02)가 같은 자리에 쓰고 뒤에 온 값이 앞의 값을
덮는다 (프론트가 '설문 다시하기'를 그렇게 처리한다). 실제 SESSION 레코드는 훈련을
시작하는 시점에 만든다 - 고르기만 하고 이탈한 사용자로 테이블이 더러워지지 않게 한다.
"""

SELECTION_KEY = "training_selection"


def store_selection(session, category, track, entry_path, difficulty=None):
    """세션의 같은 자리에 덮어쓴다.

    difficulty 는 문진(Q4)에서만 정해진다. 직접 선택 경로는 None 이고, 그러면
    ai_core.create_session() 이 시나리오 카드의 기본 난이도를 쓴다.
    """
    session[SELECTION_KEY] = {
        "category": category,
        "track": track,
        "entry_path": entry_path,
        "difficulty": difficulty,
    }


def get_selection(session):
    return session.get(SELECTION_KEY)
