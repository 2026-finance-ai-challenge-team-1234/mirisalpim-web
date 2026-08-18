import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function SurveyLoading() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/recommendation");
    }, 2200);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-center items-center p-6 text-center relative overflow-hidden">
        
        {/* 로딩 애니메이션 */}
        <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
          <div className="absolute w-full h-full border-4 border-blue-100 border-t-[#0052CC] rounded-full animate-spin"></div>
          <span className="text-2xl">✨</span>
        </div>

        <h2 className="text-lg font-extrabold text-[#191F28] mb-2 tracking-tight break-keep">
          답변을 바탕으로<br />맞춤형 훈련을 찾고 있어요
        </h2>
        <p className="text-xs text-[#8B95A1] leading-relaxed break-keep max-w-[260px]">
          평소 금융 이용 습관과 취약 상황을 분석해<br />지금 가장 도움이 될 시나리오를 구성 중입니다.
        </p>

        <div className="mt-8 px-4 py-2 bg-blue-50/60 rounded-full border border-blue-100">
          <span className="text-[11px] font-bold text-[#0052CC]">
            ✨ 규칙 기반 추천 알고리즘 가동 중...
          </span>
        </div>

      </div>
    </div>
  );
}