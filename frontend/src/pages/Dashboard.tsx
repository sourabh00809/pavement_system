import { useEffect, useState, useCallback } from 'react'
import MetricCard from '../components/MetricCard'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi, pipelineApi, uploadPathsApi } from '../api/client'

export default function Dashboard() {
  const [life, setLife] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)
  const [events, setEvents] = useState<any>(null)
  const [strains, setStrains] = useState<any>(null)
  const [sync, setSync] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [uploadStatus, setUploadStatus] = useState<any>(null)
  const [processing, setProcessing] = useState(false)

  // Read pending files from sessionStorage (set by Upload page)
  const pendingRaw = typeof window !== 'undefined' ? sessionStorage.getItem('pendingUploadFiles') : null
  const pendingFiles: { path: string; type: string }[] = pendingRaw ? JSON.parse(pendingRaw) : []

  const fetchAll = useCallback((silent = false) => {
    if (!silent) setLoading(true)
    Promise.all([
      vizApi.life(),
      vizApi.health(),
      vizApi.events(),
      vizApi.strains(),
      vizApi.sync(),
    ]).then(([l, h, e, s, sy]) => {
      setLife(l); setHealth(h); setEvents(e); setStrains(s); setSync(sy)
    }).catch(() => {
      // No data yet — that's OK
    }).finally(() => { if (!silent) setLoading(false) })
  }, [])

  // Determine effective upload status: prefer sessionStorage, fall back to backend status
  const effectiveUploadStatus = (() => {
    if (pendingFiles.length > 0) {
      const nVer = pendingFiles.filter(f => f.type === 'VER').length
      const nHor = pendingFiles.filter(f => f.type === 'HOR').length
      return { has_uploads: true, has_processed: false, files: pendingFiles, n_ver: nVer, n_hor: nHor }
    }
    return uploadStatus
  })()

  useEffect(() => {
    const fetchStatus = () => {
      uploadPathsApi.status()
        .then(s => setUploadStatus(s))
        .catch(() => setUploadStatus({ has_uploads: false, has_processed: false, files: [], n_ver: 0, n_hor: 0 }))
    }
    fetchAll()
    fetchStatus()
    const handler = () => {
      if (!document.hidden) { fetchAll(true); fetchStatus() }
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [fetchAll])

  const handleProcess = async () => {
    if (!effectiveUploadStatus?.has_uploads || processing) return
    setProcessing(true)
    try {
      const files = effectiveUploadStatus.files || []
      const { task_id } = await pipelineApi.run(files)
      const pollStart = Date.now()
      let done = false
      while (Date.now() - pollStart < 300000) {
        const st = await pipelineApi.status(task_id)
        if (st.status === 'success') { done = true; break }
        if (st.status === 'error') throw new Error(st.error || 'Processing failed')
        await new Promise(r => setTimeout(r, 2000))
      }
      if (!done) throw new Error('Processing timed out after 5 minutes')
      sessionStorage.removeItem('pendingUploadFiles')
      fetchAll(true)
      setUploadStatus((prev: any) => ({ ...prev, has_processed: true }))
    } catch (err: any) {
      alert(err.message || 'Processing failed')
    }
    setProcessing(false)
  }

  // Show spinner only on first load when there's nothing to show yet
  if (loading && !effectiveUploadStatus?.has_uploads) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const eventsVer = events?.events_ver || []
  const eventsHor = events?.events_hor || []
  const healthSummary = health?.summary || {}
  const hasData = strains?.per_gauge?.length > 0
  const hasVer = effectiveUploadStatus?.n_ver > 0 || eventsVer.length > 0
  const hasHor = effectiveUploadStatus?.n_hor > 0 || eventsHor.length > 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-primary">Dashboard</h2>
          <p className="text-gray-500 text-sm mt-1">NH-71 Instrumented Pavement · IIT Tirupati</p>
        </div>
        {effectiveUploadStatus?.has_uploads && !effectiveUploadStatus?.has_processed && (
          <button onClick={handleProcess} disabled={processing}
            className="btn-primary text-sm flex items-center gap-2">
            {processing ? (
              <><span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span> Processing...</>
            ) : `Process ${effectiveUploadStatus.n_ver || 0} VER + ${effectiveUploadStatus.n_hor || 0} HOR Files`}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Fatigue Life (Nf)" value={life?.VER?.life?.Nf ? parseFloat(life.VER.life.Nf).toExponential(2) : '—'} subtitle="VER: IRC:37-2018" color="primary" />
        <MetricCard title="Rutting Life (Nr)" value={life?.VER?.life?.Nr ? parseFloat(life.VER.life.Nr).toExponential(2) : '—'} subtitle="VER: Shell model" color="accent" />
        <MetricCard title="HOR Fatigue" value={life?.HOR?.life?.Nf ? parseFloat(life.HOR.life.Nf).toExponential(2) : '—'} subtitle="HOR tensile strain" color="secondary" />
        <MetricCard title="Status" value={life?.VER?.life?.design_adequate ? 'Adequate' : hasData ? 'Inadequate' : '—'} subtitle={life?.VER?.life?.governing_failure || '—'} color={life?.VER?.life?.design_adequate ? 'success' : 'danger'} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="VEH Events" value={eventsVer.length} subtitle={`${eventsVer.length} detections`} color="secondary" />
        <MetricCard title="HOR Events" value={eventsHor.length} subtitle={`${eventsHor.length} detections`} color="accent" />
        <MetricCard title="Synced Bundles" value={sync?.n_bundles || 0} subtitle={`${sync?.bundles?.length || 0} matched`} color="warning" />
        <MetricCard title="Total Gauges" value={strains?.n_gauges || 0} subtitle={hasData ? `${strains.per_gauge.filter((g: any) => g.group === 'VER').length} VER · ${strains.per_gauge.filter((g: any) => g.group === 'HOR').length} HOR` : '—'} color="primary" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Healthy Gauges" value={healthSummary.healthy || '—'} subtitle={`of ${healthSummary.total || '—'} total`} color="success" />
        <MetricCard title="Warning Gauges" value={healthSummary.warning || 0} subtitle="Score 0.3–0.7" color="warning" />
        <MetricCard title="Excluded Gauges" value={healthSummary.excluded || 0} subtitle="Score < 0.3" color="danger" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {life?.plot_json_ver && <InteractivePlot plotJson={life.plot_json_ver} title="VER — Pavement Life" />}
        {life?.plot_json_hor && <InteractivePlot plotJson={life.plot_json_hor} title="HOR — Pavement Life" />}
        {!life?.plot_json_ver && !life?.plot_json_hor && <div className="card text-gray-400 text-center py-8 border-dashed border-2 border-gray-200">
          <p className="text-sm">No life prediction data</p>
          <p className="text-xs mt-1">Upload and process data first</p>
        </div>}
        {health?.plot_json && <InteractivePlot plotJson={health.plot_json} title="Gauge Health Scores" />}
      </div>

      <div className="card">
        <h3 className="card-title">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="/upload" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <span className="text-sm font-medium">Upload Data</span>
          </a>
          <a href="/strains" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <span className="text-sm font-medium">View Strains</span>
          </a>
          <a href="/events" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <span className="text-sm font-medium">Events</span>
          </a>
          <a href="/docs" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <span className="text-sm font-medium">Documentation</span>
          </a>
        </div>
      </div>
    </div>
  )
}
