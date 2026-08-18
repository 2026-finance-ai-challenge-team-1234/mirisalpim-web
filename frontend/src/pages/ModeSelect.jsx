import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function ModeSelect() {
  const navigate = useNavigate();
  const [selectedMode, setSelectedMode] = useState(null);

  const handleRecommendSelect = () => {
    if (selectedMode === "recommend") {
      navigate("/survey");
    } else {
      setSelectedMode("recommend");
    }
  };

  const handleDirectSelect = () => {
    if (selectedMode === "direct") {
      navigate("/category-select");
    } else {
      setSelectedMode("direct");
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">
        
        <div>
          {/* Top Header: 좌측 뒤로가기 버튼, 중앙 로고 */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-4">
            <button 
              onClick={() => navigate("/type-select")}
              aria-label="뒤로가기"
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 
              onClick={() => navigate("/")}
              className="text-xl font-extrabold text-[#0052CC] tracking-tight cursor-pointer"
            >
              미리살핌
            </h1>
            <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition">
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </button>
          </header>

          {/* Title Section */}
          <section className="mb-6">
            <h2 className="text-[22px] font-extrabold text-[#191F28] leading-[1.3] mb-2 tracking-tight">
              어떤 방식으로<br />체험해볼까요?
            </h2>
            <p className="text-xs text-[#8B95A1] leading-relaxed break-keep">
              카드의 설명을 읽고 체험 방식을 골라주세요.
            </p>
          </section>

          {/* Mode Cards Area */}
          <div className="space-y-4">
            
            {/* [카드 1] 알고리즘 맞춤 추천 */}
            <div
              onClick={handleRecommendSelect}
              className={`p-5 rounded-2xl border-2 transition-all cursor-pointer ${
                selectedMode === "recommend"
                  ? "bg-blue-50/40 border-[#0052CC]"
                  : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
              }`}
            >
              <div className="flex items-center space-x-1.5 mb-2">
                <span className="text-sm">✨</span>
                <span className="text-sm font-bold text-[#191F28]">알고리즘 맞춤 추천</span>
              </div>
              <p className="text-xs text-[#8B95A1] leading-relaxed mb-4 break-keep">
                간단한 질문에 답하면 연령대와 평소 습관, 걱정되는 상황에 대한 답변을 분석해서 맞춤형 알고리즘이 지금 나에게 가장 필요한 훈련을 찾아드려요.
              </p>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRecommendSelect();
                }}
                className={`w-full py-3 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 ${
                  selectedMode === "recommend"
                    ? "bg-[#0052CC] text-white shadow-xs"
                    : "bg-white text-[#191F28] border border-gray-200"
                }`}
              >
                <span className="whitespace-nowrap">알고리즘 추천 받기 →</span>
              </button>
            </div>

            {/* [카드 2] 직접 선택 */}
            <div
              onClick={handleDirectSelect}
              className={`p-5 rounded-2xl border-2 transition-all cursor-pointer ${
                selectedMode === "direct"
                  ? "bg-blue-50/40 border-[#0052CC]"
                  : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
              }`}
            >
              <div className="flex items-center space-x-1.5 mb-2">
                <span className="text-sm">📂</span>
                <span className="text-sm font-bold text-[#191F28]">직접 선택</span>
              </div>
              <p className="text-xs text-[#8B95A1] leading-relaxed mb-4 break-keep">
                부모님이나 자녀를 대신해 보호자가 훈련을 골라줄 수도 있고, 이미 겪었던 특정 사기 유형을 콕 짚어 다시 연습해볼 수도 있어요.
              </p>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDirectSelect();
                }}
                className={`w-full py-3 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 ${
                  selectedMode === "direct"
                    ? "bg-[#0052CC] text-white shadow-xs"
                    : "bg-white text-[#191F28] border border-gray-200"
                }`}
              >
                <span className="whitespace-nowrap">직접 선택하기 →</span>
              </button>
            </div>

          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 text-center">
          <p className="text-[10px] text-[#8B95A1]">
            미리살핌 · AI 금융 보안 비서
          </p>
        </div>

      </div>
    </div>
  );
}