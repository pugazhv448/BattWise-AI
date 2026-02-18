"""
Simulation engine: generates realistic 24h solar curve, load patterns,
and updates SoC based on charge/discharge. Supports multi-day and cloudy days.
Fully offline; no external APIs.
"""
import math
from typing import List, Optional, Set

from backend.models.battery_models import SimulationResult, TelemetryPoint
from backend.utils.smoothing import clamp_soc


class SimulationEngine:
    """
    Produces simulated inverter telemetry for LiFePO4 solar + household.
    Solar curve is location-agnostic (normalized 24h pattern); load follows
    typical residential peaks.
    """

    # Solar: approximate clear-sky curve (normalized), sunrise ~6, sunset ~18
    _SOLAR_HOURS = list(range(25))  # 0..24
    _SOLAR_BASE = [
        0, 0, 0, 0, 0, 0, 0.05, 0.15, 0.35, 0.55, 0.75, 0.9, 1.0,
        0.95, 0.85, 0.65, 0.4, 0.2, 0.05, 0, 0, 0, 0, 0, 0,
    ]
    # Typical household load (kW) by hour (baseline + evening peak)
    _LOAD_BASE_KW = [
        0.3, 0.25, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.5, 0.45, 0.5, 0.55,
        0.5, 0.5, 0.55, 0.6, 0.7, 0.9, 1.1, 1.0, 0.85, 0.7, 0.5, 0.35, 0.3,
    ]
    # Peak solar kW for 10 kWp system (scalable)
    PEAK_SOLAR_KW = 10.0
    INVERTER_EFFICIENCY = 0.97
    CHARGING_EFFICIENCY = 0.95
    DISCHARGING_EFFICIENCY = 0.95

    def __init__(
        self,
        capacity_kwh: float = 10.0,
        min_soc_percent: float = 20.0,
        max_soc_percent: float = 95.0,
    ):
        self.capacity_kwh = capacity_kwh
        self.min_soc_percent = min_soc_percent
        self.max_soc_percent = max_soc_percent

    def _solar_kw_at_hour(self, hour: float, is_cloudy: bool) -> float:
        """Solar output at given hour; cloudy reduces by ~70%."""
        h = max(0, min(24, hour))
        idx_lo = int(math.floor(h))
        idx_hi = min(24, idx_lo + 1)
        frac = h - idx_lo
        v_lo = self._SOLAR_BASE[idx_lo] if idx_lo < len(self._SOLAR_BASE) else 0
        v_hi = self._SOLAR_BASE[idx_hi] if idx_hi < len(self._SOLAR_BASE) else 0
        clear = v_lo * (1 - frac) + v_hi * frac
        if is_cloudy:
            clear *= 0.3
        return clear * self.PEAK_SOLAR_KW * self.INVERTER_EFFICIENCY

    def _load_kw_at_hour(self, hour: float) -> float:
        """Household load at given hour (kW)."""
        h = max(0, min(24, hour))
        idx = int(h) if h < 24 else 23
        return self._LOAD_BASE_KW[min(idx, 24)]

    def run(
        self,
        num_days: int = 1,
        initial_soc_percent: float = 80.0,
        cloudy_day_indices: Optional[Set[int]] = None,
        steps_per_hour: int = 1,
    ) -> SimulationResult:
        """
        Run multi-day simulation. steps_per_hour=1 gives one point per hour (24 per day).
        """
        cloudy = cloudy_day_indices or set()
        telemetry: List[TelemetryPoint] = []
        soc = initial_soc_percent
        capacity_kwh = self.capacity_kwh
        min_soc = self.min_soc_percent
        max_soc = self.max_soc_percent
        # Energy in kWh per 1% SoC
        kwh_per_percent = capacity_kwh / 100.0

        for day in range(num_days):
            is_cloudy = day in cloudy
            for step in range(24 * steps_per_hour):
                hour = step / steps_per_hour
                solar = self._solar_kw_at_hour(hour, is_cloudy)
                load = self._load_kw_at_hour(hour)
                net_kw = solar - load
                # Duration of this step in hours
                dt = 1.0 / steps_per_hour
                if net_kw >= 0:
                    # Charging: efficiency applied to what goes into battery
                    delta_kwh = net_kw * dt * self.CHARGING_EFFICIENCY
                else:
                    # Discharging
                    delta_kwh = net_kw * dt / self.DISCHARGING_EFFICIENCY
                delta_soc = (delta_kwh / kwh_per_percent)
                soc = clamp_soc(soc + delta_soc, min_soc, max_soc)
                telemetry.append(
                    TelemetryPoint(
                        hour=hour,
                        day_index=day,
                        solar_kw=round(solar, 4),
                        load_kw=round(load, 4),
                        soc_percent=round(soc, 2),
                        net_power_kw=round(net_kw, 4),
                        is_cloudy=is_cloudy,
                    )
                )
            # Carry SoC to next day
            pass

        final_soc = telemetry[-1].soc_percent if telemetry else initial_soc_percent
        return SimulationResult(
            telemetry=telemetry,
            initial_soc_percent=initial_soc_percent,
            final_soc_percent=final_soc,
            capacity_kwh=capacity_kwh,
            num_days=num_days,
            cloudy_days=sorted(cloudy),
        )
