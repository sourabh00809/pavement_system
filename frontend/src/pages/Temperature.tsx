import { useEffect, useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import { vizApi } from '../api/client'

const THEME = {
  primary: '#1e3a5f', secondary: '#4a90d9', accent: '#e8a838',
  danger: '#e74c3c', bg: '#f5f7fa', card: '#ffffff', text: '#333333',
}

export default function Temperature() {
  const [raw, setRaw] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [offset10, setOffset10] = useState(0)
  const [offset11, setOffset11] = useState(0)

  useEffect(() => {
    vizApi.temperature(0, 0).then(setRaw).finally(() => setLoading(false))
  }, [])

  const calData = useMemo(() => {
    if (!raw) return null
    return {
      ch10: (raw.ch10_raw || []).map((v: number) => v + offset10),
      ch11: (raw.ch11_raw || []).map((v: number) => v + offset11),
    }
  }, [raw, offset10, offset11])

  const plotData = useMemo(() => {
    if (!raw || !calData) return []
    const traces: any[] = []
    if (raw.ch10_raw?.length) {
      traces.push(
        { x: raw.times, y: raw.ch10_raw, type: 'scatter', mode: 'lines',
          name: 'CH10 Raw', line: { color: THEME.danger, width: 1, dash: 'dot' },
          hovertemplate: 'Time: %{x:.3f}s<br>Raw: %{y:.1f} °C<extra></extra>' },
        { x: raw.times, y: calData.ch10, type: 'scatter', mode: 'lines',
          name: 'CH10 Calibrated', line: { color: THEME.accent, width: 1.5 },
          hovertemplate: 'Time: %{x:.3f}s<br>Cal: %{y:.1f} °C<extra></extra>' },
      )
    }
    if (raw.ch11_raw?.length) {
      traces.push(
        { x: raw.times, y: raw.ch11_raw, type: 'scatter', mode: 'lines',
          name: 'CH11 Raw', line: { color: THEME.secondary, width: 1, dash: 'dot' },
          hovertemplate: 'Time: %{x:.3f}s<br>Raw: %{y:.1f} °C<extra></extra>' },
        { x: raw.times, y: calData.ch11, type: 'scatter', mode: 'lines',
          name: 'CH11 Calibrated', line: { color: THEME.primary, width: 1.5 },
          hovertemplate: 'Time: %{x:.3f}s<br>Cal: %{y:.1f} °C<extra></extra>' },
      )
    }
    return traces
  }, [raw, calData])

  const stats = raw?.stats || {}

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Temperature Monitoring</h2>
        <p className="text-gray-500 text-sm mt-1">In-pavement temperature channels · Calibration offset controls</p>
      </div>

      <div className="card overflow-hidden">
        <Plot
          data={plotData}
          layout={{
            title: { text: 'Temperature Channels — Raw vs Calibrated', font: { size: 14, color: THEME.primary } },
            xaxis: { title: 'Time (s)', gridcolor: '#eee', zerolinecolor: '#ddd' },
            yaxis: { title: 'Temperature (°C)', gridcolor: '#eee', zerolinecolor: '#ddd' },
            plot_bgcolor: THEME.card, paper_bgcolor: THEME.bg,
            font: { family: 'Inter, sans-serif', color: THEME.text },
            margin: { l: 50, r: 20, t: 40, b: 50 },
            hovermode: 'closest', autosize: true, legend: { font: { size: 10 } },
          }}
          config={{ responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['lasso2d', 'select2d'], displaylogo: false }}
          style={{ width: '100%', height: 400 }}
          useResizeHandler
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="card-title">CH10 Calibration</h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">Offset (°C): <span className="font-mono font-bold text-accent">{offset10 >= 0 ? `+${offset10}` : offset10}</span></label>
            <input type="range" min={-50} max={50} value={offset10} onChange={e => setOffset10(Number(e.target.value))}
              className="w-full accent-accent" />
          </div>
          {stats.CH10 && (
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">Mean:</span> <span className="font-medium">{(stats.CH10.mean + offset10).toFixed(1)} °C</span></div>
              <div><span className="text-gray-500">Min:</span> <span className="font-medium">{(stats.CH10.min + offset10).toFixed(1)} °C</span></div>
              <div><span className="text-gray-500">Max:</span> <span className="font-medium">{(stats.CH10.max + offset10).toFixed(1)} °C</span></div>
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="card-title">CH11 Calibration</h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">Offset (°C): <span className="font-mono font-bold text-primary">{offset11 >= 0 ? `+${offset11}` : offset11}</span></label>
            <input type="range" min={-50} max={50} value={offset11} onChange={e => setOffset11(Number(e.target.value))}
              className="w-full accent-primary" />
          </div>
          {stats.CH11 && (
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">Mean:</span> <span className="font-medium">{(stats.CH11.mean + offset11).toFixed(1)} °C</span></div>
              <div><span className="text-gray-500">Min:</span> <span className="font-medium">{(stats.CH11.min + offset11).toFixed(1)} °C</span></div>
              <div><span className="text-gray-500">Max:</span> <span className="font-medium">{(stats.CH11.max + offset11).toFixed(1)} °C</span></div>
            </div>
          )}
        </div>
      </div>

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">About Temperature Calibration</h3>
        <p className="text-xs text-gray-600">
          CH10 and CH11 are thermocouple channels embedded in the pavement. Raw readings may require
          a constant offset correction based on field calibration. Adjust the sliders above to apply
          an additive offset — the chart and statistics update instantly without a server request.
        </p>
      </div>
    </div>
  )
}