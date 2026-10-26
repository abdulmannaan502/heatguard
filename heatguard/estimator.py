"""HeatGuard estimator: 2-state extended Kalman filter (core + skin temperature) that fuses
  (a) a population-mean heat-balance model driven by site weather, task class and acclimatization, with
  (b) the worker's own wearable heart rate (observation model: HR rises with workload and with core temperature).

Kalman-filter-from-heart-rate is established prior art (Buller et al. 2013, Physiol Meas; Falcone et al. 2024,
Front Public Health). The coefficients here are our own population priors, NOT those papers' regressions, and
must be calibrated against ingestible-pill data in a pilot.  Screening / decision support only - not diagnosis.
"""
from __future__ import annotations
import numpy as np
from .physio import psat, thermal_rates, sweat_demand, TASK_M, M_REST, acclim_factor

# population-mean priors the estimator is allowed to know
PRIOR = dict(mass=72.0, bsa=1.85, kT=19.0, kS=1.5, aM=0.25, R=9.0 ** 2,
             q_tc=0.012 ** 2, q_tsk=0.05 ** 2, assumed_drink_Lh_work=0.30, assumed_drink_Lh_rest=0.60)

def _params(A, v_assumed=1.5, N=None):
    mass, bsa = PRIOR["mass"], PRIOR["bsa"]
    return dict(hdry=3.6 + 1.2 * np.sqrt(v_assumed), he=55 + 22 * np.sqrt(v_assumed),
                Ccore=0.9 * mass * 0.964 / bsa, Csk=0.1 * mass * 0.964 / bsa,
                ksw=190 + 130 * A, Smax=400 + 280 * A, Tcon=37.0 - 0.3 * A)

def _env_from_meas(Ta, RH, S, working, v=1.5):
    pa = RH / 100.0 * psat(Ta)
    S_eff = np.where(working, S, 0.0)
    Tg = Ta + 0.012 * S_eff                       # deliberately different from the plant's globe model
    return pa, 0.5 * (Ta + Tg)

def _step(Tc, Tsk, dehyd, M, Ta, pa, Top, p, v=1.5, minutes=1.0, sub=2):
    dt = minutes / sub
    for _ in range(sub):
        S = sweat_demand(Tc, Tsk, dehyd, p)
        dTc, dTsk, _ = thermal_rates(Tc, Tsk, S, M, Ta, pa, Top, v, p)
        Tc = Tc + dTc * dt / 60.0
        Tsk = Tsk + dTsk * dt / 60.0
    return Tc, Tsk

class Estimator:
    def __init__(self, days, bsa_unused=None):
        N = len(days)
        self.N = N
        self.A = acclim_factor(days)
        self.p = _params(self.A)
        self.Tc = np.full(N, 37.1)
        self.Tsk = np.full(N, 34.5)
        self.P00 = np.full(N, 0.15 ** 2); self.P01 = np.zeros(N); self.P11 = np.full(N, 0.5 ** 2)
        self.dehyd = np.full(N, 0.8)
        self.hr0 = np.full(N, np.nan)
        self.hr_cal = []
        self.tsk_ref = np.full(N, 34.5)
        self.since_change = np.full(N, 99)
        self.prev_working = np.zeros(N, bool)
        self.kT_scale = 1.0   # for robustness ablations
        self.n = 0

    def update(self, hr_meas, Ta_m, RH_m, S_m, working, task_nom_lvl):
        """One-minute predict + correct. hr_meas may contain NaN (dropout)."""
        N = self.N
        pa, Top = _env_from_meas(Ta_m, RH_m, S_m, working)
        M = np.where(working, TASK_M[task_nom_lvl], M_REST)
        p = self.p
        # ---- predict (finite-difference Jacobian)
        T0, K0 = _step(self.Tc, self.Tsk, self.dehyd, M, Ta_m, pa, Top, p)
        e = 1e-3
        Tc1, Ks1 = _step(self.Tc + e, self.Tsk, self.dehyd, M, Ta_m, pa, Top, p)
        Tc2, Ks2 = _step(self.Tc, self.Tsk + e, self.dehyd, M, Ta_m, pa, Top, p)
        F00, F10 = (Tc1 - T0) / e, (Ks1 - K0) / e
        F01, F11 = (Tc2 - T0) / e, (Ks2 - K0) / e
        P00, P01, P11 = self.P00, self.P01, self.P11
        n00 = F00 * (F00 * P00 + F01 * P01) + F01 * (F00 * P01 + F01 * P11) + PRIOR["q_tc"]
        n01 = F10 * (F00 * P00 + F01 * P01) + F11 * (F00 * P01 + F01 * P11)
        n11 = F10 * (F10 * P00 + F11 * P01) + F11 * (F10 * P01 + F11 * P11) + PRIOR["q_tsk"]
        self.Tc, self.Tsk = T0, K0
        self.P00, self.P01, self.P11 = n00, n01, n11
        # hydration bookkeeping (assumed intake; true intake is unknown to the estimator)
        S = sweat_demand(self.Tc, self.Tsk, self.dehyd, p)
        drink = np.where(working, PRIOR["assumed_drink_Lh_work"], PRIOR["assumed_drink_Lh_rest"])
        self.dehyd = np.maximum(0.0, self.dehyd + (S * PRIOR["bsa"] / 1000.0 - drink) / 60.0 / PRIOR["mass"] * 100.0)
        # ---- baseline calibration from first 5 min of rest
        self.n += 1
        if self.n <= 5:
            self.hr_cal.append(hr_meas.copy())
            if self.n == 5:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    h0 = np.nanmean(np.vstack(self.hr_cal), axis=0)
                self.hr0 = np.where(np.isfinite(h0), h0, 70.0)
                self.tsk_ref = self.Tsk.copy()
            self.prev_working = working.copy()
            return
        # ---- correct
        changed = working != self.prev_working
        self.since_change = np.where(changed, 0, self.since_change + 1)
        self.prev_working = working.copy()
        kT = PRIOR["kT"] * self.kT_scale; kS = PRIOR["kS"]
        hr_exp = (self.hr0 + PRIOR["aM"] * (M - M_REST) + kT * (self.Tc - 37.1)
                  + kS * (self.Tsk - self.tsk_ref) + 4.0 * (self.dehyd - 0.8))
        R = PRIOR["R"] * np.where(self.since_change < 3, 4.0, 1.0)
        nu = hr_meas - hr_exp
        Sinn = kT * (kT * self.P00 + kS * self.P01) + kS * (kT * self.P01 + kS * self.P11) + R
        ok = np.isfinite(hr_meas) & (np.abs(nu) < 3.5 * np.sqrt(Sinn))
        nu = np.where(ok, nu, 0.0)
        K0g = (self.P00 * kT + self.P01 * kS) / Sinn
        K1g = (self.P01 * kT + self.P11 * kS) / Sinn
        K0g = np.where(ok, K0g, 0.0); K1g = np.where(ok, K1g, 0.0)
        self.Tc = self.Tc + K0g * nu
        self.Tsk = self.Tsk + K1g * nu
        a00 = self.P00 - K0g * (kT * self.P00 + kS * self.P01)
        a01 = self.P01 - K0g * (kT * self.P01 + kS * self.P11)
        a11 = self.P11 - K1g * (kT * self.P01 + kS * self.P11)
        self.P00, self.P01, self.P11 = np.maximum(a00, 1e-6), a01, np.maximum(a11, 1e-6)

    @property
    def sigma(self):
        return np.sqrt(self.P00)

    def forecast(self, Ta_m, RH_m, S_m, task_nom_lvl, horizon=30, work=True):
        """Tc forecast `horizon` min ahead assuming `work` (True) or rest-in-shade (False); persistence weather."""
        working = np.full(self.N, work)
        pa, Top = _env_from_meas(Ta_m, RH_m, S_m, working)
        M = np.where(working, TASK_M[task_nom_lvl], M_REST)
        Tc, Tsk, dh = self.Tc.copy(), self.Tsk.copy(), self.dehyd.copy()
        peak = Tc.copy()
        for _ in range(horizon):
            Tc, Tsk = _step(Tc, Tsk, dh, M, Ta_m, pa, Top, self.p, sub=1)
            peak = np.maximum(peak, Tc)
        return Tc, peak
