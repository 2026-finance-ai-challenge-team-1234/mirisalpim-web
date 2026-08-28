import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

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

// 등급별 표시 스타일. 점수는 쓰지 않고 등급만 노출한다(설계 확정 사항).
const GRADE_META = {
  S: { label: "S", tone: "bg-[#0052CC] text-white", desc: "최초 단서를 즉시 알아차렸어요" },
  A: { label: "A", tone: "bg-blue-500 text-white", desc: "빠르게 알아차렸어요" },
  B: { label: "B", tone: "bg-emerald-500 text-white", desc: "알아차렸지만 조금 늦었어요" },
  C: { label: "C", tone: "bg-amber-500 text-white", desc: "위험한 행동 이후에 알아차렸어요" },
  D: { label: "D", tone: "bg-red-500 text-white", desc: "끝까지 알아차리지 못했어요" },
  오탐: { label: "오탐", tone: "bg-gray-500 text-white", desc: "정상적인 연락을 사기로 판단했어요" },
};

// 타임라인 마커 3종 (백엔드 확정: tellPoint / riskyAction / judgment)
// 한 턴에 여러 마커가 겹칠 수 있어 배열로 오고, 아무 일 없던 턴은 아예 안 옴
const MARKER_META = {
  tellPoint: { icon: "🔴", label: "놓친 단서", color: "text-red-500" },
  riskyAction: { icon: "⚠️", label: "위험 행동", color: "text-amber-600" },
  judgment: { icon: "✋", label: "판단 시점", color: "text-[#0052CC]" },
};

// 백엔드 확정 5종 (turns의 riskWarnings[].type과 동일한 문자열)
const RISKY_ACTION_LABEL = {
  personalInfo: "개인정보 제공",
  linkClick: "링크 클릭",
  appInstall: "앱 설치 동의",
  transferConsent: "송금 동의",
  isolationAcceptance: "고립 요구 수용",
};

export default function Report() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const [userName] = useState(readStoredUserName);
  const [shareToast, setShareToast] = useState(false);
  const [downloadToast, setDownloadToast] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);

  const report = state?.report;

  // 판단을 거치지 않고 직접 들어온 경우(새로고침/URL 직접 입력) → 훈련 선택으로
  useEffect(() => {
    if (!report) navigate("/type-select", { replace: true });
  }, [report, navigate]);

  if (!report) return null;

  const isFalseAlarm = report.grade === "오탐";
  const gradeMeta = GRADE_META[report.grade] || GRADE_META.B;

  const handleShare = async () => {
    const shareData = {
      title: "미리살핌 - 금융사기 대응 진단 리포트",
      text: `[미리살핌] ${userName}님의 금융사기 대응 훈련 결과입니다. 지금 바로 체험해 보세요!`,
      url: window.location.origin,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.log("공유 에러:", err);
      }
    } else {
      navigator.clipboard.writeText(window.location.origin);
      setShareToast(true);
      setTimeout(() => setShareToast(false), 2000);
    }
  };

  const handleExportPrintable = () => {
    setDownloadToast(true);
    setTimeout(() => {
      setDownloadToast(false);
      window.print();
    }, 1200);
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] min-h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col relative">

        <PageHeader padding="pt-4 pb-3" bordered className="px-6 bg-white z-20" />

        <div className="px-6 py-4 space-y-4">

          {/* ───────── ① 한 줄 결과 (등급) ───────── */}
          <section>
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md">
              훈련 결과
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 tracking-tight">
              {userName}님의<br />금융사기 대응 진단
            </h2>
          </section>

          <div className={`rounded-2xl p-5 border-2 ${isFalseAlarm ? "border-gray-300 bg-gray-50" : "border-[#0052CC] bg-gradient-to-br from-blue-50 to-indigo-50/50"}`}>
            <div className="flex items-center space-x-3 mb-3">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-extrabold shrink-0 ${gradeMeta.tone}`}>
                {gradeMeta.label}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-extrabold text-[#191F28] break-keep">{gradeMeta.desc}</p>
                {report.isCorrect !== undefined && (
                  <p className={`text-[11px] font-bold mt-0.5 ${report.isCorrect ? "text-emerald-600" : "text-red-500"}`}>
                    {report.isCorrect ? "✓ 정확하게 판단했어요" : "✗ 판단이 정확하지 않았어요"}
                  </p>
                )}
              </div>
            </div>

            {/* 판별 시점 비교 — 오탐일 때는 의미가 없어 숨김 */}
            {!isFalseAlarm && (
              <div className="bg-white/80 rounded-xl p-3 border border-blue-100 space-y-1">
                {report.judgedTurn != null ? (
                  <p className="text-[11px] text-[#191F28] font-medium break-keep">
                    <b className="text-[#0052CC]">{report.judgedTurn}번째</b> 대화에서 알아차렸어요.
                  </p>
                ) : (
                  // judgedTurn이 null이면 판단 없이 최대 턴까지 대화가 이어진 경우
                  <p className="text-[11px] text-[#191F28] font-medium break-keep">
                    대화가 끝날 때까지 사기라는 것을 알아차리지 못했어요.
                  </p>
                )}
                {report.firstDetectableTurn != null && (
                  <p className="text-[11px] text-gray-600 break-keep">
                    가장 빠른 판별 가능 시점은 <b>{report.firstDetectableTurn}번째</b> 대화였어요.
                  </p>
                )}
              </div>
            )}

            {report.summary && (
              <p className="text-[11px] text-gray-600 leading-relaxed break-keep mt-3">
                {report.summary}
              </p>
            )}
          </div>

          {/* 오탐 전용 안내 — 의심한 것 자체를 실패로 비난하지 않음 */}
          {isFalseAlarm && (
            <div className="bg-blue-50/60 border border-blue-100 rounded-2xl p-4">
              <h3 className="text-xs font-extrabold text-[#0052CC] mb-1.5 flex items-center space-x-1">
                <span>💡</span>
                <span>이번 상황은 정상적인 안내였어요</span>
              </h3>
              <p className="text-[11px] text-[#191F28] leading-relaxed break-keep">
                다만 의심하고 다시 확인하려는 행동 자체는 안전한 대응이에요.
                다음에는 안내받은 링크나 번호 대신, 공식 앱·대표번호를 통해 직접 진위를 확인해보세요.
              </p>
            </div>
          )}

          {/* ───────── ② 잘한 점 ───────── */}
          {report.strength && (
            <div className="bg-emerald-50/60 border border-emerald-100 rounded-2xl p-4">
              <h3 className="text-xs font-extrabold text-emerald-700 mb-1.5 flex items-center space-x-1">
                <span>✅</span>
                <span>잘한 점</span>
              </h3>
              <p className="text-[11px] text-[#191F28] leading-relaxed break-keep">{report.strength}</p>
            </div>
          )}

          {/* ───────── ③ 대화 리플레이 타임라인 ───────── */}
          {report.timeline?.length > 0 && (
            <div>
              <button
                onClick={() => setShowTimeline((v) => !v)}
                className="w-full flex items-center justify-between mb-2.5"
              >
                <h3 className="text-xs font-extrabold text-[#191F28]">대화 흐름 다시보기</h3>
                <span className="text-[10px] text-[#8B95A1]">{showTimeline ? "접기 ▲" : "펼치기 ▼"}</span>
              </button>

              {showTimeline && (
                <div className="bg-[#F8F9FA] border border-gray-100 rounded-2xl p-4 space-y-2 animate-fade-in">
                  {report.timeline.map((item, idx) => {
                    const markers = item.markers || [];
                    return (
                      <div key={idx} className="flex items-start space-x-2.5">
                        <span className="text-[10px] font-mono font-bold text-gray-400 w-4 shrink-0 mt-0.5">
                          {item.turn}
                        </span>
                        <div className="flex-1 min-w-0">
                          {markers.length === 0 ? (
                            <span className="text-[11px] text-gray-300">●</span>
                          ) : (
                            <div className="flex flex-wrap gap-x-2 gap-y-1">
                              {markers.map((m, i) => {
                                const meta = MARKER_META[m];
                                if (!meta) return null;
                                return (
                                  <span key={i} className={`text-[10px] font-bold ${meta.color}`}>
                                    {meta.icon} {meta.label}
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  <div className="pt-2 mt-1 border-t border-gray-200 flex flex-wrap gap-x-3 gap-y-1">
                    {Object.values(MARKER_META).map((m, i) => (
                      <span key={i} className="text-[9px] text-gray-400">
                        {m.icon} {m.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ───────── ④ 놓친 단서 ───────── */}
          {report.missedTellPoints?.length > 0 && (
            <div>
              <h3 className="text-xs font-extrabold text-[#191F28] mb-2.5">놓친 단서</h3>
              <div className="space-y-2">
                {report.missedTellPoints.map((tp, idx) => (
                  <div key={tp.id || idx} className="bg-white border border-gray-200 rounded-xl p-3 shadow-2xs">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <p className="text-xs font-bold text-[#191F28] break-keep">
                        🔴 {tp.trigger}
                      </p>
                      {tp.turn != null && (
                        <span className="text-[10px] font-bold text-gray-400 shrink-0">{tp.turn}번째</span>
                      )}
                    </div>
                    <p className="text-[11px] text-gray-600 leading-relaxed break-keep">{tp.why}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ───────── 위험 행동 ───────── */}
          {report.riskyActions?.length > 0 && (
            <div className="bg-amber-50/60 border border-amber-200/60 rounded-2xl p-4">
              <h3 className="text-xs font-extrabold text-amber-700 mb-2 flex items-center space-x-1">
                <span>⚠️</span>
                <span>훈련 중 나타난 위험 행동</span>
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {report.riskyActions.map((action, idx) => (
                  <span key={idx} className="text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded-md">
                    {RISKY_ACTION_LABEL[action] || action}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ───────── ⑤ 이번 훈련에서 나타난 취약 패턴 ───────── */}
          {(report.vulnerabilityPattern?.trim() || report.weakness?.trim()) && (
            <div className="bg-[#F8F9FA] border border-gray-100 rounded-2xl p-4">
              <h3 className="text-xs font-bold text-[#0052CC] mb-2 flex items-center space-x-1">
                <span>🔍</span>
                <span>이번 훈련에서 나타난 패턴</span>
              </h3>
              {report.vulnerabilityPattern?.trim() && (
                <p className="text-xs font-extrabold text-[#191F28] mb-1.5 break-keep">
                  {report.vulnerabilityPattern}
                </p>
              )}
              {report.weakness && (
                <p className="text-[11px] text-gray-600 leading-relaxed break-keep">{report.weakness}</p>
              )}
            </div>
          )}

          {/* ───────── ⑥ 다음 행동 가이드 ───────── */}
          {report.guidance?.length > 0 && (
            <div className="bg-gradient-to-br from-blue-50/80 to-indigo-50/50 border border-blue-200/60 rounded-2xl p-4">
              <h3 className="text-xs font-extrabold text-[#0052CC] mb-2 flex items-center space-x-1">
                <span>🛡️</span>
                <span>다음엔 이렇게 해보세요</span>
              </h3>
              <ul className="space-y-2">
                {report.guidance.map((item, idx) => (
                  <li key={idx} className="text-[11px] text-[#191F28] leading-relaxed flex items-start space-x-1.5 font-medium break-keep">
                    <span className="text-[#0052CC] font-bold shrink-0">{idx + 1}.</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ───────── 시나리오 출처 (백엔드가 내려주면 자동 표시) ─────────
              ⚠️ 현재 judgment 응답에는 이 필드가 없음. 시나리오 JSON의
              source / source_refs 를 응답에 포함해달라고 백엔드에 요청한 상태.
              오면 자동으로 뜨고, 없으면 이 블록 전체가 렌더링되지 않음. */}
          {(report.source || report.sourceRefs?.length > 0) && (
            <div className="border-t border-gray-100 pt-4">
              <p className="text-[10px] font-bold text-[#8B95A1] mb-1.5">📚 이 훈련의 근거 자료</p>
              {report.source && (
                <p className="text-[10px] text-gray-500 leading-relaxed break-keep mb-1.5">
                  {report.source}
                </p>
              )}
              {report.sourceRefs?.map((url, idx) => (
                <a
                  key={idx}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-[#0052CC] underline block truncate hover:opacity-70"
                >
                  {url}
                </a>
              ))}
            </div>
          )}

        </div>

        {/* ───────── 하단 버튼 ───────── */}
        <div className="p-4 mt-2 space-y-2 bg-white">
          {shareToast && (
            <div className="bg-gray-800 text-white text-[11px] text-center py-2 rounded-xl animate-fade-in">
              🔗 링크가 클립보드에 복사되었습니다!
            </div>
          )}

          {downloadToast && (
            <div className="bg-emerald-600 text-white text-[11px] text-center py-2 rounded-xl animate-fade-in">
              📄 부착용 안심 수칙 카드 생성 중...
            </div>
          )}

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
