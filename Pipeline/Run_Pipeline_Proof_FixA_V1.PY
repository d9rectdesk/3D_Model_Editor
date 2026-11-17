# Run_Pipeline_Proof_FixA_V1.PY
# Model Editor V20, Fix A proof driver. Restarts
# Bridge_Server_V1.PY on the final code and talks
# to it by HTTP only:
#   /status lists 11 steps;
#   an OPTIONS preflight returns 204 with the CORS
#   headers, and a GET /status sent with an Origin
#   header carries Access-Control-Allow-Origin
#   (an error response carries it too);
#   a make3d POST carrying the man's three pictures
#   as base64 data URLs, in scrambled order, against
#   the sandbox settings' stand-in tool completes,
#   and its detect outputs name front / back / side
#   correctly;
#   a rig POST on Duke's completed set completes
#   with round_trip pass=true (the multi-root build
#   through Build_Redrawn_GLB_V2.PY).
# Writes the transcript to
# Pipeline_Proof_FixA_V1.JSON beside this file and
# reads it back before exiting. The Humanoid_Rig
# folder and the output folder come from the
# pipeline settings file (humanoid_home and
# output_folder), never hard-coded.
# Source: Kevin, original work (the Model Editor
# pipeline Fix A proof driver, on the same HTTP-only
# bridge-driving pattern as Run_Pipeline_Proof_V1.PY;
# nothing copied).
import base64
import json
import os
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
    print("pipeline proof FixA: humanoid_home is not "
          "set in pipeline settings file " + Settings_Path +
          " - set humanoid_home to the Humanoid_Rig "
          "folder in that file", flush=True)
    sys.exit(2)
Out_Home = Settings.get("output_folder")
if not Out_Home:
    print("pipeline proof FixA: output_folder is not "
          "set in pipeline settings file " + Settings_Path +
          " - set output_folder in that file", flush=True)
    sys.exit(2)
Base = "http://127.0.0.1:%d" % Settings["bridge_port"]
Transcript = {"settings": Settings_Path, "checks": {}}


def Http_Raw(Method, Path, Body=None, Headers=None, Timeout=30):
    Data = json.dumps(Body).encode() if Body is not None else None
    Req = urllib.request.Request(Base + Path, data=Data,
                                 method=Method)
    if Data:
        Req.add_header("Content-Type", "application/json")
    for Key, Value in (Headers or {}).items():
        Req.add_header(Key, Value)
    try:
        with urllib.request.urlopen(Req, timeout=Timeout) as Resp:
            Text = Resp.read().decode()
            return Resp.status, dict(Resp.headers), \
                json.loads(Text) if Text else {}
    except urllib.error.HTTPError as Err:
        Text = Err.read().decode()
        return Err.code, dict(Err.headers), \
            json.loads(Text) if Text else {}


def Run_Step(Name, Params, Wait=1200):
    Code, _, Body = Http_Raw("POST", "/step/" + Name, Params)
    if Code != 200 or "job_id" not in Body:
        raise RuntimeError("step %s did not start: %s %s"
                           % (Name, Code, Body))
    Job_Id = Body["job_id"]
    Start = time.time()
    while time.time() - Start < Wait:
        _, _, Job = Http_Raw("GET", "/job/" + Job_Id)
        if Job["state"] in ("done", "failed"):
            print("%s: %s in %.1fs"
                  % (Name, Job["state"], time.time() - Start),
                  flush=True)
            return Job
        time.sleep(1)
    raise RuntimeError("step %s did not finish in %ds"
                       % (Name, Wait))


def Data_Url(Path):
    with open(Path, "rb") as F:
        Raw = F.read()
    return "data:image/png;base64," + base64.b64encode(
        Raw).decode(), len(Raw)


def Main():
    Bridge = subprocess.Popen(
        [sys.executable, os.path.join(Home, "Bridge_Server_V1.PY")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        Status = None
        for _ in range(60):
            try:
                _, _, Status = Http_Raw("GET", "/status", Timeout=2)
                break
            except Exception:
                time.sleep(0.5)
        Checks = Transcript["checks"]
        Checks["status"] = Status
        Checks["status_steps_11"] = bool(
            Status and len(Status.get("steps", [])) == 11)
        print("status: " + json.dumps(Status), flush=True)

        # CORS preflight: OPTIONS answers 204 with
        # the allow headers.
        Code, Headers, _ = Http_Raw(
            "OPTIONS", "/step/make3d", Headers={
                "Origin": "null",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"})
        Checks["options"] = {
            "status": Code,
            "access_control_allow_origin":
                Headers.get("Access-Control-Allow-Origin"),
            "access_control_allow_methods":
                Headers.get("Access-Control-Allow-Methods"),
            "access_control_allow_headers":
                Headers.get("Access-Control-Allow-Headers")}
        Checks["options_204_with_cors"] = bool(
            Code == 204
            and Headers.get("Access-Control-Allow-Origin") == "*"
            and Headers.get("Access-Control-Allow-Methods")
            and Headers.get("Access-Control-Allow-Headers"))
        print("options: " + json.dumps(Checks["options"]),
              flush=True)

        # CORS on a real response and on an error
        # response, both sent with an Origin header
        # (a file:// page sends Origin: null).
        _, Headers, _ = Http_Raw(
            "GET", "/status", Headers={"Origin": "null"})
        Checks["get_status_allow_origin"] = Headers.get(
            "Access-Control-Allow-Origin")
        Code, Headers, _ = Http_Raw(
            "GET", "/no-such-path", Headers={"Origin": "null"})
        Checks["error_response"] = {
            "status": Code,
            "access_control_allow_origin":
                Headers.get("Access-Control-Allow-Origin")}
        Checks["cors_on_success_and_error"] = bool(
            Checks["get_status_allow_origin"] == "*"
            and Code == 404
            and Checks["error_response"]
            ["access_control_allow_origin"] == "*")

        # make3d with the pictures as data: the man's
        # three pictures, scrambled (side, front,
        # back), against the stand-in tool.
        Src = {"front": os.path.join(
                   Humanoid, "Human_Man_Front_Cutout_V1.PNG"),
               "back": os.path.join(
                   Humanoid, "Human_Man_Back_Cutout_V1.PNG"),
               "side": os.path.join(
                   Humanoid, "Human_Man_Side_Cutout_V1.PNG")}
        Names = {"side": "picture_a.PNG", "front": "picture_b.PNG",
                 "back": "picture_c.PNG"}
        Images = []
        Sizes = {}
        for Label in ("side", "front", "back"):
            Url, Size = Data_Url(Src[Label])
            Images.append({"name": Names[Label], "data_url": Url})
            Sizes[Names[Label]] = Size
        Job = Run_Step("make3d", {"images": Images,
                                  "out_name": "Model_3D_FixA_V1.GLB"})
        Out = Job["outputs"]
        Detect = Out.get("detect", {})
        Named = {Label: os.path.basename(Detect.get(Label, ""))
                 for Label in ("front", "back", "side")}
        Written = {W["name"]: W["bytes"]
                   for W in Out.get("inputs", {}).get("written", [])}
        Checks["make3d_images"] = {
            "state": Job["state"], "error": Job.get("error"),
            "detect_named": Named,
            "written": Written,
            "inputs_folder": Out.get("inputs", {}).get("folder"),
            "glb": Out.get("glb"), "glb_bytes": Out.get("bytes"),
            "tool_command": Out.get("command")}
        Checks["make3d_images_pass"] = bool(
            Job["state"] == "done"
            and Named == {"front": "picture_b.PNG",
                          "back": "picture_c.PNG",
                          "side": "picture_a.PNG"}
            and Written == Sizes
            and Out.get("bytes", 0) > 0)
        print("make3d images: " + json.dumps(
            Checks["make3d_images"]), flush=True)

        # rig on Duke's set: the multi-root build
        # through the V2 builder.
        Duke_Out = os.path.join(Out_Home, "FixA_Proof_V1",
                                "duke_rig")
        Job = Run_Step("rig", {
            "parts_folder": os.path.join(
                Humanoid, "Paper_Duke_Completed_V1"),
            "rig_json": os.path.join(
                Humanoid, "Paper_Duke_Completed_V1",
                "Duke_Rig_Completed_V1.JSON"),
            "output_folder": Duke_Out})
        Out = Job["outputs"]
        Report = {}
        if Out.get("report_json") and os.path.exists(
                Out["report_json"]):
            Report = json.load(open(Out["report_json"]))
        Checks["rig_duke"] = {
            "state": Job["state"], "error": Job.get("error"),
            "builder_pass": Out.get("builder_pass"),
            "nodes": Out.get("nodes"),
            "flat_glb": Out.get("flat_glb"),
            "flat_bytes": Out.get("flat_bytes"),
            "glb_3d": Out.get("glb_3d"),
            "glb_3d_bytes": Out.get("glb_3d_bytes"),
            "round_trip": Out.get("round_trip"),
            "flat_counts": Report.get("flat", {}).get("counts"),
            "flat_roots": Report.get("flat", {}).get("roots"),
            "log_builder_lines": [L for L in Job["log"]
                                  if "builder=" in L]}
        Checks["rig_duke_pass"] = bool(
            Job["state"] == "done"
            and Out.get("round_trip", {}).get("pass") is True
            and Out.get("nodes") == 32
            and Report.get("flat", {}).get("counts")
            == {"Front": 16, "Back": 16})
        print("rig duke: " + json.dumps(Checks["rig_duke"]),
              flush=True)

        Checks["all_pass"] = bool(
            Checks["status_steps_11"]
            and Checks["options_204_with_cors"]
            and Checks["cors_on_success_and_error"]
            and Checks["make3d_images_pass"]
            and Checks["rig_duke_pass"])
        Proof_Path = os.path.join(
            Home, "Pipeline_Proof_FixA_V1.JSON")
        with open(Proof_Path, "w") as F:
            json.dump(Transcript, F, indent=1)
        Back = json.load(open(Proof_Path))
        print("transcript read back: %s, all_pass=%s"
              % (Proof_Path, Back["checks"]["all_pass"]),
              flush=True)
        return 0 if Back["checks"]["all_pass"] else 1
    finally:
        Bridge.terminate()


if __name__ == "__main__":
    sys.exit(Main())
