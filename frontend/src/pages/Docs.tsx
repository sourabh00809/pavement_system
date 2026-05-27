export default function Docs() {
  const sections = [
    {
      title: 'Project Overview',
      content: `The Pavement Analysis System is an end-to-end pipeline for pavement response analysis and fatigue/rutting life prediction using real-time strain gauge data from the NH-71 instrumented pavement project at IIT Tirupati (CEE). The system processes data from 30 strain gauges (500,000 samples/file at 500 Hz) collected via GEOTRAN DAQ systems.

The pipeline implements IRC:37-2018 mechanistic-empirical design equations with physics-constrained models, providing pavement life prediction (Nf, Nr, Nd), Monte Carlo uncertainty quantification, and automated redesign recommendations.`,
    },
    {
      title: 'Module Architecture',
      content: `The system consists of 7 core processing modules:

A — Ingestion: Parses GEOTRAN .xls DAQ files, extracts gauge metadata. Supports VER (vertical/horizontal strain, temperature, EPC) and HOR files.

B — Preprocessing: Applies corrected 0.5–30 Hz bandpass Butterworth filter (critical fix from mid-term 0.1 Hz bug), polynomial baseline correction, and zero-mean normalization.

C — Sensor Health: Detects dead/saturated/drifting gauges via variance checks and autoencoder anomaly detection. Assigns health scores (0–1) and excludes unhealthy gauges from strain estimation.

D — Event Detection: Adaptive peak detection with automatic thresholding, axle grouping within 0.5s windows, vehicle event extraction within 3.0s grouping windows.

E — Synchronization: Cross-correlation lag estimation, Dynamic Time Warping (DTW) similarity matching, DBSCAN temporal clustering to link same vehicle events across multiple gauges.

F — Feature Engineering: Extracts waveform features (peak, area, rise time, zero-crossing rate) and estimates collective εt (horizontal tensile) and εv (vertical compressive) strain via health-weighted fusion.

G — Mechanistic Engine: Computes Nf (fatigue life), Nr (rutting life), Nd (design traffic) per IRC:37-2018, with Monte Carlo uncertainty propagation and pavement redesign optimization.`,
    },
    {
      title: 'IRC:37-2018 Equations',
      content: `Fatigue Life (Asphalt Institute):
Nf = K₁ × (1/εt)^K₂ × (1/E)^K₃

Where:
• εt = horizontal tensile strain at bottom of AC layer (µε)
• E = dynamic modulus of AC mix (MPa)
• K₁ = 0.005837, K₂ = 3.89, K₃ = 0.854 (B-80 bituminous mix)

Rutting Life (Shell):
Nr = K₄ × (1/εv)^K₅

Where:
• εv = vertical compressive strain at top of subgrade (µε)
• K₄ = 6.15×10⁻⁷, K₅ = 4.0

Design Traffic:
Nd = 365 × A × D × F × ((1+r)^n − 1) / r

Where:
• A = initial daily commercial vehicles (CVPD)
• D = lane distribution factor
• F = vehicle damage factor (VDF)
• r = annual traffic growth rate
• n = design period (years)`,
    },
    {
      title: 'DAQ Channel Map',
      content: `VER File:
• CH0–CH12: Vertical asphalt strain (µε)
• CH13–CH15: Horizontal asphalt strain (µε)

HOR File:
• CH0–CH9: Horizontal asphalt strain (µε)
• CH10–CH11: Temperature (°C)
• CH12–CH13: Earth Pressure Cell (MPa)

The system auto-detects faulty gauges (dead, saturated, drifting, or uncalibrated sensors) and excludes them from strain estimation via health-score weighting.`,
    },
    {
      title: 'ML Models (Vehicle Classification & Strain Prediction)',
      content: `Vehicle Type Classifier (XGBoost):
• 200 estimators, max depth 6
• 13 waveform/axle features
• 5-fold stratified cross-validation
• Falls back to RandomForest if XGBoost unavailable

Strain Response Predictor (LSTM):
• 128 hidden units, 0.2 dropout
• Predicts (εt, εv) from synchronized multi-gauge windows
• MC Dropout uncertainty quantification (100 passes)
• Physics-constrained: strains forced positive via torch.abs

Autoencoder Anomaly Detector:
• Dense 128→64→32→16→32→64→128
• 99th percentile reconstruction error threshold
• Trained on vehicle-free baseline windows`,
    },
    {
      title: 'Deployment',
      content: `Single-container deployment on Hugging Face Spaces (Docker):

• Backend: FastAPI serving all pipeline modules on port 7860
• Frontend: Built React SPA served directly by FastAPI (no separate hosting)
• Live at: https://sourabh00809-pavement-system.hf.space

Architecture:
  Browser → HF Spaces (Docker) → FastAPI (API + Static) → Core Python modules`,
    },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Documentation</h2>
        <p className="text-gray-500 text-sm mt-1">BTP Phase II · IIT Tirupati CEE · NH-71 Instrumented Pavement</p>
      </div>

      <div className="card bg-primary text-white">
        <div className="flex items-center gap-3 mb-2">
          <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <h3 className="font-semibold">Pavement Analysis System v2.0</h3>
        </div>
        <p className="text-sm text-white/80">Advisor: Prof. B. Krishna Prapoorna · IIT Tirupati · Department of Civil & Environmental Engineering</p>
      </div>

      {sections.map((section, i) => (
        <div key={i} className="card">
          <h3 className="card-title flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-primary text-white text-xs flex items-center justify-center font-medium">{i + 1}</span>
            {section.title}
          </h3>
          <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-line leading-relaxed">
            {section.content}
          </div>
        </div>
      ))}
    </div>
  )
}
