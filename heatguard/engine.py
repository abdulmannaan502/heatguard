"""Closed-loop shift simulator: plant (truth) + noisy sensors + estimator + policy."""
from __future__ import annotations
import numpy as np
from .physio import *
from .estimator import Estimator
from .policies import StatusQuo, WBGTCutoff, HeatGuard, SHIFT, HG

def make_scenario(N, seed, overrides=None, hot_bias=0.0, day_overrides=None):
    rng = np.random.default_rng(seed)
    w = make_workers(N, rng, overrides)
    day = finalize_days(make_days(N, rng, hot_bias))
    if day_overrides:
        for k, v in day_overrides.items():
            day[k] = np.broadcast_to(np.asarray(v, float), (N,)).copy()
        finalize_days(day)
    hours = (SHIFT[1] - SHIFT[0]) // 60 + 1
    tasks = make_task_schedule(N, hours, rng)
    T = SHIFT[1] - SHIFT[0]
    nz = dict(
        hr_ar=np.zeros((T, N)), hr_sens=rng.normal(0, 3.0, (T, N)),
        drop=rng.random((T, N)) < 0.04, outl=rng.random((T, N)) < 0.015,
        Ta_bias=rng.normal(0, 1.0, N), RH_err=rng.normal(0, 5.0, N),
        S_err=1 + rng.normal(0, 0.10, N), wbgt_err=rng.normal(0, 0.4, N),
        mislabel=rng.random((hours, N)) < 0.10, mis_dir=rng.choice([-1, 1], (hours, N)))
    e = rng.normal(0, 1, (T, N)); ar = np.zeros((T, N)); ar[0] = e[0] * 4.0
    for t in range(1, T):
        ar[t] = 0.9 * ar[t - 1] + np.sqrt(1 - 0.81) * 4.0 * e[t]
    nz["hr_ar"] = ar
    return dict(w=w, day=day, tasks=tasks, noise=nz, N=N, T=T, seed=seed)

def run(sc, policy, record=False, hg_params=None, kT_scale=1.0):
    w, day, tasks, nz = sc["w"], sc["day"], sc["tasks"], sc["noise"]
    N, T = sc["N"], sc["T"]
    plant = Plant(w)
    est = Estimator(w["days"]); est.kT_scale = kT_scale
    pol = {"A": StatusQuo, "B": WBGTCutoff}.get(policy)
    pol = pol() if pol else HeatGuard(N, hg_params)
    out = dict(peak=np.zeros(N), min385=np.zeros(N), min390=np.zeros(N), min380=np.zeros(N), work=np.zeros(N),
               sq_err=np.zeros(N), n_err=np.zeros(N), bias=np.zeros(N), first_red=np.full(N, np.nan),
               first_cross385=np.full(N, np.nan), red_alert_min=np.zeros(N), first_amber=np.full(N, np.nan))
    rec = {k: [] for k in ("Tc", "Tc_hat", "sig", "hr", "wbgt", "work", "tier", "Ta", "RH", "S", "task", "dehyd", "Tf")} if record else None
    working = np.ones(N, bool)
    tier_prev = np.zeros(N, int)
    est_ready = False
    Tc_hat = np.full(N, 37.1); sig = np.full(N, 0.15); Tf = np.full(N, 37.1)
    for i in range(T):
        t = SHIFT[0] + i
        h = t / 60.0
        hidx = i // 60
        Ta, RH, S, v = weather(h, day)
        wb_true, _ = wbgt_outdoor(Ta, RH, S, v)
        Ta_m = Ta + nz["Ta_bias"]; RH_m = np.clip(RH + nz["RH_err"], 10, 98); S_m = S * nz["S_err"]
        wb_m, _ = wbgt_outdoor(Ta_m, RH_m, S_m, 1.5); wb_m = wb_m + nz["wbgt_err"]
        # --- decision (uses info up to previous minute + current site sensors)
        if i < 5:
            working = np.zeros(N, bool)                     # assembly / baseline-calibration rest
            if hasattr(pol, "tier"): pol.tier = np.zeros(N, int)
        else:
            working = pol.decide(t, N, wbgt_meas=wb_m, est=Tc_hat, fc_work=Tf, sig=sig)
        lvl_true = tasks[hidx]
        lvl_nom = np.clip(lvl_true + np.where(nz["mislabel"][hidx], nz["mis_dir"][hidx], 0), 0, 3)
        resting_intake = 0.6; work_intake = 0.30
        drink = np.where(working, work_intake, resting_intake)
        plant.step_minute(lvl_true, working, (Ta, RH, S, v), drink)
        # --- sensors
        hr_m = plant.hr + nz["hr_ar"][i] * 0.5 + nz["hr_sens"][i]
        hr_m = np.where(nz["outl"][i], hr_m + 35, hr_m)
        hr_m = np.where(nz["drop"][i], np.nan, hr_m)
        est.update(hr_m, Ta_m, RH_m, S_m, working, lvl_nom)
        Tc_hat = est.Tc.copy(); sig = est.sigma
        Tf, _ = est.forecast(Ta_m, RH_m, S_m, lvl_nom, horizon=30, work=True)
        if i >= 5: est_ready = True
        # --- shadow tier (what HeatGuard would say) for every policy
        up = Tc_hat + sig
        red_s = (up >= HG["red_now"]) | (Tf >= HG["red_fc"])
        amb_s = (up >= HG["amber_now"]) | (Tf >= HG["amber_fc"])
        tier = np.where(red_s, 2, np.where(amb_s, 1, 0)) if i >= 6 else np.zeros(N, int)
        # --- metrics
        Tc = plant.Tc
        out["peak"] = np.maximum(out["peak"], Tc)
        out["min380"] += Tc >= 38.0; out["min385"] += Tc >= 38.5; out["min390"] += Tc >= 39.0
        out["work"] += working
        cross = (Tc >= 38.5) & np.isnan(out["first_cross385"]); out["first_cross385"][cross] = t
        fr = (tier == 2) & np.isnan(out["first_red"]); out["first_red"][fr] = t
        fa = (tier >= 1) & np.isnan(out["first_amber"]); out["first_amber"][fa] = t
        out["red_alert_min"] += (tier == 2)
        if i >= 20 and not in_ban_scalar(t):
            err = Tc_hat - Tc
            out["sq_err"] += err ** 2; out["n_err"] += 1; out["bias"] += err
        if record:
            rec["Tc"].append(Tc.copy()); rec["Tc_hat"].append(Tc_hat.copy()); rec["sig"].append(sig.copy())
            rec["hr"].append(np.where(np.isnan(hr_m), np.nan, hr_m)); rec["wbgt"].append(wb_true.copy())
            rec["work"].append(working.copy()); rec["tier"].append(tier.copy()); rec["Ta"].append(Ta.copy())
            rec["RH"].append(RH.copy()); rec["S"].append(S.copy()); rec["task"].append(lvl_true.copy())
            rec["dehyd"].append(plant.dehyd.copy()); rec["Tf"].append(Tf.copy())
    out["dehyd_end"] = plant.dehyd.copy()
    out["rmse"] = np.sqrt(out["sq_err"] / np.maximum(out["n_err"], 1))
    out["bias"] = out["bias"] / np.maximum(out["n_err"], 1)
    if record:
        out["rec"] = {k: np.array(v) for k, v in rec.items()}
    return out

def in_ban_scalar(t):
    return 750 <= t < 900
