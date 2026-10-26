"""Run one illustrative shift (8 workers) with and without HeatGuard and build the dashboard (web/dist/index.html)."""
import sys, os, json
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
import numpy as np
from heatguard.engine import make_scenario, run
from heatguard.alerts import MESSAGES, LANG_NAMES

SEED = 6
days = [1, 3, 12, 45, 120, 2, 200, 30]
dov = dict(Tmean=36.0, Amp=6.0, _rhmax=80.0, _rhmin=38.0, Smax=950.0, v=1.4)
roles = ["Mason", "Rebar fixer", "Scaffolder", "Delivery rider", "Labourer", "Painter", "Crane signaller", "Welder helper"]
langs = ["ml", "hi", "ne", "ur", "bn", "tl", "en", "hi"]
sc = make_scenario(8, SEED, overrides=dict(days=days), day_overrides=dov)
A = run(sc, "A", record=True); C = run(sc, "C", record=True)
r = lambda a: np.round(a.T, 2).tolist()
def hr(a): return [[None if not np.isfinite(x) else round(float(x), 0) for x in row] for row in a.T]
data = dict(
    t0=360, T=720, startAt=0,
    workers=[dict(id=f"W-{i+1:02d}", role=roles[i], days=days[i], lang=langs[i], age=round(float(sc["w"]["age"][i])),
                  mass=round(float(sc["w"]["mass"][i]))) for i in range(8)],
    A=dict(Tc=r(A["rec"]["Tc"])),
    C=dict(Tc=r(C["rec"]["Tc"]), hat=r(C["rec"]["Tc_hat"]), sig=r(C["rec"]["sig"]), fc=r(C["rec"]["Tf"]), hr=hr(C["rec"]["hr"]),
           tier=C["rec"]["tier"].T.astype(int).tolist(), work=C["rec"]["work"].T.astype(int).tolist(), task=C["rec"]["task"].T.astype(int).tolist()),
    env=dict(wbgt=np.round(C["rec"]["wbgt"][:, 0], 1).tolist(), Ta=np.round(C["rec"]["Ta"][:, 0], 1).tolist(), RH=np.round(C["rec"]["RH"][:, 0], 0).tolist()),
    msgs=MESSAGES, langNames=LANG_NAMES,
    summary=dict(A_peak=np.round(A["peak"], 2).tolist(), C_peak=np.round(C["peak"], 2).tolist(),
                 A_work_h=float(A["work"].mean() / 60), C_work_h=float(C["work"].mean() / 60), seed=SEED))
os.makedirs(f"{ROOT}/web/dist", exist_ok=True)
json.dump(data, open(f"{ROOT}/results/demo_shift.json", "w"))
src = open(f"{ROOT}/web/dashboard.src.html").read()
js = "window.HG_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\nwindow.HG_DATA.inBan=function(i){return 360+i>=750&&360+i<900};"
open(f"{ROOT}/web/dist/index.html", "w").write(src.replace("/*__DATA__*/", js))
print("peaks A", data["summary"]["A_peak"], "C", data["summary"]["C_peak"], "work", data["summary"]["A_work_h"], data["summary"]["C_work_h"])
print("size KB", os.path.getsize(f"{ROOT}/web/dist/index.html") // 1024)
