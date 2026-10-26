import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from heatguard.physio import psat, wet_bulb, wbgt_outdoor, acclim_factor, make_workers, Plant, TASK_M
from heatguard.engine import make_scenario, run
from heatguard.alerts import population_view, supervisor_view, message, MESSAGES

def test_psat_wetbulb_reference():
    assert abs(psat(25) - 3.17) < 0.05
    assert abs(wet_bulb(20.0, 50.0) - 13.7) < 0.4        # Stull paper example
    assert wet_bulb(40, 30) < 40

def test_wbgt_monotonic_in_sun_and_humidity():
    a = wbgt_outdoor(38, 40, 800, 1.5)[0]; b = wbgt_outdoor(38, 40, 0, 1.5)[0]; c = wbgt_outdoor(38, 70, 800, 1.5)[0]
    assert a > b and c > a

def test_acclimatization_curve():
    assert 0.7 < acclim_factor(7) < 0.8 and acclim_factor(14) > 0.9 and acclim_factor(0) == 0

def test_plant_rest_stable_and_work_heats():
    w = make_workers(200, np.random.default_rng(0)); p = Plant(w); N = 200
    env = (np.full(N, 30.0), np.full(N, 40.0), np.zeros(N), np.full(N, 1.5))
    for _ in range(60): p.step_minute(np.zeros(N, int), np.zeros(N, bool), env, np.full(N, .3))
    assert 36.6 < p.Tc.mean() < 37.4
    env2 = (np.full(N, 40.0), np.full(N, 35.0), np.full(N, 900.0), np.full(N, 1.5))
    for _ in range(60): p.step_minute(np.full(N, 2), np.ones(N, bool), env2, np.full(N, .3))
    assert p.Tc.mean() > 37.8

def test_closed_loop_heatguard_beats_status_quo():
    sc = make_scenario(300, 7)
    a, c = run(sc, "A"), run(sc, "C")
    assert (c["peak"] >= 38.5).mean() < (a["peak"] >= 38.5).mean() * 0.5
    assert c["work"].mean() > 5 * 60
    assert np.sqrt(np.nanmean(a["rmse"] ** 2)) < 0.8

def test_privacy_views():
    v = supervisor_view("W1", 2, False)
    assert set(v) == {"worker", "tier", "action"}                 # no temperature, no heart rate
    assert population_view({"s": ["x"] * 4})["s"]["suppressed"]   # k-anonymity
    assert population_view({"s": [2, 1, 0, 0, 0]})["s"]["workers"] == 5
    assert all({"RED", "AMBER", "OK"} <= set(m) for m in MESSAGES.values())

def test_api_roundtrip():
    from fastapi.testclient import TestClient
    from heatguard.api import app
    c = TestClient(app)
    c.post("/v1/sites", json=dict(site_id="s1", worker_ids=["a", "b"], days_on_job=[1, 100], languages=["hi", "en"]))
    r = None
    for m in range(8):
        r = c.post("/v1/sites/s1/tick", json=dict(t_min=360 + m, hr=[80, None], Ta=40, RH=40, solar=800, task_level=[2, 2], working=[m >= 5, m >= 5]))
    assert r.status_code == 200 and len(r.json()["supervisor"]) == 2
    assert "estimated_core_temp_c" not in r.json()["supervisor"][0]
