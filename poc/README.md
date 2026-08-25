# poc/ - 음성 대화 POC

`ai_core`만으로 실제 음성 대화(마이크 입력 -> STT -> `engine.step()` -> 문장 단위 TTS 재생)가
되는지 검증하는 용도. **프론트엔드·백엔드는 건드리지 않는다.** 검증 끝나면 이 폴더째
지워도 `ai_core`는 전혀 영향받지 않는다(공개 API인 `ai_core.engine`만 import해서 쓴다).

## 검증하는 것

`idea-plan.md` §7.5의 Controlled Streaming Cascade - 판정기·코드가 상태를 승인한 뒤
사기꾼 응답을 스트리밍하면서 **문장이 완성되는 즉시** TTS로 재생하는 방식 - 이 실제로
그렇게 동작하는지를, `engine.step(on_delta=speak)`로 직접 확인한다. `on_delta`는
`StreamingSafetyGate`가 승인한 문장마다 호출되므로(`ai_core/streaming.py`), 전체 응답을
기다리지 않고 첫 문장부터 재생되는 걸 귀로 확인할 수 있다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `stt.py` | Chirp 2 (Speech-to-Text V2, `us-central1`) - 오디오 -> 한국어 텍스트 |
| `tts.py` | Chirp 3: HD (Text-to-Speech) - 텍스트 -> 오디오 합성 + 즉시 재생 |
| `voice_chat.py` | 메인 루프 - 마이크 녹음 -> STT -> `ai_core.engine.step()` -> TTS 재생 |

## 준비

1. `mirisalpim-web/.env`에 다음이 있어야 한다 (이미 설정돼 있다면 생략):
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=...
   GOOGLE_APPLICATION_CREDENTIALS=.gcp-credentials.json
   ```
   `GOOGLE_APPLICATION_CREDENTIALS`는 Speech-to-Text/Text-to-Speech API가 활성화된
   GCP 프로젝트의 **서비스 계정 JSON 키** 경로. Gemini용 AI Studio 키와는 별개다 -
   AI Studio 키는 Generative Language API에만 제한돼 있어 이 두 API에는 못 쓴다.
2. 패키지: `pip install google-cloud-speech google-cloud-texttospeech sounddevice soundfile numpy`
   (POC 전용이라 아직 `backend/requirements.txt`에는 추가하지 않았다)

## 실행

```bash
cd mirisalpim-web
python -m poc.voice_chat            # 기본 시나리오 sc-02 (검찰 사칭)
python -m poc.voice_chat nm-01      # 다른 시나리오
```

`[Enter]`를 눌러 녹음을 시작하고, 말이 끝나면 다시 `[Enter]`를 눌러 종료한다.
사기꾼 쪽 응답은 문장이 나오는 대로 자동 재생된다.

## 검증 완료 (텍스트 왕복, 마이크 없이)

Chirp 3 HD로 합성한 오디오를 Chirp 2 STT로 되돌려 인식한 결과, 원문과 거의 동일하게
재인식되는 것을 API 레벨에서 확인했다(2026-08-20). 실제 마이크·스피커를 통한 대화는
이 문서를 읽는 사람이 로컬에서 직접 실행해 확인해야 한다 - 개발 환경(Claude Code의
Bash 도구)에는 오디오 하드웨어가 없다.
