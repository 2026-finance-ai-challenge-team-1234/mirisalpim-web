import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

function readStoredUserName() {
  try {
    const savedData = localStorage.getItem("userSurveyData");
    if (!savedData) return "고객";

    const parsed = JSON.parse(savedData);
    return parsed?.userName || "고객";
  } catch {
    return "고객";
  }
}

function readPrevTrack() {
  return localStorage.getItem("selectedScenario") ? "ai" : "direct";
}

export default function CallIncoming() {
  const navigate = useNavigate();
  const [userName] = useState(readStoredUserName);
  const [prevTrack] = useState(readPrevTrack);

  const handleDecline = () => {
    if (prevTrack === "ai") {
      navigate("/recommendation");
    } else {
      navigate("/user-info");
    }
  };

  const handleAccept = () => {
    navigate("/simulation");
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-hidden">

        <div>
          <PageHeader />

          {/* Simulation Notice Tag */}
          <div className="flex justify-center mb-8">
            <div className="bg-red-50 border border-red-200 text-red-600 px-3 py-1.5 rounded-full text-[11px] font-bold animate-pulse flex items-center space-x-1">
              <span>🚨</span>
              <span>[모의 훈련] 실제 전화 수신 중</span>
            </div>
          </div>

          {/* Caller Information Area */}
          <div className="flex flex-col items-center text-center mt-4">
            <div className="w-20 h-20 bg-blue-50 border border-blue-100 rounded-full flex items-center justify-center text-blue-600 mb-5 shadow-inner">
              <svg className="w-10 h-10 fill-none stroke-current stroke-1.5" viewBox="0 0 24 24">
                <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 1-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0v-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5m-4 0h4"/>
              </svg>
            </div>

            <h2 className="text-xl font-extrabold text-[#191F28] mb-1.5 tracking-tight">
              서울중앙지검 검찰청
            </h2>
            <p className="text-xs font-semibold text-[#8B95A1] mb-6">
              02-1234-5678 • 이상 거래 감지팀
            </p>

            <div className="flex items-center space-x-1.5 text-xs font-bold text-[#0052CC] bg-blue-50/80 px-3 py-1.5 rounded-lg">
              <span className="w-2 h-2 bg-[#0052CC] rounded-full animate-ping"></span>
              <span>{userName}님께 실시간 모의 전화가 걸려오고 있습니다...</span>
            </div>
          </div>
        </div>

        {/* Call Control Buttons Area */}
        <div className="pb-8 pt-4">

          <div className="flex justify-around items-center px-4">

            {/* Decline Button */}
            <div className="flex flex-col items-center">
              <button
                onClick={handleDecline}
                className="w-16 h-16 bg-red-500 text-white rounded-full flex items-center justify-center shadow-lg shadow-red-500/30 hover:bg-red-600 transition active:scale-95 mb-2"
                aria-label="거절"
              >
                <svg className="w-7 h-7 fill-none stroke-current stroke-2 rotate-[135deg]" viewBox="0 0 24 24">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
              </button>
              <span className="text-xs font-bold text-[#8B95A1]">거절</span>
            </div>

            {/* Accept Button */}
            <div className="flex flex-col items-center relative">
              <div className="absolute w-16 h-16 bg-emerald-500/30 rounded-full animate-ping"></div>

              <button
                onClick={handleAccept}
                className="w-16 h-16 bg-emerald-500 text-white rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30 hover:bg-emerald-600 transition active:scale-95 mb-2 relative z-10"
                aria-label="전화 받기"
              >
                <svg className="w-7 h-7 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
              </button>
              <span className="text-xs font-bold text-[#191F28]">전화 받기</span>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
