"""
Unit tests — Pavement Analysis System
Run with: python -m unittest tests.test_all -v
"""
import unittest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPreprocessing(unittest.TestCase):
    def setUp(self):
        from src.preprocessing.preprocessing import butter_bandpass, butter_highpass, baseline_correct
        self.bandpass = butter_bandpass
        self.highpass = butter_highpass
        self.baseline_correct = baseline_correct
        self.fs = 500
        t = np.arange(0, 5, 1 / self.fs)
        self.signal = np.random.randn(len(t)) * 2
        self.signal[1000:1030] += 150 * np.exp(-np.linspace(0, 3, 30))

    def test_bandpass_output_shape(self):
        out = self.bandpass(self.signal, self.fs)
        self.assertEqual(out.shape, self.signal.shape)

    def test_bandpass_attenuates_dc(self):
        dc_signal = self.signal + 500.0
        out = self.bandpass(dc_signal, self.fs)
        self.assertLess(abs(np.mean(out)), 10.0)

    def test_bandpass_preserves_peaks(self):
        out = self.bandpass(self.signal, self.fs)
        self.assertGreater(np.max(np.abs(out)), 20.0)

    def test_baseline_correct_shape(self):
        out = self.baseline_correct(self.signal, self.fs)
        self.assertEqual(out.shape, self.signal.shape)

    def test_highpass_shape(self):
        out = self.highpass(self.signal, self.fs)
        self.assertEqual(out.shape, self.signal.shape)

    def test_no_nan_output(self):
        out = self.bandpass(self.signal, self.fs)
        self.assertFalse(np.any(np.isnan(out)))


class TestSensorHealth(unittest.TestCase):
    def setUp(self):
        from src.sensor_health.sensor_health import check_gauge_health, get_gauge_weights
        self.check = check_gauge_health
        self.get_weights = get_gauge_weights

    def test_healthy_gauge(self):
        signal = np.random.randn(30000) * 50
        gh = self.check(signal, "CH0")
        self.assertGreater(gh.health_score, 0.5)
        self.assertFalse(gh.is_dead)
        self.assertFalse(gh.excluded)

    def test_dead_gauge(self):
        signal = np.ones(30000) * 5 + np.random.randn(30000) * 0.05
        gh = self.check(signal, "CH11")
        self.assertTrue(gh.is_dead)
        self.assertLess(gh.health_score, 0.5)

    def test_saturated_gauge(self):
        signal = np.ones(30000) * 2500 + np.random.randn(30000) * 10
        gh = self.check(signal, "CH12")
        self.assertTrue(gh.is_saturated)

    def test_health_score_bounds(self):
        for scale in [0.001, 5, 50, 200]:
            gh = self.check(np.random.randn(3000) * scale, "test")
            self.assertGreaterEqual(gh.health_score, 0.0)
            self.assertLessEqual(gh.health_score, 1.0)

    def test_weights_sum_to_one(self):
        from src.sensor_health.sensor_health import GaugeHealth
        hmap = {
            "CH0": GaugeHealth("CH0", 0.9, False, False, 0, 50),
            "CH1": GaugeHealth("CH1", 0.7, False, False, 0, 40),
            "CH2": GaugeHealth("CH2", 0.8, False, False, 0, 45),
        }
        w = self.get_weights(hmap, ["CH0", "CH1", "CH2"])
        self.assertAlmostEqual(sum(w.values()), 1.0, places=5)


class TestEventDetection(unittest.TestCase):
    def setUp(self):
        from src.event_detection.event_detection import detect_peaks, extract_events
        self.detect_peaks = detect_peaks
        self.extract_events = extract_events
        self.fs = 500
        t = np.arange(0, 10, 1 / self.fs)
        self.signal = np.random.randn(len(t)) * 2
        for ev_t in [2.0, 5.0, 8.0]:
            for ax_off in [0, int(0.3 * self.fs), int(0.6 * self.fs)]:
                idx = int(ev_t * self.fs) + ax_off
                if idx < len(self.signal) - 20:
                    self.signal[idx:idx+20] += 100 * np.exp(-np.linspace(0, 3, 20))
        self.series = pd.Series(self.signal, index=t, name="CH0")
        self.series.index.name = "time_s"

    def test_peaks_detected(self):
        peaks, _ = self.detect_peaks(self.signal)
        self.assertGreaterEqual(len(peaks), 3)

    def test_events_extracted(self):
        events = self.extract_events(self.series, "CH0")
        self.assertGreaterEqual(len(events), 1)

    def test_event_fields_valid(self):
        events = self.extract_events(self.series, "CH0")
        if events:
            e = events[0]
            self.assertGreaterEqual(e.axle_count, 1)
            self.assertLess(e.start_time, e.end_time)
            self.assertGreater(e.max_strain, 0)
            self.assertEqual(e.gauge_id, "CH0")

    def test_event_to_dict(self):
        events = self.extract_events(self.series, "CH0")
        if events:
            d = events[0].to_dict()
            for key in ["vehicle_id", "gauge_id", "axle_count", "max_strain", "start_time"]:
                self.assertIn(key, d)


class TestMechanistic(unittest.TestCase):
    def setUp(self):
        from src.mechanistic.mechanistic import (
            nf_fatigue, nr_shell, nd_irc,
            compute_pavement_life, compute_life_with_uncertainty
        )
        self.nf = nf_fatigue
        self.nr = nr_shell
        self.nd = nd_irc
        self.full = compute_pavement_life
        self.full_unc = compute_life_with_uncertainty

    def test_nf_positive(self):
        self.assertGreater(self.nf(200.0, 3000.0), 0)

    def test_nf_decreases_with_strain(self):
        self.assertGreater(self.nf(100.0, 3000.0), self.nf(400.0, 3000.0))

    def test_nf_known_value(self):
        eps_t = 200.0  # raw microstrain (no 1e-6 conversion)
        E, K1, K2, K3 = 3000.0, 3.34e18, 3.58, 1.75
        expected = K1 * (1 / eps_t) ** K2 * (1 / E) ** K3
        self.assertAlmostEqual(self.nf(200.0, E) / expected, 1.0, places=3)

    def test_nr_positive(self):
        self.assertGreater(self.nr(300.0), 0)

    def test_nr_decreases_with_strain(self):
        self.assertGreater(self.nr(100.0), self.nr(600.0))

    def test_nd_positive(self):
        self.assertGreater(self.nd(3000.0), 0)

    def test_nd_scales_with_traffic(self):
        self.assertGreater(self.nd(5000.0), self.nd(1000.0))

    def test_full_result_fields(self):
        r = self.full(200.0, 300.0, E_MPa=3000.0)
        self.assertGreater(r.Nf, 0)
        self.assertGreater(r.Nr, 0)
        self.assertGreater(r.Nd, 0)
        self.assertIn(r.governing_failure, ["fatigue", "rutting"])
        self.assertIsInstance(r.design_adequate, bool)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            self.nf(0.0, 3000.0)
        with self.assertRaises(ValueError):
            self.nr(0.0)

    def test_governing_fatigue(self):
        self.assertEqual(self.full(800.0, 100.0).governing_failure, "fatigue")

    def test_governing_rutting(self):
        self.assertEqual(self.full(50.0, 800.0).governing_failure, "rutting")

    def test_uncertainty_keys(self):
        unc = self.full_unc(200.0, 300.0, 20.0, 30.0, E_MPa=3000.0, n_samples=50)
        for key in ["Nf_mean", "Nf_std", "Nf_p5", "Nf_p95",
                    "Nr_mean", "Nr_std", "Nr_p5", "Nr_p95"]:
            self.assertIn(key, unc)

    def test_uncertainty_ci_ordering(self):
        unc = self.full_unc(200.0, 300.0, 20.0, 30.0, E_MPa=3000.0, n_samples=100)
        self.assertLessEqual(unc["Nf_p5"], unc["Nf_p95"])
        self.assertLessEqual(unc["Nr_p5"], unc["Nr_p95"])

    def test_redesign_recommendation_for_failed_section(self):
        from src.mechanistic.mechanistic import recommend_pavement_redesign
        redesign = recommend_pavement_redesign(
            100.0, 300.0, E_MPa=3000.0,
            layers=[
                {"Layer": "Wearing Course", "Thickness (mm)": 50},
                {"Layer": "Binder Course", "Thickness (mm)": 100},
                {"Layer": "Sub-base", "Thickness (mm)": 300},
            ],
            A=100.0,
        )
        rec = redesign["recommended"]
        self.assertIsNotNone(rec)
        self.assertGreaterEqual(rec["wearing_course_mm"], 50.0)
        self.assertGreaterEqual(rec["binder_course_mm"], 100.0)
        self.assertIn("binder_recommendation", rec)
        self.assertLessEqual(max(rec["fatigue_utilization"], rec["rutting_utilization"]), 0.90)


class TestFeatureEngineering(unittest.TestCase):
    def setUp(self):
        from src.feature_engineering.feature_engineering import (
            extract_waveform_features, estimate_collective_strain
        )
        self.extract_wf = extract_waveform_features
        self.collective = estimate_collective_strain

    def test_waveform_feature_keys(self):
        waveform = np.sin(np.linspace(0, np.pi, 100)) * 150
        feats = self.extract_wf(waveform)
        for key in ["max_strain", "mean_strain", "area_under_curve",
                    "peak_to_peak", "rise_time_s", "zero_crossing_rate"]:
            self.assertIn(key, feats)

    def test_waveform_features_positive(self):
        waveform = np.sin(np.linspace(0, np.pi, 100)) * 150
        feats = self.extract_wf(waveform)
        self.assertGreater(feats["max_strain"], 0)
        self.assertGreater(feats["area_under_curve"], 0)

    def test_empty_waveform(self):
        self.assertEqual(self.extract_wf(np.array([])), {})

    def test_collective_strain_nonnegative(self):
        from src.sensor_health.sensor_health import GaugeHealth
        fs = 500
        t = np.arange(0, 3, 1 / fs)
        df = pd.DataFrame({
            "CH0": np.random.randn(len(t)) * 80,
            "CH1": np.random.randn(len(t)) * 60,
        }, index=t)
        df.index.name = "time_s"
        hmap = {
            "CH0": GaugeHealth("CH0", 0.9, False, False, 0, 80),
            "CH1": GaugeHealth("CH1", 0.85, False, False, 0, 60),
        }
        gtypes = {"CH0": "horizontal_strain", "CH1": "vertical_strain"}
        eps_t, eps_v = self.collective(df, hmap, gtypes, 0.5, 1.5)
        self.assertGreaterEqual(eps_t, 0.0)
        self.assertGreaterEqual(eps_v, 0.0)


class TestSynchronization(unittest.TestCase):
    def setUp(self):
        from src.synchronization.synchronization import xcorr_lag, dtw_distance
        self.xcorr = xcorr_lag
        self.dtw = dtw_distance

    def test_xcorr_zero_lag_identical(self):
        sig = np.sin(np.linspace(0, 4 * np.pi, 500)) * 100
        lag, corr = self.xcorr(sig, sig)
        self.assertAlmostEqual(lag, 0.0, places=2)
        self.assertGreater(corr, 0.9)

    def test_xcorr_detects_lag(self):
        fs = 500
        sig_a = np.zeros(500)
        sig_a[100:130] += 100 * np.exp(-np.linspace(0, 3, 30))
        sig_b = np.zeros(500)
        sig_b[120:150] += 100 * np.exp(-np.linspace(0, 3, 30))
        lag, _ = self.xcorr(sig_a, sig_b, fs)
        self.assertAlmostEqual(abs(lag), 0.04, delta=0.01)

    def test_dtw_identical(self):
        sig = np.array([1.0, 2.0, 3.0, 2.0, 1.0])
        self.assertAlmostEqual(self.dtw(sig, sig), 0.0, places=5)

    def test_dtw_different(self):
        a = np.array([1.0, 2.0, 3.0, 2.0, 1.0])
        b = np.array([5.0, 6.0, 7.0, 6.0, 5.0])
        self.assertGreater(self.dtw(a, b), 0.0)


class TestIntegration(unittest.TestCase):
    def test_pipeline_chain(self):
        """Health → Events → Life end-to-end smoke test."""
        from src.preprocessing.preprocessing import butter_bandpass
        from src.sensor_health.sensor_health import assess_all_gauges, get_healthy_gauges
        from src.event_detection.event_detection import extract_all_events, events_to_dataframe
        from src.mechanistic.mechanistic import compute_pavement_life

        fs = 500
        t = np.arange(0, 8, 1 / fs)
        rng = np.random.default_rng(99)
        data = {}
        for i in range(3):
            s = rng.normal(0, 3, len(t))
            for ev in [2.0, 5.5]:
                for ax in range(3):
                    idx = int((ev + ax * 0.3) * fs)
                    if idx < len(s) - 25:
                        s[idx:idx+25] += 130 * np.exp(-np.linspace(0, 3, 25))
            data[f"CH{i}"] = butter_bandpass(s, fs)
        data["CH3"] = rng.normal(1800, 0.01, len(t))  # dead

        df = pd.DataFrame(data, index=t)
        df.index.name = "time_s"

        health = assess_all_gauges(df)
        healthy = get_healthy_gauges(health)
        self.assertNotIn("CH3", healthy)
        self.assertGreaterEqual(len(healthy), 1)

        events = extract_all_events(df, healthy)
        edf = events_to_dataframe(events)
        self.assertGreater(len(edf), 0)

        result = compute_pavement_life(200.0, 300.0, E_MPa=3000.0)
        self.assertGreater(result.Nf, 0)
        self.assertIn(result.governing_failure, ["fatigue", "rutting"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
