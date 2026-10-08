# State-dependent shear-suppression closures for reduced tokamak transport

**Author:** Leon Sandler, Independent Researcher (ORCID [0009-0007-4584-808X](https://orcid.org/0009-0007-4584-808X))
**Target journal:** Journal of Plasma Physics (Research Article)
**Article type:** computational and theoretical. All parameters are illustrative; no experimental data are used.

A one-dimensional radial energy equation with fusion heating, closed by a stiff critical-gradient diffusivity divided by `1 + (omega_E / (s_c gamma_0))^2`, is compared with the baseline at identical geometry, density, field,
heating and boundary conditions, so that only the closure differs. A toroidal-rotation equation with a shear-dependent viscosity `F(Lambda)` is added, and the two are coupled one way (rotation shear adds to the diamagnetic shear).

| Result | Verified against |
|---|---|
| Solver: power balance below 1e-9, baseline recovered as `s_c -> infinity`, grid convergence (observed order 2.0 to about 1.1) | independent Radau time integration (3e-11 keV), Bosch-Hale check values, 38 tests |
| Diamagnetic shear alone: gain changes by +0.07 %, +0.27 %, +0.8 % at `s_c` = 1, 0.5, 0.3 (baseline Q = 3.70) | N = 50 to 800 |
| Lower branch of steady states ends in a saddle-node fold at `s_c*` = 0.047 (Richardson limit); Q about 14.7 at the fold | pseudo-arclength continuation, leading eigenvalue, time integration |
| Rotation equation: `F(L) L = Theta` reduces existence, saturation, fold and hysteresis to the monotonicity of `L F(L)`; thresholds `m <= 1`, floors 1/9 and 0.3086 | direct finite-volume solutions (relative error 5e-11), predicted hysteresis window |
| Torque-driven shear raises Q by 34 % at 200 N m for `s_c` = 0.5 | one-way coupled solves, both shear orientations |

## Layout

```
code/model.py          energy balance, closures, steady and pseudo-time solvers
code/stability.py      Newton steady states, Jacobian, leading eigenvalue, natural continuation
code/arclength.py      pseudo-arclength continuation in 1/s_c (fold, S-curve)
code/momentum.py       rotation equation (direct solve with torque continuation; backward-Euler marching)
code/coupled.py        one-way coupling of heat and rotation
code/theory.py         closed forms of the admissibility analysis (Section 3 of the paper)
code/reproduce.py      every number in the paper -> results.json (about 10 minutes)
code/tests.py          38 checks (about 3 minutes)
code/figures.py        Figures 1-7 (PNG and EPS)
refs/build_refs.py     every journal reference harvested from Crossref by DOI
manuscript/            builders of the manuscript and the cover letter (docx; no PDFs are kept in the repository)
tools/                 Zenodo reservation/publication scripts (token from ZENODO_TOKEN, never stored)
```

## Reproducing

```bash
pip install -r requirements.txt
cd code
python reproduce.py      # writes ../results.json
python tests.py
python figures.py
cd ../manuscript && python build_manuscript.py && python build_manuscript.py && python build_cover_letter.py
```

No random numbers are used; results are deterministic.

## Notes on the numerics

* The shearing rate depends on the second derivative of the temperature. Finite-difference Jacobian steps must therefore be small: a relative step of 1e-6 gave a spurious fold at `s_c` about 1 for N = 400; the code uses central differences with a relative step of 1e-8 and `tests.py` contains a regression test.
* The Newton residual cannot be reduced below about 1e-10 of the total heating at N >= 400 (round-off); the acceptance tolerance is 1e-8.
* The Bosch-Hale fit is valid to 100 keV; nothing above that temperature is interpreted.
