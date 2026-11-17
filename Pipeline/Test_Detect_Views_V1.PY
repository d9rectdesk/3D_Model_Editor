import os
import sys

# Test_Detect_Views_V1.PY
# The driven proof for the four-view detection
# (Solomon, 2026-11-16: the editor's input set is
# FOUR pictures - front, back, left side, right
# side - on the SandBase multi-view benchmark's
# economics: each added true view buys down error
# on the faces it reveals, and the second side is
# the one the doll set currently derives).
# The man's set stands as the ground truth: his
# front, back, and side cutouts, plus a mirror of
# the side cutout standing as the second side -
# the mirror is exactly how the set's SideLeft
# view is derived today. Detection must name all
# four correctly from the unordered set: front,
# back, side_right (the source side picture, whose
# facing measures positive) and side_left (its
# mirror). The legacy three-picture set must still
# classify, with the single side named by its
# facing and carried under the old "side" key.
# Source: Kevin, original work.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HUMANOID = os.path.expanduser("~/workspace/Humanoid_Rig_V1")
TMP = "/tmp/V21_Detect_Test"
FRONT = os.path.join(HUMANOID, "Human_Man_Front_Cutout_V1.PNG")
BACK = os.path.join(HUMANOID, "Human_Man_Back_Cutout_V1.PNG")
SIDE = os.path.join(HUMANOID, "Human_Man_Side_Cutout_V1.PNG")
MIRROR = os.path.join(TMP, "Human_Man_SideLeft_Cutout_V1.PNG")
Results = {}


def Check(Name, Ok, Detail):
    Results[Name] = {"pass": bool(Ok), "detail": Detail}
    print(("PASS " if Ok else "FAIL ") + Name + " - " + Detail)


os.makedirs(TMP, exist_ok=True)
from PIL import Image
Image.open(SIDE).transpose(Image.FLIP_LEFT_RIGHT).save(MIRROR)

import importlib.machinery as Import_Mach
import importlib.util as Import_Util

Loader = Import_Mach.SourceFileLoader(
    "Pipeline_Steps_V1", os.path.join(HERE, "Pipeline_Steps_V1.PY"))
Spec = Import_Util.spec_from_loader("Pipeline_Steps_V1", Loader)
Steps = Import_Util.module_from_spec(Spec)
Spec.loader.exec_module(Steps)

Logs = []
Four = Steps.Step_Detect_Views(
    {"files": [MIRROR, BACK, SIDE, FRONT]}, {}, Logs.append)
Base = os.path.basename
Check("four_front", Base(Four.get("front", "")) == Base(FRONT),
      f"front={Base(Four.get('front', ''))}")
Check("four_back", Base(Four.get("back", "")) == Base(BACK),
      f"back={Base(Four.get('back', ''))}")
Check("four_side_right_is_the_source",
      Base(Four.get("side_right", "")) == Base(SIDE),
      f"side_right={Base(Four.get('side_right', ''))}")
Check("four_side_left_is_the_mirror",
      Base(Four.get("side_left", "")) == Base(MIRROR),
      f"side_left={Base(Four.get('side_left', ''))}")
Feats = Four.get("features", {})
Check("facing_scores_opposed",
      Feats.get(Base(SIDE), {}).get("facing_score", 0) > 0
      and Feats.get(Base(MIRROR), {}).get("facing_score", 0) < 0,
      f"source facing={Feats.get(Base(SIDE), {}).get('facing_score')} "
      f"mirror facing={Feats.get(Base(MIRROR), {}).get('facing_score')}")
Check("verdict_line_names_four",
      any(L.startswith("verdict:") and "side_left=" in L
          and "side_right=" in L for L in Logs),
      next((L for L in Logs if L.startswith("verdict:")), "no verdict"))

Logs3 = []
Three = Steps.Step_Detect_Views(
    {"files": [SIDE, FRONT, BACK]}, {}, Logs3.append)
Check("legacy_three_still_classifies",
      Base(Three.get("front", "")) == Base(FRONT)
      and Base(Three.get("back", "")) == Base(BACK)
      and Base(Three.get("side", "")) == Base(SIDE)
      and Base(Three.get("side_right", "")) == Base(SIDE),
      f"front={Base(Three.get('front', ''))} "
      f"back={Base(Three.get('back', ''))} "
      f"side={Base(Three.get('side', ''))} "
      f"side_right={Base(Three.get('side_right', ''))}")

Failed = [K for K, V in Results.items() if not V["pass"]]
print("TEST " + ("FAILED: " + ", ".join(Failed) if Failed else "PASSED"))
raise SystemExit(1 if Failed else 0)
