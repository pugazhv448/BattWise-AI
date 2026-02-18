"""
ML layer: Isolation Forest on simulated discharge features.
Detects abnormal discharge behavior; integrates into risk evaluation.
Lightweight training on generated data; no heavy loops.
"""
import numpy as np
from typing import List, Optional

from backend.models.battery_models import TelemetryPoint


class AnomalyModel:
    """
    Wraps scikit-learn Isolation Forest. Trains on simulated telemetry features;
    predicts anomaly flag for evaluation. O(n) training with n = sample size.
    """

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self._model = None
        self._trained = False

    def _extract_features(self, telemetry: List[TelemetryPoint]) -> np.ndarray:
        """Convert telemetry to feature matrix for Isolation Forest."""
        if not telemetry:
            return np.zeros((0, 5))
        # Features per time step: soc, net_power, discharge_rate, solar, load
        n = len(telemetry)
        X = np.zeros((n, 5))
        for i, p in enumerate(telemetry):
            X[i, 0] = p.soc_percent / 100.0
            X[i, 1] = p.net_power_kw
            discharge_rate = 0.0
            if i > 0 and telemetry[i].hour > telemetry[i - 1].hour:
                dt = telemetry[i].hour - telemetry[i - 1].hour
                if dt > 0:
                    discharge_rate = (telemetry[i - 1].soc_percent - telemetry[i].soc_percent) / dt
            X[i, 2] = discharge_rate
            X[i, 3] = p.solar_kw
            X[i, 4] = p.load_kw
        return X

    def fit(self, telemetry_list: List[List[TelemetryPoint]]) -> "AnomalyModel":
        """
        Train on a list of telemetry runs (e.g. from multiple simulations).
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            self._trained = False
            return self
        all_features = []
        for telemetry in telemetry_list:
            if telemetry:
                all_features.append(self._extract_features(telemetry))
        if not all_features:
            self._trained = False
            return self
        X = np.vstack(all_features)
        if len(X) < 10:
            self._trained = False
            return self
        self._model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
            max_samples=min(256, len(X)),
        )
        self._model.fit(X)
        self._trained = True
        return self

    def predict(self, telemetry: List[TelemetryPoint]) -> bool:
        """
        Returns True if anomaly detected (any point predicted as outlier).
        Returns False if model not trained or no telemetry.
        """
        if not self._trained or not self._model or not telemetry:
            return False
        X = self._extract_features(telemetry)
        pred = self._model.predict(X)  # -1 = anomaly, 1 = normal
        return np.any(pred == -1)
