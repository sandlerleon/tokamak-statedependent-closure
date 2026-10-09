# -*- coding: utf-8 -*-
"""Figures for the manuscript (IEEE Transactions style: Times-like labels, no titles, EPS and PNG) and for the supplementary material.   python figures.py   (reads ../results.json)"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import theory as TH

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "..", "figures")
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"], "mathtext.fontset": "stix", "font.size": 8,
                     "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.2})
COL = {"base": "#222222", "a": "#1f6fb5", "b": "#c0522d", "c": "#2e8b57", "d": "#8a4fb0", "e": "#d69a1c"}
WIDE = 7.1


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".eps"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def panel(ax, s):
    ax.text(-0.17, 1.04, "(%s)" % s, transform=ax.transAxes, fontsize=8, fontweight="bold")


# ---- Fig. 1: profiles of the smoothed closure
P = R["profiles"]
fig, ax = plt.subplots(1, 3, figsize=(WIDE, 2.2))
for key, lab, c in (("baseline", "baseline", COL["base"]), ("sc0.3", r"$s_c=0.3$", COL["a"]), ("sc0.1", r"$s_c=0.1$", COL["b"])):
    r = np.array(P[key]["r"]) / 2.0
    ax[0].plot(r, P[key]["T"], color=c, label=lab)
    ax[1].plot(r, P[key]["chi"], color=c, label=lab)
    ax[2].plot(r, P[key]["ratio"], color=c, label=lab)
ax[0].set_xlabel(r"$r/a$"); ax[0].set_ylabel(r"$T$ (keV)"); ax[0].legend(frameon=False)
ax[1].set_xlabel(r"$r/a$"); ax[1].set_ylabel(r"$\chi$ (m$^2$ s$^{-1}$)"); ax[1].set_yscale("log")
ax[2].set_xlabel(r"$r/a$"); ax[2].set_ylabel(r"smoothed $\omega_E/\gamma_0$")
for k, s in enumerate("abc"):
    panel(ax[k], s)
fig.tight_layout(); save(fig, "fig1_profiles")

# ---- Fig. 2: the local closure is ill-posed; the answer depends on the edge condition
LC = R["local_closure"]
fig, ax = plt.subplots(1, 3, figsize=(WIDE, 2.4))
for N, c in (("50", COL["a"]), ("100", COL["b"]), ("200", COL["c"]), ("400", COL["d"])):
    rows = [r for r in LC["rows"][N] if r["ok"]]
    sc = [r["sc"] for r in rows]
    lam = np.array([r["lam1"] for r in rows])
    ax[0].plot(sc, np.sign(lam) * np.log10(1 + np.abs(lam)), "o-", ms=2.5, color=c, label=r"$N=%s$" % N)
ax[0].axhline(0, color="k", lw=0.5)
ax[0].set_xscale("log"); ax[0].invert_xaxis()
ax[0].set_xlabel(r"$s_c$"); ax[0].set_ylabel(r"sgn($\lambda_1$) log$_{10}$(1 + |$\lambda_1$|)"); ax[0].legend(frameon=False, fontsize=6.5, loc="lower left")
th = LC["threshold"]
Ns = [int(k) for k in th if th[k]]
ax[1].loglog(Ns, [th[str(n)] for n in Ns], "o-", color=COL["b"], ms=3)
if LC["threshold_exponent"] is not None:
    n0 = np.array([min(Ns), max(Ns)], float)
    ax[1].loglog(n0, th[str(Ns[0])] * (n0 / n0[0]) ** LC["threshold_exponent"], "k--", lw=0.7)
    ax[1].text(0.08, 0.82, r"$\propto N^{%.2f}$" % LC["threshold_exponent"], transform=ax[1].transAxes, fontsize=7)
ax[1].set_xlabel(r"cells $N$"); ax[1].set_ylabel(r"onset of instability $s_c^{\mathrm{lin}}$")
EV = R["edge_variants"]
names = {"local, first-order edge": "first-order\nedge", "local, edge value held": "edge value\nheld", "local, no suppression in the last cell": "no supp.\nlast cell",
         "smoothed, l = 0.02 m": r"$\ell$=0.02", "smoothed, l = 0.05 m": r"$\ell$=0.05", "smoothed, l = 0.10 m": r"$\ell$=0.10", "smoothed, l = 0.20 m": r"$\ell$=0.20"}
xs, ys, cols = [], [], []
for rec in EV:
    if rec["name"] in names and rec.get("Q@0.1/N400") is not None:
        xs.append(names[rec["name"]]); ys.append(rec["Q@0.1/N400"]); cols.append(COL["e"] if rec["name"].startswith("local") else COL["a"])
ax[2].bar(range(len(xs)), ys, color=cols)
ax[2].set_xticks(range(len(xs))); ax[2].set_xticklabels([x.replace(chr(10), " ") for x in xs], fontsize=5.5, rotation=40, ha="right")
ax[2].set_ylim(min(ys) * 0.98, max(ys) * 1.02); ax[2].set_ylabel(r"$Q$ at $s_c=0.1$, $N=400$")
for k, s in enumerate("abc"):
    panel(ax[k], s)
fig.tight_layout(); save(fig, "fig2_illposed")

# ---- Fig. 3: smoothed closure: gain law, convergence and sensitivity
T1 = [r for r in R["table1"] if r["sc"] is not None]
base = [r for r in R["table1"] if r["sc"] is None][0]["Q"]
G = R["grid"]
UH = R["uncertainty_heat"]["stats"]
fig, ax = plt.subplots(1, 3, figsize=(WIDE, 2.4))
sc = np.array([r["sc"] for r in T1]); Q = np.array([r["Q"] for r in T1])
ax[0].loglog(sc, (Q - base) / base * 100, "o", ms=3, color=COL["b"], label="steady states ($N=400$)")
xx = np.logspace(np.log10(0.017), 0.05, 50)
Cl = R["linear_response"]["C_mean"]
ax[0].loglog(xx, Cl / xx ** 2 / base * 100, "k--", lw=0.8, label=r"$\Delta Q=C/s_c^{2}$")
for key, c, lab in (("gain@0.3", COL["a"], None), ("gain@0.1", COL["a"], None), ("gain@0.05", COL["a"], "5–95 % (uncertainty)")):
    s_ = float(key.split("@")[1]); st = UH[key]
    ax[0].plot([s_, s_], [st["p05"] * 100, st["p95"] * 100], color=c, lw=3, alpha=0.45, solid_capstyle="butt", label=lab)
ax[0].set_xlabel(r"$s_c$"); ax[0].set_ylabel(r"gain $\Delta Q/Q$ (%)"); ax[0].invert_xaxis(); ax[0].legend(frameon=False, fontsize=6)
Nn = np.array(G["N"][:-1], float)
for key, c, lab in (("0.5", COL["a"], r"$s_c=0.5$"), ("0.2", COL["c"], r"$0.2$"), ("0.1", COL["b"], r"$0.1$"), ("0.05", COL["d"], r"$0.05$")):
    q = np.array([r["Q"] for r in G["rows"][key]])
    ax[1].loglog(Nn, np.abs(q[:-1] - q[-1]) / q[-1], "o-", ms=3, color=c, label=lab)
ax[1].loglog(Nn, 0.6 / Nn, "k:", lw=0.7); ax[1].loglog(Nn, 40.0 / Nn ** 2, "k--", lw=0.7)
ax[1].set_xlabel(r"cells $N$"); ax[1].set_ylabel(r"$|Q_N-Q_{800}|/Q_{800}$"); ax[1].legend(frameon=False, fontsize=6.5)
rc = UH["gain@0.1"]["rank_corr"]
lab = {"chi_s": r"$\chi_s$", "kappa_c": r"$\kappa_c$", "w": r"$w$", "Ta": r"$T_a$", "n0": r"$n_0$", "B": r"$B$", "reg_length": r"$\ell$"}
order = sorted(rc, key=lambda k: -abs(rc[k]))
ax[2].barh(range(len(order)), [rc[k] for k in order], color=[COL["a"] if rc[k] > 0 else COL["b"] for k in order])
ax[2].set_yticks(range(len(order))); ax[2].set_yticklabels([lab[k] for k in order]); ax[2].invert_yaxis()
ax[2].set_xlabel(r"Spearman rank correlation with the gain at $s_c=0.1$"); ax[2].axvline(0, color="k", lw=0.5)
for k, s in enumerate("abc"):
    panel(ax[k], s)
fig.tight_layout(); save(fig, "fig3_smoothed")

# ---- Fig. 4: admissibility theory and tests on the rotation equation
SCR = [r for r in R["scalar_flux_relation"] if r["exists_theory"] and r["exists_numeric"]]
H = R["rotation_hysteresis"]
L = np.linspace(0, 4, 2001)
fig, ax = plt.subplots(1, 3, figsize=(WIDE, 2.4))
for mm, c in ((0.5, COL["c"]), (1.0, COL["a"]), (2.0, COL["b"]), (3.0, COL["d"])):
    ax[0].plot(L, TH.Psi(L, TH.F_alg, m=mm), color=c, label=r"$m=%g$" % mm)
for f, c in ((0.05, COL["e"]), (0.20, COL["base"])):
    ax[0].plot(L, TH.Psi(L, TH.F_floor_alg, f=f), color=c, ls="--", lw=0.9, label=r"floor $f=%.2f$" % f)
Ls, Ps = TH.alg_stationary_point(2.0)
ax[0].plot([Ls], [Ps], "ko", ms=3)
ax[0].set_ylim(0, 1.25); ax[0].set_xlabel(r"$\Lambda$"); ax[0].set_ylabel(r"$\Psi=\Lambda F(\Lambda)$"); ax[0].legend(frameon=False, fontsize=5.5, loc="upper left", bbox_to_anchor=(0.30, 0.42))
mk = {0.5: "o", 1.0: "s", 2.0: "^"}
colm = {0.5: COL["c"], 1.0: COL["a"], 2.0: COL["b"]}
for mm in (0.5, 1.0, 2.0):
    pts = [r for r in SCR if r["m"] == mm]
    ax[1].loglog([r["Lam_pred"] for r in pts], [r["Lam_sim"] for r in pts], mk[mm], ms=3.2, color=colm[mm], label=r"$m=%g$" % mm)
xx = np.logspace(-1.4, 0.2, 10); ax[1].loglog(xx, xx, "k-", lw=0.6)
ax[1].set_xlabel(r"$\Lambda_{max}$ predicted"); ax[1].set_ylabel(r"$\Lambda_{max}$ simulated"); ax[1].legend(frameon=False, fontsize=6.5)
for f, c in (("0.05", COL["b"]), ("0.2", COL["a"])):
    t = np.array(H[f]["torque"]); up = np.array([np.nan if v is None else v for v in H[f]["up"]]); dn = np.array([np.nan if v is None else v for v in H[f]["down"]])
    ax[2].plot(t, up, "-", color=c, label=r"$f=%s$ up" % f); ax[2].plot(t, dn, "--", color=c, label=r"$f=%s$ down" % f)
pw = H["0.05"]["predicted"]
ax[2].axvspan(pw["torque_down"], pw["torque_up"], color="0.9", zorder=0)
ax[2].set_yscale("log"); ax[2].set_xlabel("torque (N m)"); ax[2].set_ylabel(r"$\Lambda_{max}$"); ax[2].legend(frameon=False, fontsize=6, loc="upper left")
for k, s in enumerate("abc"):
    panel(ax[k], s)
fig.tight_layout(); save(fig, "fig4_admissibility")

# ---- Fig. 5: torque-driven shear with the neutral-beam torque estimate
CP = R["coupled_scan"]
fig, ax = plt.subplots(figsize=(3.4, 2.5))
for clos, c, mk_, lab in (("linear", COL["base"], "o", "constant viscosity"), ("m=1", COL["a"], "s", r"$m=1$"), ("m=2 f=0.20", COL["c"], "^", r"$m=2$, floor 0.20")):
    for sign, ls in ((1.0, "-"), (-1.0, ":")):
        pts = [r for r in CP if r["sign"] == sign and r["closure"] == clos and r["ok"]]
        ax.plot([r["torque"] for r in pts], [r["Q"] for r in pts], mk_ + ls, ms=2.5, color=c, label=(lab if sign > 0 else None))
nb = R["calibration"]["nbi_torque"]
ax.axvspan(nb["4.5"], nb["6.0"], color="0.88", zorder=0)
ax.text(nb["4.5"] + 1, ax.get_ylim()[1] * 0.97, "ITER-like\nbeam torque", fontsize=6, va="top")
ax.set_xlabel("torque (N m)"); ax.set_ylabel(r"fusion gain $Q$"); ax.legend(frameon=False, fontsize=6, loc="upper left", bbox_to_anchor=(0.02, 0.72))
fig.tight_layout(); save(fig, "fig5_torque")

# ---- Supplementary figure S1: power scan
Pa = R["paux_scan"]
fig, ax = plt.subplots(1, 2, figsize=(5.8, 2.4))
for key, lab, c in (("baseline", "baseline", COL["base"]), ("sc0.5", r"$s_c=0.5$", COL["a"]), ("sc0.3", r"$s_c=0.3$", COL["c"]), ("sc0.1", r"$s_c=0.1$", COL["b"])):
    ax[0].plot(Pa["P"], [q["Q"] for q in Pa[key]], "o-", ms=3, color=c, label=lab)
    if key != "baseline":
        ax[1].plot(Pa["P"], [100 * (q["Q"] / b["Q"] - 1) for q, b in zip(Pa[key], Pa["baseline"])], "o-", ms=3, color=c, label=lab)
ax[0].set_xlabel(r"$P_{aux}$ (MW)"); ax[0].set_ylabel(r"$Q$"); ax[0].set_yscale("log"); ax[0].legend(frameon=False)
ax[1].set_xlabel(r"$P_{aux}$ (MW)"); ax[1].set_ylabel(r"$\Delta Q/Q$ (%)"); ax[1].set_yscale("log")
panel(ax[0], "a"); panel(ax[1], "b")
fig.tight_layout(); save(fig, "figS1_power_scan")
