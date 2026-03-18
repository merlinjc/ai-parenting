import { Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import AuthGuard from './components/AuthGuard'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UsersPage from './pages/UsersPage'
import ChildrenPage from './pages/ChildrenPage'
import PlansPage from './pages/PlansPage'
import RecordsPage from './pages/RecordsPage'
import AISessionsPage from './pages/AISessionsPage'
import WeeklyFeedbacksPage from './pages/WeeklyFeedbacksPage'
import MessagesPage from './pages/MessagesPage'
import PushRulesPage from './pages/PushRulesPage'
import PushLogsPage from './pages/PushLogsPage'
import ChannelMonitorPage from './pages/ChannelMonitorPage'
import DevicesPage from './pages/DevicesPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <AuthGuard>
            <DashboardLayout />
          </AuthGuard>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="children" element={<ChildrenPage />} />
        <Route path="plans" element={<PlansPage />} />
        <Route path="records" element={<RecordsPage />} />
        <Route path="ai-sessions" element={<AISessionsPage />} />
        <Route path="weekly-feedbacks" element={<WeeklyFeedbacksPage />} />
        <Route path="messages" element={<MessagesPage />} />
        <Route path="push-rules" element={<PushRulesPage />} />
        <Route path="push-logs" element={<PushLogsPage />} />
        <Route path="channel-monitor" element={<ChannelMonitorPage />} />
        <Route path="devices" element={<DevicesPage />} />
      </Route>
    </Routes>
  )
}

export default App
