import { Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import PushRulesPage from './pages/PushRulesPage'
import ChannelMonitorPage from './pages/ChannelMonitorPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardLayout />}>
        <Route index element={<Navigate to="/push-rules" replace />} />
        <Route path="push-rules" element={<PushRulesPage />} />
        <Route path="channel-monitor" element={<ChannelMonitorPage />} />
      </Route>
    </Routes>
  )
}

export default App
