import { useEffect, useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi, pipelineApi } from '../api/client'

interface DesignState {
  layers?: { Layer: string; 'Thickness (mm)': number }[]
  A?: number; D?: number; F?: number; r?: number; n?: number; eMod?: number
}

export default function Prediction() {
  const location = useLocation()
  const designState = (location.state as DesignState) || {}

  const [lifeData, setLifeData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const [epsT, setEpsT] = useState(200)
  const [epsV, setEpsV] = useState(300)
  const [eMod, setEMod] = useState(designState.eMod || 3000)
  const [A, setA] = useState(designState.A || 1000)
  const [D, setD] = useState(designState.D || 0.75)
  const [F, setF] = useState(designState.F || 4.5)
  const [r, setR] = useState(designState.r || 0.05)
  const [n, setN] = useState(designState.n || 20)
  const [layers, setLayers] = useState(designState.layers || [
    { Layer: 'Wearing Course (BC)', 'Thickness (mm)': 40 },
    { Layer: 'Binder Course (DBM)', 'Thickness (mm)': 50 },
    { Layer: 'Granular Base', 'Thickness (mm)': 250 },
  ])
  const [customRunning, setCustomRunning] = useState(false)
  const [customResult, setCustomResult] = useState<any>(null)

  useEffect(() => {
    vizApi.life().then(setLifeData).finally(() => setLoading(false))
  }, [])

  const runCustom = async () => {
    setCustomRunning(true)
    try {
      const res = await pipelineApi.predict({
        epsilon_t: epsT, epsilon_v: epsV, E_MPa: eMod,
        A, D, F, r, n, layers,
      })
      setCustomResult(res)
    } catch (e: any) {
      setCustomResult({ error: e.message })
    }
    setCustomRunning(false)
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

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const life = lifeData?.life
  const unc = lifeData?.uncertainty

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-primary">Life Prediction</h2>
          <p className="text-gray-500 text-sm mt-1">IRC:37-2018 · Monte Carlo Uncertainty · Redesign Recommendations</p>
        </div>
        <Link to="/design" className="text-xs text-secondary hover:text-primary underline">Edit Design Params</Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Fatigue Life Nf" value={life?.Nf || '—'} subtitle="IRC:37-2018" color={life?.governing_failure === 'fatigue' ? 'danger' : 'primary'} icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        <MetricCard title="Rutting Life Nr" value={life?.Nr || '—'} subtitle="Shell model" color={life?.governing_failure === 'rutting' ? 'danger' : 'accent'} icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        <MetricCard title="Design Traffic Nd" value={life?.Nd || '—'} subtitle="Cumulative std axles" color="secondary" icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        <MetricCard title="Governing Mode" value={life?.governing_failure || '—'} subtitle={`Utilization: ${life?.fatigue_utilization || '—'}`} color={life?.design_adequate ? 'success' : 'danger'} icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {lifeData?.plot_json && <InteractivePlot plotJson={lifeData.plot_json} />}
        {lifeData?.plot_json2 && <InteractivePlot plotJson={lifeData.plot_json2} />}
      </div>

      {unc && (
        <div className="card">
          <h3 className="card-title">Monte Carlo Uncertainty (90% CI)</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-500">Nf p5:</span> <span className="font-medium">{unc.Nf_p5?.toExponential(2)}</span></div>
            <div><span className="text-gray-500">Nf p95:</span> <span className="font-medium">{unc.Nf_p95?.toExponential(2)}</span></div>
            <div><span className="text-gray-500">Nr p5:</span> <span className="font-medium">{unc.Nr_p5?.toExponential(2)}</span></div>
            <div><span className="text-gray-500">Nr p95:</span> <span className="font-medium">{unc.Nr_p95?.toExponential(2)}</span></div>
          </div>
        </div>
      )}

      <div className="card">
        <h3 className="card-title">Custom Life Prediction</h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
          <div>
            <h4 className="text-xs font-semibold text-gray-600 mb-2">Pavement Layers</h4>
            <div className="space-y-2">
              {layers.map((layer, i) => (
                <div key={i} className="flex gap-2 items-end">
                  <div className="flex-1">
                    <input type="text" value={layer.Layer} onChange={e => updateLayer(i, 'Layer', e.target.value)}
                      className="input-field text-xs" placeholder="Layer name" />
                  </div>
                  <div className="w-24">
                    <input type="number" value={layer['Thickness (mm)']} onChange={e => updateLayer(i, 'Thickness (mm)', e.target.value)}
                      className="input-field text-xs" min={0} />
                  </div>
                  <button onClick={() => removeLayer(i)} className="p-1 text-gray-400 hover:text-danger transition-colors">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <button onClick={addLayer} className="text-xs text-secondary hover:text-primary">+ Add Layer</button>
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-gray-600 mb-2">Traffic Parameters</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500">A — CVPD</label>
                <input type="number" value={A} onChange={e => setA(Number(e.target.value))} className="input-field text-xs" min={1} />
              </div>
              <div>
                <label className="block text-xs text-gray-500">D — Lane dist.</label>
                <input type="number" step={0.05} value={D} onChange={e => setD(Number(e.target.value))} className="input-field text-xs" min={0} max={1} />
              </div>
              <div>
                <label className="block text-xs text-gray-500">F — VDF</label>
                <input type="number" step={0.5} value={F} onChange={e => setF(Number(e.target.value))} className="input-field text-xs" min={1} />
              </div>
              <div>
                <label className="block text-xs text-gray-500">r — Growth</label>
                <input type="number" step={0.01} value={r} onChange={e => setR(Number(e.target.value))} className="input-field text-xs" min={0} max={1} />
              </div>
              <div>
                <label className="block text-xs text-gray-500">n — Period (yr)</label>
                <input type="number" value={n} onChange={e => setN(Number(e.target.value))} className="input-field text-xs" min={1} max={50} />
              </div>
              <div>
                <label className="block text-xs text-gray-500">E — Modulus (MPa)</label>
                <input type="number" value={eMod} onChange={e => setEMod(Number(e.target.value))} className="input-field text-xs" min={100} />
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4">
          <h4 className="text-xs font-semibold text-gray-600 mb-2">Strain Inputs</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">εt (µε) — Horizontal tensile</label>
              <input type="number" value={epsT} onChange={e => setEpsT(Number(e.target.value))} className="input-field" min={1} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">εv (µε) — Vertical compressive</label>
              <input type="number" value={epsV} onChange={e => setEpsV(Number(e.target.value))} className="input-field" min={1} />
            </div>
          </div>
          <button onClick={runCustom} disabled={customRunning} className="btn-primary">
            {customRunning ? 'Computing...' : 'Run Prediction'}
          </button>
        </div>

        {customResult && !customResult.error && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm p-4 bg-gray-50 rounded-lg">
              <div><span className="text-gray-500">Nf:</span> <span className="font-medium">{customResult.Nf}</span></div>
              <div><span className="text-gray-500">Nr:</span> <span className="font-medium">{customResult.Nr}</span></div>
              <div><span className="text-gray-500">Nd:</span> <span className="font-medium">{customResult.Nd}</span></div>
              <div><span className="text-gray-500">Adequate:</span> <span className={`font-medium ${customResult.design_adequate ? 'text-green-600' : 'text-red-600'}`}>{customResult.design_adequate ? 'Yes' : 'No'}</span></div>
            </div>
            {customResult.uncertainty && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Monte Carlo Uncertainty (90% CI)</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div><span className="text-gray-500">Nf p5:</span> <span className="font-medium">{customResult.uncertainty.Nf_p5?.toExponential(2)}</span></div>
                  <div><span className="text-gray-500">Nf p95:</span> <span className="font-medium">{customResult.uncertainty.Nf_p95?.toExponential(2)}</span></div>
                  <div><span className="text-gray-500">Nr p5:</span> <span className="font-medium">{customResult.uncertainty.Nr_p5?.toExponential(2)}</span></div>
                  <div><span className="text-gray-500">Nr p95:</span> <span className="font-medium">{customResult.uncertainty.Nr_p95?.toExponential(2)}</span></div>
                </div>
              </div>
            )}
            {customResult.redesign && renderRedesign(customResult.redesign)}
          </div>
        )}
        {customResult?.error && (
          <p className="mt-4 text-sm text-red-600">{customResult.error}</p>
        )}
      </div>
    </div>
  )
}