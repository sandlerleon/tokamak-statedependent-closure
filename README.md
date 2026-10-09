# Numerical admissibility and regularization of shear-suppression closures for reduced tokamak transport

**Author:** Leon Sandler, Independent Researcher (ORCID [0009-0007-4584-808X](https://orcid.org/0009-0007-4584-808X))
**Target journal:** IEEE Transactions on Plasma Science (regular paper)
**Article type:** computational and theoretical. All parameters are illustrative; no experimental data are used.

A one-dimensional radial energy equation with fusion heating, closed by a stiff critical-gradient diffusivity divided by a shear-suppression factor, is compared with the baseline at identical geometry, density, field, heating and boundary
conditions, so that only the closure differs. A toroidal-rotation equation with a shear-dependent viscosity `F(Lambda)` is added and coupled one way (rotation shear adds to the diamagnetic shear).

| Result | Verified against |
|---|---|
| The **local** closure (shearing rate from the second derivative of T) is numerically ill posed: converged answers depend on the edge treatment, and a grid-scale instability sets in at `s_c^lin ~ N^0.52` | eigenvalues for N = 50-400, edge-condition variants, principal part stays elliptic |
| The **smoothed** (adaptive-field) closure with a fixed length `l` is stable and grid converged over the tested conditions, converges at second order, and is fitted by `dQ = C/s_c^2` (C = 0.00206; an empirical fit, not a universal scaling) | N = 100-800, independent Radau integration, cold-start dynamics |
| Rotation equation: `F(L) L = Theta` gives admissibility conditions (`m <= 1`; floors 1/9 and 0.3086), saturation, fold and hysteresis | direct finite-volume solutions (relative error 5e-11), predicted hysteresis window |
| Calibration: baseline reproduces ITER89-P (H89 = 1.01), H98 = 0.48, n/nG = 0.63, beta_N = 1.05; full-energy beam torque of an ITER-like device is 30-40 N m | recognized scalings and limits |
| Uncertainty: Sobol studies over 7 heat-closure and 6 torque parameters | 128 and 64 points, all converged |
| Plant power balance (screening level, assumed efficiencies): reference device net electric power about -45 MW at 40 MW heating, negative for all 256 sampled assumptions; the closure adds about +4 MW at `s_c` = 0.1 (3.3-4.5 MW over the assumptions). No cost is computed (a relative proxy is defined only) | hand-checked balance, breakeven-gain identity, Sobol over 5 assumptions |

**Version 1.2.0 adds the plant power balance (Section VI-E, `code/plant.py`) to 1.1.1.** **Version 1.1.1 is a wording revision of 1.1.0** (new title; well-posedness claims qualified as numerical; gain law described as an empirical fit; ITER89-P agreement stated to be a consistency check; discussion of compact tokamak design added). Computed results are unchanged.

**Versions 1.1.x supersede 1.0.0.** Version 1.0.0 reported a steady-state fold at `s_c = 0.047`; that fold was an artifact of a first-order edge treatment of the shearing rate and is not a property of the model. Please cite 1.1.0.

## Layout

```
code/model.py          energy balance, closures (local and smoothed), steady and pseudo-time solvers
code/stability.py      Newton steady states, Jacobian (central differences), leading eigenvalue, continuation
code/arclength.py      pseudo-arclength continuation in 1/s_c
code/ellipticity.py    principal part of the linearized local closure
code/momentum.py       rotation equation (direct solve with torque continuation; backward-Euler marching)
code/coupled.py        one-way coupling of heat and rotation
code/theory.py         closed forms of the admissibility analysis
code/calibration.py    confinement scalings, beta_N, Greenwald fraction, beam torque, gyroradius
code/uncertainty.py    Sobol sampling and rank correlations
code/plant.py          screening-level plant power balance and relative cost proxy (post-processing; plant_post.py adds it to results.json)
code/reproduce.py      every number in the paper -> results.json (about 40 minutes)
code/tests.py          55 checks (about 5 minutes)
code/figures.py        all figures (PNG and EPS)
refs/build_refs.py     every journal reference harvested from Crossref by DOI (IEEE style)
manuscript/            builders of the manuscript, supplement and cover letter (docx; no PDFs are kept)
tools/                 Zenodo reservation/publication scripts (token from ZENODO_TOKEN, never stored)
```

## Reproducing

```bash
pip install -r requirements.txt
cd code
python reproduce.py      # writes ../results.json
python tests.py
python figures.py
cd ../manuscript && python build_manuscript.py && python build_manuscript.py && python build_supplement.py && python build_cover_letter.py
```

The Sobol sequences are scrambled with a fixed seed; everything else uses no random numbers.

## Notes on the numerics

* The shearing rate depends on the second derivative of the temperature. Finite-difference Jacobian steps must therefore be small (relative 1e-8, central differences); a relative step of 1e-6 gave a spurious instability.
* All edge and axis stencils are second order. A first-order half-cell edge stencil damps the grid-scale mode of the local closure and produces a spurious fold.
* The Newton residual cannot be reduced below about 1e-10 of the total heating at N >= 400 (round-off); the acceptance tolerance is 1e-8.
* The Bosch-Hale fit is valid to 100 keV; nothing above that temperature is interpreted.
