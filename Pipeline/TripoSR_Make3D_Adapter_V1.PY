# TripoSR_Make3D_Adapter_V1.PY
# Source: copied literally from Man_3D_Bit2_Run_V1.PY
# (Original work - Kevin, 2026-11-16; the proven TripoSR
# inference program), stages A-E only.
# The lane's inference flow mirrors TripoSR's own run.py
# (VAST-AI Research / Tripo AI, MIT - its LICENSE ships beside
# its code): same preprocessing calls from tsr.utils, same
# from_pretrained / forward / extract_mesh calls, vertex
# colours instead of texture baking.
# Purpose: the pipeline's general make3d entry point -
# the script Pipeline_Steps_V1.PY Step_Make3d invokes as
# [cuda_python, tool_home_3d/make3d_script] + make3d_args.
# Usage: TripoSR_Make3D_Adapter_V1.PY <image path> <output glb path>
# Only variables and names change from the lane program: the
# image and the output come from argv instead of the lane's
# fixed front picture and work folder, and progress goes to
# stdout instead of the lane's log file. The lane's
# man-specific proof stages (mesh statistics, cross-sections,
# orbit renders, mesh projections, send-back copies) are cut
# whole - the inference unit only.
# Dependency set (the lane's proven TripoSR venv, built by
# Man_3D_Bit1_Setup_V1.PY stage 5): torch, numpy==1.26.4,
# omegaconf, einops, Pillow, rembg, trimesh>=4.0.5, imageio,
# plus huggingface_hub and the tsr package from the TripoSR
# code home. The extracted mesh is a trimesh mesh (TripoSR's
# extract_mesh returns trimesh meshes), so the lane's own
# Mesh.export call writes the GLB by the output extension,
# vertex colours carried as the lane extracts them.
# Source: Original work - Kevin - the argv handling, the stdout
# progress lines, the output-folder creation, and the GLB
# magic check below are new glue written for this adapter.
import os
import shutil
import sys
import time
import traceback

# The TripoSR home comes from the TRIPOSR_HOME environment
# variable; the code home and the weights path follow from
# it. No machine-specific default is built in: when
# TRIPOSR_HOME is not set, this adapter stops at once with
# a plain line naming what is missing.
# Source: Man_3D_Bit2_Run_V1.PY lines 22-25 (Original
# work - Kevin, 2026-11-16), rewritten so the home comes
# from a setting only; the fail-fast check below is new
# glue for this adapter. Original work - Kevin.
TripoSR_Home = os.environ.get("TRIPOSR_HOME")
if not TripoSR_Home:
    print("make3d: TRIPOSR_HOME is not set - set it to the "
          "folder holding the TripoSR code and weights",
          flush=True)
    sys.exit(2)
Code_Home = os.path.join(TripoSR_Home, "TripoSR-main")
Model_Home = os.path.join(TripoSR_Home, "Model")
Weights_Source = os.path.join(TripoSR_Home, "Model_V1.CKPT")

# Source: Original work - Kevin - the output's parent folder is
# created here so the pipeline's output path always lands.
os.makedirs(Model_Home, exist_ok=True)


# Writes one line to stdout and flushes it at once.
# Source: Man_3D_Bit2_Run_V1.PY lines 37-40 (Original
# work - Kevin) - the lane's Log, retargeted from its log file to
# stdout for this adapter, as the pipeline step streams the
# child's stdout into the job log.
def Log(Line):
    print(str(Line), flush=True)


# Source: Original work - Kevin - argv is this adapter's only
# interface: exactly an image path and an output GLB path.
if len(sys.argv) != 3:
    print("usage: TripoSR_Make3D_Adapter_V1.PY "
          "<image path> <output glb path>", flush=True)
    sys.exit(2)
Image_Path = sys.argv[1]
Output_Path = sys.argv[2]
Output_Folder = os.path.dirname(os.path.abspath(Output_Path))
os.makedirs(Output_Folder, exist_ok=True)

Stage = "start"
Started = time.time()
try:
    Log("MAKE3D START " + time.strftime("%Y-%m-%d %H:%M:%S"))
    Log("make3d image=" + Image_Path + " output=" + Output_Path)
    sys.path.insert(0, Code_Home)

    # Stage A: stage the local model folder run.py's call expects -
    # config.yaml from the model's own Hugging Face repo (a few KB)
    # and the weights already stored locally, under their working
    # name.
    # Source: Man_3D_Bit2_Run_V1.PY lines 59-74, copied literally
    # (TripoSR, VAST-AI Research / Tripo AI, MIT).
    Stage = "A model folder"
    Config_Path = os.path.join(Model_Home, "config.yaml")
    if not os.path.exists(Config_Path):
        from huggingface_hub import hf_hub_download
        hf_hub_download(repo_id="stabilityai/TripoSR",
                        filename="config.yaml", local_dir=Model_Home)
        Log("config.yaml downloaded from stabilityai/TripoSR")
    Ckpt_Path = os.path.join(Model_Home, "model.ckpt")
    if not os.path.exists(Ckpt_Path) or \
            os.path.getsize(Ckpt_Path) != os.path.getsize(Weights_Source):
        shutil.copy2(Weights_Source, Ckpt_Path)
        Log("model.ckpt copied from Model_V1.CKPT")
    Log("STAGE A DONE: " + str(sorted(os.listdir(Model_Home))))

    # Stage B: load the model onto the GPU, as run.py does.
    # Source: Man_3D_Bit2_Run_V1.PY lines 76-87, copied literally
    # (TripoSR, VAST-AI Research / Tripo AI, MIT).
    Stage = "B model load"
    import torch
    from tsr.system import TSR
    Model = TSR.from_pretrained(Model_Home, config_name="config.yaml",
                                weight_name="model.ckpt")
    Model.renderer.set_chunk_size(8192)
    Device = "cuda:0" if torch.cuda.is_available() else "cpu"
    Model.to(Device)
    Model.eval()
    Log("STAGE B DONE: model on " + Device + ", VRAM MiB " +
        str(round(torch.cuda.memory_allocated() / 1048576)))

    # Stage C: preprocess the front picture, run.py's exact calls.
    # Source: Man_3D_Bit2_Run_V1.PY lines 89-104, copied literally
    # (TripoSR, VAST-AI Research / Tripo AI, MIT) - only the
    # lane's fixed Front_Image name becomes this adapter's
    # Image_Path from argv, and the lane's input-copy save and
    # send-back lines are cut with the proof stages.
    Stage = "C preprocess"
    import numpy as np
    import rembg
    from PIL import Image
    from tsr.utils import remove_background, resize_foreground
    Session = rembg.new_session()
    Image_In = remove_background(Image.open(Image_Path), Session)
    Image_In = resize_foreground(Image_In, 0.85)
    Arr = np.array(Image_In).astype(np.float32) / 255.0
    Arr = Arr[:, :, :3] * Arr[:, :, 3:4] + (1 - Arr[:, :, 3:4]) * 0.5
    Image_In = Image.fromarray((Arr * 255.0).astype(np.uint8))
    Log("STAGE C DONE: processed input " + str(Image_In.size))

    # Stage D: the inference itself.
    # Source: Man_3D_Bit2_Run_V1.PY lines 106-111, copied
    # literally (TripoSR, VAST-AI Research / Tripo AI, MIT).
    Stage = "D inference"
    with torch.no_grad():
        Scene_Codes = Model([Image_In], device=Device)
    Log("STAGE D DONE: scene codes " + str(tuple(Scene_Codes.shape)) +
        ", VRAM MiB " + str(round(torch.cuda.memory_allocated() / 1048576)))

    # Stage E: extract the mesh with vertex colours, run.py's call.
    # Source: Man_3D_Bit2_Run_V1.PY lines 113-133, copied
    # literally (TripoSR, VAST-AI Research / Tripo AI, MIT) -
    # the lane exported its mesh to a fixed OBJ path with the
    # same Mesh.export call; here the destination is this
    # adapter's Output_Path from argv, so the trimesh export
    # writes a GLB, and the lane's NPZ proof save is cut.
    Stage = "E extract mesh"
    Meshes = Model.extract_mesh(Scene_Codes, True, resolution=256)
    Mesh = Meshes[0]
    Mesh.export(Output_Path)
    Verts = np.asarray(Mesh.vertices, dtype=np.float32)
    Faces = np.asarray(Mesh.faces, dtype=np.int64)
    Colors = None
    try:
        Raw_Colors = np.asarray(Mesh.visual.vertex_colors)
        if Raw_Colors.shape[0] == Verts.shape[0]:
            Colors = (Raw_Colors[:, :3].astype(np.float32) / 255.0)
    except Exception:
        Colors = None
    Log("STAGE E DONE: mesh exported, GLB bytes " +
        str(os.path.getsize(Output_Path)) + ", vertex colors " +
        str(Colors is not None))

    # Source: Original work - Kevin - prove the export is a GLB
    # before reporting success; the pipeline step checks the
    # same magic, and failing here names the stage at fault.
    with open(Output_Path, "rb") as Handle:
        Head = Handle.read(4)
    if Head != b"glTF" or os.path.getsize(Output_Path) == 0:
        raise RuntimeError("exported file is not a GLB: " +
                           Output_Path)
    Log("MAKE3D_DONE in " + str(int(time.time() - Started)) +
        " seconds")
except Exception:
    Log("MAKE3D_FAIL stage " + Stage)
    traceback.print_exc()
    sys.exit(1)
sys.exit(0)
