import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Simulation() {
  const navigate = useNavigate();

  const [userName, setUserName] = useState("고객");
  const [category, setCategory] = useState("voice");
  const [chatHistory, setChatHistory] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [inputText, setInputText] = useState("");
  
  // 스미싱 경고 모달 상태 관리
  const [showSmishingWarning, setShowSmishingWarning] = useState(false);

  const [scenarioInfo, setScenarioInfo] = useState({
    caller: "서울중앙지검 김민수 수사관",
    subInfo: "02-1234-5678 • 이상 거래 감지팀",
  });

  useEffect(() => {
    const savedUser = localStorage.getItem("userSurveyData");
    let currentName = "고객";
    if (savedUser) {
      const parsed = JSON.parse(savedUser);
      if (parsed.userName) currentName = parsed.userName;
    }
    setUserName(currentName);

    const savedScenario = localStorage.getItem("selectedScenario");
    let currentCat = localStorage.getItem("selectedCategory") || "voice";

    if (savedScenario) {
      const parsedScenario = JSON.parse(savedScenario);
      if (parsedScenario.isVoice) {
        currentCat = "voice";
      } else {
        currentCat = "smishing";
      }
    }
    setCategory(currentCat);

    if (currentCat === "smishing") {
      setScenarioInfo({
        caller: "국민건강보험공단",
        subInfo: "1577-1000 • 환급금 지급팀",
      });
      setChatHistory([
        {
          sender: "bot",
          text: `[국민건강보험] ${currentName}님 환급금 184,500원 미신청 내역이 있습니다. 오늘 24시까지 아래 링크를 통해 신청해 주시기 바랍니다.`,
          url: "http://nhis-check.kr/claim",
        },
      ]);
    } else {
      setScenarioInfo({
        caller: "서울중앙지검 김민수 수사관",
        subInfo: "02-1234-5678 • 이상 거래 감지팀",
      });
      const firstMsg = `${currentName} 고객님 맞으시죠? 서울중앙지검 김민수 수사관입니다. 현재 본인 명의 계좌가 대포통장 범죄 사건에 연루되어 연락드렸습니다. 당황하지 마시고 제 질문에 답변해 주세요.`;
      
      setChatHistory([{ sender: "bot", text: firstMsg }]);

      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(firstMsg);
        utterance.lang = "ko-KR";
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
      }
    }

    return () => {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

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

  // 스미싱 URL 클릭 시 경고 팝업 모달 출력
  const handleUrlClick = () => {
    setShowSmishingWarning(true);
  };

  const handleMicToggle = () => {
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
    navigate("/report");
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      {/* PC에서도 모바일 비율로 깔끔하게 핏되는 Container */}
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] sm:max-h-[844px] bg-white shadow-xl rounded-none sm:rounded-3xl border-0 sm:border border-gray-200 flex flex-col justify-between p-5 relative overflow-y-auto">
        
        <div>
          {/* Header */}
          <header className="flex justify-between items-center pt-1 pb-3 mb-2 border-b border-gray-100">
            <h1 onClick={() => navigate("/")} className="text-lg font-extrabold text-[#0052CC] cursor-pointer tracking-tight">
              미리살핌
            </h1>
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
              <span className="text-[10px] font-bold text-red-500">실시간 모의 체험 중</span>
            </div>
          </header>

          {/* Voice Mode Header */}
          {category === "voice" && (
            <div className="bg-[#F8F9FA] rounded-xl p-3 border border-gray-100 flex items-center justify-between mb-4 shadow-xs">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 bg-[#0052CC]/10 text-[#0052CC] rounded-full flex items-center justify-center font-bold text-xs">
                  📞
                </div>
                <div>
                  <span className="text-xs font-bold text-[#191F28] block">{scenarioInfo.caller}</span>
                  <span className="text-[10px] text-[#8B95A1]">{scenarioInfo.subInfo}</span>
                </div>
              </div>
              <span className="text-xs text-[#0052CC] font-mono font-bold">00:42</span>
            </div>
          )}

          {/* Voice Chat */}
          {category === "voice" && (
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              {chatHistory.map((item, idx) => (
                <div key={idx} className={`flex ${item.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[85%] break-keep ${
                    item.sender === "user"
                      ? "bg-[#0052CC] text-white rounded-br-none"
                      : "bg-blue-50/70 border border-blue-100 text-[#191F28] rounded-bl-none font-medium"
                  }`}>
                    {item.sender === "bot" && (
                      <span className="text-[10px] font-bold text-[#0052CC] block mb-1">AI 피싱범 (통화 중)</span>
                    )}
                    {item.text}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Smishing Mode */}
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

        {/* 스미싱 링크 클릭 모달 경고 레이어 */}
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

        {/* Bottom Actions */}
        <div className="pt-3 border-t border-gray-100">
          {category === "voice" && (
            <div className="mb-3 flex flex-col items-center">
              <p className="text-[11px] text-[#0052CC] font-bold mb-2">
                {isListening ? "🎙️ 답변을 음성으로 인식 중..." : "🎙️ 마이크를 눌러 답변을 말해보세요"}
              </p>

              <button
                onClick={handleMicToggle}
                className={`w-14 h-14 rounded-full flex items-center justify-center transition active:scale-95 shadow-md ${
                  isListening
                    ? "bg-red-500 text-white shadow-red-500/30 animate-pulse"
                    : "bg-[#0052CC] text-white shadow-blue-500/30 hover:bg-blue-700"
                }`}
              >
                <svg className="w-6 h-6 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              </button>
            </div>
          )}

          {category === "smishing" && (
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
          )}

          <button
            onClick={handleFinish}
            className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
          >
            체험 종료하고 분석 리포트 확인하기 →
          </button>
        </div>

      </div>
    </div>
  );
}