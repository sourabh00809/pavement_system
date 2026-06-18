import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const DEFAULT_LAYERS = [
  { Layer: 'Wearing Course (BC)', 'Thickness (mm)': 40 },
  { Layer: 'Binder Course (DBM)', 'Thickness (mm)': 50 },
  { Layer: 'Granular Base', 'Thickness (mm)': 250 },
]

export default function PavementDesign() {
  const navigate = useNavigate()
  const [layers, setLayers] = useState(DEFAULT_LAYERS)
  const [A, setA] = useState(1000)
  const [D, setD] = useState(0.75)
  const [F, setF] = useState(4.5)
  const [r, setR] = useState(0.05)
  const [n, setN] = useState(20)
  const [eMod, setEMod] = useState(3000)
  const [K1, setK1] = useState(3.34e18)
  const [K2, setK2] = useState(3.58)
  const [K3, setK3] = useState(1.75)
  const [K4, setK4] = useState(6.15e-7)
  const [K5, setK5] = useState(4.0)

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

  const continueToPrediction = () => {
    navigate('/prediction', { state: { layers, A, D, F, r, n, eMod, K1, K2, K3, K4, K5 } })
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Pavement Design</h2>
        <p className="text-gray-500 text-sm mt-1">Layer configuration · Traffic parameters</p>
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
        <h3 className="card-title">Material Parameters</h3>
        <p className="text-xs text-gray-500 mb-3">Fatigue: Nf = K1 × (1/εt)^K2 × (1/E)^K3 &nbsp;·&nbsp; Rutting: Nr = K4 × (1/εv)^K5</p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">K1 (fatigue factor)</label>
            <input type="number" step="1e15" value={K1} onChange={e => setK1(Number(e.target.value))} className="input-field" min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">K2 (strain exponent)</label>
            <input type="number" step={0.01} value={K2} onChange={e => setK2(Number(e.target.value))} className="input-field" min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">K3 (modulus exponent)</label>
            <input type="number" step={0.01} value={K3} onChange={e => setK3(Number(e.target.value))} className="input-field" min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">K4 (rutting factor)</label>
            <input type="number" step="1e-7" value={K4} onChange={e => setK4(Number(e.target.value))} className="input-field" min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">K5 (rutting exponent)</label>
            <input type="number" step={0.1} value={K5} onChange={e => setK5(Number(e.target.value))} className="input-field" min={0} />
          </div>
        </div>
      </div>

      <div className="card text-center">
        <p className="text-sm text-gray-500 mb-4">Design params are sent to the Life Prediction section where you'll also enter strain values.</p>
        <button onClick={continueToPrediction} className="btn-primary">
          Continue to Life Prediction
        </button>
      </div>
    </div>
  )
}