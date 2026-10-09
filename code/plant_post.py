# -*- coding: utf-8 -*-
"""Add the plant power-balance block (Section VI-E) to an existing ../results.json. Deterministic; reproduce.py computes the same block at the end of a full run.   python plant_post.py"""
import json

import plant

R = json.load(open("../results.json", encoding="utf-8"))
R["plant"] = plant.block(R)
json.dump(R, open("../results.json", "w"), indent=1)
c = R["plant"]["cases"]
print("baseline Pnet %.1f MW | s_c=0.1 dPnet %+.2f MW | Q breakeven at 40 MW: %.2f" % (c[0]["Pnet"], c[2]["dPnet"], R["plant"]["q_breakeven_40"]))
print(json.dumps(R["plant"]["uncertainty"], indent=1))
