import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

// 판단(POST /judgment) API가 채점·진단까지 한 번에 처리하므로,
// 여기서 별도 API를 부르지 않고 Simulation이 넘겨준 결과를 그대로 Report로 전달함.
// 최소 시간을 두는 건, 결과가 즉시 도착해도 화면이 번쩍이지 않게 하려는 연출용.
const MIN_LOADING_MS = 900;

export default function ReportLoading() {
  const navigate = useNavigate();
  const { state } = useLocation();

  useEffect(() => {
    const report = state?.report;
    const transcript = state?.transcript;

    const timer = setTimeout(() => {
      if (report) {
        navigate("/report", { state: { report, transcript }, replace: true });
      } else {
        // 판단을 거치지 않고 직접 들어온 경우 (새로고침 등) → 훈련 선택으로 되돌림
        navigate("/type-select", { replace: true });
      }
    }, MIN_LOADING_MS);

    return () => clearTimeout(timer);
  }, [state, navigate]);

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