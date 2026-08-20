# data/

미리살핌의 시나리오 카드와 (후순위) RAG 코퍼스 원본. **`ai_core`와 `backend` 양쪽이 이 디렉터리 하나를 공유**한다 — 카드를 한 번만 고치면 AI 코어 로더와 Django seed importer 동시에 같은 내용을 본다.

이 디렉터리가 배포 저장소(`mirisalpim-web`) **안에** 있는 이유: 예전에는 시나리오 원본이 `AI_challenge/scenario/`(별도 git 저장소)에 있어서, Railway 같은 곳에서 `mirisalpim-web`만 체크아웃하면 그 경로가 아예 존재하지 않았다. `ai_core/engine.py`의 `DATA_DIR`과 `backend/config/settings.py`의 `SCENARIO_SEED_DIR`이 둘 다 여기(`data/scenarios/`)를 본다.

## 출처

시나리오 20개(사기 14 · 정상 6)는 `AI_challenge/scenario/`에서 팀원이 조사·작성한 원본을 통합 스키마로 재구성한 것이다. 조사 당시 원본(연구 메모, 성격 특성 산문 등 런타임에 쓰지 않는 필드 포함)은 `AI_challenge/scenario/json_data/_source/`에 그대로 보존돼 있다 — 이 디렉터리(`mirisalpim-web/data/`)에는 옮기지 않았다(배포 저장소를 조사 원본으로 부풀리지 않기 위해).

각 카드 자체에 출처가 있다 — 별도 카탈로그를 두지 않는다.

| 필드                   | 의미                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| `source`               | 결과 리포트에 표시할 짧은 출처명 (예: "경찰청·금융위원회 기관사칭형 주요 시나리오 및 피싱안심SOS 실제 사례") |
| `source_refs`          | 결과 리포트의 "공식 자료 보기" 링크용 공식 HTTPS URL 1~2개                                                   |
| `source_review_status` | `human_reviewed` \| `auto_labeled` (내부 관리용, 리포트엔 미노출)                                            |

`source_refs`의 실제 URL은 사기범·판정기 프롬프트에는 주입하지 않는다 — 결과 API에서만 반환한다.

## 가공 기준

원본(성격 특성 산문, 연구 메모, 종료/의심대응/핸드오프가 뒤섞인 대화 단계 등)을 실제 런타임 구조로 재구성한 규칙은 `AI_challenge/scenario/claude-report1.md`에 상세히 기록돼 있다.

요약:

- `stages`는 선형 대화 흐름만 담는다. 의심 대응은 `persona.resistance_strategy`, 종료 조건은 `end_conditions`로 분리했다 (그렇지 않으면 상태머신이 "종료 단계"를 중간에 다음 대화 단계처럼 진행한다).
- `min_turns` 합이 `max_turns`를 넘지 않아야 마지막 단계까지 도달할 수 있다 (`2 × Σmin_turns − 1 ≤ max_turns`, `ai_core/validate.py`가 강제한다).
- `weight` = 이 단서가 사기 판별에 갖는 결정력. **1 = 약한 보조 신호, 3 = 결정적 신호.**

## 라이선스 / 사용 범위

- 원문은 경찰청·금융위원회·금융감독원 등 **공개된 예방 자료**를 재구성한 것이며, 특정 실제 피해 사례를 그대로 재현하지 않는다 (`is_scam` 시나리오도 마찬가지). 훈련 목적 외 재배포·상업적 이용 전에는 각 `source_refs`의 원 발행처 이용조건을 확인할 것.
- 정상(비사기) 시나리오는 실제 사건의 출처로 오인되지 않도록 `source`를 "훈련용 정상 비교 사례 (... 예방 자료 참고)" 형식으로 적는다.
- CLAUDE.md의 비협상 안전 제약(실제 URL·계좌번호·실존 기관명 생성 금지)은 카드 내용에도 그대로 적용된다 — `forbidden` 필드가 카드별로 명시하고 `ai_core/agents/safety.py`가 런타임에 한 번 더 강제한다.

## 구조

```
data/
├── README.md              # 이 파일
├── schemas/
│   └── scenario.schema.json   # 참고용 JSON Schema. 실제 강제는 ai_core/validate.py 가 한다
├── scenarios/              # 운영 시나리오 원본 — ai_core·backend 공용
│   ├── sc-01.json … sc-14.json   (사기 14개)
│   └── nm-01.json … nm-06.json   (정상 6개)
└── corpus/                 # RAG 도입 시에만 사용 (PoC-4, 현재 MVP 후순위)
    ├── raw/                # 원본 녹취/기사 — git 제외 (대용량·저작권)
    └── processed/          # 임베딩 전처리 결과
```

## 명령

```bash
cd mirisalpim-web
python -m ai_core.validate                  # data/scenarios/ 전체 검증 (기본 경로)
python -m ai_core.smoke                     # 상태머신 회귀 (sc-02 사용)

cd backend
python manage.py seed_scenarios --check     # 검증만, DB 미변경
python manage.py seed_scenarios -v 2        # DB 적재
```

## 새 시나리오 추가

1. `schemas/scenario.schema.json`을 참고해 카드를 작성한다 (필드 의미는 위 표 + `AI_challenge/scenario/scenario.md` 참고).
2. `scenario_id`는 사기 `sc-15`부터, 정상 `nm-07`부터 — 한 번 배정한 번호는 재사용하지 않는다.
3. `data/scenarios/`에 저장한 뒤 `python -m ai_core.validate`로 검증한다.
4. 통과하면 `python manage.py seed_scenarios --check` → `-v 2`로 DB에 반영한다.
5. 커버리지가 바뀌면 `AI_challenge/scenario/index.json`도 재생성 대상이다 (별도 스크립트, `claude-report1.md` §3.3 참고).
