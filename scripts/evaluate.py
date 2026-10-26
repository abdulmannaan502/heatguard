"""Synthetic validation: tuning curve (seed 101), held-out evaluation (seed 202), replicate (seed 303)."""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from heatguard.engine import make_scenario, run
from heatguard.policies import HG

OUT = os.path.join(os.path.dirname(__file__), "..", "results"); os.makedirs(OUT, exist_ok=True)
INK, TAUPE, BROWN, RED, GREEN, AMB = "#4a3f38", "#b9a995", "#7a6656", "#c0392b", "#3a7d5c", "#d99a1e"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})
rng = np.random.default_rng(0)

def pct(x): return float(100 * np.mean(x))
def boot(x, B=2000):
    x = np.asarray(x, float); idx = rng.integers(0, len(x), (B, len(x)))
    m = x[idx].mean(1) * 100
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]

def summarize(sc, R):
    w = sc["w"]; A, B, C = R["A"], R["B"], R["C"]
    S = {}
    for k, o in R.items():
        S[k] = dict(exc385=pct(o["peak"] >= 38.5), exc385_ci=boot(o["peak"] >= 38.5), exc380=pct(o["peak"] >= 38.0),
                    exc390=pct(o["peak"] >= 39.0), work_h=float(o["work"].mean() / 60), min_over385=float(o["min385"].mean()),
                    mean_peak=float(o["peak"].mean()), dehyd3=pct(o["dehyd_end"] >= 3.0))
    # estimator accuracy measured on policy A (no intervention => full range of Tc)
    S["estimator"] = dict(rmse=float(np.sqrt(np.nanmean(A["rmse"] ** 2))), mae_proxy=float(np.nanmean(A["rmse"])),
                          bias=float(np.nanmean(A["bias"])))
    # warning lead time on A: workers whose true Tc crosses 38.5
    cross = ~np.isnan(A["first_cross385"])
    lead = A["first_cross385"][cross] - A["first_red"][cross]
    lead = np.where(np.isnan(lead), -999, lead)
    S["warning"] = dict(n_cross=int(cross.sum()), warned_10=pct(lead >= 10), warned_any_before=pct(lead > 0),
                        median_lead_min=float(np.median(lead[lead > -999])) if (lead > -999).any() else None,
                        p25_lead=float(np.percentile(lead[lead > -999], 25)) if (lead > -999).any() else None)
    safe = A["peak"] < 38.0
    S["warning"]["red_alert_rate_among_never_38"] = pct(~np.isnan(A["first_red"][safe]))
    S["warning"]["amber_or_red_rate_among_never_38"] = pct(~np.isnan(A["first_amber"][safe]))
    S["warning"]["red_alert_rate_among_exceeders"] = pct(~np.isnan(A["first_red"][cross]))
    # fairness
    groups = {"acclim <7 d": w["days"] < 7, "acclim >=7 d": w["days"] >= 7, "age <30": w["age"] < 30,
              "age 30-40": (w["age"] >= 30) & (w["age"] < 40), "age >=40": w["age"] >= 40,
              "BMI <25": w["bmi"] < 25, "BMI 25-30": (w["bmi"] >= 25) & (w["bmi"] < 30), "BMI >=30": w["bmi"] >= 30}
    F = {}
    for g, m in groups.items():
        c = m & cross
        ld = A["first_cross385"][c] - A["first_red"][c]; ld = np.where(np.isnan(ld), -999, ld)
        F[g] = dict(n=int(m.sum()), rmse=float(np.sqrt(np.nanmean(A["rmse"][m] ** 2))), bias=float(np.nanmean(A["bias"][m])),
                    exc_A=pct(A["peak"][m] >= 38.5), exc_B=pct(B["peak"][m] >= 38.5), exc_C=pct(C["peak"][m] >= 38.5),
                    work_C=float(C["work"][m].mean() / 60), n_cross=int(c.sum()),
                    warned_10=pct(ld >= 10) if c.sum() else None)
    S["fairness"] = F
    return S

# ------------------------------------------------------------- tuning curve
print("tuning...")
sc_t = make_scenario(1500, 101)
tA, tB = run(sc_t, "A"), run(sc_t, "B")
curve = []
for z in (0, 1, 2):
    for d in np.arange(-0.6, 0.21, 0.1):
        prm = dict(red_now=38.3 + d, red_fc=38.7 + d, amber_now=37.9 + d, amber_fc=38.2 + d, z=z, resume_T=37.8 + d * 0.5)
        o = run(sc_t, "C", hg_params=prm)
        curve.append(dict(z=z, d=float(round(d, 2)), exc=pct(o["peak"] >= 38.5), work=float(o["work"].mean() / 60)))
json.dump(dict(curve=curve, A=dict(exc=pct(tA["peak"] >= 38.5), work=float(tA["work"].mean() / 60)),
               B=dict(exc=pct(tB["peak"] >= 38.5), work=float(tB["work"].mean() / 60))), open(f"{OUT}/tuning.json", "w"), indent=1)
fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=200)
for z, col in zip((0, 1, 2), (TAUPE, BROWN, INK)):
    pts = [(c["work"], c["exc"]) for c in curve if c["z"] == z]
    ax.plot(*zip(*pts), "-o", ms=3, color=col, lw=1.4, label=f"HeatGuard (uncertainty margin z={z})")
ax.scatter([tA["work"].mean() / 60], [pct(tA["peak"] >= 38.5)], color=RED, s=60, zorder=5, label="A status quo")
ax.scatter([tB["work"].mean() / 60], [pct(tB["peak"] >= 38.5)], color=AMB, s=60, zorder=5, label="B site WBGT cut-off")
cz = [c for c in curve if c["z"] == 1 and abs(c["d"] + 0.3) < 1e-6][0]
ax.scatter([cz["work"]], [cz["exc"]], facecolors="none", edgecolors=GREEN, s=190, lw=2, zorder=6, label="chosen operating point")
ax.set_xlabel("Productive work per worker (h / shift)"); ax.set_ylabel("Workers reaching Tc ≥ 38.5 °C (%)")
ax.legend(frameon=False, fontsize=7); ax.set_title("Safety vs productivity trade-off (tuning set, synthetic)", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/fig_tradeoff.png"); plt.close()

# ------------------------------------------------------------- held-out evaluations
final = {}
for name, seed in (("holdout_202", 202), ("replicate_303", 303)):
    print(name)
    sc = make_scenario(3000, seed)
    R = {k: run(sc, k) for k in "ABC"}
    final[name] = summarize(sc, R)
    if name == "holdout_202":
        keep = (sc, R)
json.dump(final, open(f"{OUT}/evaluation.json", "w"), indent=1)

# ------------------------------------------------------------- ablations (holdout)
print("ablations")
sc, R = keep
abl = {}
for label, kw in {"full": {}, "no heart-rate correction (model only)": dict(kT_scale=0.0),
                  "HR sensitivity prior -30 %": dict(kT_scale=0.7), "HR sensitivity prior +30 %": dict(kT_scale=1.3)}.items():
    a = run(sc, "A", kT_scale=kw.get("kT_scale", 1.0)); c = run(sc, "C", kT_scale=kw.get("kT_scale", 1.0))
    abl[label] = dict(rmse=float(np.sqrt(np.nanmean(a["rmse"] ** 2))), exc_C=pct(c["peak"] >= 38.5), work_C=float(c["work"].mean() / 60))
json.dump(abl, open(f"{OUT}/ablation.json", "w"), indent=1)

# ------------------------------------------------------------- figures
A, B, C = R["A"], R["B"], R["C"]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.2), dpi=200)
S = final["holdout_202"]
names = ["A\nstatus quo", "B\nWBGT cut-off", "C\nHeatGuard"]; cols = [RED, AMB, GREEN]
ex = [S[k]["exc385"] for k in "ABC"]; wk = [S[k]["work_h"] for k in "ABC"]
bars = axs[0].bar(names, ex, color=cols)
for b, v, k in zip(bars, ex, "ABC"):
    lo, hi = S[k]["exc385_ci"]; axs[0].errorbar(b.get_x() + b.get_width() / 2, v, yerr=[[v - lo], [hi - v]], color=INK, capsize=3, lw=1)
    axs[0].text(b.get_x() + b.get_width() / 2, hi + 1.2, f"{v:.1f}%", ha="center", fontsize=8)
axs[0].set_ylabel("Workers reaching Tc ≥ 38.5 °C (%)"); axs[0].set_ylim(0, max(ex) * 1.25)
bars = axs[1].bar(names, wk, color=cols)
for b, v in zip(bars, wk): axs[1].text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.1f} h", ha="center", fontsize=8)
axs[1].set_ylabel("Productive work (h / shift)"); axs[1].set_ylim(0, max(wk) * 1.2)
plt.tight_layout(); plt.savefig(f"{OUT}/fig_outcomes.png"); plt.close()

# estimator scatter at peak: est vs true over all minutes on a sample (re-run small recorded)
from heatguard.engine import make_scenario as ms
sc_s = ms(300, 505)
oa = run(sc_s, "A", record=True)
tc = oa["rec"]["Tc"][30:].ravel(); te = oa["rec"]["Tc_hat"][30:].ravel()
sel = np.random.default_rng(1).choice(len(tc), 12000, replace=False)
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.2), dpi=200)
axs[0].scatter(tc[sel], te[sel], s=2, alpha=0.25, color=BROWN, lw=0)
axs[0].plot([36.5, 40.5], [36.5, 40.5], color=INK, lw=1); axs[0].set_xlim(36.5, 40.5); axs[0].set_ylim(36.5, 40.5)
axs[0].set_xlabel("True core temperature (°C)"); axs[0].set_ylabel("HeatGuard estimate (°C)")
axs[0].set_title("Estimate vs truth (synthetic, 300 workers)", fontsize=9)
cross = ~np.isnan(A["first_cross385"]); lead = (A["first_cross385"] - A["first_red"])[cross]
lead = lead[~np.isnan(lead)]
axs[1].hist(np.clip(lead, -30, 120), bins=np.arange(-30, 130, 10), color=BROWN)
axs[1].axvline(0, color=INK, lw=1); axs[1].set_xlabel("Warning lead before 38.5 \u00b0C (min; 120 = 120+)"); axs[1].set_ylabel("Workers")
axs[1].set_title("Early-warning lead time (holdout)", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/fig_accuracy.png"); plt.close()
print(json.dumps({k: final["holdout_202"][k] for k in ("A", "B", "C", "estimator", "warning")}, indent=1))
