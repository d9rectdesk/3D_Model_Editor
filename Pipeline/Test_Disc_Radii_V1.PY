import json
import math
import os
import subprocess
import sys

# Test_Disc_Radii_V1.PY
# The driven proof for Model Editor V21's per-point
# fill radii, at the pipeline level:
# A. Wiring: Step_Redraw, handed disc_radii the way the
#    editor's Ai Redraw step sends them, writes the map
#    to Disc_Radii_Overrides_V1.JSON in the output
#    folder and passes its path to the redraw engine in
#    the REDRAW_DISC_RADII_JSON environment variable,
#    with REDRAW_VIEWS alongside.
# B. Pixels: the real redraw engine runs twice on the
#    Front view - once plain (the computed default
#    radii) and once with the neck's radius overridden
#    to 120. The head part's filled disc, measured over
#    72 rays from the neck pin (the median reach - the
#    engine's strip step trims the few rays pointing
#    straight across the joint), must match each run's
#    radius; an untouched joint (the left wrist) must
#    come out identical in both runs, and the written
#    rig must record the override for the neck and the
#    untouched fallback for the wrist.
# Source: Kevin, original work.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HUMANOID = os.path.expanduser("~/workspace/Humanoid_Rig_V1")
TMP = "/tmp/V21_Disc_Radii_Test"
OVR_JSON = os.path.join(TMP, "Overrides.JSON")
DEF_ROOT = os.path.join(TMP, "Default")
OVR_ROOT = os.path.join(TMP, "Override")
Results = {}


def Check(Name, Ok, Detail):
    Results[Name] = {"pass": bool(Ok), "detail": Detail}
    print(("PASS " if Ok else "FAIL ") + Name + " - " + Detail)


# ---------------- A. the wiring ----------------
# Loaded the way Bridge_Server_V1.PY loads it (the
# capital .PY extension is not importable directly).
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
     "disc_radii": {"Front": {"neck": 120}}, "views": "Front",
     "run_engine": True,
     "battery_out": os.path.join(TMP, "Battery.JSON")},
    {"humanoid_home": HUMANOID, "output_folder": TMP},
    Logs.append)
Engine_Calls = [(C, E) for C, E in Calls
                if any("Redraw_Circles_V1.PY" in str(X) for X in C)]
Check("wiring_engine_called_once", len(Engine_Calls) == 1,
      f"{len(Engine_Calls)} engine call(s) recorded")
if Engine_Calls:
    Env = Engine_Calls[0][1] or {}
    Path = Env.get("REDRAW_DISC_RADII_JSON", "")
    Written = None
    if Path and os.path.exists(Path):
        Written = json.load(open(Path))
    Check("wiring_overrides_file", Written == {"Front": {"neck": 120}},
          f"path={Path} content={Written}")
    Check("wiring_views_env", Env.get("REDRAW_VIEWS") == "Front",
          f"REDRAW_VIEWS={Env.get('REDRAW_VIEWS')}")
    Check("wiring_outputs", Out.get("disc_radii") == {"Front": {"neck": 120}},
          f"outputs disc_radii={Out.get('disc_radii')}")

# ---------------- B. the pixels ----------------
os.makedirs(TMP, exist_ok=True)
with open(OVR_JSON, "w") as F:
    json.dump({"Front": {"neck": 120}}, F)


def Run_Engine(Root, Extra_Env):
    Env = dict(os.environ)
    Env["REDRAW_VIEWS"] = "Front"
    Env["REDRAW_OUT_ROOT"] = Root
    Env.update(Extra_Env)
    Proc = subprocess.run(
        [sys.executable, os.path.join(HUMANOID, "Redraw_Circles_V1.PY")],
        cwd=HUMANOID, env=Env, capture_output=True, text=True,
        timeout=3600)
    return Proc


for Root, Extra in ((DEF_ROOT, {}),
                    (OVR_ROOT, {"REDRAW_DISC_RADII_JSON": OVR_JSON})):
    if not os.path.exists(os.path.join(Root, "Redrawn_Rig_V1.JSON")):
        Proc = Run_Engine(Root, Extra)
        print(f"engine run {Root}: exit {Proc.returncode}")
        if Proc.returncode != 0:
            print(Proc.stdout[-2000:])
            print(Proc.stderr[-2000:])
            raise SystemExit("engine run failed")

Def_Rig = json.load(open(os.path.join(DEF_ROOT, "Redrawn_Rig_V1.JSON")))
Ovr_Rig = json.load(open(os.path.join(OVR_ROOT, "Redrawn_Rig_V1.JSON")))


def Joint(Rig, View, Name):
    for J in Rig["views"][View]["joints"]:
        if J["name"] == Name:
            return J
    raise KeyError(Name)


Neck_Def = Joint(Def_Rig, "Front", "neck")
Neck_Ovr = Joint(Ovr_Rig, "Front", "neck")
Wrist_Def = Joint(Def_Rig, "Front", "wrist_l")
Wrist_Ovr = Joint(Ovr_Rig, "Front", "wrist_l")
Check("rig_default_neck_radius", Neck_Def.get("disc_radius") == 515,
      f"default neck disc_radius={Neck_Def.get('disc_radius')}")
Check("rig_override_neck_radius", Neck_Ovr.get("disc_radius") == 120,
      f"override neck disc_radius={Neck_Ovr.get('disc_radius')}")
Check("rig_wrist_fallback_intact",
      Wrist_Ovr.get("disc_radius") == Wrist_Def.get("disc_radius"),
      f"wrist disc_radius default={Wrist_Def.get('disc_radius')} "
      f"override={Wrist_Ovr.get('disc_radius')}")


def Reach_Profile(Png_Path, Pin):
    # The farthest opaque reach from the pin along 72
    # rays. The disc's size is the profile's MEDIAN:
    # the engine's strip step trims the few rays that
    # point straight across the joint into the parent
    # part (the head's downward sector measured 496
    # against a 515 disc, 67 of 72 rays at 515), so
    # the minimum is the strip's evidence, not the
    # disc's size.
    from PIL import Image
    A = Image.open(Png_Path).convert("RGBA").getchannel("A")
    W, H = A.size
    Px = A.load()
    X0, Y0 = Pin
    Profile = []
    for K in range(72):
        Ang = 2 * math.pi * K / 72
        Dx, Dy = math.cos(Ang), math.sin(Ang)
        Far = 0
        for R in range(1, 760):
            X = int(round(X0 + Dx * R))
            Y = int(round(Y0 + Dy * R))
            if not (0 <= X < W and 0 <= Y < H):
                break
            if Px[X, Y] > 0:
                Far = R
        Profile.append(Far)
    return min(Profile), sorted(Profile)[36]


Head_Def_Min, Head_Def = Reach_Profile(
    os.path.join(DEF_ROOT, "Front", "Part_Head_V1.PNG"), Neck_Def["pin"])
Head_Ovr_Min, Head_Ovr = Reach_Profile(
    os.path.join(OVR_ROOT, "Front", "Part_Head_V1.PNG"), Neck_Ovr["pin"])
Hand_Def_Min, Hand_Def = Reach_Profile(
    os.path.join(DEF_ROOT, "Front", "Part_Hand_Left_V1.PNG"),
    Wrist_Def["pin"])
Hand_Ovr_Min, Hand_Ovr = Reach_Profile(
    os.path.join(OVR_ROOT, "Front", "Part_Hand_Left_V1.PNG"),
    Wrist_Ovr["pin"])
Check("pixel_default_disc", abs(Head_Def - 515) <= 3,
      f"default head disc (median reach)={Head_Def} vs radius 515; "
      f"strip-sector min={Head_Def_Min}")
Check("pixel_override_disc", abs(Head_Ovr - 120) <= 3,
      f"override head disc (median reach)={Head_Ovr} vs chosen "
      f"radius 120; min={Head_Ovr_Min}")
Check("pixel_outputs_differ", Head_Def - Head_Ovr >= 300,
      f"default {Head_Def} - override {Head_Ovr} = {Head_Def - Head_Ovr}")
Check("pixel_untouched_joint_same",
      abs(Hand_Def - Hand_Ovr) <= 2 and abs(Hand_Def_Min - Hand_Ovr_Min) <= 2,
      f"hand reach default={Hand_Def}/{Hand_Def_Min} "
      f"override={Hand_Ovr}/{Hand_Ovr_Min}")

Failed = [K for K, V in Results.items() if not V["pass"]]
print(json.dumps(Results, indent=1))
print("TEST " + ("FAILED: " + ", ".join(Failed) if Failed else "PASSED"))
raise SystemExit(1 if Failed else 0)
