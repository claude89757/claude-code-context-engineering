import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Timeline from './pages/Timeline'
import VersionDetail from './pages/VersionDetail'
import ScenarioDetail from './pages/ScenarioDetail'
import ScenarioHistory from './pages/ScenarioHistory'
import PatrolStatus from './pages/PatrolStatus'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <Link to="/" className="text-lg font-bold text-blue-400">CC Observatory</Link>
          <Link to="/timeline" className="text-sm text-gray-400 hover:text-gray-200">Timeline</Link>
          <Link to="/scenarios" className="text-sm text-gray-400 hover:text-gray-200">Scenarios</Link>
          <Link to="/patrol" className="text-sm text-gray-400 hover:text-gray-200">Patrol</Link>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/versions/:id" element={<VersionDetail />} />
            <Route path="/test-runs/:id" element={<ScenarioDetail />} />
            <Route path="/scenarios/:key" element={<ScenarioHistory />} />
            <Route path="/patrol" element={<PatrolStatus />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
