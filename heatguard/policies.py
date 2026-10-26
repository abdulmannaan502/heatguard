"""Work-rest policies compared in the evaluation. All policies obey the statutory midday break."""
from __future__ import annotations
import numpy as np

BAN = (750, 900)            # 12:30-15:00 (UAE midday break, 15 Jun - 15 Sep)
SHIFT = (360, 1080)         # 06:00-18:00
STATUS_QUO_BREAK = (570, 585)   # one 15-min tea break at 09:30
WBGT_CUTOFF = 32.0          # site-wide cut-off used by baseline B (screening-grade WBGT)

# HeatGuard thresholds (tuned on a separate seed set, see scripts/evaluate.py)
HG = dict(red_now=38.0, red_fc=38.4, amber_now=37.6, amber_fc=37.9, z=1.0,
          rest_red=15, rest_amber=5, resume_T=37.65, micro_gap=20)

def in_ban(t):
    return BAN[0] <= t < BAN[1]

class StatusQuo:
    name = "A  Status quo"
    def decide(self, t, N, **kw):
        if in_ban(t) or STATUS_QUO_BREAK[0] <= t < STATUS_QUO_BREAK[1]:
            return np.zeros(N, bool)
        return np.ones(N, bool)

class WBGTCutoff:
    name = "B  Site WBGT cut-off"
    def decide(self, t, N, wbgt_meas=None, **kw):
        if in_ban(t):
            return np.zeros(N, bool)
        return wbgt_meas < WBGT_CUTOFF

class HeatGuard:
    name = "C  HeatGuard"
    def __init__(self, N, params=None):
        self.p = dict(HG, **(params or {}))
        self.rest_until = np.zeros(N, int)
        self.last_micro = np.full(N, -999)
        self.rest_kind = np.zeros(N, int)       # 0 none, 1 amber micro-break, 2 red rest
        self.tier = np.zeros(N, int)

    def decide(self, t, N, est=None, fc_work=None, sig=None, **kw):
        p = self.p
        if in_ban(t):
            self.tier = np.zeros(N, int)
            return np.zeros(N, bool)
        Tc, Tf = est, fc_work
        up = Tc + p["z"] * sig
        red = (up >= p["red_now"]) | (Tf >= p["red_fc"])
        amber = (up >= p["amber_now"]) | (Tf >= p["amber_fc"])
        resting = t < self.rest_until
        # extend red rest until safe to resume
        cant_resume = (Tc > p["resume_T"]) | (Tf >= p["red_fc"])
        ext = (self.rest_kind == 2) & (self.rest_until == t) & cant_resume
        new_red = red & ~resting
        self.rest_until = np.where(new_red, t + p["rest_red"], self.rest_until)
        self.rest_kind = np.where(new_red, 2, self.rest_kind)
        # extension (5 min) while still hot after nominal rest
        self.rest_until = np.where(ext, t + 5, self.rest_until)
        resting = t < self.rest_until
        new_amber = amber & ~red & ~resting & (t - self.last_micro >= p["micro_gap"])
        self.rest_until = np.where(new_amber, t + p["rest_amber"], self.rest_until)
        self.rest_kind = np.where(new_amber, 1, self.rest_kind)
        self.last_micro = np.where(new_amber, t, self.last_micro)
        resting = t < self.rest_until
        self.tier = np.where(red, 2, np.where(amber, 1, 0))
        return ~resting
