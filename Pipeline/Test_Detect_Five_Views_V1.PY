import os
import shutil
import sys

# Test_Detect_Five_Views_V1.PY
# The driven proof for the loosened picture count
# (Solomon, 2026-11-16: "four images (or more) of
# the same object"). Detection used to hard-stop
# above four pictures; now a set of five must still
# name front, back, side_left and side_right, and
# the fifth picture - a second shot of the same
# side, the natural "or more" case - must ride
# along in the outputs as an extra view instead of
# pushing a true side out of its name or being
# rejected. The set is the man's: his front, back
# and side cutouts, the mirror of the side standing
# as the second side (exactly how the set's
# SideLeft view is derived today), and a byte copy
# of the side under a second name as the extra
# picture, all in a scrambled order with the extra
# placed first.
# Source: Kevin, original work; the scaffolding is
# copied from Test_Detect_Views_V1.PY (the estate's
# proven detection test), the case added.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HUMANOID = os.path.expanduser("~/workspace/Humanoid_Rig_V1")
TMP = "/tmp/V21_Detect_Five_Test"
FRONT = os.path.join(HUMANOID, "Human_Man_Front_Cutout_V1.PNG")
BACK = os.path.join(HUMANOID, "Human_Man_Back_Cutout_V1.PNG")
SIDE = os.path.join(HUMANOID, "Human_Man_Side_Cutout_V1.PNG")
MIRROR = os.path.join(TMP, "Human_Man_SideLeft_Cutout_V1.PNG")
COPY = os.path.join(TMP, "Human_Man_Side_Cutout_V2.PNG")
Results = {}


def Check(Name, Ok, Detail):
    Results[Name] = {"pass": bool(Ok), "detail": Detail}
    print(("PASS " if Ok else "FAIL ") + Name + " - " + Detail)


os.makedirs(TMP, exist_ok=True)
from PIL import Image
Image.open(SIDE).transpose(Image.FLIP_LEFT_RIGHT).save(MIRROR)
shutil.copyfile(SIDE, COPY)

import importlib.machinery as Import_Mach
import importlib.util as Import_Util

Loader = Import_Mach.SourceFileLoader(
    "Pipeline_Steps_V1", os.path.join(HERE, "Pipeline_Steps_V1.PY"))
Spec = Import_Util.spec_from_loader("Pipeline_Steps_V1", Loader)
Steps = Import_Util.module_from_spec(Spec)
Spec.loader.exec_module(Steps)

Base = os.path.basename
Logs = []
Five = Steps.Step_Detect_Views(
    {"files": [COPY, FRONT, MIRROR, BACK, SIDE]}, {}, Logs.append)
Check("five_front", Base(Five.get("front", "")) == Base(FRONT),
      f"front={Base(Five.get('front', ''))}")
Check("five_back", Base(Five.get("back", "")) == Base(BACK),
      f"back={Base(Five.get('back', ''))}")
Check("five_side_left_is_the_mirror",
      Base(Five.get("side_left", "")) == Base(MIRROR),
      f"side_left={Base(Five.get('side_left', ''))}")
Extras = Five.get("extra_views", [])
Check("five_side_right_and_extra_share_the_source_side",
      {Base(Five.get("side_right", ""))}
      | {Base(P) for P in Extras}
      == {Base(SIDE), Base(COPY)},
      f"side_right={Base(Five.get('side_right', ''))} "
      f"extras={[Base(P) for P in Extras]}")
Check("five_extra_rides_along",
      len(Extras) == 1,
      f"extra_views={[Base(P) for P in Extras]}")
Check("five_verdict_names_four",
      any(L.startswith("verdict:") and "side_left=" in L
          and "side_right=" in L for L in Logs),
      next((L for L in Logs if L.startswith("verdict:")),
           "no verdict"))

Failed = [K for K, V in Results.items() if not V["pass"]]
print("TEST " + ("FAILED: " + ", ".join(Failed) if Failed
                 else "PASSED"))
raise SystemExit(1 if Failed else 0)
