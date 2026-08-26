// src/components/PageHeader.jsx
//
// 모든 페이지가 각자 복붙해서 쓰던 헤더를 하나로 통일함.
// - 알림/설정 아이콘은 완전히 제거함 (필요해지면 rightContent로 다시 넣을 수 있음)
// - 로고는 항상 절대좌표로 정중앙에 고정함 (좌/우 콘텐츠 폭이 서로 달라도 로고가 안 밀림 —
//   PhishingLab.jsx에서 쓰던 "100% 오차 없는 정중앙 헤더" 방식을 공용 컴포넌트로 승격함)
//
// 사용 예:
//   <PageHeader onBack={() => navigate("/mode-select")} />
//   <PageHeader />                                                         // 뒤로가기 없음 (Home 등)
//   <PageHeader onBack={...} variant="title" label="기본 정보 입력" />      // 로고 대신 페이지 제목
//   <PageHeader onBack={...} rightContent={<LiveBadge />} />               // 우측에 커스텀 콘텐츠

import { useNavigate } from "react-router-dom";

export default function PageHeader({
  onBack,
  label = "미리살핌",
  variant = "logo", // "logo": 클릭 시 홈으로 이동하는 파란 로고 / "title": 클릭 안 되는 검정 페이지 제목
  bordered = false,
  rightContent = null,
  padding = "pt-2 pb-4 mb-2",
  className = "",
}) {
  const navigate = useNavigate();

  const centerClass =
    variant === "logo"
      ? "text-lg font-extrabold text-[#0052CC] tracking-tight cursor-pointer"
      : "text-sm font-bold text-[#191F28]";

  return (
    <header
      className={`relative flex items-center justify-between min-h-9 ${padding} ${
        bordered ? "border-b border-gray-100" : ""
      } ${className}`}
    >
      {onBack ? (
        <button
          onClick={onBack}
          aria-label="뒤로가기"
          className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1 z-10"
        >
          <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      ) : (
        <div className="w-5 z-10" />
      )}

      <h1
        onClick={variant === "logo" ? () => navigate("/") : undefined}
        className={`absolute left-1/2 -translate-x-1/2 whitespace-nowrap z-0 ${centerClass}`}
      >
        {label}
      </h1>

      <div className="z-10">{rightContent ?? <div className="w-5" />}</div>
    </header>
  );
}
