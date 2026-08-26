import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

export default function TypeSelect() {
  const navigate = useNavigate();

  const handleSelectInteractive = () => {
    localStorage.setItem("mainExperienceType", "interactive");
    navigate("/mode-select");
  };

  const handleSelectPhishingLab = () => {
    localStorage.setItem("mainExperienceType", "phishing-lab");
    navigate("/phishing-lab");
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] min-h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col justify-between p-6 relative">

        <div>
          <PageHeader onBack={() => navigate("/")} bordered />

          <section className="mt-4 mb-6">
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md">
              체험 모드 선택
            </span>
            <h2 className="text-[21px] font-extrabold text-[#191F28] leading-[1.3] mt-2.5 tracking-tight">
              어떤 방식의 모의 훈련을<br />진행해 볼까요?
            </h2>
            <p className="text-xs text-[#8B95A1] mt-1.5 break-keep">
              원하시는 훈련 방식을 선택하시면 맞춤형 체험이 시작됩니다.
            </p>
          </section>

          <div className="space-y-4">

            <button
              onClick={handleSelectInteractive}
              className="w-full text-left bg-[#F8F9FA] hover:bg-blue-50/50 border border-gray-200 hover:border-[#0052CC] rounded-2xl p-5 cursor-pointer transition-all duration-200 shadow-2xs group relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-2xl">📞💬</span>
                <span className="text-[10px] font-extrabold text-[#0052CC] bg-blue-100/70 px-2 py-0.5 rounded-md">
                  실시간 AI 연동
                </span>
              </div>
              <h3 className="text-sm font-extrabold text-[#191F28] group-hover:text-[#0052CC] transition mb-1">
                보이스피싱 & 스미싱 모의 훈련
              </h3>
              <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep font-medium">
                실제 음성 통화 및 메신저 인터페이스 환경에서 AI 피싱범과 직접 주고받는 대화형 맞춤 시뮬레이션입니다.
              </p>
            </button>

            <button
              onClick={handleSelectPhishingLab}
              className="w-full text-left bg-[#F8F9FA] hover:bg-blue-50/50 border border-gray-200 hover:border-[#0052CC] rounded-2xl p-5 cursor-pointer transition-all duration-200 shadow-2xs group relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-2xl">🌐</span>
                <span className="text-[10px] font-extrabold text-amber-700 bg-amber-100/70 px-2 py-0.5 rounded-md">
                  시나리오 체험관
                </span>
              </div>
              <h3 className="text-sm font-extrabold text-[#191F28] group-hover:text-[#0052CC] transition mb-1">
                피싱 사이트 정밀 분석 체험관
              </h3>
              <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep font-medium">
                정교하게 모방된 가짜 공공기관 및 금융사 브라우저 웹사이트의 주요 수법을 단계별로 식별하고 탐색합니다.
              </p>
            </button>

          </div>
        </div>

        <div className="pt-2 pb-1 text-center">
          <p className="text-[11px] text-[#8B95A1] font-medium">
            💡 체험 중 입력되는 모든 정보는 가상의 모의 데이터입니다.
          </p>
        </div>

      </div>
    </div>
  );
}
