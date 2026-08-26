import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

// 지금은 실제 분석 API가 없어서 정해진 시간만 기다렸다가 Report로 넘어감.
// 나중에 백엔드 리포트 생성 API가 생기면, SurveyLoading이 fetchRecommendation을
// 부르는 것과 같은 방식으로 여기서 실제 API를 호출하도록 바꾸면 됨.
const MIN_LOADING_MS = 1800;

export default function ReportLoading() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/report", { replace: true });
    }, MIN_LOADING_MS);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-center items-center p-6 text-center relative overflow-hidden">

        <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
          <div className="absolute w-full h-full border-4 border-blue-100 border-t-[#0052CC] rounded-full animate-spin"></div>
          <span className="text-2xl">📊</span>
        </div>

        <h2 className="text-lg font-extrabold text-[#191F28] mb-2 tracking-tight break-keep">
          대화 내용을 분석해서<br />맞춤형 리포트를 만들고 있어요
        </h2>
        <p className="text-xs text-[#8B95A1] leading-relaxed break-keep max-w-[260px]">
          체험하신 대화 패턴과 취약 행동을<br />분석해 진단 리포트를 구성 중입니다.
        </p>

        <div className="mt-8 px-4 py-2 bg-blue-50/60 rounded-full border border-blue-100">
          <span className="text-[11px] font-bold text-[#0052CC]">
            ✨ AI 대화 분석 진행 중...
          </span>
        </div>

      </div>
    </div>
  );
}
