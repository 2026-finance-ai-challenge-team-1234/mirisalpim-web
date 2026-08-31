import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { useTrainee } from "../hooks/useTrainee";

function readPrevTrack() {
  return localStorage.getItem("selectedScenario") ? "ai" : "direct";
}

export default function CallIncoming() {
  const navigate = useNavigate();
  const { trainee } = useTrainee();
  const [prevTrack] = useState(readPrevTrack);

  // 새로고침 등으로 Context 가 비면 기본 호칭으로 표시한다 (저장하지 않는 값이라 자연스러운 동작).
  const userName = trainee.name || "고객";

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
          {/* ⚠️ 발신자 정보는 절대 구체적으로 노출하면 안 됨.
              시나리오 중 일부는 정상 상황이라, 여기서 기관명을 보여주면 사기 여부가 미리 드러남.
              실제 보이스피싱도 발신자가 특정되지 않은 채로 걸려오므로 이게 더 현실적임. */}
          <div className="flex flex-col items-center text-center mt-4">
            <div className="w-20 h-20 bg-gray-100 border border-gray-200 rounded-full flex items-center justify-center text-gray-500 mb-5 shadow-inner">
              <svg className="w-10 h-10 fill-none stroke-current stroke-1.5" viewBox="0 0 24 24">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>

            <h2 className="text-xl font-extrabold text-[#191F28] mb-1.5 tracking-tight">
              알 수 없는 번호
            </h2>
            <p className="text-xs font-semibold text-[#8B95A1] mb-6">
              발신자 정보 없음
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