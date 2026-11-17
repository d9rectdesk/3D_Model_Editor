# Run_Pipeline_Proof_V1.PY
# Model Editor V20, Half B Piece 2: the Duke-side proof
# driver. Starts Bridge_Server_V1.PY, then talks to it
# by HTTP only: /status, detect_views on the man's three
# pictures in all 6 scrambled orders, make3d against the
# test settings' stand-in tool, snapshots and
# slice_layers on the man's 3D GLB, movement_reference
# posed-vs-rest, redraw on the OLD completed parts
# folder (the failing baseline set), and the model_up /
# model_down on-demand cycle. Writes the transcript to
# Pipeline_Proof_V1.JSON beside this file. The
# Humanoid_Rig folder and the output folder come
# from the pipeline settings file (humanoid_home
# and output_folder), never hard-coded.
# Source: Kevin, original work (the Model Editor
# pipeline proof driver; it talks to the bridge by
# HTTP only, the estate's own proof pattern, written
# for these runs; nothing copied).
import itertools
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

Home = os.path.dirname(os.path.abspath(__file__))

# Settings loading, copied literally from
# Bridge_Server_V1.PY (Original work - Kevin): the
# settings file is Editor_Pipeline_Settings_V1.JSON
# beside this file, or the file named by the
# environment variable EDITOR_PIPELINE_SETTINGS.
# Every folder path in this runner comes from that
# settings file, never hard-coded; a needed folder
# setting that is absent stops the run at once with
# a plain line naming what is missing.
# Source: Bridge_Server_V1.PY settings block
# (Original work - Kevin); the fail-fast folder
# checks below are new glue for this proof runner.
# Original work - Kevin.
Settings_Path = os.environ.get(
    "EDITOR_PIPELINE_SETTINGS",
    os.path.join(Home, "Editor_Pipeline_Settings_V1.JSON"))
with open(Settings_Path) as F:
    Settings = json.load(F)
Humanoid = Settings.get("humanoid_home")
if not Humanoid:
    print("pipeline proof: humanoid_home is not set in "
          "pipeline settings file " + Settings_Path +
          " - set humanoid_home to the Humanoid_Rig "
          "folder in that file", flush=True)
    sys.exit(2)
Out_Home = Settings.get("output_folder")
if not Out_Home:
    print("pipeline proof: output_folder is not set in "
          "pipeline settings file " + Settings_Path +
          " - set output_folder in that file", flush=True)
    sys.exit(2)
Base = "http://127.0.0.1:%d" % Settings["bridge_port"]
Transcript = {"settings": Settings_Path, "runs": []}


def Http(Method, Path, Body=None, Timeout=30):
    Data = json.dumps(Body).encode() if Body is not None else None
    Req = urllib.request.Request(Base + Path, data=Data,
                                 method=Method)
    if Data:
        Req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(Req, timeout=Timeout) as Resp:
        return json.loads(Resp.read().decode())


def Run_Step(Name, Params, Wait=1800):
    Job_Id = Http("POST", "/step/" + Name, Params)["job_id"]
    Start = time.time()
    while time.time() - Start < Wait:
        Job = Http("GET", "/job/" + Job_Id)
        if Job["state"] in ("done", "failed"):
            Entry = {"step": Name, "state": Job["state"],
                     "seconds": round(time.time() - Start, 1),
                     "outputs": Job["outputs"],
                     "error": Job.get("error"),
                     "log_tail": Job["log"][-40:]}
            Transcript["runs"].append(Entry)
            print("%s: %s in %.1fs" % (Name, Job["state"],
                                       time.time() - Start),
                  flush=True)
            return Entry
        time.sleep(2)
    raise RuntimeError("step %s did not finish in %ds" % (Name, Wait))


def Main():
    Bridge = subprocess.Popen(
        [sys.executable, os.path.join(Home, "Bridge_Server_V1.PY")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                Status = Http("GET", "/status", Timeout=2)
                break
            except Exception:
                time.sleep(0.5)
        Transcript["status"] = Status
        print("status: " + json.dumps(Status), flush=True)

        # detect_views: all 6 scrambles of the man's set.
        Src = {"front": os.path.join(
                   Humanoid, "Human_Man_Front_Cutout_V1.PNG"),
               "back": os.path.join(
                   Humanoid, "Human_Man_Back_Cutout_V1.PNG"),
               "side": os.path.join(
                   Humanoid, "Human_Man_Side_Cutout_V1.PNG")}
        Scramble_Home = os.path.join(Out_Home, "Scrambled_Views_V1")
        Correct = 0
        for I, Perm in enumerate(itertools.permutations(
                ["front", "back", "side"])):
            Folder = os.path.join(Scramble_Home, "perm%d" % I)
            os.makedirs(Folder, exist_ok=True)
            Truth = {}
            for J, Label in enumerate(Perm):
                Dest = os.path.join(Folder, "pic%d.PNG" % J)
                shutil.copyfile(Src[Label], Dest)
                Truth[Label] = Dest
            Entry = Run_Step("detect_views", {"folder": Folder})
            Out = Entry["outputs"]
            Good = (Out.get("front") == Truth["front"]
                    and Out.get("back") == Truth["back"]
                    and Out.get("side") == Truth["side"])
            Entry["permutation"] = list(Perm)
            Entry["correct"] = Good
            Correct += 1 if Good else 0
        Transcript["detect_views_permutations"] = "%d/6" % Correct

        # make3d against the stand-in tool (test settings).
        Run_Step("make3d", {"image": Src["front"]})

        # snapshots + slice_layers on the man's 3D GLB.
        Glb = os.path.join(Humanoid, "Human_Man_Paper_Doll_3D_V1.GLB")
        Rig = os.path.join(Humanoid, "Doll_Parts_Completed_V1",
                           "Completed_Rig_V1.JSON")
        Run_Step("snapshots", {
            "glb": Glb,
            "reference_stills": {
                "folder": os.path.join(
                    Humanoid, "Paper_Doll_3D_Stills_V1"),
                "names": {
                    "Front": "Human_Man_Paper_Doll_3D_Front_V1.PNG",
                    "Back": "Human_Man_Paper_Doll_3D_Back_V1.PNG",
                    "Left": "Human_Man_Paper_Doll_3D_Left_V1.PNG",
                    "Right": "Human_Man_Paper_Doll_3D_Right_V1.PNG"}}})
        Run_Step("slice_layers", {"glb": Glb, "rig_json": Rig})
        Run_Step("movement_reference", {
            "glb": Glb, "rig_json": Rig, "view": "Front",
            "part": "Part_Arm_Upper_Left_V1", "angle_degrees": 35})

        # redraw on the OLD completed parts folder: the
        # battery must return the failing baseline numbers.
        Run_Step("redraw", {
            "parts_folder": os.path.join(
                Humanoid, "Paper_Doll_Stitch_V1",
                "Doll_Parts_Completed_V1"),
            "rig_json": os.path.join(
                Humanoid, "Paper_Doll_Stitch_V1",
                "Doll_Parts_Completed_V1", "Completed_Rig_V1.JSON"),
            "views": "Front"}, Wait=3600)

        # model_up / model_down on-demand cycle, including
        # the not-ours case: a stand-in started by hand is
        # reported already-running and left alone.
        Manual = subprocess.Popen(
            Settings["llm"]["server_cmd"][0:2] + [
                Settings["llm"]["model_path"],
                str(Settings["llm"]["port"])],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(2)
            Run_Step("model_up", {})
            Run_Step("model_down", {})
        finally:
            Manual.terminate()
            time.sleep(1)
        Run_Step("model_up", {})
        Run_Step("model_down", {})

        Proof_Path = os.path.join(Home, "Pipeline_Proof_V1.JSON")
        with open(Proof_Path, "w") as F:
            json.dump(Transcript, F, indent=1)
        print("transcript: " + Proof_Path, flush=True)
        Failed = [R["step"] for R in Transcript["runs"]
                  if R["state"] != "done"]
        print("runs: %d, failed: %s"
              % (len(Transcript["runs"]), Failed), flush=True)
        return 1 if Failed else 0
    finally:
        Bridge.terminate()


if __name__ == "__main__":
    sys.exit(Main())
