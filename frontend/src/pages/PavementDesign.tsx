import { useState } from 'react'
import MetricCard from '../components/MetricCard'
import { pipelineApi } from '../api/client'

const DEFAULT_LAYERS = [
  { Layer: 'Wearing Course (BC)', 'Thickness (mm)': 40 },
  { Layer: 'Binder Course (DBM)', 'Thickness (mm)': 50 },
  { Layer: 'Granular Base', 'Thickness (mm)': 250 },
]

export default function PavementDesign() {
  const [epsT, setEpsT] = useState(200)
  const [epsV, setEpsV] = useState(300)
  const [eMod, setEMod] = useState(3000)
  const [A, setA] = useState(1000)
  const [D, setD] = useState(0.75)
  const [F, setF] = useState(4.5)
  const [r, setR] = useState(0.05)
  const [n, setN] = useState(20)
  const [layers, setLayers] = useState(DEFAULT_LAYERS)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)

  const runPrediction = async () => {
    setRunning(true)
    try {
      const res = await pipelineApi.predict({
        epsilon_t: epsT,
        epsilon_v: epsV,
        E_MPa: eMod,
        A, D, F, r, n,
        layers,
      })
      setResult(res)
    } catch (e: any) {
      setResult({ error: e.message })
    }
    setRunning(false)
  }

  const updateLayer = (i: number, field: string, value: string | number) => {
    const next = [...layers]
    next[i] = { ...next[i], [field]: field === 'Thickness (mm)' ? Number(value) : value }
    setLayers(next)
  }

  const addLayer = () => {
    setLayers([...layers, { Layer: '', 'Thickness (mm)': 0 }])
  }

  const removeLayer = (i: number) => {
    if (layers.length > 1) setLayers(layers.filter((_, idx) => idx !== i))
  }

  const renderRedesign = (redesign: any) => {
    if (!redesign?.recommended) return null
    const rec = redesign.recommended
    return (
      <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
        <h4 className="font-semibold text-sm text-green-800 mb-2">Recommended Redesign</h4>
        <div className="text-xs text-green-700 space-y-1">
          <p>Wearing course: <strong>{rec.wearing_course_mm} mm</strong></p>
          <p>Binder course: <strong>{rec.binder_course_mm} mm</strong></p>
          <p>Granular layer: <strong>{rec.granular_layer_mm} mm</strong></p>
          <p>Binder: <strong>{rec.binder_recommendation}</strong></p>
          <p>Added thickness: <strong>{rec.added_thickness_mm} mm</strong></p>
          <p>Redesigned Nf: <strong>{rec.Nf ? rec.Nf.toExponential(2) : '—'}</strong></p>
          <p>Redesigned Nr: <strong>{rec.Nr ? rec.Nr.toExponential(2) : '—'}</strong></p>
          <p className={`font-semibold ${rec.design_adequate ? 'text-green-700' : 'text-red-600'}`}>
            Design adequate: {rec.design_adequate ? 'Yes' : 'No'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Pavement Design</h2>
        <p className="text-gray-500 text-sm mt-1">Layer configuration · Traffic parameters · IRC:37-2018</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="card-title">Pavement Layers</h3>
          <div className="space-y-3">
            {layers.map((layer, i) => (
              <div key={i} className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Layer</label>
                  <input type="text" value={layer.Layer} onChange={e => updateLayer(i, 'Layer', e.target.value)}
                    className="input-field text-sm" placeholder="Layer name" />
                </div>
                <div className="w-28">
                  <label className="block text-xs text-gray-500 mb-1">Thickness (mm)</label>
                  <input type="number" value={layer['Thickness (mm)']} onChange={e => updateLayer(i, 'Thickness (mm)', e.target.value)}
                    className="input-field text-sm" min={0} />
                </div>
                <button onClick={() => removeLayer(i)} className="p-2 text-gray-400 hover:text-danger transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
            <button onClick={addLayer} className="text-xs text-secondary hover:text-primary transition-colors flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Layer
            </button>
          </div>
        </div>

        <div className="card">
          <h3 className="card-title">Traffic Parameters</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">A — Initial CVPD</label>
              <input type="number" value={A} onChange={e => setA(Number(e.target.value))} className="input-field" min={1} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">D — Lane distribution</label>
              <input type="number" step={0.05} value={D} onChange={e => setD(Number(e.target.value))} className="input-field" min={0} max={1} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">F — VDF</label>
              <input type="number" step={0.5} value={F} onChange={e => setF(Number(e.target.value))} className="input-field" min={1} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">r — Growth rate</label>
              <input type="number" step={0.01} value={r} onChange={e => setR(Number(e.target.value))} className="input-field" min={0} max={1} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">n — Design period (years)</label>
              <input type="number" value={n} onChange={e => setN(Number(e.target.value))} className="input-field" min={1} max={50} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">E — AC modulus (MPa)</label>
              <input type="number" value={eMod} onChange={e => setEMod(Number(e.target.value))} className="input-field" min={100} />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Strain Inputs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">εt (µε) — Horizontal tensile strain</label>
            <input type="number" value={epsT} onChange={e => setEpsT(Number(e.target.value))} className="input-field" min={1} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">εv (µε) — Vertical compressive strain</label>
            <input type="number" value={epsV} onChange={e => setEpsV(Number(e.target.value))} className="input-field" min={1} />
          </div>
        </div>
        <button onClick={runPrediction} disabled={running} className="btn-primary mt-4">
          {running ? 'Computing...' : 'Run Life Prediction'}
        </button>
      </div>

      {result && !result.error && (
        <div className="card">
          <h3 className="card-title">Prediction Results</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <MetricCard title="Fatigue Life Nf" value={result.Nf} color="secondary" icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            <MetricCard title="Rutting Life Nr" value={result.Nr} color="accent" icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            <MetricCard title="Design Traffic Nd" value={result.Nd} color="primary" icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            <MetricCard title="Adequate" value={result.design_adequate ? 'Yes' : 'No'} color={result.design_adequate ? 'success' : 'danger'} icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </div>
          {result.uncertainty && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Monte Carlo Uncertainty (90% CI)</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div><span className="text-gray-500">Nf p5:</span> <span className="font-medium">{result.uncertainty.Nf_p5?.toExponential(2)}</span></div>
                <div><span className="text-gray-500">Nf p95:</span> <span className="font-medium">{result.uncertainty.Nf_p95?.toExponential(2)}</span></div>
                <div><span className="text-gray-500">Nr p5:</span> <span className="font-medium">{result.uncertainty.Nr_p5?.toExponential(2)}</span></div>
                <div><span className="text-gray-500">Nr p95:</span> <span className="font-medium">{result.uncertainty.Nr_p95?.toExponential(2)}</span></div>
              </div>
            </div>
          )}
          {result.redesign && renderRedesign(result.redesign)}
        </div>
      )}

      {result?.error && (
        <div className="card border border-red-200 bg-red-50">
          <p className="text-sm text-danger">{result.error}</p>
        </div>
      )}
    </div>
  )
}