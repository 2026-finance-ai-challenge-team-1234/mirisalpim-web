# 미리살핌 - Mirisalpim

## 음성 레이턴시 측정

고정 음성 파일은 저장소에 넣지 않고 로컬 경로로만 전달한다. 서버 `.env`에서
`VOICE_LATENCY_DIAGNOSTICS=True`를 설정한 뒤 서버를 재시작한다.

⚠️ **로컬 HTTP(`http://127.0.0.1:8000`)로 측정할 때는 `.env`에 `DEBUG=True`도 필요하다.**
`DEBUG=False`면 `SESSION_COOKIE_SECURE`·`CSRF_COOKIE_SECURE`가 켜져 http 로는 세션·CSRF
쿠키가 저장되지 않고, `SECURE_SSL_REDIRECT`가 요청을 https 로 돌려버린다. 배포
(Railway HTTPS)로 측정할 때는 `DEBUG` 를 건드리지 않는다 - 명령이 요청에 same-origin
`Origin`/`Referer`를 붙이므로 CSRF 검사를 그대로 통과한다.

```powershell
cd backend
python manage.py benchmark_voice_latency `
  --audio C:\path\to\fixed-korean.webm `
  --base-url http://127.0.0.1:8000 `
  --track-id T01-1 `
  --iterations 5 `
  --output benchmark-results\voice-baseline.json
```

결과에는 `accepted`, 첫 자막, 첫 음성, 완료까지의 클라이언트 시간과 서버의
STT·판정기·사기범 첫 토큰·안전 필터·문장별 TTS 시간이 기록된다. 음성 원본과
대화문은 결과 파일에 저장하지 않는다.

## 판정기 모델 비교

같은 대화 상태에 두 모델을 호출하고 사람이 어느 출력이 정확한지 표시한다.

```powershell
$env:LLM_PROVIDER = "gemini"
python -m ai_core.eval.judge_compare --max-cases 20
```

기본 비교는 `gemini-3.7-flash`와 `gemini-3.5-flash-lite`다. 정확도 80% 이상 및
기존 기준 대비 회귀가 없을 때만 기본 판정기 모델을 변경한다.
