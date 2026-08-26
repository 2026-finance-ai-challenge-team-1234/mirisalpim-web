import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      {/* 원본 p-6 여백 및 레이아웃 100% 유지 */}
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">

        <div>
          <PageHeader />

          {/* 2. Hero Section */}
          <section className="mb-5">
            <h2 className="text-[22px] font-extrabold text-[#191F28] leading-[1.3] mb-2 tracking-tight break-keep">
              당하기 전에,<br />미리 겪어보세요.
            </h2>
            <p className="text-xs text-[#8B95A1] leading-relaxed mb-4 break-keep">
              실제 금융사기 시나리오를 바탕으로 AI 피싱범과 직접 대화하며 대응을 연습해보세요.
            </p>

            {/* 가치 제안 뱃지 */}
            <div className="bg-[#0052CC]/5 border border-[#0052CC]/15 rounded-xl p-3 flex items-start space-x-2">
              <span className="text-sm">⏱️</span>
              <p className="text-[11px] font-semibold text-[#0052CC] leading-snug break-keep">
                5분이면 충분해요. 당신의 금융 사기 대응 습관을 확인할 수 있어요.
              </p>
            </div>
          </section>

          {/* 3. Interactive Preview Card */}
          <div className="bg-[#F8F9FA] rounded-2xl p-3.5 mb-6 border border-gray-100">
            <div className="bg-white rounded-xl p-2.5 flex items-center justify-between shadow-xs mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                  %
                </div>
                <span className="text-xs font-bold text-[#191F28]">
                  서울중앙지검 김민수 수사관 (AI) • 00:12
                </span>
              </div>
              <span className="text-xs text-[#8B95A1]">🎙️</span>
            </div>

            <div className="bg-blue-50/60 rounded-xl p-3 border border-blue-100/50">
              <span className="text-[10px] font-bold text-[#0052CC] block mb-1">
                AI 피싱범 (검찰 사칭)
              </span>
              <p className="text-xs text-[#191F28] leading-relaxed font-medium break-keep">
                OOO 고객님 맞으시죠?<br />
                서울중앙지검 김민수 수사관입니다.<br />
                현재 본인 명의의 계좌가 대포통장 범죄 사건에 연루되어 연락드렸습니다.<br />
                당황하지 마시고 제 질문에 답변해 주세요.
              </p>
            </div>
          </div>
        </div>

        {/* 4. Bottom Action Area & Footer */}
        <div className="pt-2">
          <button
            onClick={() => navigate("/type-select")}
            className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
          >
            체험 시작하기
          </button>

          <p className="text-[10px] text-center text-[#8B95A1] mt-3 mb-1 whitespace-nowrap">
            본 서비스는 실제 금융 사기를 모의한 예방 훈련 서비스입니다.
          </p>
        </div>

      </div>
    </div>
  );
}
