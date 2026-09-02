import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toPng } from "html-to-image";
import PageHeader from "../components/PageHeader";
import { useTrainee } from "../hooks/useTrainee";

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
  const { trainee } = useTrainee();

  const userName = trainee.name || "고객";
  const [toast, setToast] = useState(null); // { type: "success" | "error", text }
  const [saving, setSaving] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);

  // 이미지로 저장할 영역 (헤더~본문까지, 하단 버튼은 제외)
  const captureRef = useRef(null);

  const showToast = (type, text, ms = 2400) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), ms);
  };

  const report = state?.report;
  // 훈련 중 주고받은 대화. 서버가 원문을 저장하지 않으므로 Simulation 이 메모리로 넘겨준다.
  const transcript = state?.transcript || [];

  // 판단을 거치지 않고 직접 들어온 경우(새로고침/URL 직접 입력) → 훈련 선택으로
  useEffect(() => {
    if (!report) navigate("/type-select", { replace: true });
  }, [report, navigate]);

  if (!report) return null;

  // 턴 번호 → 그 턴에 붙은 마커 목록. 자막 옆에 위험 표시를 달기 위해 미리 만들어 둔다.
  const markersByTurn = new Map(
    (report.timeline || []).map((item) => [item.turn, item.markers || []]),
  );

  const isFalseAlarm = report.grade === "오탐";
  const gradeMeta = GRADE_META[report.grade] || GRADE_META.B;

  // ───────── 결과 이미지로 저장 ─────────
  // 모바일은 다운로드 대신 공유 시트(파일 공유)를 띄우는 편이 훨씬 자연스러워서
  // navigator.share(files)를 먼저 시도하고, 안 되면 다운로드로 떨어뜨린다.
  const handleSaveImage = async () => {
    if (!captureRef.current || saving) return;
    setSaving(true);

    try {
      // html2canvas는 Tailwind v4가 쓰는 oklch() 색상을 파싱하지 못해 실패함 → html-to-image 사용.
      //
      // 폰트는 그대로 살리는 게 기본이다. index.html 의 구글 폰트 <link> 에
      // crossorigin 을 붙여두면 폰트 CSS 를 읽어 이미지에 심을 수 있다.
      // 그래도 브라우저가 막는 경우가 있어(확장 프로그램, 사설 프록시 등),
      // 실패하면 폰트만 빼고 한 번 더 시도해 저장 자체는 반드시 되게 한다.
      const baseOptions = {
        backgroundColor: "#ffffff",
        pixelRatio: Math.min(window.devicePixelRatio || 1, 2), // 너무 큰 이미지 방지
        cacheBust: true,
      };

      let dataUrl;
      try {
        dataUrl = await toPng(captureRef.current, baseOptions);
      } catch (fontError) {
        console.warn("[Report] 폰트 포함 캡처 실패, 폰트 없이 다시 시도합니다:", fontError);
        dataUrl = await toPng(captureRef.current, { ...baseOptions, skipFonts: true });
      }

      const blob = await (await fetch(dataUrl)).blob();
      if (!blob) throw new Error("이미지 생성에 실패했습니다.");

      const fileName = `미리살핌_진단리포트_${userName}.png`;
      const file = new File([blob], fileName, { type: "image/png" });

      // 1순위: 파일 공유 (모바일에서 "이미지 저장" 옵션이 함께 뜸)
      if (navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "미리살핌 진단 리포트" });
          return;
        } catch (err) {
          if (err?.name === "AbortError") return; // 사용자가 취소한 것은 오류가 아님
          // 공유가 막힌 환경이면 아래 다운로드로 계속 진행
        }
      }

      // 2순위: 파일 다운로드
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showToast("success", "리포트 이미지를 저장했어요!");
    } catch (err) {
      console.error("[Report] 이미지 저장 실패:", err);
      showToast("error", "이미지 저장에 실패했어요. 화면을 캡처해 저장해주세요.");
    } finally {
      setSaving(false);
    }
  };

  // ───────── 가족에게 체험 공유 ─────────
  // 리포트 내용이 아니라 "체험 자체"를 권하는 링크(서비스 홈)를 공유한다.
  const handleShareService = async () => {
    const shareUrl = window.location.origin;
    const shareData = {
      title: "미리살핌 - 금융사기 예방 모의 훈련",
      text: "보이스피싱, 말로만 조심하지 말고 미리 한번 겪어봐요. 5분이면 충분해요!",
      url: shareUrl,
    };

    // 1순위: 공유 시트 (모바일)
    if (navigator.share) {
      try {
        await navigator.share(shareData);
        return;
      } catch (err) {
        if (err?.name === "AbortError") return; // 사용자가 취소
        // 그 외에는 아래 복사로 계속 진행
      }
    }

    // 2순위: 클립보드 복사 (https 또는 localhost에서만 동작)
    try {
      await navigator.clipboard.writeText(shareUrl);
      showToast("success", "링크를 복사했어요! 가족에게 붙여넣어 보내주세요.");
      return;
    } catch {
      // 3순위: 구형/비보안 환경 폴백 — 임시 input을 만들어 선택 후 복사
      try {
        const input = document.createElement("input");
        input.value = shareUrl;
        input.setAttribute("readonly", "");
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        input.setSelectionRange(0, 99999); // iOS 대응
        document.execCommand("copy");
        document.body.removeChild(input);
        showToast("success", "링크를 복사했어요! 가족에게 붙여넣어 보내주세요.");
      } catch {
        showToast("error", `링크 복사에 실패했어요. 주소창의 주소를 직접 공유해주세요.`, 3200);
      }
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] min-h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col relative">

        {/* 이미지로 저장되는 영역 (하단 버튼은 제외) */}
        <div ref={captureRef} className="bg-white">
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
                    {/* 턴 번호가 아니라 대화 횟수를 쓴다. 한 번의 교환마다 턴이 2씩
                        올라서 turn 3 은 세 번째가 아니라 두 번째 대화다. */}
                    <b className="text-[#0052CC]">{report.judgedExchange ?? report.judgedTurn}번째</b> 대화에서 알아차렸어요.
                  </p>
                ) : (
                  // judgedTurn이 null이면 판단 없이 최대 턴까지 대화가 이어진 경우
                  <p className="text-[11px] text-[#191F28] font-medium break-keep">
                    대화가 끝날 때까지 사기라는 것을 알아차리지 못했어요.
                  </p>
                )}
                {report.firstDetectableTurn != null && (
                  <p className="text-[11px] text-gray-600 break-keep">
                    가장 빠른 판별 가능 시점은 <b>{report.firstDetectableExchange ?? report.firstDetectableTurn}번째</b> 대화였어요.
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

          {/* ───────── ③ 대화 리플레이 (자막 + 위험 지점 강조) ───────── */}
          {(transcript.length > 0 || report.timeline?.length > 0) && (
            <div>
              <button
                onClick={() => setShowTimeline((v) => !v)}
                className="w-full flex items-center justify-between mb-2.5"
              >
                <h3 className="text-xs font-extrabold text-[#191F28]">대화 흐름 다시보기</h3>
                <span className="text-[10px] text-[#8B95A1]">{showTimeline ? "접기 ▲" : "펼치기 ▼"}</span>
              </button>

              {showTimeline && (
                <div className="bg-[#F8F9FA] border border-gray-100 rounded-2xl p-4 animate-fade-in">
                  {transcript.length > 0 ? (
                    <div className="space-y-3">
                      {transcript.map((line, idx) => {
                        // 이 발화가 속한 턴에 표시할 마커가 있으면 함께 보여준다.
                        const markers = line.turn != null ? markersByTurn.get(line.turn) : undefined;
                        const isUser = line.sender === "user";
                        const highlighted = Boolean(markers?.length);

                        return (
                          <div key={idx}>
                            <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                              <div
                                className={`px-3 py-2 rounded-xl text-[11px] leading-relaxed max-w-[85%] break-keep ${
                                  isUser
                                    ? "bg-[#0052CC] text-white rounded-br-none"
                                    : "bg-white text-[#191F28] border border-gray-200 rounded-bl-none"
                                } ${highlighted ? "ring-2 ring-red-300" : ""}`}
                              >
                                <span className={`text-[9px] font-bold block mb-0.5 ${isUser ? "text-blue-100" : "text-gray-400"}`}>
                                  {isUser ? "나" : "상대방"}
                                </span>
                                <span className="whitespace-pre-wrap">{line.text}</span>
                              </div>
                            </div>

                            {highlighted && (
                              <div className={`flex flex-wrap gap-x-2 gap-y-1 mt-1 ${isUser ? "justify-end" : "justify-start"}`}>
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
                        );
                      })}
                    </div>
                  ) : (
                    // 대화 내용이 없으면(새로고침 등) 기존처럼 턴별 마커만이라도 보여준다.
                    <div className="space-y-2">
                      {report.timeline.map((item, idx) => (
                        <div key={idx} className="flex items-start space-x-2.5">
                          <span className="text-[10px] font-mono font-bold text-gray-400 w-4 shrink-0 mt-0.5">
                            {item.turn}
                          </span>
                          <div className="flex-1 min-w-0 flex flex-wrap gap-x-2 gap-y-1">
                            {(item.markers || []).map((m, i) => {
                              const meta = MARKER_META[m];
                              if (!meta) return null;
                              return (
                                <span key={i} className={`text-[10px] font-bold ${meta.color}`}>
                                  {meta.icon} {meta.label}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="pt-3 mt-3 border-t border-gray-200 flex flex-wrap gap-x-3 gap-y-1">
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
                      {(tp.exchange ?? tp.turn) != null && (
                        <span className="text-[10px] font-bold text-gray-400 shrink-0">{tp.exchange ?? tp.turn}번째</span>
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
        </div>

        {/* ───────── 하단 버튼 ───────── */}
        <div className="p-4 mt-2 space-y-2 bg-white">
          {toast && (
            <div
              className={`text-white text-[11px] text-center py-2 px-3 rounded-xl animate-fade-in break-keep ${
                toast.type === "error" ? "bg-red-500" : "bg-gray-800"
              }`}
            >
              {toast.text}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleSaveImage}
              disabled={saving}
              className="bg-[#0052CC] text-white py-3 rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99] flex items-center justify-center space-x-1 disabled:opacity-60"
            >
              <span>🖼️</span>
              <span>{saving ? "저장 중..." : "결과 이미지 저장"}</span>
            </button>

            <button
              onClick={handleShareService}
              className="bg-emerald-500 text-white py-3 rounded-xl text-xs font-bold shadow-md shadow-emerald-500/20 hover:bg-emerald-600 transition active:scale-[0.99] flex items-center justify-center space-x-1"
            >
              <span>👨‍👩‍👧‍👦</span>
              <span>가족에게 권하기</span>
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