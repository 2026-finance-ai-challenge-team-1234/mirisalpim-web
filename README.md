# 미리살핌 (Mirisalpim)

> AI 사기범과 직접 대화하고, 내가 어디에서 흔들렸는지 진단받는 금융사기 모의훈련 서비스

미리살핌은 보이스피싱·스미싱·피싱 상황을 실제와 유사하게 재현하는 웹 기반 예방 훈련 서비스입니다. 사용자는 생성형 AI와 통화 또는 문자로 대화하고, 훈련이 끝난 뒤 판단 시점·놓친 위험 신호·위험 행동·대응 방법을 개인화된 리포트로 확인할 수 있습니다.

정답이 고정된 퀴즈 대신 사용자의 반응에 따라 설득 전략이 바뀌는 다중 턴 역할극을 제공합니다. 다만 단계 전환과 채점은 LLM에 맡기지 않고 코드 상태머신이 최종 결정합니다.

## 서비스 이름

**미리살핌**은 피해가 발생한 뒤 수습하는 대신, 위험한 상황을 미리 경험하고 사기 신호를 살피는 훈련이라는 의미를 담고 있습니다.

## 주요 기능

- 로그인 없는 익명 훈련
- 설문 기반 맞춤 추천과 직접 유형 선택
- Chirp 2 STT와 Chirp 3 HD TTS를 사용하는 보이스피싱 훈련
- 통화·문자 채널에 맞춰 반응하는 스미싱 훈련
- 사기 111개와 정상 비교 사례 7개를 섞은 중립 판별 훈련
- 개인정보 제공·링크 클릭·앱 설치·송금 동의·고립 수용 감지와 즉시 경고
- 판단한 대화 횟수, 놓친 단서, 위험 행동, 취약 패턴, 행동 가이드를 제공하는 진단 리포트
- 가상의 로그인·결제·OTP 탈취 과정을 체험하는 4단계 피싱 체험관
- 고정 음성을 이용한 STT·판정·생성·안전 검사·TTS 구간별 레이턴시 측정

## AI 처리 구조

음성 대화는 판정과 코드 상태 승인이 끝난 뒤 생성·안전 검사·TTS를 문장 단위로 겹쳐 수행하는 **Controlled Streaming Cascade** 방식입니다.

```mermaid
flowchart LR
    U[사용자] -->|텍스트| API[Django API]
    U -->|MediaRecorder 음성| STT[Chirp 2 STT]
    STT --> API
    API --> PII[입력 검증·PII 마스킹]
    PII --> J[판정기]
    J --> S[코드 상태머신 승인]
    S --> G[사기범 발화 스트리밍]
    G --> F[문장별 안전 필터]
    F -->|승인 문장| SSE[SSE 자막]
    F --> TTS[Chirp 3 HD TTS]
    TTS -->|문장별 MP3| SSE
    SSE --> U
    API <--> DB[(PostgreSQL)]
```

| 역할      | 운영 모델               | 책임|
| --------- | ----------------------- | ------------------------------------------------------ |
| 사기범    | `gemini-3.7-flash`      | 현재 단계·대화 이력·전달 채널에 맞는 다음 발화 생성    |
| 판정기    | `gemini-3.5-flash-lite` | 사용자 반응, 위험 행동, 단계 전환 후보를 구조화 출력   |
| 안전 필터 | `gemini-3.5-flash-lite` | 역할 이탈, 프롬프트 유출, 실제 URL·계좌·기관 노출 차단 |
| 진단      | `gemini-3.5-flash-lite` | 코드가 확정한 채점 결과를 사용자 친화적으로 설명       |

사기범 모델에서 429·503 등 일시 장애가 발생하면, 아직 승인된 문장이 전송되지 않은 경우에만 `gemini-3.5-flash-lite`로 한 번 재시도합니다. 이미 문장이 전송된 뒤에는 같은 발화가 중복되지 않도록 폴백하지 않습니다.

### 채점과 리포트 기준

내부 상태의 원시 턴 번호는 한 번의 사용자–AI 교환마다 2씩 증가합니다. 따라서 판별 지연과 사용자 화면의 “N번째 대화”는 원시 턴 차이가 아니라 **주고받은 대화 횟수**로 계산합니다. 사기 시나리오는 최초 판별 가능 시점 이후 0~1회 내에 위험 행동 없이 판단하면 S, 2~3회는 A, 4~6회 또는 경미한 위험 행동이 있으면 B, 중대 위험 행동 또는 그보다 늦은 판단은 C, 오판은 D입니다. 정상 시나리오를 사기로 판단하면 오탐으로 안내합니다.

판단 API는 화면용 `judgedExchange`·`firstDetectableExchange`와 놓친 단서의 `exchange`를 반환합니다. `judgedTurn`·`firstDetectableTurn`과 타임라인의 `turn`은 내부 마커 정렬을 위한 원시 턴 번호로 유지합니다.

## 시나리오 데이터

운영 시나리오의 단일 원본은 `data/scenarios/`입니다.

| 구분           | 개수 |
| -------------- | ---: |
| 전체           |  118 |
| 사기           |  111 |
| 정상 비교 사례 |    7 |
| 음성           |   62 |
| 스미싱         |   56 |

각 카드는 페르소나, 목표, 대화 단계, 단계 전환 조건, 위험 신호, 학습 목표, 금칙 항목과 공식 출처를 구조화합니다. 실제 계좌번호·작동 URL·실존 기관을 사용하지 않으며, 정상 사례는 실제 사건으로 오해되지 않도록 별도로 표시합니다.

RAG와 파인튜닝은 현재 MVP에 포함하지 않습니다. 검수된 시나리오 카드, 상태머신, 판정기, 프롬프트와 안전 필터로 먼저 품질과 통제 가능성을 확보합니다.

## 기술 스택

| 영역       | 기술                                                                |
| ---------- | ------------------------------------------------------------------- |
| Frontend   | React 19, Vite 8, Tailwind CSS 4, React Router                      |
| Backend    | Python 3.12+, Django 6.1, Uvicorn                                   |
| Database   | PostgreSQL 16                                                       |
| AI         | Google Gemini, provider adapter (`gemini` / `anthropic` / `ollama`) |
| Voice      | Google Cloud Chirp 2 STT, Chirp 3 HD TTS                            |
| Deployment | Railway, Docker multi-stage build, WhiteNoise                       |

## 프로젝트 구조

```text
mirisalpim-web/
├── ai_core/                 # Django 비의존 AI 코어와 평가 도구
│   ├── agents/              # 사기범·판정기·안전 필터
│   └── eval/                # 안전 필터·판정기 평가 도구
├── backend/                 # Django API, DB 모델, 음성 처리
│   ├── config/
│   └── training/
├── data/
│   ├── scenarios/           # 운영 시나리오 118개 단일 원본
│   └── schemas/
├── frontend/                # React SPA
├── poc/                     # 음성 파이프라인 임시 검증 도구
├── Dockerfile               # Node 빌드 + Python 런타임
└── .env.example
```

## 로컬 실행

### 요구 사항

- Python 3.12 이상
- Node.js 22 이상
- Docker Desktop 또는 로컬 PostgreSQL 16
- 전체 MVP 대화 사용 시 Gemini API 키
- 음성 기능 사용 시 Speech-to-Text·Text-to-Speech가 활성화된 GCP 서비스 계정

### 1. 환경변수 준비

저장소 루트의 `.env.example`을 `.env`로 복사합니다. `backend/.env`를 별도로 만들면 Django와 AI 코어의 설정이 분리되므로 사용하지 않습니다.

```bash
cp .env.example .env
```

로컬 HTTP 개발에서는 다음 값을 사용합니다.

```dotenv
SECRET_KEY=local-development-secret
DEBUG=True
DATABASE_URL=postgresql://mirisalpim:localdev@localhost:5432/mirisalpim
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

운영 환경에서는 반드시 `DEBUG=False`를 유지합니다.

현재 판정기와 안전 필터의 구조화 출력은 Gemini 경로에서만 구현되어 있습니다. Anthropic과 Ollama 어댑터는 비구조화 생성 및 코어 디버깅용으로 유지하며, 전체 웹 훈련에는 `LLM_PROVIDER=gemini`를 사용합니다.

### 2. PostgreSQL 실행

```bash
docker compose -f backend/docker-compose.yml up -d db
```

### 3. 백엔드 실행

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py seed_scenarios
python manage.py runserver 0.0.0.0:8000
```

### 4. 프론트엔드 실행

새 터미널에서 실행합니다. Vite 개발 서버는 `/api` 요청을 Django의 `localhost:8000`으로 전달합니다.

```bash
cd frontend
npm ci
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

### 음성 기능 설정

Gemini API 키와 GCP 서비스 계정 키는 서로 다른 자격증명입니다. 로컬에서는 `.env`에 서비스 계정 JSON 경로를 지정합니다.

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=.gcp-credentials.json
```

Railway에서는 서비스 계정 JSON 전체를 `GCP_CREDENTIALS_JSON`에 넣고, 파일 경로를 `/tmp/gcp-credentials.json`으로 지정합니다.

```dotenv
GCP_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json
```

음성 자격증명이 없거나 잘못되어도 서비스는 텍스트 모드로 기동합니다.

## 주요 API

기본 경로는 `/api/v1`이며, 변경 요청에는 Django CSRF 토큰과 익명 세션 쿠키가 필요합니다.

| 메서드 | 경로                                         | 용도                                |
| ------ | -------------------------------------------- | ----------------------------------- |
| `GET`  | `/bootstrap`                                 | 익명 세션, CSRF, 기능 플래그 초기화 |
| `GET`  | `/all-scenarios`                             | 트랙과 사용 가능한 시나리오 수 조회 |
| `POST` | `/user-info`                                 | 직접 선택한 훈련 트랙 저장          |
| `POST` | `/recommendations`                           | 설문 기반 훈련 추천                 |
| `POST` | `/training-sessions`                         | 훈련 세션과 첫 발화 생성            |
| `POST` | `/training-sessions/{id}/turns`              | 동기 텍스트 턴 처리                 |
| `POST` | `/training-sessions/{id}/turns/audio/stream` | 음성 업로드와 문장별 SSE 응답       |
| `POST` | `/training-sessions/{id}/judgment`           | 사기 여부 판단, 채점과 진단 생성    |

음성 SSE는 `accepted`, `status`, `riskWarning`, `delta`, `audio`, `timing`, `done` 이벤트를 사용합니다. 정상 완료 시 `done`이 마지막 이벤트입니다. `timing`은 서버 설정과 요청 옵션을 모두 켠 진단 요청에서만 반환합니다.

판단 응답의 사용자 표시에는 `judgedExchange`와 `firstDetectableExchange`를 사용합니다. 이전 클라이언트 호환과 타임라인 정렬을 위해 원시 `judgedTurn`·`firstDetectableTurn`도 함께 반환합니다.

## 검증

### 결정론적 검증

```bash
# 저장소 루트
python -m ai_core.validate
python -m ai_core.smoke

# Django
cd backend
python manage.py seed_scenarios --check
python manage.py test

# Frontend
cd ../frontend
npm run lint
npm run build
```

현재 기준 결과:

- 시나리오 검증: 118/118
- 판정기 평가: 20턴 중 19턴 정확, 95%
- 안전 필터 평가: 27/27
- Django 테스트: 176건 통과, 1건 skip
- AI 코어 smoke, 프론트 lint와 production build 통과

Gemini가 필요한 평가 도구는 저장소 루트에서 실행합니다.

```bash
python -m ai_core.eval.safety_eval
python -m ai_core.eval.judge_eval
python -m ai_core.eval.judge_compare --max-cases 20
```

### 음성 레이턴시 측정

미리 녹음한 `webm/opus` 파일을 반복 입력할 수 있으므로 매번 직접 말할 필요가 없습니다. 서버 `.env`에서 `VOICE_LATENCY_DIAGNOSTICS=True`를 설정한 뒤 실행합니다.

```bash
cd backend
python manage.py benchmark_voice_latency \
  --audio /absolute/path/to/fixed-korean.webm \
  --base-url http://127.0.0.1:8000 \
  --track-id T01-1 \
  --iterations 20 \
  --output benchmark-results/voice-baseline.json
```

표본이 작으면 Gemini 호출 변동과 환경 차이를 구분하기 어려우므로 환경·모델 비교에는 최소 20회를 권장합니다. 로컬 HTTP 측정은 `DEBUG=True`, Railway HTTPS 측정은 반드시 `DEBUG=False`를 사용합니다.

최근 고정 음성 20회 측정 결과:

| 지표                |  변경 전 |    현재 |
| ------------------- | -------: | ------: |
| 판정기 p50          |  6,048ms |   908ms |
| 판정기 p95          | 13,461ms | 1,040ms |
| Railway 첫 음성 p50 |   19.3초 |   8.1초 |
| Railway 첫 음성 p95 |   34.9초 |  11.4초 |

첫 음성 개선에는 판정기 교체뿐 아니라 측정 시점의 사기범 모델 과부하 해소도 함께 영향을 주었으므로, 전체 개선분을 하나의 변경에만 귀속하지 않습니다.

## 안전 및 개인정보

- 실제로 작동하는 URL·계좌번호·카드번호·앱 설치 경로를 생성하지 않습니다.
- 실존 금융회사·공공기관 화면과 브랜드를 복제하지 않습니다.
- 음성 클로닝을 사용하지 않고 공개 TTS 화자 프리셋만 사용합니다.
- 사용자는 항상 표적 역할이며, 사기범 역할 모드는 제공하지 않습니다.
- 로그인이나 영구 사용자 프로필을 만들지 않습니다.
- 이름·나이·주소는 React 메모리와 매 턴 요청에서만 처리하며 localStorage·Django 세션·DB에 저장하지 않습니다.
- 주민번호·계좌·전화번호 패턴은 모델 전달과 DB 저장 전에 마스킹합니다.
- 음성 바이트는 STT 처리 중 메모리에서만 사용하고 파일이나 DB에 저장하지 않습니다.
- 대화 원문은 진행 중 상태 복구를 위해 임시 보관하며 판단 완료 또는 세션 만료 시 비웁니다.
- 안전 필터를 통과한 문장만 자막과 TTS로 전달하며 차단된 원문은 로그에 남기지 않습니다.

## 배포

`Dockerfile`은 두 단계로 구성됩니다.

1. `node:22-alpine`에서 React production build 실행
2. `python:3.13-slim`에 Django, AI 코어, 시나리오와 정적 파일 통합

컨테이너 기동 시 마이그레이션과 시나리오 seed를 실행한 뒤 Uvicorn ASGI 서버를 시작합니다. 프론트 정적 파일은 Django와 WhiteNoise가 제공하므로 배포 대상은 하나입니다.

운영 환경에서는 다음을 반드시 확인합니다.

- `DEBUG=False`
- 충분히 긴 `SECRET_KEY`
- PostgreSQL `DATABASE_URL`
- Railway 도메인을 포함한 `ALLOWED_HOSTS`와 `CSRF_TRUSTED_ORIGINS`
- `LLM_PROVIDER=gemini`와 Gemini API 키
- 음성 사용 시 GCP 서비스 계정 설정
- `/health/` 응답과 시나리오 118개 seed 로그

## 프로젝트 팀원


|            |**김하람** | **권민찬** | **엄민송** | **오하연** |
|:---------:|:---------: | :----------: | :----------: | :----------: |
| **Profile** | <img src="https://avatars.githubusercontent.com/u/37824335?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/235444774?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/235094857?v=4" width="100" height="100"> | <img src="https://avatars.githubusercontent.com/u/202039164?v=4" width="100" height="100"> |
| **Role** | Project Manager<br>AI Core Developer | Backend Developer<br>Deployment | Frontend Developer<br>UI/UX | AI QA Engineer<br>Scenario Design |
| **GitHub**  | [@1unaram ](https://github.com/1unaram)| [@tronve ](https://github.com/tronve)  | [@skymin1121 ](https://github.com/skymin1121) |  [@oohayeon ](https://github.com/oohayeon) |
