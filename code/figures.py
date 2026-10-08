# -*- coding: utf-8 -*-
"""Figures 1-7 for the manuscript (Journal of Plasma Physics style: Times-like labels, no titles, EPS and PNG).   python figures.py   (reads ../results.json)"""
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
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"], "mathtext.fontset": "stix", "font.size": 9,
                     "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.linewidth": 0.7, "lines.linewidth": 1.4})
COL = {"base": "#222222", "a": "#1f6fb5", "b": "#c0522d", "c": "#2e8b57", "d": "#8a4fb0"}


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".eps"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def panel(ax, s):
    ax.text(-0.14, 1.04, s, transform=ax.transAxes, fontsize=10, fontweight="bold")


# ---- Figure 1: profiles
P = R["profiles"]
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.5))
for key, lab, c in (("baseline", "baseline", COL["base"]), ("sc0.5", r"$s_c=0.5$", COL["a"]), ("sc0.1", r"$s_c=0.1$", COL["b"])):
    r = np.array(P[key]["r"]); a_ = 2.0
    ax[0].plot(r / a_, P[key]["T"], color=c, label=lab)
    ax[1].plot(r / a_, P[key]["chi"], color=c, label=lab)
    ax[2].plot(r / a_, P[key]["ratio"], color=c, label=lab)
ax[0].set_xlabel(r"$r/a$"); ax[0].set_ylabel(r"$T$ (keV)"); ax[0].legend(frameon=False)
ax[1].set_xlabel(r"$r/a$"); ax[1].set_ylabel(r"$\chi$ (m$^2$ s$^{-1}$)"); ax[1].set_yscale("log")
ax[2].set_xlabel(r"$r/a$"); ax[2].set_ylabel(r"$\omega_E/\gamma_0$")
for k, s in enumerate("abc"):
    panel(ax[k], s)
fig.tight_layout(); save(fig, "fig1_profiles")

# ---- Figure 2: power scan
Pa = R["paux_scan"]
fig, ax = plt.subplots(1, 2, figsize=(5.8, 2.5))
for key, lab, c in (("baseline", "baseline", COL["base"]), ("sc0.5", r"$s_c=0.5$", COL["a"]), ("sc0.3", r"$s_c=0.3$", COL["c"]), ("sc0.1", r"$s_c=0.1$", COL["b"])):
    ax[0].plot(Pa["P"], [q["Q"] for q in Pa[key]], "o-", ms=3, color=c, label=lab)
    if key != "baseline":
        ax[1].plot(Pa["P"], [100 * (q["Q"] / b["Q"] - 1) for q, b in zip(Pa[key], Pa["baseline"])], "o-", ms=3, color=c, label=lab)
ax[0].set_xlabel(r"$P_{aux}$ (MW)"); ax[0].set_ylabel(r"$Q$"); ax[0].set_yscale("log"); ax[0].legend(frameon=False)
ax[1].set_xlabel(r"$P_{aux}$ (MW)"); ax[1].set_ylabel(r"$\Delta Q/Q$ (%)"); ax[1].set_yscale("log")
panel(ax[0], "a"); panel(ax[1], "b")
fig.tight_layout(); save(fig, "fig2_power_scan")

# ---- Figure 3: grid convergence and fold location
G = R["grid"]; Ns = np.array(G["N"], float)
fig, ax = plt.subplots(1, 2, figsize=(5.8, 2.5))
for key, lab, c in (("none", "baseline", COL["base"]), ("0.5", r"$s_c=0.5$", COL["a"]), ("0.2", r"$s_c=0.2$", COL["c"]), ("0.1", r"$s_c=0.1$", COL["b"])):
    q = np.array([r["Q"] for r in G["rows"][key]])
    ref = q[-1]
    ax[0].loglog(Ns[:-1], np.abs(q[:-1] - ref) / ref, "o-", ms=3, color=c, label=lab)
ax[0].loglog(Ns[:-1], 4e-1 / Ns[:-1], "k:", lw=0.8); ax[0].loglog(Ns[:-1], 2.0e1 / Ns[:-1] ** 2, "k--", lw=0.8)
ax[0].set_xlabel(r"cells $N$"); ax[0].set_ylabel(r"$|Q_N-Q_{800}|/Q_{800}$"); ax[0].legend(frameon=False)
F = R["fold"]["by_N"]; nn = sorted(int(k) for k in F)
ax[1].plot(1.0 / np.array(nn), [F[str(k)]["sc_fold"] for k in nn], "o-", ms=3, color=COL["a"])
ax[1].axhline(R["fold"]["extrapolated"], color="k", lw=0.8, ls="--")
ax[1].text(0.0105, R["fold"]["extrapolated"] + 0.0004, r"Richardson limit %.4f" % R["fold"]["extrapolated"], fontsize=8)
ax[1].set_xlabel(r"$1/N$"); ax[1].set_ylabel(r"fold position $s_c^{*}$"); ax[1].set_xlim(0, 0.022)
panel(ax[0], "a"); panel(ax[1], "b")
fig.tight_layout(); save(fig, "fig3_convergence")

# ---- Figure 4: steady-state branch (S-curve)
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.5), gridspec_kw={"width_ratios": [1.15, 1, 1]})
for key, N, c in (("branch_N100", 100, COL["a"]), ("branch_N200", 200, COL["b"])):
    br = np.array(R[key])                 # mu, Q, T0, lam1, ratio_max
    ok = br[:, 2] <= 100.0
    sc = 1.0 / br[:, 0]
    stable = br[:, 3] < 0
    first_fold = int(np.where(np.diff(br[:, 0]) < 0)[0][0])
    low = np.arange(len(br)) <= first_fold
    ax[0].plot(np.where(low, sc, np.nan), np.where(low, br[:, 1], np.nan), color=c, label=r"$N=%d$" % N)
    for a_, col in ((ax[1], 1), (ax[2], 2)):
        a_.plot(np.where(ok & stable, sc, np.nan), np.where(ok & stable, br[:, col], np.nan), color=c, ls="-", label=r"$N=%d$ stable" % N)
        a_.plot(np.where(ok & ~stable, sc, np.nan), np.where(ok & ~stable, br[:, col], np.nan), color=c, ls=":", label=r"$N=%d$ unstable" % N)
ax[0].set_xscale("log"); ax[0].set_xlim(0.045, 3.0); ax[0].set_ylim(3, 15)
ax[0].set_xlabel(r"$s_c$"); ax[0].set_ylabel(r"$Q$ (lower branch)"); ax[0].legend(frameon=False)
for a_ in ax[1:]:
    a_.set_xlim(0.0455, 0.0535); a_.set_xlabel(r"$s_c$")
    a_.axvline(R["fold"]["extrapolated"], color="gray", lw=0.7, ls="--")
ax[1].set_ylabel(r"$Q$"); ax[1].set_ylim(3, 33)
ax[2].set_ylabel(r"$T_0$ (keV)"); ax[2].set_ylim(10, 105); ax[2].legend(frameon=False, fontsize=6.5, loc="lower left", bbox_to_anchor=(0.0, 0.3))
panel(ax[0], "a"); panel(ax[1], "b"); panel(ax[2], "c")
fig.tight_layout(); save(fig, "fig4_branch")

# ---- Figure 5: normalised flux Psi(Lambda)
L = np.linspace(0, 4, 2001)
fig, ax = plt.subplots(1, 2, figsize=(6.0, 2.6))
for mm, c in ((0.5, COL["c"]), (1.0, COL["a"]), (2.0, COL["b"]), (3.0, COL["d"])):
    ax[0].plot(L, TH.Psi(L, TH.F_alg, m=mm), color=c, label=r"$m=%g$" % mm)
Ls, Ps = TH.alg_stationary_point(2.0)
ax[0].plot([Ls], [Ps], "ko", ms=3); ax[0].text(1.05, 0.52, r"fold, $\Theta=1/2$", fontsize=7)
ax[0].axhline(1.0, color="gray", lw=0.6, ls=":"); ax[0].set_ylim(0, 1.25)
ax[0].set_xlabel(r"$\Lambda$"); ax[0].set_ylabel(r"$\Psi=\Lambda F(\Lambda)$"); ax[0].legend(frameon=False)
for f, c, ls in ((0.05, COL["b"], "-"), (0.20, COL["a"], "-")):
    ax[1].plot(L, TH.Psi(L, TH.F_floor_alg, f=f), color=c, ls=ls, label=r"$f=%.2f$ (algebraic)" % f)
for f, c in ((0.20, COL["d"]), (0.40, COL["c"])):
    ax[1].plot(L, TH.Psi(L, TH.F_floor_exp, f=f), color=c, ls="--", label=r"$f=%.2f$ (exponential)" % f)
ax[1].set_xlabel(r"$\Lambda$"); ax[1].set_ylabel(r"$\Psi$"); ax[1].legend(frameon=False, fontsize=7)
panel(ax[0], "a"); panel(ax[1], "b")
fig.tight_layout(); save(fig, "fig5_flux")

# ---- Figure 6: tests of the rotation theory
SCR = [r for r in R["scalar_flux_relation"] if r["exists_theory"] and r["exists_numeric"]]
H = R["rotation_hysteresis"]
fig, ax = plt.subplots(1, 2, figsize=(6.0, 2.6))
mk = {0.5: "o", 1.0: "s", 2.0: "^"}
for mm in (0.5, 1.0, 2.0):
    pts = [r for r in SCR if r["m"] == mm]
    ax[0].loglog([r["Lam_pred"] for r in pts], [r["Lam_sim"] for r in pts], mk[mm], ms=3.5, color=[COL["c"], COL["a"], COL["b"]][[0.5, 1.0, 2.0].index(mm)], label=r"$m=%g$" % mm)
xx = np.logspace(-1.4, 0.2, 10); ax[0].loglog(xx, xx, "k-", lw=0.6)
ax[0].set_xlabel(r"$\Lambda_{max}$ predicted, $F(\Lambda)\Lambda=\Theta$"); ax[0].set_ylabel(r"$\Lambda_{max}$ simulated"); ax[0].legend(frameon=False)
for f, c in (("0.05", COL["b"]), ("0.2", COL["a"])):
    t = np.array(H[f]["torque"]); up = np.array([np.nan if v is None else v for v in H[f]["up"]]); dn = np.array([np.nan if v is None else v for v in H[f]["down"]])
    ax[1].plot(t, up, "-", color=c, label=r"$f=%s$ up" % f); ax[1].plot(t, dn, "--", color=c, label=r"$f=%s$ down" % f)
pw = H["0.05"]["predicted"]
ax[1].axvspan(pw["torque_down"], pw["torque_up"], color="0.9", zorder=0)
ax[1].set_yscale("log")
ax[1].set_xlabel("torque (N m)"); ax[1].set_ylabel(r"$\Lambda_{max}$"); ax[1].legend(frameon=False, fontsize=7, loc="upper left")
panel(ax[0], "a"); panel(ax[1], "b")
fig.tight_layout(); save(fig, "fig6_rotation_tests")

# ---- Figure 7: torque-driven coupling
CP = R["coupled_scan"]
fig, ax = plt.subplots(1, 2, figsize=(6.4, 2.7))
for sign, a_, s in ((1.0, ax[0], "a"), (-1.0, ax[1], "b")):
    for clos, c, mk_ in (("linear", COL["base"], "o"), ("m=1", COL["a"], "s"), ("m=2 f=0.20", COL["c"], "^"), ("m=2", COL["b"], "x")):
        pts = [r for r in CP if r["sign"] == sign and r["closure"] == clos]
        t = [r["torque"] for r in pts if r["ok"]]; q = [r["Q"] for r in pts if r["ok"]]
        lab = {"linear": "constant viscosity", "m=1": r"$m=1$", "m=2 f=0.20": r"$m=2$, floor 0.20", "m=2": r"$m=2$"}[clos]
        a_.plot(t, q, mk_ + "-", ms=3, color=c, label=lab)
        bad = [r["torque"] for r in pts if not r["ok"]]
        if bad:
            a_.axvline(min(bad), color=c, lw=0.6, ls=":")
    a_.set_xlabel("torque (N m)"); a_.set_ylabel(r"$Q$"); panel(a_, s)
ax[0].legend(frameon=False, fontsize=7)
fig.tight_layout(); save(fig, "fig7_coupled")
