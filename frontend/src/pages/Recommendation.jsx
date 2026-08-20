import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

// 채널(voice/smishing) 값에 따른 표시 라벨. title/description/reasons는 이제
// 백엔드 응답에 다 포함되어 있어서, 여기선 화면 표시용 라벨만 최소한으로 관리함.
const CHANNEL_META = {
  voice: { label: "📞 음성 통화 (Voice)", isVoice: true },
  smishing: { label: "📱 문자 URL (SMS)", isVoice: false },
};

export default function Recommendation() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [showNoticeModal, setShowNoticeModal] = useState(false);

  const recommendation = state?.recommendation;

  // SurveyLoading을 안 거치고 새로고침/직접 URL 접근한 경우 → 되돌려보냄
  useEffect(() => {
    if (!recommendation) {
      navigate("/mode-select", { replace: true });
    }
  }, [recommendation, navigate]);

  if (!recommendation) return null;

  const savedUser = localStorage.getItem("userSurveyData");
  const userName = savedUser ? JSON.parse(savedUser).userName || "고객" : "고객";

  const channelMeta = CHANNEL_META[recommendation.category] || CHANNEL_META.voice;

  const handleStartTraining = () => setShowNoticeModal(true);

  const handleConfirmStart = () => {
    setShowNoticeModal(false);
    localStorage.setItem(
      "selectedScenario",
      JSON.stringify({ ...recommendation, isVoice: channelMeta.isVoice })
    );

    if (channelMeta.isVoice) {
      navigate("/call-incoming");
    } else {
      navigate("/simulation");
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">

        <div>
          <header className="flex justify-between items-center pt-2 pb-4 mb-2">
            <button
              onClick={() => navigate("/survey")}
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 onClick={() => navigate("/")} className="text-lg font-extrabold text-[#0052CC] cursor-pointer">
              미리살핌
            </h1>
            <div className="w-5"></div>
          </header>

          <div className="mb-4">
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md">
              AI 분석 완료
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 tracking-tight">
              {userName}님에게<br />가장 필요한 훈련이에요.
            </h2>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-indigo-50/50 border-2 border-[#0052CC] rounded-2xl p-5 mb-5 shadow-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-[#0052CC]">{channelMeta.label}</span>
              <span className="text-xs bg-[#0052CC] text-white px-2 py-0.5 rounded-full font-bold">
                적합도 {recommendation.suitability}%
              </span>
            </div>

            <h3 className="text-base font-extrabold text-[#191F28] mb-1.5">{recommendation.title}</h3>
            <p className="text-xs text-gray-600 leading-relaxed mb-4">{recommendation.description}</p>

            <div className="bg-white/80 rounded-xl p-3 border border-blue-100">
              <span className="text-[11px] font-bold text-[#191F28] block mb-1.5">
                💡 왜 이 훈련을 추천했나요?
              </span>
              <ul className="space-y-1">
                {recommendation.reasons?.map((reason, idx) => (
                  <li key={idx} className="text-[11px] text-gray-600 flex items-center space-x-1.5">
                    <span className="text-[#0052CC] font-bold">✓</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="pt-2 space-y-2">
          <button
            onClick={handleStartTraining}
            className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
          >
            이 체험 시작하기 →
          </button>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              onClick={() => navigate("/survey")}
              className="w-full bg-[#F8F9FA] border border-gray-200 text-[#191F28] py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
            >
              🔄 설문 다시하기
            </button>
            <button
              onClick={() => navigate("/category-select")}
              className="w-full bg-[#F8F9FA] border border-gray-200 text-[#191F28] py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
            >
              🎯 직접 선택하기
            </button>
          </div>
        </div>

        {showNoticeModal && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex justify-center items-center p-5 z-50 animate-fade-in">
            <div className="bg-white rounded-3xl p-6 text-center max-w-[320px] shadow-2xl border border-gray-100 space-y-4">
              <div className="w-12 h-12 bg-blue-50 text-[#0052CC] rounded-full flex items-center justify-center text-xl font-bold mx-auto">
                💡
              </div>
              <div>
                <h3 className="text-base font-extrabold text-[#191F28] mb-2">실전 모의 훈련 안내</h3>
                <p className="text-xs text-gray-600 leading-relaxed break-keep">
                  훈련에는 <b className="text-red-500">실제 사기 상황</b>뿐만 아니라,<br />
                  <b className="text-[#0052CC]">정상적인 상황</b>도 함께 섞여 있어요.<br /><br />
                  무조건 의심하기보다, 상황을 차분히 살펴보고<br />
                  판단하는 연습이라고 생각해 주세요!
                </p>
              </div>
              <button
                onClick={handleConfirmStart}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition shadow-md shadow-blue-500/20"
              >
                이해했습니다 (체험 시작) →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
