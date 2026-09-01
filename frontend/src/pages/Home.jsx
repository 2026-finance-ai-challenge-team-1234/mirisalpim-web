import { useNavigate } from "react-router-dom";

// 파비콘과 같은 심볼. 외부 파일 대신 인라인으로 두어 크기·색을 화면에 맞게 바로 조절한다.
function BrandLogo({ className = "" }) {
  return (
    <svg viewBox="0 0 64 64" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect width="64" height="64" rx="16" fill="#1B2E52" />
      <path
        d="M32 12 L48 18 V32 C48 42 32 50 32 50 C32 50 16 42 16 32 V18 Z"
        fill="none"
        stroke="#5B8DEF"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M26 32 V32" stroke="#8FB4F7" strokeWidth="4" strokeLinecap="round" />
      <path d="M32 26 V38" stroke="#5B8DEF" strokeWidth="4" strokeLinecap="round" />
      <path d="M38 30 V34" stroke="#8FB4F7" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

const EXPERIENCES = ["전화", "문자", "가짜 사이트"];

export default function Home() {
  const navigate = useNavigate();

  return (
    // 메인만 단색 남색으로 두어 훈련 화면(흰 배경 + 카드 UI)과 확실히 구분한다.
    // 바깥은 연한 회색이라 웹에서 볼 때 프레임이 카드처럼 떠 보인다.
    // 그라데이션·광원 같은 장식은 넣지 않는다 — 로고와 타이포만으로 정리한다.
    <div className="min-h-[100dvh] bg-[#EEF1F6] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-[#1B2E52] sm:rounded-3xl shadow-2xl flex flex-col justify-between px-7 py-12">

        <div />

        {/* 중앙: 로고 → 이름 → 설명 */}
        <div className="flex flex-col items-center text-center">
          <BrandLogo className="w-28 h-28 mb-8" />

          <h1 className="text-[30px] font-extrabold text-white tracking-tight mb-2.5">
            미리살핌
          </h1>

          <p className="text-sm font-bold text-[#7BA5F5] mb-6">
            당하기 전에, 미리 겪어보세요
          </p>

          <p className="text-[13px] text-[#A8BCDD] leading-[1.7] break-keep">
            걸려온 연락이 사기인지 아닌지 직접 판단해보고,
            <br />
            내 대응 습관을 진단받는 훈련이에요.
          </p>

          {/* 체험 종류는 텍스트로만. 이모지·카드 없이 구분선으로 정리한다. */}
          <div className="flex items-center gap-3 mt-8 text-[11px] font-semibold text-[#8296B8]">
            {EXPERIENCES.map((label, idx) => (
              <span key={label} className="flex items-center gap-3">
                {label}
                {idx < EXPERIENCES.length - 1 && (
                  <span className="w-px h-2.5 bg-[#3A4E75]" aria-hidden="true" />
                )}
              </span>
            ))}
          </div>
        </div>

        {/* 하단 */}
        <div>
          <p className="text-[11px] text-center text-[#8296B8] leading-snug break-keep mb-5">
            모든 연락이 사기는 아니에요.
            <br />
            정상적인 안내도 섞여 있어요.
          </p>

          <button
            onClick={() => navigate("/type-select")}
            className="w-full bg-white text-[#1B2E52] py-4 rounded-xl text-sm font-extrabold hover:bg-[#EEF3FB] transition active:scale-[0.99]"
          >
            체험 시작하기
          </button>

          <p className="text-[10px] text-center text-[#5E7093] mt-4">
            5분이면 충분해요 · 실제 금융사기를 모의한 예방 훈련입니다
          </p>
        </div>

      </div>
    </div>
  );
}