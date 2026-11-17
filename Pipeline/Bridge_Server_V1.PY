# Bridge_Server_V1.PY
# Model Editor V20, Half B Piece 2: the local pipeline
# bridge. A small localhost HTTP server, stdlib only.
# The editor page builds to this contract exactly:
#   GET  /status        -> {ok, steps:[...]}
#   POST /step/<name>   -> {job_id}   (JSON params body;
#                          the step runs async in a worker
#                          thread)
#   GET  /job/<id>      -> {state, progress, log[],
#                          outputs{}}
#   GET  /file?path=    -> one pipeline-made GLB's
#                          bytes (output folder only);
#   HEAD /file?path=    -> the same question answered
#                          with headers only, so the
#                          page's Models list can tell
#                          a file still there from one
#                          gone (2026-11-16).
# Settings come from Editor_Pipeline_Settings_V1.JSON
# beside this file (or the file named by the environment
# variable EDITOR_PIPELINE_SETTINGS): tool_home_3d,
# cuda_python, model_home, output_folder, and llm
# {server_cmd, model_path, port}. Nothing machine-
# specific is hard-coded; every path comes from
# settings. Loud operation: every step logs its
# settings, what it is doing now, and its results into
# the job log - nothing works mute.
# Usage: python3 Bridge_Server_V1.PY [port]
# Original work - Kevin.
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

Home = os.path.dirname(os.path.abspath(__file__))

# The estate's .PY extension is not importable by name on
# a case-sensitive filesystem, so the steps module is
# loaded from its file path.
# Source: Run_Redraw_Battery_V2.PY's importlib loading
# of Pose_Census_V1.PY (Kevin, Half A).
import importlib.machinery as Import_Mach
import importlib.util as Import_Util
Loader = Import_Mach.SourceFileLoader(
    "Pipeline_Steps_V1", os.path.join(Home, "Pipeline_Steps_V1.PY"))
Spec = Import_Util.spec_from_loader("Pipeline_Steps_V1", Loader)
Steps_Mod = Import_Util.module_from_spec(Spec)
Spec.loader.exec_module(Steps_Mod)
Settings_Path = os.environ.get(
    "EDITOR_PIPELINE_SETTINGS",
    os.path.join(Home, "Editor_Pipeline_Settings_V1.JSON"))
with open(Settings_Path) as F:
    Settings = json.load(F)

Jobs = {}
Jobs_Lock = threading.Lock()


def Log_Line(Job, Text):
    with Jobs_Lock:
        Job["log"].append("[%s] %s" % (
            time.strftime("%H:%M:%S"), Text))
    print(Job["log"][-1], flush=True)


def Run_Job(Job_Id, Name, Params):
    Job = Jobs[Job_Id]
    Job["state"] = "running"
    Job["progress"] = 0.1
    Log_Line(Job, "step %s starting; settings file %s"
             % (Name, Settings_Path))
    Log_Line(Job, "params: " + json.dumps(Params)[:400])
    try:
        Outputs = Steps_Mod.STEPS[Name](
            Params, Settings, lambda T: Log_Line(Job, T))
        Job["outputs"] = Outputs
        Job["state"] = "done"
        Job["progress"] = 1.0
        Log_Line(Job, "step %s done" % Name)
    except Exception as Exc:
        Job["state"] = "failed"
        Job["error"] = "%s: %s" % (type(Exc).__name__, Exc)
        Log_Line(Job, "step %s FAILED: %s" % (Name, Job["error"]))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *Args):
        pass

    # CORS, rewritten whole (Fix A, Defect 1 -
    # Harness_V20 check 6c: the bridge sent no
    # Access-Control-Allow-Origin and answered
    # OPTIONS with 501, so the editor page, which
    # runs from a file:// origin, could not read
    # any bridge response). This bridge is a
    # localhost-only bridge: it binds 127.0.0.1,
    # holds no credentials, and serves only the
    # editor on this machine, so every response -
    # success and error alike - carries
    # Access-Control-Allow-Origin: *, and an
    # OPTIONS preflight is answered 204 with the
    # allow-methods and allow-headers the page
    # needs. Source: Fetch/CORS preflight contract
    # (browser standard) - Kevin, Fix A.
    def Send_Cors_Headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, OPTIONS")
        Requested = self.headers.get(
            "Access-Control-Request-Headers")
        self.send_header("Access-Control-Allow-Headers",
                         Requested or "Content-Type")

    def Send_Json(self, Code, Obj):
        Body = json.dumps(Obj).encode()
        self.send_response(Code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(Body)))
        self.Send_Cors_Headers()
        self.end_headers()
        self.wfile.write(Body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.Send_Cors_Headers()
        self.end_headers()

    # /file serves one pipeline-made GLB back to the
    # editor page, so a Models list entry for a made
    # model can load it, and HEAD /file answers the
    # same question headers-only, so the list can
    # tell a file still there from one gone. The
    # fence is strict: the path must resolve inside
    # the settings' output folder and end in .glb -
    # the bridge serves the models its pipeline
    # made, nothing else on the machine.
    # Source: Kevin, original work (2026-11-16, the
    # Models list); the response shape follows this
    # file's own Send_Json / CORS pattern.
    def Serve_Model_File(self, Head_Only):
        Query = parse_qs(urlparse(self.path).query)
        Raw = (Query.get("path") or [""])[0]
        Root = os.path.realpath(
            Settings.get("output_folder") or "")
        Target = os.path.realpath(Raw) if Raw else ""
        Ok = (bool(Target) and bool(Root)
              and Target.startswith(Root + os.sep)
              and Target.lower().endswith(".glb")
              and os.path.isfile(Target))
        if not Ok:
            if Head_Only:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.Send_Cors_Headers()
                self.end_headers()
            else:
                self.Send_Json(
                    404, {"error": "no such model file"})
            return
        Size = os.path.getsize(Target)
        self.send_response(200)
        self.send_header("Content-Type",
                         "model/gltf-binary")
        self.send_header("Content-Length", str(Size))
        self.Send_Cors_Headers()
        self.end_headers()
        if not Head_Only:
            with open(Target, "rb") as F:
                while True:
                    Chunk = F.read(262144)
                    if not Chunk:
                        break
                    self.wfile.write(Chunk)

    def do_HEAD(self):
        if self.path.startswith("/file?"):
            self.Serve_Model_File(True)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.Send_Cors_Headers()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/file?"):
            self.Serve_Model_File(False)
            return
        if self.path == "/status":
            self.Send_Json(200, {"ok": True,
                                 "steps": sorted(Steps_Mod.STEPS)})
            return
        if self.path.startswith("/job/"):
            Job_Id = self.path[len("/job/"):]
            with Jobs_Lock:
                Job = Jobs.get(Job_Id)
                Snap = dict(Job) if Job else None
            if Snap is None:
                self.Send_Json(404, {"error": "no such job"})
                return
            self.Send_Json(200, {
                "state": Snap["state"], "progress": Snap["progress"],
                "log": Snap["log"], "outputs": Snap["outputs"],
                "error": Snap.get("error")})
            return
        self.Send_Json(404, {"error": "unknown path"})

    def do_POST(self):
        if not self.path.startswith("/step/"):
            self.Send_Json(404, {"error": "unknown path"})
            return
        Name = self.path[len("/step/"):]
        if Name not in Steps_Mod.STEPS:
            self.Send_Json(404, {"error": "no such step: " + Name})
            return
        Length = int(self.headers.get("Content-Length") or 0)
        Raw = self.rfile.read(Length) if Length else b"{}"
        try:
            Params = json.loads(Raw.decode() or "{}")
        except ValueError:
            self.Send_Json(400, {"error": "body is not JSON"})
            return
        Job_Id = uuid.uuid4().hex[:12]
        with Jobs_Lock:
            Jobs[Job_Id] = {"state": "queued", "progress": 0.0,
                            "log": [], "outputs": {}}
        Thread = threading.Thread(target=Run_Job,
                                  args=(Job_Id, Name, Params),
                                  daemon=True)
        Thread.start()
        self.Send_Json(200, {"job_id": Job_Id})


def Main():
    Port = int(os.sys.argv[1]) if len(os.sys.argv) > 1 else int(
        Settings.get("bridge_port", 8765))
    Server = ThreadingHTTPServer(("127.0.0.1", Port), Handler)
    print("bridge listening on 127.0.0.1:%d, settings %s"
          % (Port, Settings_Path), flush=True)
    print("steps: " + ", ".join(sorted(Steps_Mod.STEPS)), flush=True)
    Server.serve_forever()


if __name__ == "__main__":
    Main()
