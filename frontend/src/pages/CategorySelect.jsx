import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function CategorySelect() {
  const navigate = useNavigate();

  // 1. 선택 단계 관리 (1: 전화/문자 대분류, 2: 8대 중분류 선택, 3: 세부 소분류 시나리오 선택)
  const [step, setStep] = useState(1);

  // 2. 선택된 데이터 상태 관리
  const [mainCategory, setMainCategory] = useState(null); // 'voice' | 'smishing'
  const [selectedSubGroup, setSelectedSubGroup] = useState(null); // 중분류 ID (T01~T08, S01~S08)
  const [selectedScenario, setSelectedScenario] = useState(null); // 소분류 시나리오 객체 { id, name, code }

  // [데이터 셋] 보이스피싱 8대 중분류 및 세부 소분류
  const voiceCategories = [
    {
      id: "T01",
      code: "T01",
      title: "1. 기관 사칭",
      badge: "🛡️ 다빈도 수법",
      desc: "검찰, 경찰, 금감원, 은행 등 공공·금융기관을 사칭하여 접근",
      subItems: [
        { id: "T01-1", code: "prosecution_impersonation", name: "검찰 사칭" },
        { id: "T01-2", code: "police_impersonation", name: "경찰 사칭" },
        { id: "T01-3", code: "court_admin", name: "법원 사칭" },
        { id: "T01-4", code: "financial_supervision", name: "금융감독원 사칭" },
        { id: "T01-5", code: "bank_staff", name: "은행 사칭" },
        { id: "T01-6", code: "card_company", name: "카드사 사칭" },
        { id: "T01-7", code: "insurance_company", name: "보험사 사칭" },
        { id: "T01-8", code: "public_institution", name: "건강보험공단·국민연금 등 공공기관 사칭" },
        { id: "T01-9", code: "telecom_company", name: "통신사 사칭" },
      ],
    },
    {
      id: "T02",
      code: "T02",
      title: "2. 금융 사기",
      badge: "💰 금전 갈취형",
      desc: "대출, 이상거래, 투자 환급 등을 빌미로 자금 이체 유도",
      subItems: [
        { id: "T02-1", code: "loan_fraud", name: "대출 사기" },
        { id: "T02-2", code: "refinance_loan", name: "저금리 대환대출 사기" },
        { id: "T02-3", code: "loan_guarantee_fee", name: "대출 보증료·수수료 요구" },
        { id: "T02-4", code: "abnormal_transaction", name: "계좌 이상거래 사기" },
        { id: "T02-5", code: "foreign_card_payment", name: "카드·해외결제 사기" },
        { id: "T02-6", code: "refund_fraud", name: "환급금 사기" },
        { id: "T02-7", code: "stock_investment_fraud", name: "투자·주식 사기" },
        { id: "T02-8", code: "crypto_investment_fraud", name: "가상자산 투자 사기" },
      ],
    },
    {
      id: "T03",
      code: "T03",
      title: "3. 자녀·가족 사칭",
      badge: "📱 심리적 약점 공략",
      desc: "휴대폰 고장, 사고, 긴급 송금 필요를 핑계로 가족을 사칭",
      subItems: [
        { id: "T03-1", code: "child_impersonation", name: "자녀 사칭" },
        { id: "T03-2", code: "parent_impersonation", name: "부모 사칭" },
        { id: "T03-3", code: "spouse_impersonation", name: "배우자 사칭" },
        { id: "T03-4", code: "friend_impersonation", name: "친구·지인 사칭" },
        { id: "T03-5", code: "phone_broken", name: "휴대폰 고장 사칭" },
        { id: "T03-6", code: "number_changed", name: "번호 변경 사칭" },
        { id: "T03-7", code: "emergency_accident", name: "사고·응급상황 사칭" },
        { id: "T03-8", code: "urgent_remittance", name: "긴급 송금 요구" },
      ],
    },
    {
      id: "T04",
      code: "T04",
      title: "4. 수사·사건 연루",
      badge: "🚨 극심한 공포 유발",
      desc: "명의도용, 대포통장, 자금세탁 등 범죄 연루를 주장하며 안전계좌 이체 요구",
      subItems: [
        { id: "T04-1", code: "identity_theft_case", name: "명의도용 사건 연루" },
        { id: "T04-2", code: "mule_account_case", name: "대포통장 사건 연루" },
        { id: "T04-3", code: "money_laundering_case", name: "불법 자금세탁 사건 연루" },
        { id: "T04-4", code: "data_leak_case", name: "개인정보 유출 사건 연루" },
        { id: "T04-5", code: "victim_protection", name: "범죄 피해자 보호 명목" },
        { id: "T04-6", code: "safe_account_transfer", name: "안전계좌로 자금 이체 요구" },
      ],
    },
    {
      id: "T05",
      code: "T05",
      title: "5. 대출·취업·알바",
      badge: "💼 구직/생계형 미끼",
      desc: "대출 승인, 고수익 알바, 채용 합격을 미끼로 계좌 대여 및 자금 편취",
      subItems: [
        { id: "T05-1", code: "loan_approval", name: "대출 승인 사칭" },
        { id: "T05-2", code: "refinance_offer", name: "대환대출 제안" },
        { id: "T05-3", code: "high_income_part_time", name: "고수익 아르바이트 제안" },
        { id: "T05-4", code: "job_offer_passed", name: "채용 합격 사칭" },
        { id: "T05-5", code: "proxy_purchase_exchange", name: "구매대행·환전 업무 사칭" },
        { id: "T05-6", code: "account_rental_request", name: "계좌 대여 요구" },
      ],
    },
    {
      id: "T06",
      code: "T06",
      title: "6. 원격제어·악성앱",
      badge: "⚙️ 기술적 탈취형",
      desc: "보안 점검 명목 원격제어 앱, 위장 금융앱 설치 및 OTP 탈취",
      subItems: [
        { id: "T06-1", code: "security_check_app", name: "금융 보안점검 명목 앱 설치" },
        { id: "T06-2", code: "remote_control_app", name: "원격제어 앱 설치" },
        { id: "T06-3", code: "screen_share_request", name: "화면공유 요구" },
        { id: "T06-4", code: "otp_code_request", name: "인증번호·OTP 요구" },
        { id: "T06-5", code: "fake_bank_app", name: "금융앱 위장 설치" },
        { id: "T06-6", code: "personal_info_input", name: "개인정보 입력 유도" },
      ],
    },
    {
      id: "T07",
      code: "T07",
      title: "7. 택배·생활 사칭",
      badge: "📦 일상생활 밀착",
      desc: "배송 주소 오류, 반품/환불, 미납 요금 및 보상금 명목의 전화",
      subItems: [
        { id: "T07-1", code: "delivery_issue", name: "택배 배송 문제" },
        { id: "T07-2", code: "address_error", name: "배송 주소 오류" },
        { id: "T07-3", code: "return_refund", name: "반품·환불 사칭" },
        { id: "T07-4", code: "unpaid_telecom_fee", name: "통신요금 미납 사칭" },
        { id: "T07-5", code: "utility_fee", name: "공공서비스 이용료 사칭" },
        { id: "T07-6", code: "refund_compensation", name: "각종 환급·보상금 사칭" },
      ],
    },
    {
      id: "T08",
      code: "T08",
      title: "8. 관계·신뢰 형성형",
      badge: "🤝 신뢰 악용형",
      desc: "로맨스스캠, 지인 및 투자 전문가 사칭을 통해 오랜 신뢰 형성 후 금전 요구",
      subItems: [
        { id: "T08-1", code: "romance_scam", name: "로맨스 스캠" },
        { id: "T08-2", code: "acquaintance_relation", name: "지인 관계 사칭" },
        { id: "T08-3", code: "investment_expert", name: "투자 전문가 사칭" },
        { id: "T08-4", code: "long_term_trust_money", name: "장기간 신뢰 형성 후 금전 요구" },
        { id: "T08-5", code: "help_request_money", name: "도움 요청을 통한 금전 요구" },
      ],
    },
  ];

  // [데이터 셋] 스미싱 8대 중분류 및 세부 소분류
  const smishingCategories = [
    {
      id: "S01",
      code: "S01",
      title: "1. 기관 사칭",
      badge: "🛡️ 공공기관 위장",
      desc: "검찰, 경찰, 법원, 금감원, 은행, 통신사 사칭 문자",
      subItems: [
        { id: "S01-1", code: "smish_prosecution", name: "검찰 사칭" },
        { id: "S01-2", code: "smish_police", name: "경찰 사칭" },
        { id: "S01-3", code: "smish_court", name: "법원 사칭" },
        { id: "S01-4", code: "smish_fss", name: "금융감독원 사칭" },
        { id: "S01-5", code: "smish_bank", name: "은행 사칭" },
        { id: "S01-6", code: "smish_card", name: "카드사 사칭" },
        { id: "S01-7", code: "smish_insurance", name: "보험사 사칭" },
        { id: "S01-8", code: "smish_public_agency", name: "공공기관 사칭" },
        { id: "S01-9", code: "smish_telecom", name: "통신사 사칭" },
      ],
    },
    {
      id: "S02",
      code: "S02",
      title: "2. 자녀·가족 사칭",
      badge: "📱 모바일 메신저/SMS",
      desc: "휴대폰 파손, 번호 변경, 긴급 송금을 유도하는 문자",
      subItems: [
        { id: "S02-1", code: "smish_child", name: "자녀 사칭" },
        { id: "S02-2", code: "smish_parent", name: "부모 사칭" },
        { id: "S02-3", code: "smish_friend", name: "친구·지인 사칭" },
        { id: "S02-4", code: "smish_phone_broken", name: "휴대폰 고장 사칭" },
        { id: "S02-5", code: "smish_number_changed", name: "번호 변경 사칭" },
        { id: "S02-6", code: "smish_emergency", name: "긴급 상황 사칭" },
        { id: "S02-7", code: "smish_urgent_money", name: "긴급 송금 요청" },
      ],
    },
    {
      id: "S03",
      code: "S03",
      title: "3. 택배·배송",
      badge: "📦 가장 높은 클릭률",
      desc: "배송 조회, 주소지 불명 오류, 배송비 결제 링크 유도",
      subItems: [
        { id: "S03-1", code: "smish_delivery_check", name: "택배 배송 조회" },
        { id: "S03-2", code: "smish_address_error", name: "배송 주소 오류" },
        { id: "S03-3", code: "smish_delivery_fee", name: "배송비 결제" },
        { id: "S03-4", code: "smish_return_refund", name: "반품·환불" },
        { id: "S03-5", code: "smish_delivery_confirm", name: "택배 수령 확인" },
      ],
    },
    {
      id: "S04",
      code: "S04",
      title: "4. 금융·결제",
      badge: "💳 이상거래 결제 알림",
      desc: "해외결제 승인, 이상거래 감지, 환급금 조회 링크 발송",
      subItems: [
        { id: "S04-1", code: "smish_card_approved", name: "카드 결제 승인" },
        { id: "S04-2", code: "smish_overseas_approved", name: "해외 결제 승인" },
        { id: "S04-3", code: "smish_abnormal_account", name: "계좌 이상거래" },
        { id: "S04-4", code: "smish_finance_confirm", name: "금융정보 확인" },
        { id: "S04-5", code: "smish_loan_limit", name: "대출 승인·한도 조회" },
        { id: "S04-6", code: "smish_refund_notice", name: "환급금 안내" },
        { id: "S04-7", code: "smish_insurance_payout", name: "보험금 지급 안내" },
      ],
    },
    {
      id: "S05",
      code: "S05",
      title: "5. 공공·행정",
      badge: "🏛️ 전자고지서 위장",
      desc: "교통과태료, 법원 전자문서, 건강보험료, 세금 환급 안내",
      subItems: [
        { id: "S05-1", code: "smish_traffic_fine", name: "교통범칙금·과태료" },
        { id: "S05-2", code: "smish_court_doc", name: "법원 전자문서" },
        { id: "S05-3", code: "smish_health_insurance", name: "건강보험료 안내" },
        { id: "S05-4", code: "smish_tax_refund", name: "세금·환급금" },
        { id: "S05-5", code: "smish_gov_subsidy", name: "정부지원금" },
        { id: "S05-6", code: "smish_civil_complaint", name: "민원 처리 안내" },
        { id: "S05-7", code: "smish_resident_data", name: "주민등록·개인정보 관련 안내" },
      ],
    },
    {
      id: "S06",
      code: "S06",
      title: "6. 생활·경조사",
      badge: "💌 지인 빙자 클릭 유도",
      desc: "모바일 청첩장, 부고장, 돌잔치, 이벤트 당첨 쿠폰 위장",
      subItems: [
        { id: "S06-1", code: "smish_wedding_invitation", name: "모바일 청첩장" },
        { id: "S06-2", code: "smish_obituary", name: "부고장" },
        { id: "S06-3", code: "smish_party_invitation", name: "돌잔치·초대장" },
        { id: "S06-4", code: "smish_event_prize", name: "경품·이벤트 당첨" },
        { id: "S06-5", code: "smish_coupon_discount", name: "쿠폰·할인 이벤트" },
        { id: "S06-6", code: "smish_survey_poll", name: "설문조사" },
      ],
    },
    {
      id: "S07",
      code: "S07",
      title: "7. 악성앱·피싱 링크",
      badge: "⚠️ 악성 APK 다운로드",
      desc: "가짜 보안앱/금융앱 설치 유도 및 OTP·개인정보 탈취",
      subItems: [
        { id: "S07-1", code: "smish_apk_install", name: "APK 설치 유도" },
        { id: "S07-2", code: "smish_fake_bank_app", name: "가짜 금융앱 설치" },
        { id: "S07-3", code: "smish_fake_login", name: "가짜 로그인 페이지" },
        { id: "S07-4", code: "smish_personal_data_input", name: "개인정보 입력 유도" },
        { id: "S07-5", code: "smish_financial_data_input", name: "금융정보 입력 유도" },
        { id: "S07-6", code: "smish_otp_input", name: "인증번호 입력 유도" },
        { id: "S07-7", code: "smish_remote_app_install", name: "원격제어 앱 설치 유도" },
      ],
    },
    {
      id: "S08",
      code: "S08",
      title: "8. 투자·대출",
      badge: "📈 고수익 현혹",
      desc: "주식 리딩방, 무료 투자 정보, 저금리 대환대출 안내 링크",
      subItems: [
        { id: "S08-1", code: "smish_stock_recommend", name: "주식 종목 추천" },
        { id: "S08-2", code: "smish_free_invest_info", name: "무료 투자정보 제공" },
        { id: "S08-3", code: "smish_leading_room_invite", name: "투자 리딩방 초대" },
        { id: "S08-4", code: "smish_high_return_offer", name: "고수익 투자 제안" },
        { id: "S08-5", code: "smish_loan_limit_check", name: "대출 한도 조회" },
        { id: "S08-6", code: "smish_low_loan_notice", name: "저금리 대출 안내" },
        { id: "S08-7", code: "smish_refinance_notice", name: "대환대출 안내" },
      ],
    },
  ];

  // [단계 1] 메인 카테고리(전화 vs 문자) 선택
  const handleSelectMain = (type) => {
    setMainCategory(type);
    setSelectedSubGroup(null);
    setSelectedScenario(null);
    setStep(2); // 둘 다 2단계(8대 중분류 선택)로 직행
  };

  // [단계 2] 8대 중분류 선택
  const handleSelectSubGroup = (groupId) => {
    setSelectedSubGroup(groupId);
    setSelectedScenario(null);
    setStep(3); // 3단계(세부 소분류 선택)로 이동
  };

  // [최종 제출] 다음 페이지(UserInfo)로 이동
  const handleStart = () => {
    if (!mainCategory || !selectedScenario) return;

    localStorage.removeItem("selectedScenario");
    localStorage.setItem("selectedCategory", mainCategory);
    localStorage.setItem("selectedScenarioId", selectedScenario.id);
    localStorage.setItem("selectedScenarioName", selectedScenario.name);
    localStorage.setItem("selectedScenarioCode", selectedScenario.code);

    // AI 대화 연동 시 필요한 페르소나 키값 매핑
    localStorage.setItem("selectedPersonaKey", `${selectedScenario.code}_persona.json`);

    navigate("/user-info");
  };

  // 상단 뒤로가기 핸들러
  const handleHeaderBack = () => {
    if (step === 3) {
      setStep(2);
      setSelectedScenario(null);
    } else if (step === 2) {
      setStep(1);
      setSelectedSubGroup(null);
      setMainCategory(null);
    } else {
      navigate("/mode-select");
    }
  };

  // 현재 활성화된 카테고리 목록 및 선택된 중분류 객체
  const currentCategoryList = mainCategory === "voice" ? voiceCategories : smishingCategories;
  const currentGroupObj = currentCategoryList.find((g) => g.id === selectedSubGroup);

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">
        
        <div>
          {/* Header */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2 border-b border-gray-100">
            <button 
              onClick={handleHeaderBack}
              aria-label="뒤로가기"
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1 flex items-center justify-center"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 
              onClick={() => navigate("/")}
              className="text-lg font-extrabold text-[#0052CC] cursor-pointer tracking-tight"
            >
              미리살핌
            </h1>
            <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition p-1 -mr-1">
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </button>
          </header>

          {/* Title Section */}
          <section className="mb-4">
            <span className="text-[10px] font-bold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md">
              직접 선택 훈련 • STEP {step}/3
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 mb-1 tracking-tight break-keep">
              {step === 1 && <>어떤 금융사기를<br />체험해볼까요?</>}
              {step === 2 && (
                mainCategory === "voice"
                  ? <>보이스피싱 중분류를<br />선택해 주세요.</>
                  : <>스미싱 중분류를<br />선택해 주세요.</>
              )}
              {step === 3 && <>상세 시나리오를<br />선택해 주세요.</>}
            </h2>
            <p className="text-xs text-[#8B95A1] leading-relaxed break-keep">
              {step === 1 && "체험하고 싶은 금융사기 채널(통화 또는 문자)을 선택하세요."}
              {step === 2 && (
                mainCategory === "voice"
                  ? "체험을 원하는 보이스피싱 핵심 수법을 골라주세요."
                  : "체험을 원하는 스미싱 주요 유형을 골라주세요."
              )}
              {step === 3 && "훈련받을 구체적인 상황을 직접 지정해 보세요."}
            </p>
          </section>

          {/* STEP 1: 전화(보이스피싱) vs 문자(스미싱) 대분류 선택 */}
          {step === 1 && (
            <div className="space-y-3.5 animate-fade-in">
              {/* 보이스피싱 카드 */}
              <div
                onClick={() => handleSelectMain("voice")}
                className={`p-4 rounded-2xl border-2 transition-all cursor-pointer ${
                  mainCategory === "voice"
                    ? "bg-blue-50/40 border-[#0052CC] shadow-xs"
                    : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
                }`}
              >
                <div className="mb-2">
                  <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#0052CC] text-white">
                    📞 실시간 음성 통화 대응
                  </span>
                </div>
                <h3 className="text-sm font-extrabold text-[#191F28] mb-1">
                  전화 사기 (보이스피싱)
                </h3>
                <p className="text-xs text-[#8B95A1] leading-relaxed mb-2 break-keep">
                  검찰·금융기관·가족을 사칭한 실시간 음성 압박 통화에 침착하게 대응해보는 훈련이에요.
                </p>
                <div className="text-[11px] font-semibold text-[#0052CC]">
                  8대 중분류 및 소분류 선택하기 →
                </div>
              </div>

              {/* 스미싱 카드 */}
              <div
                onClick={() => handleSelectMain("smishing")}
                className={`p-4 rounded-2xl border-2 transition-all cursor-pointer ${
                  mainCategory === "smishing"
                    ? "bg-blue-50/40 border-[#0052CC] shadow-xs"
                    : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
                }`}
              >
                <div className="mb-2">
                  <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500 text-white">
                    💬 문자 속 악성 URL 대응
                  </span>
                </div>
                <h3 className="text-sm font-extrabold text-[#191F28] mb-1">
                  문자 사기 (스미싱)
                </h3>
                <p className="text-xs text-[#8B95A1] leading-relaxed mb-2 break-keep">
                  택배, 공공기관 알림, 청첩장 등 일상 문자 속 악성 링크와 가짜 페이지 유입에 대응하는 훈련이에요.
                </p>
                <div className="text-[11px] font-semibold text-[#0052CC]">
                  8대 중분류 및 소분류 선택하기 →
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: 8대 중분류 선택 */}
          {step === 2 && (
            <div className="space-y-3 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              {currentCategoryList.map((cat) => (
                <div
                  key={cat.id}
                  onClick={() => handleSelectSubGroup(cat.id)}
                  className="p-3.5 rounded-2xl border-2 border-transparent bg-[#F8F9FA] hover:border-[#0052CC] hover:bg-blue-50/30 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="text-xs sm:text-sm font-extrabold text-[#191F28]">
                      {cat.title}
                    </h3>
                    <span className="text-[10px] font-bold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md">
                      {cat.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep">
                    {cat.desc}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* STEP 3: 세부 소분류 시나리오 선택 */}
          {step === 3 && currentGroupObj && (
            <div className="space-y-2.5 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              <div className="bg-blue-50/60 p-3 rounded-xl border border-blue-100 mb-3">
                <span className="text-[10px] font-bold text-[#0052CC] block">선택된 중분류</span>
                <span className="text-xs font-extrabold text-[#191F28]">{currentGroupObj.title}</span>
              </div>

              {currentGroupObj.subItems.map((item) => {
                const isSelected = selectedScenario?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedScenario(item)}
                    className={`p-3 rounded-xl border-2 transition-all cursor-pointer flex justify-between items-center ${
                      isSelected
                        ? "bg-blue-50/60 border-[#0052CC] shadow-2xs"
                        : "bg-[#F8F9FA] border-gray-100 hover:border-gray-200"
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold text-gray-400 font-mono">
                        {item.id}
                      </span>
                      <span className="text-xs font-bold text-[#191F28]">
                        {item.name}
                      </span>
                    </div>
                    <span className={`text-xs shrink-0 ${isSelected ? "text-[#0052CC] font-extrabold" : "text-gray-300"}`}>
                      {isSelected ? "✓ 선택됨" : "선택"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 하단 실행 버튼 */}
        <div className="pt-4 border-t border-gray-100 bg-white">
          <button
            onClick={handleStart}
            disabled={
              (step === 1 && !mainCategory) ||
              (step === 2) ||
              (step === 3 && !selectedScenario)
            }
            className={`w-full py-3.5 rounded-xl text-xs sm:text-sm font-bold transition ${
              (step === 3 && selectedScenario)
                ? "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            {step === 1 && "금융사기 유형을 먼저 선택해 주세요"}
            {step === 2 && "위 중분류 목록 중 하나를 선택해 주세요"}
            {step === 3 && (selectedScenario ? `[${selectedScenario.name}] 훈련 시작하기 →` : "세부 시나리오를 선택해 주세요")}
          </button>
        </div>

      </div>
    </div>
  );
}