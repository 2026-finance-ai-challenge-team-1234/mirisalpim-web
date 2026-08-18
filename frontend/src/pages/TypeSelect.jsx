import { useNavigate } from "react-router-dom";

export default function TypeSelect() {
  const navigate = useNavigate();

  // 1. 보이스피싱 / 스미싱 선택 시 -> 기존 ModeSelect로 이동
  const handleSelectInteractive = () => {
    localStorage.setItem("mainExperienceType", "interactive");
    navigate("/mode-select"); // 기존 ModeSelect 페이지 경로
  };

  // 2. 피싱 사이트 체험관 선택 시 -> 신규 피싱사이트 전용 페이지로 이동
  const handleSelectPhishingLab = () => {
    localStorage.setItem("mainExperienceType", "phishing-lab");
    navigate("/phishing-lab");
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      {/* 다른 페이지들과 동일한 컨테이너 규칙 적용: 웹에서 고정 812px+overflow-hidden 대신
          h-auto + min-h-[780px]로 통일해서 프레임 높이 불일치를 방지함 */}
      <div className="w-full max-w-[393px] min-h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col justify-between p-6 relative">

        <div>
          {/* Top Header — 다른 페이지와 동일하게 뒤로가기 버튼 추가 (모든 화면 뒤로가기 지원 원칙) */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2 border-b border-gray-100">
            <button
              onClick={() => navigate("/")}
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1"
              aria-label="뒤로가기"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 onClick={() => navigate("/")} className="text-lg font-extrabold text-[#0052CC] cursor-pointer tracking-tight">
              미리살핌
            </h1>
            <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition">
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </button>
          </header>

          {/* Title Section */}
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

          {/* Option Cards Area */}
          <div className="space-y-4">

            {/* Option 1: 보이스피싱 & 스미싱 (대화형 실시간 훈련) */}
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

            {/* Option 2: 피싱 사이트 정밀 분석 체험관 */}
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

        {/* Bottom Notice */}
        <div className="pt-2 pb-1 text-center">
          <p className="text-[11px] text-[#8B95A1] font-medium">
            💡 체험 중 입력되는 모든 정보는 가상의 모의 데이터입니다.
          </p>
        </div>

      </div>
    </div>
  );
}
