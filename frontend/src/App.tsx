import { Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage/HomePage";
import LoginPage from "./pages/LoginPage/LoginPage";
import SignupPage from "./pages/SignupPage/SignupPage";
import ProfileSetupPage from "./pages/ProfileSetupPage/ProfileSetupPage";
import ProfilePage from "./pages/ProfilePage/ProfilePage";
import HowItWorksPage from "./pages/HowItWorksPage/HowItWorksPage";
import FeaturesPage from "./pages/FeaturesPage/FeaturesPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage/ResetPasswordPage";
import VerifyEmailPage from "./pages/VerifyEmailPage/VerifyEmailPage";
import CheckEmailPage from "./pages/CheckEmailPage/CheckEmailPage";
import RequireVerifiedEmail from "./components/RequireVerifiedEmail/RequireVerifiedEmail";
import Feedback from "./pages/Feedback/Feedback";
import RequireAdmin from "./components/RequireAdmin/RequireAdmin";
import RedirectAdmin from "./components/RedirectAdmin/RedirectAdmin";
import AdminDashboardPage from "./pages/AdminDashboardPage/AdminDashboardPage";
{
  /* Routes is what nests <Route>s
   * Route maps URLs to components
   */
}
function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/profileSetup"
        element={
          <RequireVerifiedEmail>
            <RedirectAdmin>
              <ProfileSetupPage />
            </RedirectAdmin>
          </RequireVerifiedEmail>
        }
      />
      <Route
        path="/profile"
        element={
          <RequireVerifiedEmail>
            <RedirectAdmin>
              <ProfilePage />
            </RedirectAdmin>
          </RequireVerifiedEmail>
        }
      />
      <Route
        path="/admin-dashboard"
        element={
          <RequireVerifiedEmail>
            <RequireAdmin>
              <AdminDashboardPage />
            </RequireAdmin>
          </RequireVerifiedEmail>
        }
      />
      <Route path="/how-it-works" element={<HowItWorksPage />} />
      <Route path="/features" element={<FeaturesPage />} />
      <Route
        path="/feedback"
        element={
          <RequireVerifiedEmail>
            <Feedback />
          </RequireVerifiedEmail>
        }
      />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/verify-your-email" element={<CheckEmailPage />} />
    </Routes>
  );
}

export default App;
