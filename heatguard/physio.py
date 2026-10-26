"""Physiology + environment models.

PLANT  = the synthetic "ground truth" human (richer, individually varied, hidden from the estimator).
The estimator (estimator.py) uses a *simpler, population-mean* version of the same physics, so the
validation is not circular: parameters, clothing, wind, hydration, workload and sensor errors differ.

Units: Tc/Tsk degC, M and heat fluxes W/m2 of body surface, pressures kPa, sweat g/m2/h, time minutes.
"""
from __future__ import annotations
import numpy as np

# ---------------------------------------------------------------- environment
def psat(T):
    """Saturation vapour pressure (kPa), Tetens."""
    return 0.6108 * np.exp(17.27 * T / (T + 237.3))

def wet_bulb(T, RH):
    """Stull (2011) wet-bulb approximation (valid RH 5-99 %, T -20..50 degC)."""
    RH = np.clip(RH, 5.0, 99.0)
    return (T * np.arctan(0.151977 * np.sqrt(RH + 8.313659)) + np.arctan(T + RH)
            - np.arctan(RH - 1.676331) + 0.00391838 * RH ** 1.5 * np.arctan(0.023101 * RH) - 4.686035)

def wbgt_outdoor(Ta, RH, S, v):
    """Simplified outdoor WBGT = 0.7 Tnwb + 0.2 Tg + 0.1 Ta (screening-grade, not a Liljegren solution)."""
    Tw = wet_bulb(Ta, RH)
    Tnwb = Tw + 0.0011 * S
    Tg = Ta + 0.0135 * S / (0.6 + 0.3 * v)
    return 0.7 * Tnwb + 0.2 * Tg + 0.1 * Ta, Tg

def weather(t_h, day):
    """True weather at clock hour t_h for per-worker 'day' parameters (arrays shape (N,))."""
    Ta = day["Tmean"] + day["Amp"] * np.cos(2 * np.pi * (t_h - 15.0) / 24.0)
    RH = day["Rm"] + day["Ra"] * np.cos(2 * np.pi * (t_h - 4.0) / 24.0)
    RH = np.clip(RH, 15, 95)
    sun = np.clip(np.sin(np.pi * (t_h - 5.8) / 12.4), 0, None) ** 1.3
    S = day["Smax"] * sun * day["cloud"](t_h) if callable(day.get("cloud")) else day["Smax"] * sun
    return Ta, RH, S, day["v"]

# ---------------------------------------------------------------- tasks
TASK_M = np.array([120.0, 175.0, 235.0, 290.0])      # W/m2: light, moderate, heavy, very heavy (ISO 8996-like classes)
TASK_NAMES = ["light", "moderate", "heavy", "very heavy"]
M_REST = 65.0

def acclim_factor(days):
    """0..1 heat-acclimatization level; ~75 % after 7 days, ~94 % after 14 days."""
    return 1.0 - np.exp(-np.asarray(days, float) / 5.0)

# ---------------------------------------------------------------- shared thermal core
def thermal_rates(Tc, Tsk, sw, M, Ta, pa, Top, v, p):
    """Return dTc/dh, dTsk/dh (degC per hour) and evaporative heat E.  p = parameter dict (arrays or scalars)."""
    Eres = 0.0173 * M * (5.624 - pa)
    Cres = 0.0014 * M * (35.0 - Ta)
    resp = Eres + Cres
    skbf = np.clip((6.3 + 200.0 * np.maximum(0.0, Tc - 36.8)) / (1.0 + 0.5 * np.maximum(0.0, 33.7 - Tsk)), 0.5, 90.0)
    Qcs = (5.28 + 1.163 * skbf) * (Tc - Tsk)
    D = p["hdry"] * (Top - Tsk)
    Emax = np.maximum(0.0, p["he"] * (psat(Tsk) - pa))
    E = np.minimum(sw * 0.675, Emax)
    dTc = (M - resp - Qcs) / p["Ccore"]
    dTsk = (Qcs + D - E) / p["Csk"]
    return dTc, dTsk, E

def sweat_demand(Tc, Tsk, dehyd, p):
    S = p["ksw"] * np.maximum(0.0, Tc - (p["Tcon"] + 0.12 * dehyd)) + 18.0 * np.maximum(0.0, Tsk - 34.5)
    return np.minimum(S, p["Smax"] * (1.0 - 0.04 * dehyd))

# ---------------------------------------------------------------- synthetic workers / days
def make_workers(N, rng, overrides=None):
    age = np.clip(rng.normal(34, 8, N), 20, 58)
    mass = np.clip(rng.normal(70, 12, N), 48, 115)
    height = np.clip(rng.normal(168, 7, N), 150, 190)
    bsa = 0.007184 * mass ** 0.425 * height ** 0.725      # DuBois
    new = rng.random(N) < 0.30
    days = np.where(new, rng.integers(0, 7, N), rng.integers(7, 400, N)).astype(float)
    A = acclim_factor(days)
    w = dict(age=age, mass=mass, height=height, bsa=bsa, days=days, A=A,
             bmi=mass / (height / 100) ** 2,
             hrrest=np.clip(rng.normal(68, 8, N), 48, 95),
             a_hr=np.clip(rng.normal(0.25, 0.05, N), 0.12, 0.45),
             kT_hr=np.clip(rng.normal(20, 5, N), 8, 36) * (1.2 - 0.3 * A),
             Meps=rng.normal(0, 0.12, N),
             ksw=(190 + 130 * A) * rng.lognormal(0, 0.15, N),
             Smax=(400 + 280 * A) * rng.lognormal(0, 0.15, N),
             Tcon=37.0 - 0.3 * A + rng.normal(0, 0.1, N),
             Tc0=rng.normal(37.1, 0.15, N),
             dehyd0=np.maximum(0, rng.normal(0.8, 0.6, N)),
             fcl=rng.uniform(0.8, 1.25, N))
    if overrides:
        for k, val in overrides.items():
            w[k] = np.asarray(val, float)
        # keep derived fields coherent
        w["A"] = acclim_factor(w["days"])
        w["bsa"] = 0.007184 * w["mass"] ** 0.425 * w["height"] ** 0.725
        w["bmi"] = w["mass"] / (w["height"] / 100) ** 2
        if "ksw" not in overrides: w["ksw"] = (190 + 130 * w["A"]) * (w["ksw"] / (190 + 130 * acclim_factor(days)))
        if "Smax" not in overrides: w["Smax"] = (400 + 280 * w["A"]) * (w["Smax"] / (400 + 280 * acclim_factor(days)))
        if "Tcon" not in overrides: w["Tcon"] = w["Tcon"] + 0.3 * A - 0.3 * w["A"]
        if "kT_hr" not in overrides: w["kT_hr"] = w["kT_hr"] / (1.2 - 0.3 * A) * (1.2 - 0.3 * w["A"])
    return w

def make_days(N, rng, hot_bias=0.0):
    return dict(Tmean=rng.uniform(29.0, 37.5, N) + hot_bias, Amp=rng.uniform(4.5, 7.0, N),
                Rm=0, Ra=0, Smax=rng.uniform(750, 980, N), v=rng.uniform(0.7, 3.0, N),
                _rhmax=rng.uniform(55, 85, N), _rhmin=rng.uniform(25, 50, N))

def finalize_days(d):
    d["Rm"] = (d["_rhmax"] + d["_rhmin"]) / 2
    d["Ra"] = (d["_rhmax"] - d["_rhmin"]) / 2
    return d

def make_task_schedule(N, hours, rng):
    """task level per hour per worker; random walk +/-1 level with p=0.3 each hour."""
    probs = np.array([0.30, 0.40, 0.25, 0.05])
    lvl = rng.choice(4, size=N, p=probs)
    out = np.zeros((hours, N), int)
    for h in range(hours):
        step = rng.choice([-1, 0, 1], size=N, p=[0.15, 0.7, 0.15])
        lvl = np.clip(lvl + step, 0, 3)
        out[h] = lvl
    return out

# ---------------------------------------------------------------- plant
class Plant:
    def __init__(self, w):
        self.w = w
        N = len(w["age"])
        self.N = N
        self.Tc = w["Tc0"].copy()
        self.Tsk = np.full(N, 34.5)
        self.sw = np.zeros(N)
        self.hr = w["hrrest"].copy()
        self.cum_loss = np.zeros(N)       # kg
        self.cum_intake = np.zeros(N)     # kg
        self.hrmax = 208 - 0.7 * w["age"]

    @property
    def dehyd(self):
        return np.maximum(0.0, self.w["dehyd0"] + (self.cum_loss - self.cum_intake) / self.w["mass"] * 100.0)

    def step_minute(self, task_lvl, working, env, drink_Lh):
        w = self.w
        Ta, RH, S, v = env
        pa = RH / 100.0 * psat(Ta)
        S_eff = np.where(working, S, 0.0)                          # shade when resting
        Tg = Ta + 0.0135 * S_eff / (0.6 + 0.3 * v)
        Top = 0.5 * (Ta + Tg)
        pace = 1.0 - 0.25 * np.clip((self.Tc - 38.5) / 1.0, 0.0, 1.0)     # involuntary self-pacing above 38.5 degC
        M = np.where(working, TASK_M[task_lvl] * (1 + w["Meps"]) * pace, M_REST)
        p = dict(hdry=(3.6 + 1.2 * np.sqrt(v)) / np.sqrt(w["fcl"]),
                 he=w["fcl"] * (55 + 22 * np.sqrt(v)),
                 Ccore=0.9 * w["mass"] * 0.964 / w["bsa"], Csk=0.1 * w["mass"] * 0.964 / w["bsa"],
                 ksw=w["ksw"], Smax=w["Smax"], Tcon=w["Tcon"])
        sub, dt = 4, 0.25
        for _ in range(sub):
            dh = self.dehyd
            Sd = sweat_demand(self.Tc, self.Tsk, dh, p)
            self.sw += (Sd - self.sw) * dt / 2.0
            dTc, dTsk, E = thermal_rates(self.Tc, self.Tsk, self.sw, M, Ta, pa, Top, v, p)
            self.Tc += dTc * dt / 60.0
            self.Tsk += dTsk * dt / 60.0
            self.cum_loss += self.sw * w["bsa"] * dt / 60.0 / 1000.0
            self.cum_intake += drink_Lh * dt / 60.0
        dh = self.dehyd
        hrt = (w["hrrest"] + w["a_hr"] * (M - M_REST) + w["kT_hr"] * np.maximum(0, self.Tc - 37.0)
               + 1.5 * np.maximum(0, self.Tsk - 34.0) + 4.0 * dh)
        hrt = np.minimum(hrt, self.hrmax)
        self.hr += (hrt - self.hr) * (1 - np.exp(-1.0 / 1.0))
        return self.Tc, self.hr
