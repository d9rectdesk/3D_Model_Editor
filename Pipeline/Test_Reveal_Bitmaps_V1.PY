import json
import math
import os
import subprocess
import sys

# Test_Reveal_Bitmaps_V1.PY
# The driven proof for the reveal-bitmap fill source
# (Solomon, 2026-11-16: the bitmap is "the whole key
# behind building the 3D model first"). Precedence
# under test, per joint: a reveal bitmap - the 3D
# lane's composite of the model's own rendered pixels
# from 5-degree pose sweeps - is the fill where one
# exists and supersedes the disc ENTIRELY, even a
# hand-tuned radius; where none exists the joint
# falls back to the disc at its per-point radius.
# A. Wiring: Step_Redraw handed reveal_dir (and a
#    tuned disc_radii map alongside) passes the
#    folder to the engine as REDRAW_REVEAL_DIR and
#    counts the bitmaps it holds.
# B. Pixels: a fabricated Front neck bitmap - a
#    magenta bar 640x80 centred on the neck pin,
#    a shape no disc makes, in a colour no tone
#    makes - and two real engine runs, both with
#    the neck's radius tuned to 400: a control run
#    (no bitmap folder) and the reveal run. In the
#    reveal run the head part must carry the bar's
#    own pixels and shape (left reach 320, the
#    bar's half width; magenta at the bar's end),
#    its downward reach must fall back to the
#    head's own stub (128) instead of the tuned
#    400 disc, the written rig and census must
#    record fill_source reveal_bitmap for the neck
#    and disc for the untouched wrist, and the
#    wrist's part must come out identical in both
#    runs. Both runs must pass the engine's own
#    proof (exit 0).
# Source: Kevin, original work.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HUMANOID = os.path.expanduser("~/workspace/Humanoid_Rig_V1")
TMP = "/tmp/V21_Reveal_Test"
REVEAL_DIR = os.path.join(TMP, "Reveal_Bitmaps")
CTL_ROOT = os.path.join(TMP, "Control")
REV_ROOT = os.path.join(TMP, "Reveal")
OVR_JSON = os.path.join(TMP, "Overrides400.JSON")
PIN = (1022, 500)
MAGENTA = (255, 0, 255)
Results = {}


def Check(Name, Ok, Detail):
    Results[Name] = {"pass": bool(Ok), "detail": Detail}
    print(("PASS " if Ok else "FAIL ") + Name + " - " + Detail)


# ---------------- the fabricated bitmap ----------------
os.makedirs(os.path.join(REVEAL_DIR, "Front"), exist_ok=True)
from PIL import Image
import numpy as np

Bmp = np.zeros((2048, 2048, 4), dtype=np.uint8)
Bmp[460:540, 702:1342] = (255, 0, 255, 255)
Image.fromarray(Bmp, "RGBA").save(
    os.path.join(REVEAL_DIR, "Front", "Reveal_neck_V1.PNG"))
with open(OVR_JSON, "w") as F:
    json.dump({"Front": {"neck": 400}}, F)

# ---------------- A. the wiring ----------------
import importlib.machinery as Import_Mach
import importlib.util as Import_Util

Loader = Import_Mach.SourceFileLoader(
    "Pipeline_Steps_V1", os.path.join(HERE, "Pipeline_Steps_V1.PY"))
Spec = Import_Util.spec_from_loader("Pipeline_Steps_V1", Loader)
Steps = Import_Util.module_from_spec(Spec)
Spec.loader.exec_module(Steps)
Calls = []


class Fake_Proc:
    returncode = 0


def Fake_Run(Cmd, Log, **Kw):
    Calls.append((Cmd, Kw.get("Env")))
    return Fake_Proc()


Steps.Run_Captured = Fake_Run
Logs = []
Out = Steps.Step_Redraw(
    {"parts_folder": "/unused/parts", "rig_json": "/unused/rig.json",
     "disc_radii": {"Front": {"neck": 400}}, "reveal_dir": REVEAL_DIR,
     "views": "Front", "run_engine": True,
     "battery_out": os.path.join(TMP, "Battery.JSON")},
    {"humanoid_home": HUMANOID, "output_folder": TMP},
    Logs.append)
Engine_Calls = [(C, E) for C, E in Calls
                if any("Redraw_Circles_V1.PY" in str(X) for X in C)]
Env = (Engine_Calls[0][1] or {}) if Engine_Calls else {}
Check("wiring_engine_called_once", len(Engine_Calls) == 1,
      f"{len(Engine_Calls)} engine call(s) recorded")
Check("wiring_reveal_env", Env.get("REDRAW_REVEAL_DIR") == REVEAL_DIR,
      f"REDRAW_REVEAL_DIR={Env.get('REDRAW_REVEAL_DIR')}")
Check("wiring_radii_env_too",
      bool(Env.get("REDRAW_DISC_RADII_JSON")),
      f"REDRAW_DISC_RADII_JSON={Env.get('REDRAW_DISC_RADII_JSON')}")
Check("wiring_outputs", Out.get("reveal_bitmaps") == 1
      and Out.get("reveal_dir") == REVEAL_DIR,
      f"reveal_bitmaps={Out.get('reveal_bitmaps')} "
      f"reveal_dir={Out.get('reveal_dir')}")

# ---------------- B. the pixels ----------------
def Run_Engine(Root, Extra_Env):
    E = dict(os.environ)
    E["REDRAW_VIEWS"] = "Front"
    E["REDRAW_OUT_ROOT"] = Root
    E["REDRAW_DISC_RADII_JSON"] = OVR_JSON
    E.update(Extra_Env)
    return subprocess.run(
        [sys.executable, os.path.join(HUMANOID, "Redraw_Circles_V1.PY")],
        cwd=HUMANOID, env=E, capture_output=True, text=True,
        timeout=3600)


Runs = {}
for Root, Extra in ((CTL_ROOT, {}),
                    (REV_ROOT, {"REDRAW_REVEAL_DIR": REVEAL_DIR})):
    if not os.path.exists(os.path.join(Root, "Redrawn_Rig_V1.JSON")):
        Proc = Run_Engine(Root, Extra)
        print(f"engine run {Root}: exit {Proc.returncode}")
        if Proc.returncode != 0:
            print(Proc.stdout[-1500:])
            print(Proc.stderr[-1500:])
        Runs[Root] = Proc.returncode
    else:
        Runs[Root] = 0
Check("engine_proofs_pass", Runs[CTL_ROOT] == 0 and Runs[REV_ROOT] == 0,
      f"control exit={Runs[CTL_ROOT]} reveal exit={Runs[REV_ROOT]}")


def Reach(Png_Path, Dx, Dy):
    A = np.array(Image.open(Png_Path).convert("RGBA"))[:, :, 3] > 0
    X, Y = PIN
    D = 0
    while True:
        Nx, Ny = X + Dx * (D + 1), Y + Dy * (D + 1)
        if not (0 <= Nx < 2048 and 0 <= Ny < 2048) or not A[Ny, Nx]:
            return D
        D += 1


Ctl_Head = os.path.join(CTL_ROOT, "Front", "Part_Head_V1.PNG")
Rev_Head = os.path.join(REV_ROOT, "Front", "Part_Head_V1.PNG")
Ctl_Down, Rev_Down = Reach(Ctl_Head, 0, 1), Reach(Rev_Head, 0, 1)
Ctl_Left, Rev_Left = Reach(Ctl_Head, -1, 0), Reach(Rev_Head, -1, 0)
Check("control_disc_drawn", Ctl_Down >= 330 and Ctl_Left >= 330,
      f"control head reach down={Ctl_Down} left={Ctl_Left} "
      f"(the tuned 400 disc)")
Check("reveal_no_disc", Rev_Down <= 175 and Rev_Down < Ctl_Down - 150,
      f"reveal head downward reach={Rev_Down} (the head's own "
      f"stub, not the 400 disc at {Ctl_Down})")
Check("reveal_shape_is_the_bar", 300 <= Rev_Left <= 345,
      f"reveal head left reach={Rev_Left} (the bar's 320 half "
      f"width, not a disc)")

Rev_Arr = np.array(Image.open(Rev_Head).convert("RGBA"))
Px = tuple(int(V) for V in Rev_Arr[PIN[1], PIN[0] - 300][:3])
Check("reveal_colours_are_the_bitmaps", Px == MAGENTA,
      f"head pixel 300 left of the pin = {Px}, the bitmap's "
      f"own colour {MAGENTA}")
Total_Magenta = 0
Front_Dir = os.path.join(REV_ROOT, "Front")
for F in sorted(os.listdir(Front_Dir)):
    if F.endswith(".PNG"):
        A = np.array(Image.open(os.path.join(Front_Dir, F))
                     .convert("RGBA"))[:, :, :3]
        Total_Magenta += int((np.all(A == MAGENTA, axis=2)).sum())
Check("reveal_bitmap_pixels_present", Total_Magenta >= 5000,
      f"{Total_Magenta} bitmap-coloured pixels across the "
      f"Front parts")

Ctl_Rig = json.load(open(os.path.join(CTL_ROOT, "Redrawn_Rig_V1.JSON")))
Rev_Rig = json.load(open(os.path.join(REV_ROOT, "Redrawn_Rig_V1.JSON")))
Rev_Census = json.load(open(os.path.join(REV_ROOT, "Redraw_Census_V1.JSON")))


def Joint(Rig, Name):
    for J in Rig["views"]["Front"]["joints"]:
        if J["name"] == Name:
            return J
    raise KeyError(Name)


Check("rig_records_sources",
      Joint(Rev_Rig, "neck").get("fill_source") == "reveal_bitmap"
      and Joint(Rev_Rig, "wrist_l").get("fill_source") == "disc"
      and Joint(Ctl_Rig, "neck").get("fill_source") == "disc",
      f"reveal neck={Joint(Rev_Rig, 'neck').get('fill_source')} "
      f"wrist={Joint(Rev_Rig, 'wrist_l').get('fill_source')} "
      f"control neck={Joint(Ctl_Rig, 'neck').get('fill_source')}")
Check("census_records_sources",
      Rev_Census["views"]["Front"]["fill_sources"]["neck"]
      == "reveal_bitmap"
      and Rev_Census["views"]["Front"]["fill_sources"]["wrist_l"]
      == "disc",
      f"census fill_sources neck="
      f"{Rev_Census['views']['Front']['fill_sources'].get('neck')} "
      f"wrist_l="
      f"{Rev_Census['views']['Front']['fill_sources'].get('wrist_l')}")


def Hand_Profile(Root):
    A = np.array(Image.open(os.path.join(
        Root, "Front", "Part_Hand_Left_V1.PNG")).convert("RGBA"))[:, :, 3] > 0
    Wrist = Joint(json.load(open(os.path.join(
        Root, "Redrawn_Rig_V1.JSON"))), "wrist_l")
    X0, Y0 = Wrist["pin"]
    Profile = []
    for K in range(72):
        Ang = 2 * math.pi * K / 72
        Dx, Dy = math.cos(Ang), math.sin(Ang)
        Far = 0
        for R in range(1, 700):
            X = int(round(X0 + Dx * R))
            Y = int(round(Y0 + Dy * R))
            if not (0 <= X < 2048 and 0 <= Y < 2048):
                break
            if A[Y, X]:
                Far = R
        Profile.append(Far)
    return min(Profile), sorted(Profile)[36]


Ctl_Hand = Hand_Profile(CTL_ROOT)
Rev_Hand = Hand_Profile(REV_ROOT)
Check("fallback_joint_identical",
      abs(Ctl_Hand[0] - Rev_Hand[0]) <= 2
      and abs(Ctl_Hand[1] - Rev_Hand[1]) <= 2,
      f"hand reach (min/median) control={Ctl_Hand} reveal={Rev_Hand}")

Failed = [K for K, V in Results.items() if not V["pass"]]
print(json.dumps(Results, indent=1))
print("TEST " + ("FAILED: " + ", ".join(Failed) if Failed else "PASSED"))
raise SystemExit(1 if Failed else 0)
