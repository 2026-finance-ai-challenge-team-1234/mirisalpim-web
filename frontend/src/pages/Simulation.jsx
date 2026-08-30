import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import {
  startTrainingSession,
  sendAudioTurn,
  sendTurn,
  submitJudgment,
} from "../api/trainingApi";
import { newIdempotencyKey } from "../api/client";

const MAX_INPUT_CHARS = 200;
const MAX_RECORDING_MS = 30_000;
const AUDIO_MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm"];

function readStoredJson(key) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

// 훈련 채널만 로컬에서 미리 판단 (화면 레이아웃 결정용).
// 실제 시나리오 내용은 전부 서버가 준다.
function readInitialCategory() {
  const savedScenario = readStoredJson("selectedScenario");
  if (savedScenario) return savedScenario.isVoice ? "voice" : "smishing";
  return localStorage.getItem("selectedCategory") || "voice";
}

function LiveBadge() {
  return (
    <div className="flex items-center space-x-1.5">
      <span className="w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
      <span className="text-[10px] font-bold text-red-500">실시간 모의 체험 중</span>
    </div>
  );
}

function formatCallTime(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function supportedRecordingMimeType() {
  if (!("MediaRecorder" in window)) return null;
  return AUDIO_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) || null;
}

function stopMediaStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

function CallToggleButton({ active, disabled = false, onClick, label, children }) {
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        aria-pressed={active}
        className={`w-12 h-12 rounded-full flex items-center justify-center transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 ${
          active ? "bg-[#0052CC] text-white" : "bg-gray-100 text-[#191F28] hover:bg-gray-200"
        }`}
      >
        {children}
      </button>
      <span className="text-[10px] font-semibold text-[#8B95A1] mt-1.5">{label}</span>
    </div>
  );
}

// 사용자가 시작 화면에서 겪는 오류를 안내하는 문구.
// 백엔드 오류 코드별로 다음 행동을 다르게 제시함.
function describeError(err) {
  switch (err?.code) {
    case "NO_SELECTION":
      return { text: "훈련 유형이 선택되지 않았어요. 유형을 다시 골라주세요.", action: "reselect" };
    case "SCENARIO_NOT_AVAILABLE":
      return { text: "아직 준비되지 않은 유형이에요. 다른 유형을 선택해주세요.", action: "reselect" };
    case "SESSION_NOT_FOUND":
      return { text: "훈련 세션을 찾을 수 없어요. 처음부터 다시 시작해주세요.", action: "restart" };
    case "SESSION_EXPIRED":
      return { text: "훈련 시간이 만료됐어요. 처음부터 다시 시작해주세요.", action: "restart" };
    case "JUDGMENT_IN_PROGRESS":
    case "JUDGMENT_CONFLICT":
    case "TURN_CONFLICT":
      return { text: "이전 요청을 처리하고 있어요. 잠시 후 다시 시도해주세요.", action: "retry" };
    case "SESSION_ENDED":
    case "ALREADY_JUDGED":
      return { text: "이미 종료된 훈련이에요. 결과 리포트를 확인해주세요.", action: "report" };
    case "RATE_LIMITED":
      return { text: "요청이 너무 많아요. 잠시 후 다시 시도해주세요.", action: "retry" };
    case "AI_TIMEOUT":
    case "AI_ERROR":
      return { text: "응답을 받아오지 못했어요. 다시 시도해주세요.", action: "retry" };
    case "VOICE_UNAVAILABLE":
      return { text: "현재 음성 기능을 사용할 수 없어요. 잠시 후 다시 시도해주세요.", action: "retry" };
    case "STT_ERROR":
    case "NO_SPEECH_DETECTED":
    case "EMPTY_AUDIO":
      return { text: "말씀하신 내용을 알아듣지 못했어요. 마이크를 눌러 다시 말씀해주세요.", action: "retry" };
    case "AUDIO_TOO_LARGE":
      return { text: "녹음이 너무 길어요. 30초 이내로 다시 말씀해주세요.", action: "retry" };
    case "INPUT_TOO_LARGE":
      return { text: "입력이 너무 길어요. 200자 이내로 줄여주세요.", action: "retry" };
    default:
      return { text: err?.message || "문제가 발생했어요. 다시 시도해주세요.", action: "retry" };
  }
}

export default function Simulation() {
  const navigate = useNavigate();

  const [category] = useState(readInitialCategory);

  const [sessionId, setSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [turnNo, setTurnNo] = useState(0);
  const [maxTurns, setMaxTurns] = useState(null);
  const [ended, setEnded] = useState(false);

  const [starting, setStarting] = useState(true);
  const [waiting, setWaiting] = useState(false); // 사기범 응답 대기(8~10초)
  const [error, setError] = useState(null);

  const [inputText, setInputText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [audioNotice, setAudioNotice] = useState(null);
  const [callSeconds, setCallSeconds] = useState(0);

  const [riskWarning, setRiskWarning] = useState(null); // { type, message }
  const [showJudgment, setShowJudgment] = useState(false);
  const [judging, setJudging] = useState(false);

  const chatEndRef = useRef(null);
  const categoryRef = useRef(category); // 최초 마운트 effect에서 category를 안전하게 참조
  const mountedRef = useRef(true);
  const speakerOnRef = useRef(true);
  const audioPlayerRef = useRef(null);
  const latestAudioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const sampleRateRef = useRef(48000);
  const recordingTimeoutRef = useRef(null);
  const shouldSubmitRecordingRef = useRef(false);

  const stopAudioPlayback = useCallback(() => {
    const player = audioPlayerRef.current;
    if (!player) return;
    player.pause();
    player.removeAttribute("src");
    audioPlayerRef.current = null;
  }, []);

  const playServerAudio = useCallback(
    (base64Audio, force = false) => {
      latestAudioRef.current = base64Audio || null;
      if (!base64Audio) {
        setAudioNotice("음성을 재생할 수 없어 화면에 자막을 표시하고 있어요.");
        return;
      }
      if (!force && !speakerOnRef.current) return;

      stopAudioPlayback();
      const player = new Audio(`data:audio/mpeg;base64,${base64Audio}`);
      audioPlayerRef.current = player;
      player.play().then(() => setAudioNotice(null)).catch((err) => {
        console.warn("[Simulation] 오디오 자동 재생 차단:", err);
        setAudioNotice("자동 재생이 차단됐어요. 스피커를 껐다 켜면 다시 들을 수 있어요.");
      });
    },
    [stopAudioPlayback],
  );

  // ───────── 훈련 시작: 사기범 첫 마디 받아오기 ─────────
  useEffect(() => {
    let cancelled = false;

    startTrainingSession()
      .then((data) => {
        if (cancelled) return;
        setSessionId(data.sessionId);
        setTurnNo(data.turnNo ?? 1);
        setMaxTurns(data.maxTurns ?? null);
        setChatHistory(data.opening ? [{ sender: "bot", text: data.opening }] : []);
        setStarting(false);
        if (categoryRef.current === "voice") playServerAudio(data.openingAudio);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("[Simulation] 훈련 시작 실패:", err);
        setError(describeError(err));
        setStarting(false);
      });

    return () => {
      cancelled = true;
    };
  }, [playServerAudio]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      shouldSubmitRecordingRef.current = false;
      clearTimeout(recordingTimeoutRef.current);
      if (mediaRecorderRef.current?.state !== "inactive") {
        mediaRecorderRef.current?.stop();
      }
      stopMediaStream(mediaStreamRef.current);
      stopAudioPlayback();
    };
  }, [stopAudioPlayback]);

  // 통화 타이머 (음성 모드, 훈련 시작 후에만)
  useEffect(() => {
    if (category !== "voice" || starting || error) return;
    const id = setInterval(() => setCallSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [category, starting, error]);

  // 새 메시지가 오면 아래로 자동 스크롤
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, waiting]);

  // ───────── 대화 한 턴 ─────────
  const applyTurnResult = (data, userText = null) => {
    if (userText) {
      setChatHistory((prev) => [...prev, { sender: "user", text: userText }]);
    }

    if (data.riskWarnings?.length) {
      setRiskWarning(data.riskWarnings[0]);
    }

    if (data.scammerText) {
      setChatHistory((prev) => [...prev, { sender: "bot", text: data.scammerText }]);
      if (category === "voice") playServerAudio(data.scammerAudio);
    }
    setTurnNo((current) => data.turnNo ?? current + 1);

    if (data.ended) {
      setEnded(true);
      setShowJudgment(true);
    }
  };

  const handleUserResponse = async (userMsg) => {
    const text = userMsg.trim();
    if (!text || !sessionId || waiting || ended) return;

    setChatHistory((prev) => [...prev, { sender: "user", text }]);
    setInputText("");
    setWaiting(true);
    setError(null);

    try {
      const data = await sendTurn(sessionId, text, newIdempotencyKey());
      applyTurnResult(data);
    } catch (err) {
      console.error("[Simulation] 턴 처리 실패:", err);
      setError(describeError(err));
    } finally {
      setWaiting(false);
    }
  };

  const handleUrlClick = () => {
    // 링크 클릭 자체도 하나의 '행동'이라 서버에 전달해 판정받음
    handleUserResponse("(문자 속 링크를 클릭했습니다)");
  };

  const submitRecordedAudio = async (audioBlob, sampleRate) => {
    if (!sessionId || !audioBlob.size || waiting || ended) return;
    setWaiting(true);
    setError(null);

    try {
      const data = await sendAudioTurn(
        sessionId,
        audioBlob,
        sampleRate,
        newIdempotencyKey(),
      );
      applyTurnResult(data, data.userText);
    } catch (err) {
      console.error("[Simulation] 음성 턴 처리 실패:", err);
      setError(describeError(err));
    } finally {
      if (mountedRef.current) setWaiting(false);
    }
  };

  const stopRecording = (shouldSubmit = true) => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    shouldSubmitRecordingRef.current = shouldSubmit;
    clearTimeout(recordingTimeoutRef.current);
    recorder.stop();
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError({
        text: "이 브라우저에서는 마이크를 사용할 수 없어요. 최신 Chrome 또는 Edge에서 다시 시도해주세요.",
        action: "retry",
      });
      return;
    }

    const mimeType = supportedRecordingMimeType();
    if (!mimeType) {
      setError({
        text: "이 브라우저는 필요한 음성 녹음 형식을 지원하지 않아요. 최신 Chrome 또는 Edge에서 다시 시도해주세요.",
        action: "retry",
      });
      return;
    }

    try {
      stopAudioPlayback();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      if (!mountedRef.current || waiting || ended) {
        stopMediaStream(stream);
        return;
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      sampleRateRef.current = stream.getAudioTracks()[0]?.getSettings().sampleRate || 48000;
      shouldSubmitRecordingRef.current = true;

      recorder.ondataavailable = (event) => {
        if (event.data.size) audioChunksRef.current.push(event.data);
      };
      recorder.onerror = (event) => {
        console.error("[Simulation] 마이크 녹음 실패:", event.error);
        shouldSubmitRecordingRef.current = false;
        setError({ text: "녹음 중 문제가 발생했어요. 다시 시도해주세요.", action: "retry" });
      };
      recorder.onstop = () => {
        const shouldSubmit = shouldSubmitRecordingRef.current;
        const chunks = audioChunksRef.current;
        stopMediaStream(mediaStreamRef.current);
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        audioChunksRef.current = [];
        if (mountedRef.current) setIsListening(false);

        if (shouldSubmit && mountedRef.current) {
          const audioBlob = new Blob(chunks, { type: mimeType });
          submitRecordedAudio(audioBlob, sampleRateRef.current);
        }
      };

      recorder.start(250);
      setIsListening(true);
      setError(null);
      recordingTimeoutRef.current = setTimeout(() => stopRecording(true), MAX_RECORDING_MS);
    } catch (err) {
      console.error("[Simulation] 마이크 접근 실패:", err);
      stopMediaStream(mediaStreamRef.current);
      setIsListening(false);
      setError({
        text:
          err?.name === "NotAllowedError"
            ? "마이크 권한이 필요해요. 브라우저 주소창에서 마이크를 허용한 뒤 다시 시도해주세요."
            : "마이크를 시작할 수 없어요. 연결 상태를 확인하고 다시 시도해주세요.",
        action: "retry",
      });
    }
  };

  const handleMicToggle = () => {
    if (isMuted || waiting || ended) return;
    if (isListening) stopRecording(true);
    else startRecording();
  };

  const handleSpeakerToggle = () => {
    const next = !speakerOnRef.current;
    speakerOnRef.current = next;
    setIsSpeakerOn(next);
    if (!next) {
      stopAudioPlayback();
      return;
    }
    if (latestAudioRef.current) playServerAudio(latestAudioRef.current, true);
  };

  // ───────── 판단 제출 → 채점·진단 ─────────
  const handleSubmitJudgment = async (isScamGuess) => {
    if (!sessionId || judging || waiting || isListening) return;
    setJudging(true);
    stopAudioPlayback();

    try {
      const report = await submitJudgment(sessionId, isScamGuess);
      navigate("/report-loading", { state: { report } });
    } catch (err) {
      console.error("[Simulation] 판단 제출 실패:", err);
      setJudging(false);
      setShowJudgment(false);
      setError(describeError(err));
    }
  };

  // ───────── 화면 ─────────
  const containerClass =
    "w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] sm:max-h-[844px] bg-white shadow-xl rounded-none sm:rounded-3xl border-0 sm:border border-gray-200 flex flex-col justify-between p-5 relative overflow-y-auto";

  // 훈련 시작 중
  if (starting) {
    return (
      <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
        <div className={containerClass}>
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <div className="w-14 h-14 border-4 border-blue-100 border-t-[#0052CC] rounded-full animate-spin mb-5"></div>
            <p className="text-sm font-bold text-[#191F28]">훈련을 준비하고 있어요</p>
            <p className="text-[11px] text-[#8B95A1] mt-1.5">잠시만 기다려 주세요...</p>
          </div>
        </div>
      </div>
    );
  }

  // 시작 자체가 실패한 경우
  if (error && !sessionId) {
    return (
      <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
        <div className={containerClass}>
          <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
            <span className="text-3xl mb-3">⚠️</span>
            <p className="text-sm font-bold text-[#191F28] mb-2">훈련을 시작할 수 없어요</p>
            <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep mb-6">{error.text}</p>

            <div className="w-full space-y-2">
              {error.action === "report" ? (
                <button
                  onClick={() => navigate("/report")}
                  className="w-full bg-[#0052CC] text-white py-3 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
                >
                  결과 리포트 보기
                </button>
              ) : (
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-[#0052CC] text-white py-3 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
                >
                  다시 시도하기
                </button>
              )}
              <button
                onClick={() => navigate("/type-select")}
                className="w-full bg-[#F8F9FA] text-[#8B95A1] border border-gray-200 py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
              >
                유형 다시 선택하기
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className={containerClass}>

        <div className="flex-1 flex flex-col">
          <PageHeader padding="pt-1 pb-3 mb-2" bordered rightContent={<LiveBadge />} />

          {/* ───────── 음성(전화) 모드 ───────── */}
          {category === "voice" && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-4">
              <div className="w-24 h-24 bg-gray-100 border border-gray-200 rounded-full flex items-center justify-center text-gray-500 mb-5 shadow-inner">
                <svg className="w-11 h-11 fill-none stroke-current stroke-1.5" viewBox="0 0 24 24">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
              <h2 className="text-xl font-extrabold text-[#191F28] mb-1.5 tracking-tight">
                알 수 없는 번호
              </h2>
              <p className="text-xs font-semibold text-[#8B95A1] mb-4">발신자 정보 없음</p>
              <div className="flex items-center space-x-1.5">
                <span className="text-base font-mono font-bold text-[#0052CC]">{formatCallTime(callSeconds)}</span>
                <span className="text-[11px] text-gray-400">
                  {waiting ? "응답 처리 중..." : isListening ? "듣는 중..." : "통화 중"}
                </span>
              </div>
              {maxTurns && (
                <p className="text-[10px] text-gray-400 mt-3">대화 {turnNo} / {maxTurns}</p>
              )}
              {chatHistory.length > 0 && (
                <div className="w-full mt-4 bg-[#F8F9FA] border border-gray-100 rounded-xl px-4 py-3 text-left">
                  <p className="text-[9px] font-bold text-[#8B95A1] mb-1">통화 자막</p>
                  <p className="text-[11px] text-[#191F28] leading-relaxed break-keep">
                    {chatHistory[chatHistory.length - 1].text}
                  </p>
                </div>
              )}
              {audioNotice && (
                <p className="text-[10px] text-amber-600 mt-2 break-keep">{audioNotice}</p>
              )}
            </div>
          )}

          {/* ───────── 문자(스미싱) 모드 ───────── */}
          {category === "smishing" && (
            <div className="flex-1 flex flex-col">
              <div className="bg-[#F8F9FA] rounded-xl p-3 border border-gray-100 flex items-center space-x-2.5 mb-4">
                <div className="w-8 h-8 bg-gray-300 text-white rounded-full flex items-center justify-center font-bold text-xs">
                  💬
                </div>
                <div>
                  <span className="text-xs font-bold text-[#191F28] block">알 수 없는 발신번호</span>
                  <span className="text-[10px] text-[#8B95A1]">발신자 정보 없음</span>
                </div>
              </div>

              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                <div className="text-center text-[10px] text-gray-400 my-2">오늘 수신된 메시지</div>
                {chatHistory.map((item, idx) => (
                  <div key={idx} className={`flex ${item.sender === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[85%] break-all ${
                      item.sender === "user"
                        ? "bg-[#0052CC] text-white rounded-br-none"
                        : "bg-gray-100 text-[#191F28] border border-gray-200 rounded-bl-none"
                    }`}>
                      <p className="whitespace-pre-wrap">{item.text}</p>
                      {item.sender === "bot" && /https?:\/\/\S+/.test(item.text) && (
                        <button
                          onClick={handleUrlClick}
                          disabled={waiting || ended}
                          className="text-[#0052CC] font-bold underline block mt-2 hover:opacity-80 transition disabled:opacity-40"
                        >
                          링크 열기
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {waiting && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3">
                      <span className="text-xs text-gray-400">입력 중...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {maxTurns && (
                <p className="text-[10px] text-gray-400 text-center mt-2">대화 {turnNo} / {maxTurns}</p>
              )}
            </div>
          )}
        </div>

        {/* 턴 처리 중 발생한 오류 (대화는 계속 가능) */}
        {error && sessionId && (
          <div className="mb-2 bg-red-50 border border-red-200 rounded-xl p-3 flex items-start justify-between gap-2">
            <p className="text-[11px] text-red-700 leading-relaxed break-keep">{error.text}</p>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs shrink-0">
              ✕
            </button>
          </div>
        )}

        {/* 위험 행동 즉시 개입 팝업 */}
        {riskWarning && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex justify-center items-center p-4 z-30 animate-fade-in">
            <div className="bg-white rounded-2xl p-5 text-center max-w-[320px] border border-red-100 shadow-2xl">
              <span className="text-3xl mb-2 block">🚨</span>
              <h3 className="text-sm font-extrabold text-[#191F28] mb-1.5">잠깐, 위험한 행동이에요!</h3>
              <p className="text-xs text-gray-600 leading-relaxed mb-4 break-keep">
                {riskWarning.message}
              </p>
              <button
                onClick={() => setRiskWarning(null)}
                className="w-full bg-[#0052CC] text-white py-2.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
              >
                확인하고 계속하기
              </button>
            </div>
          </div>
        )}

        {/* 판단 제출 모달 */}
        {showJudgment && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex justify-center items-center p-5 z-40 animate-fade-in">
            <div className="bg-white rounded-3xl p-6 text-center max-w-[320px] shadow-2xl border border-gray-100">
              <div className="w-12 h-12 bg-blue-50 text-[#0052CC] rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-3">
                🤔
              </div>
              <h3 className="text-base font-extrabold text-[#191F28] mb-2">이 연락, 어떻게 보셨나요?</h3>
              <p className="text-xs text-gray-600 leading-relaxed break-keep mb-5">
                방금 나눈 대화가 <b className="text-red-500">사기</b>였다고 생각하시나요,<br />
                아니면 <b className="text-[#0052CC]">정상적인 연락</b>이었다고 보시나요?
              </p>

              {judging ? (
                <div className="py-4">
                  <div className="w-8 h-8 border-4 border-blue-100 border-t-[#0052CC] rounded-full animate-spin mx-auto mb-3"></div>
                  <p className="text-[11px] text-[#8B95A1]">결과를 분석하고 있어요...</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    onClick={() => handleSubmitJudgment(true)}
                    className="w-full bg-red-500 text-white py-3.5 rounded-xl text-xs font-bold hover:bg-red-600 transition"
                  >
                    🚨 사기인 것 같아요 (신고)
                  </button>
                  <button
                    onClick={() => handleSubmitJudgment(false)}
                    className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
                  >
                    ✅ 정상적인 연락 같아요
                  </button>
                  {!ended && (
                    <button
                      onClick={() => setShowJudgment(false)}
                      className="w-full bg-[#F8F9FA] text-[#8B95A1] border border-gray-200 py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
                    >
                      좀 더 대화해볼게요
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ───────── 하단 컨트롤 ───────── */}
        <div className="pt-3 border-t border-gray-100">
          {category === "voice" ? (
            <div className="flex flex-col items-center gap-4 mb-1">
              <div className="flex items-center justify-center gap-6">
                <CallToggleButton
                  active={isMuted}
                  disabled={isListening || waiting}
                  onClick={() => setIsMuted((m) => !m)}
                  label="음소거"
                >
                  <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                    <line x1="1" y1="1" x2="23" y2="23" />
                    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
                    <path d="M17 16.95A7 7 0 0 1 5 12v-2" />
                    <path d="M19 10v2a7 7 0 0 1-.11 1.23" />
                    <line x1="12" y1="19" x2="12" y2="23" />
                    <line x1="8" y1="23" x2="16" y2="23" />
                  </svg>
                </CallToggleButton>

                <div className="flex flex-col items-center">
                  <button
                    onClick={handleMicToggle}
                    disabled={isMuted || waiting || ended}
                    aria-label="말하기"
                    className={`w-16 h-16 rounded-full flex items-center justify-center transition active:scale-95 shadow-md ${
                      isMuted || waiting || ended
                        ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                        : isListening
                        ? "bg-red-500 text-white shadow-red-500/30 animate-pulse"
                        : "bg-[#0052CC] text-white shadow-blue-500/30 hover:bg-blue-700"
                    }`}
                  >
                    <svg className="w-7 h-7 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                      <line x1="12" y1="19" x2="12" y2="23"/>
                      <line x1="8" y1="23" x2="16" y2="23"/>
                    </svg>
                  </button>
                  <span className="text-[10px] font-bold text-[#191F28] mt-1.5">말하기</span>
                </div>

                <CallToggleButton active={isSpeakerOn} onClick={handleSpeakerToggle} label="스피커">
                  <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  </svg>
                </CallToggleButton>
              </div>

              <p className="text-[10px] text-[#8B95A1]">
                {waiting
                  ? "상대방이 말하고 있어요..."
                  : ended
                  ? "통화가 종료되었어요"
                  : isMuted
                  ? "음소거 중이에요"
                  : isListening
                  ? "말씀한 뒤 마이크를 한 번 더 누르면 전송돼요"
                  : "마이크를 눌러 답변해보세요 (최대 30초)"}
              </p>

              <button
                onClick={() => setShowJudgment(true)}
                disabled={waiting || isListening}
                aria-label="통화 종료"
                className="w-14 h-14 bg-red-500 text-white rounded-full flex items-center justify-center shadow-lg shadow-red-500/30 hover:bg-red-600 transition active:scale-95 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed"
              >
                <svg className="w-6 h-6 fill-none stroke-current stroke-2 rotate-[135deg]" viewBox="0 0 24 24">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
              </button>
            </div>
          ) : (
            <>
              <div className="flex space-x-2 mb-3">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleUserResponse(inputText)}
                  maxLength={MAX_INPUT_CHARS}
                  disabled={waiting || ended}
                  placeholder={ended ? "대화가 종료되었어요" : "답장 메시지를 입력하세요..."}
                  className="flex-1 p-2.5 rounded-xl border border-gray-200 text-xs focus:border-[#0052CC] focus:outline-none disabled:bg-gray-50"
                />
                <button
                  onClick={() => handleUserResponse(inputText)}
                  disabled={waiting || ended || !inputText.trim()}
                  className="bg-[#0052CC] text-white px-3.5 py-2.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition disabled:bg-gray-200 disabled:text-gray-400"
                >
                  {waiting ? "..." : "전송"}
                </button>
              </div>

              <button
                onClick={() => setShowJudgment(true)}
                disabled={waiting}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99] disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed"
              >
                체험 종료하고 판단하기 →
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}
