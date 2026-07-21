import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { ThemeToggle } from './components/ThemeToggle'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Signals from './pages/Signals'
import Health from './pages/Health'
import Events from './pages/Events'
import Sync from './pages/Sync'
import StrainViewer from './pages/StrainViewer'
import Temperature from './pages/Temperature'
import PavementDesign from './pages/PavementDesign'
import Prediction from './pages/Prediction'
import Export from './pages/Export'
import Docs from './pages/Docs'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-card border-b border-border px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-muted-foreground hover:text-foreground transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-foreground">Pavement Analysis System</h1>
              <p className="text-xs text-muted-foreground">NH-71 Instrumented Pavement · IIT Tirupati</p>
            </div>
          </div>
          <ThemeToggle />
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/health" element={<Health />} />
            <Route path="/events" element={<Events />} />
            <Route path="/sync" element={<Sync />} />
            <Route path="/strains" element={<StrainViewer />} />
            <Route path="/temperature" element={<Temperature />} />
            <Route path="/design" element={<PavementDesign />} />
            <Route path="/prediction" element={<Prediction />} />
            <Route path="/export" element={<Export />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
