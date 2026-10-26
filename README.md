# HeatGuard

Personal heat-strain early warning for outdoor workers (Future Health Digital Innovation Challenge, Population Health: Climate-Resilient Worker Health).

* `heatguard/physio.py` synthetic worker + weather simulator (hidden "truth")
* `heatguard/estimator.py` extended Kalman filter (core + skin temperature) with heart-rate correction and 30-min forecast
* `heatguard/policies.py` status quo, site WBGT cut-off, HeatGuard work-rest policies
* `heatguard/engine.py` closed-loop shift simulator
* `heatguard/alerts.py` multilingual alerts and role-based privacy views (machine-drafted translations, need native review)
* `heatguard/api.py` FastAPI service (`uvicorn heatguard.api:app`)
* `scripts/evaluate.py` tuning (seed 101), held-out (seed 202) and replicate (seed 303) evaluation, figures in `results/`
* `scripts/make_demo.py` builds the replay console `web/dist/index.html`
* `scripts/build_deck.py` fills the submission template

```
pip install numpy scipy matplotlib fastapi uvicorn httpx pytest
python -m pytest -q tests
python scripts/evaluate.py
python scripts/make_demo.py
```

All results are from simulation. The estimator uses its own population priors (it does not reuse the coefficients of Buller 2013 or Falcone 2024) and must be calibrated against ingestible-pill data before field use. Screening and decision support only; not a medical device.
