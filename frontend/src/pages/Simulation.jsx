import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

function readStoredJson(key) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function readStoredUserName() {
  const savedUser = readStoredJson("userSurveyData");
  return savedUser?.userName || "고객";
}

function buildInitialSimulationState() {
  const userName = readStoredUserName();
  const savedScenario = readStoredJson("selectedScenario");

  let category = localStorage.getItem("selectedCategory") || "voice";
  if (savedScenario) {
    category = savedScenario.isVoice ? "voice" : "smishing";
  }

  if (category === "smishing") {
    return {
      category: "smishing",
      scenarioInfo: {
        caller: "국민건강보험공단",
        subInfo: "1577-0000 • 환급금 지급팀",
      },
      chatHistory: [
        {
          sender: "bot",
          text: `[국민건강보험] ${userName}님 환급금 184,500원 미신청 내역이 있습니다. 오늘 24시까지 아래 링크를 통해 신청해 주시기 바랍니다.`,
          url: "https://training-link.example/claim",
        },
      ],
      voiceOpening: null,
    };
  }

  const voiceOpening = `${userName} 고객님 맞으시죠? 서울중앙지검 김민수 수사관입니다. 현재 본인 명의 계좌가 대포통장 범죄 사건에 연루되어 연락드렸습니다. 당황하지 마시고 제 질문에 답변해 주세요.`;

  return {
    category: "voice",
    scenarioInfo: {
      caller: "서울중앙지검 김민수 수사관",
      subInfo: "02-1234-5678 • 이상 거래 감지팀",
    },
    chatHistory: [{ sender: "bot", text: voiceOpening }],
    voiceOpening,
  };
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

// 통화 화면 아이콘 버튼 (음소거/스피커처럼 토글되는 작은 원형 버튼)
function CallToggleButton({ active, onClick, label, children }) {
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={onClick}
        aria-label={label}
        aria-pressed={active}
        className={`w-12 h-12 rounded-full flex items-center justify-center transition active:scale-95 ${
          active ? "bg-[#0052CC] text-white" : "bg-gray-100 text-[#191F28] hover:bg-gray-200"
        }`}
      >
        {children}
      </button>
      <span className="text-[10px] font-semibold text-[#8B95A1] mt-1.5">{label}</span>
    </div>
  );
}

export default function Simulation() {
  const navigate = useNavigate();

  const [initialState] = useState(buildInitialSimulationState);
  const category = initialState.category;
  const scenarioInfo = initialState.scenarioInfo;

  const [chatHistory, setChatHistory] = useState(initialState.chatHistory);
  const [isListening, setIsListening] = useState(false);
  const [inputText, setInputText] = useState("");
  const [showSmishingWarning, setShowSmishingWarning] = useState(false);
  const [callSeconds, setCallSeconds] = useState(0);

  // ⚠️ 음소거/스피커는 실제 오디오 라우팅 없이 화면 연출/상태 토글용임
  // (브라우저에서 기기 스피커·마이크 하드웨어를 직접 전환하는 건 불가능함)
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(false);

  // 음성 모드일 때만 첫 마디를 TTS로 재생 (마운트 시 1회)
  useEffect(() => {
    const firstMessage = initialState.voiceOpening;
    if (firstMessage && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(firstMessage);
      utterance.lang = "ko-KR";
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }

    return () => {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, [initialState.voiceOpening]);

  // 통화 중 표시용 실시간 타이머 (음성 모드 전용)
  useEffect(() => {
    if (category !== "voice") return;
    const id = setInterval(() => setCallSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [category]);

  const handleUserResponse = (userMsg) => {
    if (!userMsg.trim()) return;

    const newHistory = [...chatHistory, { sender: "user", text: userMsg }];
    setChatHistory(newHistory);
    setInputText("");

    setTimeout(() => {
      let aiReply = "본인 명의 계좌가 맞는지 확인이 필요합니다. 안내해 드리는 지침에 따라주시기 바랍니다.";
      if (category === "smishing") {
        aiReply = "[국민건강보험] 본인인증이 완료되지 않았습니다. 안내된 절차를 다시 확인해 주세요.";
      }

      setChatHistory((prev) => [...prev, { sender: "bot", text: aiReply }]);

      if (category === "voice" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(aiReply);
        utterance.lang = "ko-KR";
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
      }
    }, 1200);
  };

  const handleUrlClick = () => {
    setShowSmishingWarning(true);
  };

  const handleMicToggle = () => {
    if (isMuted) return; // 음소거 상태에선 말하기 버튼 무시

    if (isListening) {
      setIsListening(false);
    } else {
      setIsListening(true);
      setTimeout(() => {
        setIsListening(false);
        handleUserResponse("제가 무슨 범죄 사건에 연루되었다는 건가요?");
      }, 1800);
    }
  };

  const handleFinish = () => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();

    // Report 페이지에서 나중에 "대화 기록 토글"로 보여줄 수 있도록 저장해둠.
    // 지금 화면엔 안 보이지만, 데이터는 여기서 미리 남겨두는 것.
    localStorage.setItem("lastSimulationTranscript", JSON.stringify(chatHistory));

    navigate("/report-loading");
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] sm:max-h-[844px] bg-white shadow-xl rounded-none sm:rounded-3xl border-0 sm:border border-gray-200 flex flex-col justify-between p-5 relative overflow-y-auto">

        <div className="flex-1 flex flex-col">
          <PageHeader padding="pt-1 pb-3 mb-2" bordered rightContent={<LiveBadge />} />

          {/* ───────────── 음성(전화) 모드: 실제 통화 화면 ───────────── */}
          {category === "voice" && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-4">
              <div className="w-24 h-24 bg-blue-50 border border-blue-100 rounded-full flex items-center justify-center text-blue-600 mb-5 shadow-inner">
                <svg className="w-11 h-11 fill-none stroke-current stroke-1.5" viewBox="0 0 24 24">
                  <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 1-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0v-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5m-4 0h4"/>
                </svg>
              </div>
              <h2 className="text-xl font-extrabold text-[#191F28] mb-1.5 tracking-tight">
                {scenarioInfo.caller}
              </h2>
              <p className="text-xs font-semibold text-[#8B95A1] mb-4">{scenarioInfo.subInfo}</p>
              <div className="flex items-center space-x-1.5">
                <span className="text-base font-mono font-bold text-[#0052CC]">{formatCallTime(callSeconds)}</span>
                <span className="text-[11px] text-gray-400">통화 중</span>
              </div>
            </div>
          )}

          {/* ───────────── 문자(스미싱) 모드: 기존 그대로 유지 ───────────── */}
          {category === "smishing" && (
            <div>
              <div className="bg-[#F8F9FA] rounded-xl p-3 border border-gray-100 flex items-center space-x-2.5 mb-4">
                <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold text-xs">
                  💬
                </div>
                <div>
                  <span className="text-xs font-bold text-[#191F28] block">{scenarioInfo.caller}</span>
                  <span className="text-[10px] text-[#8B95A1]">{scenarioInfo.subInfo}</span>
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
                      <p>{item.text}</p>
                      {item.url && (
                        <button
                          onClick={handleUrlClick}
                          className="text-[#0052CC] font-bold underline block mt-2 hover:opacity-80 transition"
                        >
                          {item.url}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {showSmishingWarning && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex justify-center items-center p-4 z-30 animate-fade-in">
            <div className="bg-white rounded-2xl p-5 text-center max-w-[320px] border border-red-100 shadow-2xl">
              <span className="text-3xl mb-2 block">🚨</span>
              <h3 className="text-sm font-extrabold text-[#191F28] mb-1.5">
                악의적 피싱 링크 감지!
              </h3>
              <p className="text-xs text-gray-600 leading-relaxed mb-4 break-keep">
                방금 클릭한 URL은 출처가 불분명한 <span className="text-red-500 font-bold">스미싱 피싱 링크</span>입니다. 실제 상황이라면 악성 앱이 설치되거나 개인정보가 유출될 위험이 있습니다.
              </p>
              <button
                onClick={() => setShowSmishingWarning(false)}
                className="w-full bg-[#0052CC] text-[#ffffff] py-2.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
              >
                확인하고 대화 계속하기
              </button>
            </div>
          </div>
        )}

        {/* ───────────── 하단 컨트롤 ───────────── */}
        <div className="pt-3 border-t border-gray-100">
          {category === "voice" ? (
            <div className="flex flex-col items-center gap-4 mb-1">
              {/* 음소거 · 말하기 · 스피커 3버튼 (실제 통화 화면 스타일) */}
              <div className="flex items-center justify-center gap-6">
                <CallToggleButton active={isMuted} onClick={() => setIsMuted((m) => !m)} label="음소거">
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
                    disabled={isMuted}
                    aria-label="말하기"
                    className={`w-16 h-16 rounded-full flex items-center justify-center transition active:scale-95 shadow-md ${
                      isMuted
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

                <CallToggleButton active={isSpeakerOn} onClick={() => setIsSpeakerOn((s) => !s)} label="스피커">
                  <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  </svg>
                </CallToggleButton>
              </div>

              <p className="text-[10px] text-[#8B95A1]">
                {isMuted ? "음소거 중이에요" : isListening ? "답변을 인식하고 있어요..." : "마이크를 눌러 답변해보세요"}
              </p>

              {/* 통화 종료 버튼 */}
              <button
                onClick={handleFinish}
                aria-label="통화 종료"
                className="w-14 h-14 bg-red-500 text-white rounded-full flex items-center justify-center shadow-lg shadow-red-500/30 hover:bg-red-600 transition active:scale-95"
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
                  placeholder="답장 메시지를 입력하세요..."
                  className="flex-1 p-2.5 rounded-xl border border-gray-200 text-xs focus:border-[#0052CC] focus:outline-none"
                />
                <button
                  onClick={() => handleUserResponse(inputText)}
                  className="bg-[#0052CC] text-white px-3.5 py-2.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition"
                >
                  전송
                </button>
              </div>

              <button
                onClick={handleFinish}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
              >
                체험 종료하고 분석 리포트 확인하기 →
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}
