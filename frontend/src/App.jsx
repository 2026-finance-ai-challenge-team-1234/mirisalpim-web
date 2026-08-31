import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { BootstrapProvider } from "./context/BootstrapContext";
import { TraineeProvider } from "./context/TraineeContext";
import Home from "./pages/Home";
import TypeSelect from "./pages/TypeSelect";
import ModeSelect from "./pages/ModeSelect";
import Survey from "./pages/Survey";
import SurveyLoading from "./pages/SurveyLoading";
import Recommendation from "./pages/Recommendation";
import CategorySelect from "./pages/CategorySelect";
import UserInfo from "./pages/UserInfo";
import CallIncoming from "./pages/CallIncoming";
import Simulation from "./pages/Simulation";
import ReportLoading from "./pages/ReportLoading";
import Report from "./pages/Report";
import PhishingLab from "./pages/PhishingLab";

// 화면 전환 시 페이드 애니메이션. 페이지 파일들은 전혀 안 건드리고,
// 여기서 <Routes> 전체를 감싸서 pathname이 바뀔 때마다 부드럽게 전환되게 함.
function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18, ease: "easeInOut" }}
      >
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/type-select" element={<TypeSelect />} />
          <Route path="/mode-select" element={<ModeSelect />} />
          <Route path="/survey" element={<Survey />} />
          <Route path="/survey-loading" element={<SurveyLoading />} />
          <Route path="/recommendation" element={<Recommendation />} />
          <Route path="/category-select" element={<CategorySelect />} />
          <Route path="/user-info" element={<UserInfo />} />
          <Route path="/call-incoming" element={<CallIncoming />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/report-loading" element={<ReportLoading />} />
          <Route path="/report" element={<Report />} />
          <Route path="/phishing-lab" element={<PhishingLab />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BootstrapProvider>
      {/* 훈련생 정보(이름·나이·주소)는 localStorage 대신 이 Provider 안에서만 산다.
          새로고침하면 사라지는 게 정상이다 (개인정보 미저장 원칙). */}
      <TraineeProvider>
        <BrowserRouter>
          <AnimatedRoutes />
        </BrowserRouter>
      </TraineeProvider>
    </BootstrapProvider>
  );
}