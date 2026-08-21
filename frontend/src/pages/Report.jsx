import { useState } from "react";
import { useNavigate } from "react-router-dom";

function readStoredUserName() {
  try {
    const savedUser = localStorage.getItem("userSurveyData");
    if (!savedUser) return "고객";

    const parsed = JSON.parse(savedUser);
    return parsed?.userName || "고객";
  } catch {
    return "고객";
  }
}

function buildInitialReportData() {
  const category = localStorage.getItem("selectedCategory") || "voice";

  const analysisResult = {
    type: "권위 압박형 기관사칭",
    vulnerableUtterances: [
      {
        // ⚠️ 실제 기관 도메인처럼 보이던 URL을 더미(.example)로 교체함
        quote: '"https://training-link.example/claim 링크 클릭 시도"',
        risk: "공식 도메인이 아닌 출처가 불분명한 URL에 접근함",
      },
    ],
    behaviorPatterns: [
      { title: "시간 압박 취약", desc: "서두르는 요구에 경계심이 낮아지고 판단을 조급히 내리는 경향이 있습니다.", status: "주의" },
      { title: "공식 채널 재확인 미흡", desc: "해당 기관 공식 대표 번호로 직접 사실 여부를 확인하는 절차가 누락되었습니다.", status: "취약" },
      { title: "주변 도움 요청", desc: "의심스러운 상황에서 가족이나 지인에게 공유하여 검증하는 습관이 필요합니다.", status: "보통" },
    ],
    solutions: [
      "검찰·경찰·금감원은 전화로 자금 이체나 보안 인증번호를 절대 요구하지 않습니다.",
      "의심스러운 연락은 일단 끊고, 해당 기관의 공식 대표 번호로 직접 전화하여 사실을 확인하세요.",
      "악성 앱 설치 요구 시 절대 응하지 마시고 주변 지인에게 상황을 공유하세요.",
    ],
  };

  if (category === "smishing") {
    analysisResult.type = "공공기관 스미싱 피싱";
  }

  return analysisResult;
}

export default function Report() {
  const navigate = useNavigate();

  const [userName] = useState(readStoredUserName);
  const [reportData] = useState(buildInitialReportData);
  const [shareToast, setShareToast] = useState(false);
  const [downloadToast, setDownloadToast] = useState(false);

  // 1. 일반 웹 URL 공유
  const handleShare = async () => {
    const shareData = {
      title: "미리살핌 - AI 금융 사기 대응 진단 리포트",
      text: `[미리살핌] ${userName}님의 금융사기 대응 습관 진단 리포트 결과를 공유합니다. 지금 바로 체험해 보세요!`,
      url: window.location.href,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.log("공유 에러:", err);
      }
    } else {
      navigator.clipboard.writeText(window.location.href);
      setShareToast(true);
      setTimeout(() => setShareToast(false), 2000);
    }
  };

  // 2. 어르신 부착용 / 카드뉴스 / PDF 출력용 핸들러 (백엔드 전송 연동 준비)
  const handleExportPrintable = () => {
    const printablePayload = {
      userName,
      reportType: reportData.type,
      behaviorSummary: reportData.behaviorPatterns.map((b) => `${b.title}: ${b.desc}`),
      coreSolutions: reportData.solutions,
      createdAt: new Date().toISOString(),
    };

    console.log("백엔드 PDF/카드뉴스 생성 요청 데이터:", printablePayload);

    setDownloadToast(true);
    setTimeout(() => {
      setDownloadToast(false);
      window.print();
    }, 1200);
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] min-h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col relative">

        {/* 1. 상단 헤더 */}
        <header className="flex justify-between items-center pt-4 pb-3 px-6 border-b border-gray-100 bg-white z-20">
          <h1
            onClick={() => navigate("/")}
            className="text-lg font-extrabold text-[#0052CC] cursor-pointer tracking-tight"
          >
            미리살핌
          </h1>
          <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition">
            <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
          </button>
        </header>

        {/* 2. 본문 영역 */}
        <div className="px-6 py-4 space-y-4">

          {/* Sub Title Section */}
          <section className="mb-2">
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md">
              AI 대화 분석 완료
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 tracking-tight">
              {userName}님의 금융사기<br />대응 습관 진단 리포트
            </h2>
            <p className="text-xs text-[#8B95A1] mt-1 break-keep">
              실제 모의 대화 발언과 행동 패턴을 분석한 결과입니다.
            </p>
          </section>

          {/* 대화 기반 취약 발언 분석 카드 */}
          <div className="bg-[#F8F9FA] border border-gray-100 rounded-2xl p-4">
            <h3 className="text-xs font-bold text-[#0052CC] mb-2 flex items-center space-x-1">
              <span>🔍</span>
              <span>체험 중 발견된 취약 대화 패턴</span>
            </h3>
            <p className="text-xs font-extrabold text-[#191F28] mb-3 break-keep">
              주요 사기 유형: {reportData.type}
            </p>

            <div className="space-y-2">
              {reportData.vulnerableUtterances.map((item, idx) => (
                <div key={idx} className="bg-white rounded-xl p-3 border border-gray-200 shadow-2xs">
                  <span className="text-[11px] font-bold text-red-500 block mb-1">
                    취약 발언 / 행동
                  </span>
                  <p className="text-xs font-semibold text-[#191F28] mb-1.5 italic">
                    {item.quote}
                  </p>
                  <p className="text-[11px] text-gray-600 leading-relaxed break-keep">
                    💡 <span className="font-semibold text-gray-700">AI 분석:</span> {item.risk}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 취약 행동 성향 분석 카드 */}
          <div>
            <h3 className="text-xs font-extrabold text-[#191F28] mb-2.5">
              취약 행동 성향 분석
            </h3>
            <div className="space-y-2">
              {reportData.behaviorPatterns.map((pattern, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded-xl p-3 flex justify-between items-start shadow-2xs">
                  <div>
                    <h4 className="text-xs font-bold text-[#191F28] mb-0.5">{pattern.title}</h4>
                    <p className="text-[11px] text-gray-500 leading-snug break-keep">{pattern.desc}</p>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md whitespace-nowrap ml-2 ${
                    pattern.status === "취약"
                      ? "bg-red-50 text-red-600"
                      : pattern.status === "주의"
                      ? "bg-amber-50 text-amber-600"
                      : "bg-blue-50 text-[#0052CC]"
                  }`}>
                    {pattern.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 맞춤 대응 행동 지침 */}
          <div className="bg-gradient-to-br from-blue-50/80 to-indigo-50/50 border border-blue-200/60 rounded-2xl p-4">
            <h3 className="text-xs font-extrabold text-[#0052CC] mb-2 flex items-center space-x-1">
              <span>🛡️</span>
              <span>이 3가지만 꼭 기억하세요!</span>
            </h3>
            <ul className="space-y-2">
              {reportData.solutions.map((sol, idx) => (
                <li key={idx} className="text-[11px] text-[#191F28] leading-relaxed flex items-start space-x-1.5 font-medium break-keep">
                  <span className="text-[#0052CC] font-bold">▪</span>
                  <span>{sol}</span>
                </li>
              ))}
            </ul>
          </div>

        </div>

        {/* 3. 버튼 영역: 2열 그리드로 공간 낭비 없는 4개 버튼 구조 */}
        <div className="p-4 mt-2 space-y-2 bg-white">
          {shareToast && (
            <div className="bg-gray-800 text-white text-[11px] text-center py-2 rounded-xl animate-fade-in">
              🔗 리포트 링크가 클립보드에 복사되었습니다!
            </div>
          )}

          {downloadToast && (
            <div className="bg-emerald-600 text-white text-[11px] text-center py-2 rounded-xl animate-fade-in">
              📄 부착용 안심 수칙 카드 생성 중...
            </div>
          )}

          {/* 상단 1열: 주요 기능 2개 (가족 공유 & 냉장고 부착용 카드 저장) */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleShare}
              className="bg-[#0052CC] text-white py-3 rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99] flex items-center justify-center space-x-1"
            >
              <span>👨‍👩‍👧‍👦</span>
              <span>가족 공유</span>
            </button>

            <button
              onClick={handleExportPrintable}
              className="bg-amber-500 text-white py-3 rounded-xl text-xs font-bold shadow-md shadow-amber-500/20 hover:bg-amber-600 transition active:scale-[0.99] flex items-center justify-center space-x-1"
            >
              <span>🧲</span>
              <span>부착용 카드 인쇄</span>
            </button>
          </div>

          {/* 하단 2열: 네비게이션 버튼 2개 */}
          <button
            onClick={() => navigate("/type-select")}
            className="w-full bg-blue-50 text-[#0052CC] border border-blue-100 py-2.5 rounded-xl text-xs font-bold hover:bg-blue-100 transition"
          >
            🔄 다른 훈련 연습해보기
          </button>

          <button
            onClick={() => navigate("/")}
            className="w-full bg-[#F8F9FA] text-[#8B95A1] border border-gray-200 py-2 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
          >
            🏠 홈으로 돌아가기
          </button>
        </div>

      </div>
    </div>
  );
}
