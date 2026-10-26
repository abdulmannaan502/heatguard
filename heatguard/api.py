"""Minimal FastAPI service.  POST /v1/sites -> register workers; POST /v1/sites/{id}/tick -> one-minute update."""
from __future__ import annotations
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .estimator import Estimator
from .policies import HeatGuard
from .alerts import supervisor_view, worker_view, population_view

app = FastAPI(title="HeatGuard", version="0.1.0")
SITES: dict = {}

class SiteIn(BaseModel):
    site_id: str
    worker_ids: list[str]
    days_on_job: list[float]
    languages: list[str] | None = None

class Tick(BaseModel):
    t_min: int                    # minutes since midnight
    hr: list[float | None]        # bpm per worker (None = sensor dropout)
    Ta: float; RH: float; solar: float
    task_level: list[int]         # 0 light .. 3 very heavy (supervisor / accelerometer class)
    working: list[bool]

@app.post("/v1/sites")
def create_site(s: SiteIn):
    n = len(s.worker_ids)
    if len(s.days_on_job) != n: raise HTTPException(422, "days_on_job length mismatch")
    SITES[s.site_id] = dict(ids=s.worker_ids, lang=s.languages or ["en"] * n, est=Estimator(np.array(s.days_on_job)),
                            pol=HeatGuard(n), tier=np.zeros(n, int), tf=np.full(n, 37.1))
    return {"site_id": s.site_id, "workers": n}

@app.post("/v1/sites/{site_id}/tick")
def tick(site_id: str, k: Tick):
    S = SITES.get(site_id)
    if not S: raise HTTPException(404, "unknown site")
    n = len(S["ids"]); est = S["est"]
    hr = np.array([np.nan if x is None else x for x in k.hr], float)
    Ta, RH, So = (np.full(n, v) for v in (k.Ta, k.RH, k.solar))
    lvl = np.array(k.task_level)
    est.update(hr, Ta, RH, So, np.array(k.working), lvl)
    tf, _ = est.forecast(Ta, RH, So, lvl, 30, True)
    working = S["pol"].decide(k.t_min, n, est=est.Tc, fc_work=tf, sig=est.sigma)
    tier = S["pol"].tier
    return {"supervisor": [supervisor_view(i, t, bool(w)) for i, t, w in zip(S["ids"], tier, working)],
            "workers": [worker_view(i, t, c, l) for i, t, c, l in zip(S["ids"], tier, est.Tc, S["lang"])],
            "population": population_view({site_id: tier.tolist()})}
