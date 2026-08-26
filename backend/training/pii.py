"""훈련생 입력의 개인정보 마스킹.

API 설계 6절: "사용자 입력에서 주민번호·계좌·전화번호 등 PII 패턴을 탐지하면
LLM 전달 및 DB 저장 전에 마스킹하고 riskWarning 을 반환한다."

⚠️ 지우지 않고 라벨로 바꾸는 이유: 판정기가 마스킹된 텍스트를 보기 때문이다.
값을 통째로 지우면 "훈련생이 개인정보를 제공했다"는 사실까지 사라져서 판정기가
personal_info 위험행동을 놓친다. "[주민등록번호]" 로 남기면 값은 지워지고
행동은 남는다.
"""

import re

#: 순서가 중요하다 - 자릿수가 긴 패턴을 먼저 지워야 짧은 패턴이 일부만 먹지 않는다.
#:
#: \b 를 쓰지 않는다. 한글도 단어문자라서 "900101-1234567이에요" 처럼 숫자 뒤에
#: 조사가 바로 붙으면 경계가 생기지 않아 매칭에 실패한다. 숫자 경계로 직접 막는다.
PATTERNS = [
    ("resident_registration_number", "[주민등록번호]",
     re.compile(r"(?<!\d)\d{6}[-\s]?[1-4]\d{6}(?!\d)")),
    ("card_number", "[카드번호]",
     re.compile(r"(?<!\d)\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)")),
    ("phone_number", "[전화번호]",
     re.compile(r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)")),
    ("account_number", "[계좌번호]",
     re.compile(r"(?<!\d)\d{2,6}-\d{2,6}-\d{2,8}(?!\d)")),
    # 하이픈 없이 길게 이어진 숫자도 계좌로 본다 (전화·카드를 먼저 지운 뒤라 안전하다)
    ("account_number", "[계좌번호]", re.compile(r"(?<!\d)\d{10,16}(?!\d)")),
]


def mask_pii(text):
    """(마스킹된 텍스트, 탐지된 유형 목록) 을 돌려준다."""
    detected = []
    masked = text
    for kind, label, pattern in PATTERNS:
        masked, count = pattern.subn(label, masked)
        if count and kind not in detected:
            detected.append(kind)
    return masked, detected
