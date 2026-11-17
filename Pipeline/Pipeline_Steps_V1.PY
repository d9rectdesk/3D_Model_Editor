# Pipeline_Steps_V1.PY
# Model Editor V20, Half B Piece 2: the pipeline step
# modules the bridge calls. Each step is one function
# Step_<name>(Params, Settings, Log) -> outputs dict.
# Log is a callable taking one string; every step logs
# its settings, what it is doing now, and its results -
# nothing works mute. Steps spin up per call and stand
# down after: no resident anything lives in this file.
# Reuse, not rebuild: snapshots render through the
# estate's Vendor_Three_V1 in headless Chrome (the Bit 5
# engine route, Shoot_Paper_Doll_Bit5_V1.JS); slice_layers
# runs the proven GLB_To_PNG_V1.PY; redraw wraps
# Redraw_Circles_V1.PY and Run_Redraw_Battery_V2.PY by
# subprocess and copies none of their logic; rig,
# make_paper, and make_3d wrap Build_Redrawn_GLB_V2.PY
# by subprocess the same way (V2, Fix A: multi-root
# rigs; the builder path is logged on every run).
# V21: redraw also carries the page's per-point fill
# radii (Params["disc_radii"], view -> joint -> radius)
# to the engine as its REDRAW_DISC_RADII_JSON override
# file, so a completion fills to the circles Solomon
# tuned in the editor; a joint with no tuned radius
# keeps the engine's own computed radius.
# Fill-source precedence (Solomon, 2026-11-16): a
# joint's REVEAL BITMAP - the 3D lane's composite of
# the model's own rendered pixels from 5-degree pose
# sweeps - is the fill where one exists, and the disc
# at the per-point radius is the manual fallback where
# none does. Params["reveal_dir"] names the bitmap
# folder (<folder>/<View>/Reveal_<joint>_V1.PNG) and
# reaches the engine as REDRAW_REVEAL_DIR; the bitmap
# wins per joint even over a tuned radius.
# Original work - Kevin.
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

Home = os.path.dirname(os.path.abspath(__file__))


# Run one subprocess, streaming its tail into the job log.
# Source: estate pattern from Check_Paper_Doll_Bit5_V1.PY
# era harnesses (Kevin) - subprocess with captured streams.
def Run_Captured(Cmd, Log, Cwd=None, Timeout=1800, Env=None):
    Log("run: " + " ".join(str(C) for C in Cmd))
    Full_Env = None
    if Env:
        Full_Env = dict(os.environ)
        Full_Env.update(Env)
    Proc = subprocess.run([str(C) for C in Cmd], cwd=Cwd,
                          capture_output=True, text=True,
                          timeout=Timeout, env=Full_Env)
    for Line in (Proc.stdout or "").splitlines()[-25:]:
        Log("  out: " + Line)
    for Line in (Proc.stderr or "").splitlines()[-10:]:
        Log("  err: " + Line)
    Log("exit code: %d" % Proc.returncode)
    return Proc


# Picture inputs carried as data (Fix A, Defect 2):
# the editor page holds the user's pictures in the
# browser, so a step's params may carry
# images: [{name, data_url}] instead of a folder on
# this machine. The pictures are decoded into
# <output_folder>/Ai_Inputs/<job_id>/ - the job id
# comes from params when the caller supplies one,
# else one is minted here - and every written file
# is logged with its name and byte count, so the
# job log shows exactly what arrived. Returns None
# when the params carry no images, so the folder
# and files params keep working unchanged.
# Source: the data URL form (RFC 2397), decoded
# with the stdlib base64 module - Kevin, Fix A.
def Materialize_Images(Params, Settings, Log):
    Images = Params.get("images")
    if not Images:
        return None
    Job_Id = str(Params.get("job_id") or uuid.uuid4().hex[:12])
    Folder = os.path.join(Settings["output_folder"],
                          "Ai_Inputs", Job_Id)
    os.makedirs(Folder, exist_ok=True)
    Written = []
    for Item in Images:
        Name = os.path.basename(
            str(Item.get("name") or "image.PNG")) or "image.PNG"
        Data_Url = str(Item.get("data_url") or "")
        if Data_Url.startswith("data:") and "," in Data_Url:
            Data_Url = Data_Url.split(",", 1)[1]
        Raw = base64.b64decode(Data_Url)
        Path = os.path.join(Folder, Name)
        with open(Path, "wb") as F:
            F.write(Raw)
        Written.append({"name": Name, "path": Path,
                        "bytes": len(Raw)})
        Log("images input: wrote %s, %d bytes, to %s"
            % (Name, len(Raw), Path))
    Log("images input: %d pictures in %s"
        % (len(Written), Folder))
    return {"folder": Folder, "job_id": Job_Id,
            "written": Written}


# detect_views: classify an unordered set of pictures
# as front / back / side_left / side_right from the
# pictures' own evidence.
# Source: Kevin, original work (2026-11-16).
# Census before writing: no estate code classifies a
# side picture's facing from its pixels - the paper
# doll sets name sides by filename - so the facing
# score below was written for this step; front/back
# classification extends this step's own V20 method
# (stride aspect + head features) to the second side.
# The four-view standard (Solomon, 2026-11-16, on the
# SandBase multi-view benchmark's measured view-count
# economics): each added true view buys down error on
# the faces it reveals, and the second side is the one
# our doll set currently derives - so the input set is
# FOUR pictures, front, back, left side, right side.
# A three-picture set (one side) still classifies,
# for the sets already made.
# Method: the sides are the stride profiles - their
# silhouette bounding boxes are the widest in the set
# (the stride spreads front-to-back). Front vs back is
# decided in the head region (top fifth of the
# silhouette): the front carries face features - small
# dark components (eyes, mouth) set in skin - while
# the back head is one dark hair mass, so its dark
# fraction is far higher and its small-feature count
# is near zero. The two sides are told apart by the
# facing score: the feet band's centroid sits toward
# the facing direction (the toes lead), and the head
# band's mass skews the same way; both measures flip
# sign under mirroring. A positive score names the
# picture side_right, a negative one side_left - the
# sign convention is calibrated on the man's set,
# whose source side picture measures positive and is
# the rig's SideRight view (SideLeft is its mirror).
def Step_Detect_Views(Params, Settings, Log):
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    Mat = Materialize_Images(Params, Settings, Log)
    if Mat is not None:
        Folder = Mat["folder"]
        Files = None
    else:
        Folder = Params.get("folder")
        Files = Params.get("files")
    if not Files:
        Files = sorted(os.path.join(Folder, F)
                       for F in os.listdir(Folder)
                       if F.lower().endswith(".png"))
    Log("detect_views: %d pictures, unordered set" % len(Files))
    # The count gate, loosened (Solomon, 2026-11-16:
    # "four images (or more) of the same object"). The
    # old gate hard-stopped above four. Now any set of
    # three or more runs: the four named views are
    # picked by the same measures as before, and every
    # picture past the named four rides along in the
    # outputs as an extra view. Fewer than three
    # cannot name front, back and a side, so the stop
    # stays there. Source: Kevin, original work.
    if len(Files) < 3:
        raise ValueError(
            "need at least 3 pictures (front, back and a "
            "side - the four-view standard is front, back, "
            "left side, right side, and more pictures of "
            "the same object ride along), got %d"
            % len(Files))
    Feats = {}
    for Path in Files:
        Arr = np.asarray(Image.open(Path).convert("RGBA"))
        Alpha = Arr[:, :, 3] > 10
        Ys, Xs = np.where(Alpha)
        W = int(Xs.max() - Xs.min() + 1)
        H = int(Ys.max() - Ys.min() + 1)
        Head = Arr[Ys.min():Ys.min() + int(H * 0.2),
                   Xs.min():Xs.max() + 1]
        Head_A = Head[:, :, 3] > 10
        Lum = Head[:, :, :3].mean(axis=2)
        Dark = (Lum < 70) & Head_A
        Dark_Frac = float(Dark.sum() / max(Head_A.sum(), 1))
        Lab, N = ndimage.label(Dark)
        Sizes = ndimage.sum_labels(Dark, Lab, range(1, N + 1))
        Small = int(((Sizes >= 15) & (Sizes <= 2500)).sum())
        # The facing measures (see the header): the
        # feet band's centroid toward the facing
        # direction, and the head band's mass skew.
        Mid_X = (int(Xs.min()) + int(Xs.max())) / 2.0
        Feet = Alpha[Ys.max() - int(H * 0.08):Ys.max() + 1,
                     Xs.min():Xs.max() + 1]
        _, Feet_Xs = np.where(Feet)
        Feet_Rel = (float(Feet_Xs.mean() + Xs.min() - Mid_X) / W
                    if len(Feet_Xs) else 0.0)
        _, Head_Xs = np.where(Head_A)
        if len(Head_Xs):
            Band_Mid = (Head_Xs.min() + Head_Xs.max()) / 2.0
            Skew = float((Head_Xs < Band_Mid).mean()
                         - (Head_Xs > Band_Mid).mean())
        else:
            Skew = 0.0
        Facing = round(Feet_Rel + Skew, 4)
        Feats[Path] = {"aspect_w_over_h": round(W / H, 4),
                       "bbox_w": W, "bbox_h": H,
                       "head_dark_fraction": round(Dark_Frac, 4),
                       "head_small_dark_features": Small,
                       "feet_centroid_rel": round(Feet_Rel, 4),
                       "head_skew": round(Skew, 4),
                       "facing_score": Facing}
        Log("  %s aspect=%.3f head_dark=%.3f features=%d facing=%+.3f"
            % (os.path.basename(Path), W / H, Dark_Frac, Small,
               Facing))
    # Naming the views (selection rewritten whole
    # with the count loosening, 2026-11-16): the
    # side-like pictures are ranked by the same
    # measures as before - aspect first, then facing
    # strength - and the two named sides are a pair
    # facing opposite ways whenever the set holds
    # one, so an extra side picture can never push a
    # true side out of its name. The front keeps its
    # rule (the most face features) and is picked
    # from the non-side-like pictures when there are
    # any. The back is the remaining picture closest
    # in aspect to the front - front and back are
    # the two full-frontal views - which is the old
    # "the other one" whenever the set is exactly
    # the named views. Anything left over is an
    # extra view and rides along. For three- and
    # four-picture sets every pick lands exactly
    # where the old code put it.
    # Source: Kevin, original work.
    Max_Aspect = max(F["aspect_w_over_h"] for F in Feats.values())
    Side_Like = [P for P in Files
                 if Feats[P]["aspect_w_over_h"] >= 0.8 * Max_Aspect]
    Side_Like.sort(key=lambda P: (
        -Feats[P]["aspect_w_over_h"],
        -abs(Feats[P]["facing_score"])))
    if len(Side_Like) <= 2:
        Sides = list(Side_Like)
    else:
        First = Side_Like[0]
        Opposite = [P for P in Side_Like[1:]
                    if (Feats[P]["facing_score"] > 0)
                    != (Feats[First]["facing_score"] > 0)]
        Sides = [First, (Opposite[0] if Opposite
                         else Side_Like[1])]
    if not Sides:
        Sides = [max(Feats, key=lambda P:
                     Feats[P]["aspect_w_over_h"])]
    Rest = [P for P in Files if P not in Sides]
    Plain = [P for P in Rest if P not in Side_Like] or Rest
    Front = max(Plain, key=lambda P: (
        Feats[P]["head_small_dark_features"],
        -Feats[P]["head_dark_fraction"]))
    Back_Cands = [P for P in Plain if P != Front] or \
        [P for P in Rest if P != Front]
    Back = min(Back_Cands, key=lambda P: abs(
        Feats[P]["aspect_w_over_h"]
        - Feats[Front]["aspect_w_over_h"]))
    Extras = [P for P in Files
              if P not in Sides and P != Front and P != Back]
    if Extras:
        Log("  extra views riding along: %s"
            % ", ".join(os.path.basename(P) for P in Extras))
    Named_Sides = {}
    for Path in sorted(Sides,
                       key=lambda P: -abs(Feats[P]["facing_score"])):
        Name = ("side_right" if Feats[Path]["facing_score"] > 0
                else "side_left")
        if Name in Named_Sides:
            Other = ("side_left" if Name == "side_right"
                     else "side_right")
            Log("  both side pictures face the same way; %s "
                "named %s by elimination"
                % (os.path.basename(Path), Other))
            Name = Other
        Named_Sides[Name] = Path
    Verdict = ["front=" + os.path.basename(Front),
               "back=" + os.path.basename(Back)]
    for Name in ("side_left", "side_right"):
        if Name in Named_Sides:
            Verdict.append(
                Name + "=" + os.path.basename(Named_Sides[Name]))
    if len(Named_Sides) == 1:
        Verdict.append(
            "side=" + os.path.basename(list(Named_Sides.values())[0]))
    Log("verdict: " + " ".join(Verdict))
    Outputs = {"front": Front, "back": Back,
               "features": {os.path.basename(K): V
                            for K, V in Feats.items()}}
    Outputs.update(Named_Sides)
    if len(Named_Sides) == 1:
        Outputs["side"] = list(Named_Sides.values())[0]
    if Extras:
        Outputs["extra_views"] = Extras
    if Mat is not None:
        Outputs["inputs"] = Mat
    return Outputs
# make3d: settings-driven invocation of the local
# image-to-3D tool. The command is built only from
# settings: cuda_python + tool_home_3d/make3d_script +
# make3d_args with {image} and {output} substituted.
# Nothing machine-specific is hard-coded here.
# Input pictures (input-handling section rewritten
# whole, Fix A, Defect 2): params may carry the
# pictures as data (images: [{name, data_url}]) or
# as a folder / files set on this machine; either
# way detection runs on the set first and the tool
# receives the detected front picture, and the
# detect verdict rides in the outputs as "detect".
# The original single-image param (image) keeps
# working unchanged and skips detection.
def Step_Make3d(Params, Settings, Log):
    Mat = Materialize_Images(Params, Settings, Log)
    Detect = None
    if Mat is not None:
        Detect = Step_Detect_Views(
            {"folder": Mat["folder"]}, Settings, Log)
        Image_Path = Detect["front"]
        Log("make3d: pictures as data - detection named "
            "the front picture %s" % Image_Path)
    elif Params.get("folder") or Params.get("files"):
        Detect = Step_Detect_Views(Params, Settings, Log)
        Image_Path = Detect["front"]
        Log("make3d: folder pictures - detection named "
            "the front picture %s" % Image_Path)
    else:
        Image_Path = Params["image"]
    Out_Name = Params.get("out_name", "Model_3D_V1.GLB")
    Out_Folder = Settings["output_folder"]
    os.makedirs(Out_Folder, exist_ok=True)
    Out_Path = os.path.join(Out_Folder, Out_Name)
    Script = os.path.join(Settings["tool_home_3d"],
                          Settings["make3d_script"])
    Args = [A.replace("{image}", Image_Path)
            .replace("{output}", Out_Path)
            .replace("{out_folder}", Out_Folder)
            for A in Settings.get("make3d_args", [])]
    Cmd = [Settings["cuda_python"], Script] + Args
    Log("make3d settings: cuda_python=%s tool_home_3d=%s script=%s"
        % (Settings["cuda_python"], Settings["tool_home_3d"], Script))
    Log("make3d image=%s output=%s" % (Image_Path, Out_Path))
    Proc = Run_Captured(Cmd, Log, Timeout=3600)
    if Proc.returncode != 0:
        raise RuntimeError("make3d tool exited %d" % Proc.returncode)
    if not os.path.exists(Out_Path):
        raise RuntimeError("make3d produced no output at " + Out_Path)
    Head = open(Out_Path, "rb").read(4)
    Size = os.path.getsize(Out_Path)
    Log("output: %s %d bytes, glTF magic=%s" % (Out_Path, Size, Head == b"glTF"))
    if Head != b"glTF" or Size == 0:
        raise RuntimeError("make3d output is not a GLB")
    Outputs = {"glb": Out_Path, "bytes": Size, "command": Cmd}
    if Detect is not None:
        Outputs["detect"] = Detect
    if Mat is not None:
        Outputs["inputs"] = Mat
    return Outputs


# Shared Chrome/Three shooting route for snapshots and
# movement_reference: Render_Shoot_V1.JS (CDP scaffolding
# adapted from Shoot_Paper_Doll_Bit5_V1.JS, Kevin, Bit 5)
# drives headless Chrome with the estate flags
# --allow-file-access-from-files --enable-unsafe-swiftshader
# over a page built on Vendor_Three_V1.
def Shoot(Glb, Out_Folder, Dirs, Settings, Log, Pose=None,
          Size=1024):
    Page = os.path.join(Home, "Render_Page_V1.HTML")
    Shooter = os.path.join(Home, "Render_Shoot_V1.JS")
    os.makedirs(Out_Folder, exist_ok=True)
    Args = [Settings.get("node", "node"), Shooter,
            "--page", Page, "--glb", Glb, "--out", Out_Folder,
            "--vendor", Settings["vendor_three_home"],
            "--chrome", Settings["chrome_path"],
            "--dirs", ",".join(Dirs), "--size", str(Size)]
    if Pose:
        Args += ["--pose", json.dumps(Pose)]
    Proc = Run_Captured(Args, Log, Timeout=600)
    if Proc.returncode != 0:
        raise RuntimeError("render shooter exited %d" % Proc.returncode)
    Summary = {}
    for Line in (Proc.stdout or "").splitlines():
        if Line.startswith("SHOOT_JSON "):
            Summary = json.loads(Line[len("SHOOT_JSON "):])
    return Summary


def Silhouette(Png_Path):
    import numpy as np
    from PIL import Image
    Arr = np.asarray(Image.open(Png_Path).convert("RGBA"))
    return Arr, int((Arr[:, :, 3] > 10).sum())


# snapshots: render a GLB at the paper views' angles.
def Step_Snapshots(Params, Settings, Log):
    Glb = Params["glb"]
    Out_Folder = Params.get("out_folder") or os.path.join(
        Settings["output_folder"], "Snapshots_V1")
    Log("snapshots settings: chrome=%s vendor=%s"
        % (Settings["chrome_path"], Settings["vendor_three_home"]))
    Log("snapshots glb=%s out=%s" % (Glb, Out_Folder))
    Dirs = ["Front", "Back", "Left", "Right"]
    Shoot(Glb, Out_Folder, Dirs, Settings, Log)
    Outputs = {"folder": Out_Folder, "views": {}}
    for D in Dirs:
        P = os.path.join(Out_Folder, D + ".PNG")
        if not os.path.exists(P) or os.path.getsize(P) == 0:
            raise RuntimeError("snapshot missing or empty: " + P)
        _, Pix = Silhouette(P)
        Outputs["views"][D] = {"png": P, "bytes": os.path.getsize(P),
                               "silhouette_pixels": Pix}
        Log("  %s: %d bytes, silhouette %d px"
            % (D, os.path.getsize(P), Pix))
    Ref = Params.get("reference_stills")
    if Ref:
        import numpy as np
        Ious = {}
        for D in Dirs:
            Rp = os.path.join(Ref["folder"], Ref["names"][D])
            A, _ = Silhouette(os.path.join(Out_Folder, D + ".PNG"))
            B, _ = Silhouette(Rp)
            Am = A[:, :, 3] > 10
            Bm = B[:, :, 3] > 10
            Ious[D] = round(float((Am & Bm).sum() /
                                  max((Am | Bm).sum(), 1)), 6)
        Outputs["iou_vs_reference"] = Ious
        Log("IoU vs reference stills: " + json.dumps(Ious))
    return Outputs


# movement_reference: pose the 3D model (one joint
# rotation from params) and render the posed still next
# to the rest still; the diff is measured overall and
# inside the disc around the posed joint's pin.
def Step_Movement_Reference(Params, Settings, Log):
    Glb = Params["glb"]
    Rig = json.load(open(Params["rig_json"]))
    View = Params.get("view", "Front")
    Part = Params["part"]
    Angle = float(Params.get("angle_degrees", 30))
    Pin = Rig["views"][View]["parts"][Part]["pin"]
    Out_Folder = Params.get("out_folder") or os.path.join(
        Settings["output_folder"], "Movement_Reference_V1")
    Log("movement_reference: view=%s part=%s angle=%s pin=%s"
        % (View, Part, Angle, Pin))
    Rest_Dir = os.path.join(Out_Folder, "Rest")
    Pose_Dir = os.path.join(Out_Folder, "Posed")
    Shoot(Glb, Rest_Dir, [View], Settings, Log)
    Pose = {"view": View, "part": Part, "angle_degrees": Angle,
            "pin": Pin, "canvas": Rig["canvas"]}
    Shoot(Glb, Pose_Dir, [View], Settings, Log, Pose=Pose)
    import numpy as np
    A, _ = Silhouette(os.path.join(Rest_Dir, View + ".PNG"))
    B, _ = Silhouette(os.path.join(Pose_Dir, View + ".PNG"))
    Diff = (np.abs(A.astype(int) - B.astype(int)).sum(axis=2) > 24)
    Scale = A.shape[0] / float(Rig["canvas"])
    Cx, Cy = Pin[0] * Scale, Pin[1] * Scale
    Yy, Xx = np.mgrid[0:A.shape[0], 0:A.shape[1]]
    Disc = (Xx - Cx) ** 2 + (Yy - Cy) ** 2 <= (340 * Scale) ** 2
    Out = {"view": View, "part": Part, "angle_degrees": Angle,
           "pin": Pin, "rest_png": os.path.join(Rest_Dir, View + ".PNG"),
           "posed_png": os.path.join(Pose_Dir, View + ".PNG"),
           "diff_pixels_total": int(Diff.sum()),
           "diff_pixels_at_joint_disc": int((Diff & Disc).sum()),
           "diff_pixels_outside_disc": int((Diff & ~Disc).sum())}
    Log("diff: total=%d at joint disc=%d outside=%d"
        % (Out["diff_pixels_total"], Out["diff_pixels_at_joint_disc"],
           Out["diff_pixels_outside_disc"]))
    if Out["diff_pixels_at_joint_disc"] == 0:
        raise RuntimeError("posed render does not differ at the joint")
    return Out


# slice_layers: cut a GLB into the paper layers in the
# estate's scheme (views x parts) by running the proven
# GLB_To_PNG_V1.PY on a copy in the output folder, then
# grouping its layers by view and censusing against the
# rig's part counts per view.
def Step_Slice_Layers(Params, Settings, Log):
    Glb = Params["glb"]
    Rig = json.load(open(Params["rig_json"]))
    Out_Folder = Params.get("out_folder") or os.path.join(
        Settings["output_folder"], "Sliced_Layers_V1")
    os.makedirs(Out_Folder, exist_ok=True)
    Local_Glb = os.path.join(Out_Folder, os.path.basename(Glb))
    shutil.copyfile(Glb, Local_Glb)
    Tool = os.path.join(Settings["humanoid_home"], "GLB_To_PNG_V1.PY")
    Log("slice_layers settings: tool=%s" % Tool)
    Proc = Run_Captured([sys.executable, Tool, Local_Glb], Log,
                        Timeout=600)
    if Proc.returncode != 0:
        raise RuntimeError("GLB_To_PNG exited %d" % Proc.returncode)
    Stem = os.path.splitext(os.path.basename(Glb))[0]
    Flat = os.path.join(Out_Folder, Stem + "_Layers_V1")
    Per_View = {}
    for Name in sorted(os.listdir(Flat)):
        View = Name.split("_Part_")[0]
        Dest = os.path.join(Out_Folder, View)
        os.makedirs(Dest, exist_ok=True)
        shutil.move(os.path.join(Flat, Name),
                    os.path.join(Dest, Name))
        Per_View[View] = Per_View.get(View, 0) + 1
    os.rmdir(Flat)
    Want = {V: len(I["parts"]) for V, I in Rig["views"].items()}
    Match = Per_View == Want
    Log("census per view: got=%s want=%s match=%s"
        % (json.dumps(Per_View), json.dumps(Want), Match))
    if not Match:
        raise RuntimeError("slice census mismatch: %s vs %s"
                           % (Per_View, Want))
    return {"folder": Out_Folder, "per_view": Per_View,
            "want_per_view": Want, "total": sum(Per_View.values()),
            "census_match": Match}


# redraw: the circle completion as a callable step.
# Wraps Redraw_Circles_V1.PY's engine by subprocess (its
# own proven roots: the stitch completed set in, the
# Paper_Doll_Redraw_V2 folder out - nothing copied) and
# then runs Run_Redraw_Battery_V2.PY on the caller's
# parts folder + rig, returning the battery numbers.
# V21: Params["disc_radii"] (view -> joint -> radius,
# the radii tuned in the editor) is written to an
# overrides file in the output folder and handed to
# the engine through its REDRAW_DISC_RADII_JSON
# environment variable; Params["views"], when given,
# also reaches the engine as REDRAW_VIEWS.
# Params["reveal_dir"], when given, reaches it as
# REDRAW_REVEAL_DIR: per joint, a reveal bitmap in
# that folder is the fill source and supersedes the
# disc - even a tuned radius; joints without a
# bitmap fall back to their disc.
def Step_Redraw(Params, Settings, Log):
    Humanoid = Settings["humanoid_home"]
    Outputs = {}
    if Params.get("run_engine", True):
        Env = {}
        Radii = Params.get("disc_radii")
        if Radii:
            Out_Folder = Settings["output_folder"]
            os.makedirs(Out_Folder, exist_ok=True)
            Ovr_Path = os.path.join(
                Out_Folder, "Disc_Radii_Overrides_V1.JSON")
            with open(Ovr_Path, "w") as F:
                json.dump(Radii, F, indent=1)
            Env["REDRAW_DISC_RADII_JSON"] = Ovr_Path
            Count = sum(len(V) for V in Radii.values())
            Log("redraw disc radii: %d tuned joint(s) written "
                "to %s" % (Count, Ovr_Path))
            Outputs["disc_radii"] = Radii
        Reveal_Dir = Params.get("reveal_dir")
        if Reveal_Dir:
            if os.path.isdir(Reveal_Dir):
                Found = []
                for View in ("Front", "Back", "SideRight",
                             "SideLeft"):
                    VDir = os.path.join(Reveal_Dir, View)
                    if os.path.isdir(VDir):
                        Found += [os.path.join(View, F)
                                  for F in sorted(os.listdir(VDir))
                                  if F.startswith("Reveal_")
                                  and F.endswith("_V1.PNG")]
                Env["REDRAW_REVEAL_DIR"] = Reveal_Dir
                Log("redraw reveal bitmaps: %d bitmap(s) in %s - "
                    "a bitmap is the fill where present and "
                    "supersedes the disc; the rest fill by disc"
                    % (len(Found), Reveal_Dir))
                Outputs["reveal_dir"] = Reveal_Dir
                Outputs["reveal_bitmaps"] = len(Found)
            else:
                Log("redraw reveal_dir %s not found - no reveal "
                    "bitmaps; every joint fills by disc"
                    % Reveal_Dir)
        if Params.get("views"):
            Env["REDRAW_VIEWS"] = Params["views"]
        Proc = Run_Captured(
            [sys.executable, os.path.join(Humanoid,
                                          "Redraw_Circles_V1.PY")],
            Log, Cwd=Humanoid, Timeout=3600, Env=Env or None)
        Census_Path = os.path.join(
            Humanoid, "Paper_Doll_Redraw_V2", "Redraw_Census_V1.JSON")
        Outputs["engine"] = {
            "exit_code": Proc.returncode,
            "census": Census_Path if os.path.exists(Census_Path)
            else None}
        Log("redraw engine exit=%d census=%s"
            % (Proc.returncode, Outputs["engine"]["census"]))
    Parts = Params["parts_folder"]
    Rig_Path = Params["rig_json"]
    Bat_Out = Params.get("battery_out") or os.path.join(
        Settings["output_folder"], "Redraw_Battery_Result_V1.JSON")
    os.makedirs(os.path.dirname(Bat_Out), exist_ok=True)
    Cmd = [sys.executable, os.path.join(Humanoid,
                                        "Run_Redraw_Battery_V2.PY"),
           Parts, Rig_Path, Bat_Out]
    if Params.get("views"):
        Cmd += ["--views", Params["views"]]
    Proc = Run_Captured(Cmd, Log, Cwd=Humanoid, Timeout=7200)
    Outputs["battery_exit_code"] = Proc.returncode
    Outputs["battery_json"] = Bat_Out
    if os.path.exists(Bat_Out):
        Bat = json.load(open(Bat_Out))
        Summary = {}
        for View, Data in Bat.get("views", {}).items():
            Per_Joint = Data.get("per_joint_trapped", {})
            Worst = 0
            Failed_Joints = []
            for Joint, J in Per_Joint.items():
                Worst = max(Worst, J.get("plus_max", 0),
                            J.get("minus_max", 0),
                            J.get("rest_trapped", 0))
                if not J.get("pass", True):
                    Failed_Joints.append(Joint)
            Summary[View] = {
                "worst_trapped_pixels": Worst,
                "failed_joints": Failed_Joints,
                "pass": not Failed_Joints}
        Outputs["battery"] = Summary
        Log("battery summary: " + json.dumps(Summary))
    # The chain continues from this step's product:
    # report where the redrawn parts and their rig
    # stand - the engine's output folder (its
    # REDRAW_OUT_ROOT default; this step never
    # overrides it) and the rig it wrote there.
    # Without these the next steps keep the slice
    # step's folder and build the wrong parts.
    Out_Root = os.path.join(Humanoid, "Paper_Doll_Redraw_V2")
    Outputs["parts_folder"] = Out_Root
    Outputs["rig_json"] = os.path.join(Out_Root,
                                       "Redrawn_Rig_V1.JSON")
    Log("redraw product: parts_folder=%s rig_json=%s"
        % (Outputs["parts_folder"], Outputs["rig_json"]))
    return Outputs


def Llm_Endpoint(Settings):
    Llm = Settings["llm"]
    return "http://127.0.0.1:%d" % int(Llm["port"])


def Llm_Answers(Settings):
    try:
        Req = urllib.request.Request(Llm_Endpoint(Settings) + "/health")
        with urllib.request.urlopen(Req, timeout=2) as Resp:
            return Resp.status == 200
    except Exception:
        return False


def Llm_State_Path():
    return os.path.join(Home, "Pipeline_Llm_State_V1.JSON")


# model_up: the local LLM as on-demand only. If the
# configured endpoint already answers, report it and
# own nothing. Otherwise start settings llm.server_cmd
# with the settings' model_path (used by path from the
# shared model home, never copied), wait for health.
def Step_Model_Up(Params, Settings, Log):
    Llm = Settings["llm"]
    Endpoint = Llm_Endpoint(Settings)
    Log("model_up settings: endpoint=%s model_path=%s"
        % (Endpoint, Llm["model_path"]))
    if Llm_Answers(Settings):
        Log("endpoint already answers; not ours, leaving it")
        return {"endpoint": Endpoint, "already_running": True,
                "owned": False}
    Cmd = [C.replace("{model_path}", Llm["model_path"])
           .replace("{port}", str(Llm["port"]))
           for C in Llm["server_cmd"]]
    Log("starting server: " + " ".join(Cmd))
    Proc = subprocess.Popen(Cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True)
    with open(Llm_State_Path(), "w") as F:
        json.dump({"pid": Proc.pid, "owned": True,
                   "endpoint": Endpoint}, F)
    Deadline = time.time() + 180
    while time.time() < Deadline:
        if Llm_Answers(Settings):
            Log("endpoint healthy, pid=%d" % Proc.pid)
            return {"endpoint": Endpoint, "already_running": False,
                    "owned": True, "pid": Proc.pid}
        if Proc.poll() is not None:
            raise RuntimeError("llm server exited %d" % Proc.returncode)
        time.sleep(1)
    raise RuntimeError("llm server did not answer in 180s")


# model_down: stop only what model_up started. A server
# the pipeline did not start is reported and left alone.
def Step_Model_Down(Params, Settings, Log):
    Endpoint = Llm_Endpoint(Settings)
    Log("model_down settings: endpoint=%s" % Endpoint)
    if not os.path.exists(Llm_State_Path()):
        Log("no owned server recorded; nothing to stop")
        return {"endpoint": Endpoint, "stopped": False,
                "note": "no server started by model_up is recorded"}
    State = json.load(open(Llm_State_Path()))
    if not State.get("owned"):
        return {"endpoint": Endpoint, "stopped": False,
                "note": "recorded server was not owned"}
    Pid = int(State["pid"])
    try:
        os.kill(Pid, 15)
        Log("sent SIGTERM to owned pid=%d" % Pid)
        Stopped = True
    except ProcessLookupError:
        Log("owned pid=%d already gone" % Pid)
        Stopped = True
    os.remove(Llm_State_Path())
    return {"endpoint": Endpoint, "stopped": Stopped, "pid": Pid}


# Shared runner for rig, make_paper, and make_3d: the
# proven GLB builder Build_Redrawn_GLB_V2.PY (Kevin,
# Humanoid_Rig_V1) invoked by subprocess - its logic is
# never copied here. V2, not V1 (Fix A, Defect 3): V2
# builds multi-root rigs (Duke) and stays byte-
# identical to V1 on single-root rigs (the man); the
# builder path is printed in every job log below, so
# the choice is visible, not hidden. The builder takes a parts folder
# and a rig JSON, always emits both the flat paper GLB
# and the assembled 3D GLB plus its report JSON into
# the output folder, and runs the Bit-4-style
# round-trip on the flat GLB. The builder's home comes
# from settings (humanoid_home), never hard-coded.
def Run_Glb_Builder(Params, Settings, Log, Step_Name):
    Parts_Folder = Params.get("parts_folder")
    Rig_Path = Params.get("rig_json")
    if not Parts_Folder:
        raise ValueError(Step_Name + ": missing param parts_folder")
    if not Rig_Path:
        raise ValueError(Step_Name + ": missing param rig_json")
    if not os.path.isdir(Parts_Folder):
        raise ValueError(
            Step_Name + ": parts folder not found: " + str(Parts_Folder))
    if not os.path.isfile(Rig_Path):
        raise ValueError(
            Step_Name + ": rig JSON not found: " + str(Rig_Path))
    Out_Folder = Params.get("output_folder") or os.path.join(
        Settings["output_folder"], "Rig_V1")
    os.makedirs(Out_Folder, exist_ok=True)
    Builder = os.path.join(Settings["humanoid_home"],
                           "Build_Redrawn_GLB_V2.PY")
    if not os.path.isfile(Builder):
        raise ValueError(
            Step_Name + ": GLB builder not found: " + Builder)
    Log("%s settings: humanoid_home=%s builder=%s python=%s"
        % (Step_Name, Settings["humanoid_home"], Builder,
           sys.executable))
    Log("%s inputs: parts_folder=%s rig_json=%s output_folder=%s"
        % (Step_Name, Parts_Folder, Rig_Path, Out_Folder))
    Log(Step_Name + ": the builder always emits both the flat "
        "paper GLB and the 3D GLB; this step returns its own kind")
    Proc = Run_Captured(
        [sys.executable, Builder, Parts_Folder, Rig_Path, Out_Folder],
        Log, Timeout=600)
    if Proc.returncode != 0:
        raise RuntimeError(
            "%s: GLB builder exited %d" % (Step_Name, Proc.returncode))
    Report_Path = os.path.join(
        Out_Folder, "Build_Redrawn_GLB_Report_V1.JSON")
    if not os.path.isfile(Report_Path):
        raise RuntimeError(
            Step_Name + ": builder wrote no report at " + Report_Path)
    Report = json.load(open(Report_Path))
    Flat_Path = os.path.join(Out_Folder, "Redrawn_Paper_Doll_V1.GLB")
    Path_3D = os.path.join(Out_Folder, "Redrawn_Paper_Doll_3D_V1.GLB")
    for Glb_Path in (Flat_Path, Path_3D):
        if not os.path.isfile(Glb_Path) or os.path.getsize(Glb_Path) == 0:
            raise RuntimeError(
                Step_Name + ": builder output missing or empty: "
                + Glb_Path)
        Head = open(Glb_Path, "rb").read(4)
        if Head != b"glTF":
            raise RuntimeError(
                Step_Name + ": builder output is not a GLB: " + Glb_Path)
    Flat_Bytes = os.path.getsize(Flat_Path)
    Bytes_3D = os.path.getsize(Path_3D)
    Trip = Report.get("round_trip", {})
    Round_Trip = {
        "pass": bool(Trip.get("pass")),
        "nodes_before": Trip.get("node_count_before"),
        "nodes_after": Trip.get("node_count_after"),
        "bin_identical": bool(Trip.get("bin_chunk_byte_identical"))}
    Log("%s builder report: pass=%s flat_nodes=%s three_d_nodes=%s"
        % (Step_Name, Report.get("pass"),
           Report.get("flat", {}).get("nodes"),
           Report.get("three_d", {}).get("nodes")))
    Log("%s results: flat_glb=%s %d bytes; glb_3d=%s %d bytes"
        % (Step_Name, Flat_Path, Flat_Bytes, Path_3D, Bytes_3D))
    Log("%s round-trip: pass=%s nodes %s -> %s, bin identical %s"
        % (Step_Name, Round_Trip["pass"], Round_Trip["nodes_before"],
           Round_Trip["nodes_after"], Round_Trip["bin_identical"]))
    return {"flat_glb": Flat_Path, "flat_bytes": Flat_Bytes,
            "glb_3d": Path_3D, "glb_3d_bytes": Bytes_3D,
            "report_json": Report_Path,
            "builder_pass": bool(Report.get("pass")),
            "flat_pass": bool(Report.get("flat", {}).get("pass")),
            "three_d_pass": bool(Report.get("three_d", {}).get("pass")),
            "nodes": Report.get("flat", {}).get("nodes"),
            "round_trip": Round_Trip}


# rig: the Ai "Rig it" step - run the builder and
# return both GLBs plus the round-trip verdict from
# the builder's own report. A rig whose census or
# round-trip failed is a failed step, not a done one.
def Step_Rig(Params, Settings, Log):
    Outputs = Run_Glb_Builder(Params, Settings, Log, "rig")
    if not Outputs["builder_pass"] or not Outputs["round_trip"]["pass"]:
        raise RuntimeError(
            "rig: builder report did not pass (builder_pass=%s, "
            "round_trip pass=%s)"
            % (Outputs["builder_pass"], Outputs["round_trip"]["pass"]))
    Log("rig done: rigged model proven by the round-trip")
    return Outputs


# make_paper: return the flat paper GLB path and size.
# The builder always emits both GLBs; the flat one is
# this step's product, as the log above states.
def Step_Make_Paper(Params, Settings, Log):
    Outputs = Run_Glb_Builder(Params, Settings, Log, "make_paper")
    if not Outputs["flat_pass"]:
        raise RuntimeError("make_paper: builder flat census did not pass")
    Outputs["glb"] = Outputs["flat_glb"]
    Outputs["bytes"] = Outputs["flat_bytes"]
    Log("make_paper done: flat paper GLB %s %d bytes "
        "(the builder also emitted the 3D GLB)"
        % (Outputs["glb"], Outputs["bytes"]))
    return Outputs


# make_3d: return the assembled 3D GLB path and size.
# The builder always emits both GLBs; the 3D one is
# this step's product, as the log above states.
def Step_Make_3D(Params, Settings, Log):
    Outputs = Run_Glb_Builder(Params, Settings, Log, "make_3d")
    if not Outputs["three_d_pass"]:
        raise RuntimeError("make_3d: builder 3D census did not pass")
    Outputs["glb"] = Outputs["glb_3d"]
    Outputs["bytes"] = Outputs["glb_3d_bytes"]
    Log("make_3d done: 3D GLB %s %d bytes "
        "(the builder also emitted the flat paper GLB)"
        % (Outputs["glb"], Outputs["bytes"]))
    return Outputs


STEPS = {
    "detect_views": Step_Detect_Views,
    "make3d": Step_Make3d,
    "snapshots": Step_Snapshots,
    "slice_layers": Step_Slice_Layers,
    "movement_reference": Step_Movement_Reference,
    "redraw": Step_Redraw,
    "model_up": Step_Model_Up,
    "model_down": Step_Model_Down,
    "rig": Step_Rig,
    "make_paper": Step_Make_Paper,
    "make_3d": Step_Make_3D,
}
