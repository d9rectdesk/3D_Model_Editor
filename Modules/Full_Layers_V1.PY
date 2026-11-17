# Full_Layers_V1.PY
# Standalone full-layer completion for the Model Editor.
# Solomon's rule (2026-11-16): "the layers are full" -
# every layer is a complete part, drawn whole underneath
# the parts above it, so when a part moves, the layer
# beneath shows finished drawing and the background
# never shows. His refinement the same day: the paper
# data comes from the 2D views themselves; a 3D build
# is NOT a required step. This program takes a folder
# of part layers (transparent PNGs on one shared
# canvas) plus a rig file, completes every part from
# the 2D material alone, and proves the result with
# its own sweep test. It runs end to end with no 3D
# input present.
# Completion, per joint: the parent part grows, inside
# the figure's own resting silhouette, under the whole
# resting footprint of the moving subtree, so whatever
# the movement uncovers was already drawn beneath it;
# the child part grows a complete disc of its own
# substance centred on the pin, the estate's circle
# rule, clipped to the same silhouette. Fill colour is
# the part's own local tone at the joint. Nothing is
# drawn outside the resting silhouette (plus a 3 px
# resampling apron, the estate's proven margin), so no
# part balloons: the estate's unclipped circle fill
# grew Duke's torso to 3,623,186 px on a 2048 canvas
# (measured 2026-11-16), and Solomon's own PSD layers
# extend only 8 to 35 percent of a part's length past
# each joint.
# The sweep test, built in: every joint turns through
# its full rig range in 5-degree steps while the rest
# of the figure stands at rest, and the program counts
# background pixels revealed inside the resting
# silhouette within the joint's counting zone (joint
# radius plus 300 px around the pin, the estate
# battery's own reach). A layer set passes only at
# zero, at every joint.
# Output is a NEW folder of completed part layers
# plus a completion report; inputs are never edited
# in place (crew output rule).
# Dependencies: Python 3, NumPy, Pillow, SciPy.
# Source: Duke, original work, except the blocks
# below, which name their sources.
import argparse
import hashlib
import json
import math
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

# The shared canvas size, set from the loaded parts.
# The estate's programs carry it the same way.
Canvas = 0


# A 3x3 matrix turning canvas points about one pin.
# Source: Rot_About in Complete_And_Buffer_V1.PY
# (Duke), copied from Gap_Check_V1.PY (Kevin),
# unchanged.
def Rot_About(Pin, Deg):
    T = np.deg2rad(Deg)
    C, S = np.cos(T), np.sin(T)
    M = np.array([[C, -S, Pin[0] - C * Pin[0] + S * Pin[1]],
                  [S, C, Pin[1] - S * Pin[0] - C * Pin[1]],
                  [0, 0, 1]], float)
    return M


# Warp one full-canvas image by a world matrix,
# returning only a window of the result. PIL affine
# takes the inverse map, from output to input, so the
# window's origin is folded into the map and the
# source is sampled wherever the warp reaches.
# Source: Warp_Alpha in Complete_And_Buffer_V1.PY
# (Duke), Gap_Check_V1.PY's Warp (Kevin), carried to
# a windowed output in the manner of
# Run_Redraw_Battery_V2.PY's windowed warps (Kevin).
def Warp_Window(Img, M, X0, Y0, Width, Height):
    Inv = np.linalg.inv(M)
    B = Inv @ np.array([[1, 0, X0], [0, 1, Y0], [0, 0, 1]], float)
    return Img.transform((Width, Height), Image.AFFINE,
                         (B[0, 0], B[0, 1], B[0, 2],
                          B[1, 0], B[1, 1], B[1, 2]),
                         resample=Image.BILINEAR)


# Forward kinematics down the parent chain, and every
# joint pin carried into the posed frame.
# Source: World_And_Pins in Complete_And_Buffer_V1.PY
# (Duke), unchanged. Its composition rule is
# Gap_Check_V1.PY's Render rule (Kevin) and its posed
# pins follow Gap_Diagnose_V1.PY's World_Pins (Kevin).
def World_And_Pins(Rig, Angles):
    World = {}
    Pending = list(Rig)
    while Pending:
        Ready = [P for P in Pending
                 if Rig[P][1] is None or Rig[P][1] in World]
        if not Ready:
            raise ValueError("rig parent chain does not settle")
        for Part in Ready:
            Pin, Parent = Rig[Part]
            Own = Rot_About(Pin, Angles.get(Part, 0.0))
            if Parent is None:
                World[Part] = Own
            else:
                World[Part] = World[Parent] @ Own
            Pending.remove(Part)
    Pins = {}
    for Part, (Pin, Parent) in Rig.items():
        if Parent is None:
            Pins[Part] = np.array(Pin, float)
        else:
            P = np.array([Pin[0], Pin[1], 1.0])
            Pins[Part] = (World[Parent] @ P)[:2]
    return World, Pins


# The descendants of one part, itself included: the
# set of parts whose world moves when that part's
# joint turns.
# Source: Subtree in Pose_Census_V1.PY (Kevin), with
# the children table built by the caller.
def Subtree(Root, Children_Of):
    Out = []
    Stack = [Root]
    while Stack:
        Part = Stack.pop()
        Out.append(Part)
        Stack.extend(Children_Of.get(Part, []))
    return Out


# A filled disc structuring element of a given
# radius, for the silhouette aprons.
# Source: the Disc_18 construction in
# Pose_Audit_V1.PY (Kevin), at caller radii.
def Disc_Structure(Radius):
    Size = 2 * Radius + 1
    Disc = np.zeros((Size, Size), dtype=bool)
    for Y in range(Size):
        for X in range(Size):
            Disc[Y, X] = (X - Radius) ** 2 + (Y - Radius) ** 2 <= Radius ** 2
    return Disc


# Grow a mask by a filled disc of the given radius.
def Dilate(Mask, Radius):
    return ndimage.binary_dilation(Mask, structure=Disc_Structure(Radius))


# Fill every Want pixel of one part with the part's own
# local tone, and add the pixels to its mask. The arrays
# are one window of the part's canvas, so the tone stays
# local, the proven pad pattern. The tone is the median
# colour of the part's interior pixels in the window; the
# interior test is Complete_Disc's
# (Separate_Humanoid_Back_V1.PY, Duke) - fully opaque,
# neither outline-dark nor edge-pale. Source_Restrict,
# when given, replaces that test (the pelvis takes cloth
# only, as Extend_Shorts does). Returns the pixels added.
# Source: Fill_Flat in Complete_And_Buffer_V1.PY
# (Kevin), unchanged.
def Fill_Flat(Canvas_Arr, Mask, Want, Source_Restrict=None):
    if not Want.any():
        return 0
    Have = Mask.copy()
    if not Have.any():
        return 0
    Window = Canvas_Arr.astype(np.int32)
    Lum_W = Window[:, :, :3].mean(axis=2)
    # Interior sources only: fully opaque, neither
    # outline-dark nor edge-pale.
    Spread_W = Window[:, :, :3].max(axis=2) - Window[:, :, :3].min(axis=2)
    Interior = Have & (Window[:, :, 3] >= 250) & (Lum_W >= 110) & \
        (Lum_W <= 232) & (Spread_W > 24)
    if Source_Restrict is not None:
        Interior = Have & Source_Restrict(Window, Lum_W)
    if Interior.sum() < 24:
        Interior = Have
    Source = Window[Interior, :3].astype(np.float64)
    Tone = np.median(Source, axis=0).astype(np.uint8)
    Wy, Wx = np.where(Want)
    Canvas_Arr[Wy, Wx, :3] = Tone
    Canvas_Arr[Wy, Wx, 3] = 255
    Mask[Wy, Wx] = True
    return int(len(Wy))


# A source test that keeps only a part's fully opaque
# pixels within a radius of the joint pin, so a large
# fill window still tones from the joint's own
# neighbourhood.
# Source: Duke, original work, in the pattern of
# Cloth_Sources in Complete_And_Buffer_V1.PY (Duke).
def Near_Pin_Sources(X0, Y0, Pin, Radius):
    def Restrict(Window, Lum_W):
        H, W = Lum_W.shape
        YY, XX = np.mgrid[Y0:Y0 + H, X0:X0 + W]
        Near = (XX - Pin[0]) ** 2 + (YY - Pin[1]) ** 2 <= Radius ** 2
        return (Window[:, :, 3] >= 250) & Near
    return Restrict


# Fill one part's Want region, a full-canvas boolean,
# with the part's own local tone at the pin. The work
# happens in the Want region's window, widened so the
# tone search has the part's substance around it.
# Source: adapted from Fill_Disc in
# Complete_And_Buffer_V1.PY (Duke): the window and pad
# pattern are its own; the Want region is the caller's
# silhouette-clipped region instead of a bare disc,
# for the reason the header records.
def Fill_Region(Canvas_Arr, Mask, Want, Pin, Source_Radius):
    if not Want.any():
        return 0
    Wys, Wxs = np.where(Want)
    Pad = 70
    Y0 = max(0, int(Wys.min()) - Pad); Y1 = min(Canvas, int(Wys.max()) + Pad + 1)
    X0 = max(0, int(Wxs.min()) - Pad); X1 = min(Canvas, int(Wxs.max()) + Pad + 1)
    Restrict = Near_Pin_Sources(X0, Y0, Pin, Source_Radius)
    return Fill_Flat(Canvas_Arr[Y0:Y1, X0:X1], Mask[Y0:Y1, X0:X1],
                     Want[Y0:Y1, X0:X1], Source_Restrict=Restrict)


# A boolean disc on the full canvas, as a window
# slice: returns (Y0, Y1, X0, X1, Disc) with Disc the
# disc's mask inside that window.
def Disc_Window(Centre, Radius):
    Cx, Cy = float(Centre[0]), float(Centre[1])
    Y0 = max(0, int(math.floor(Cy - Radius)))
    Y1 = min(Canvas, int(math.ceil(Cy + Radius)) + 1)
    X0 = max(0, int(math.floor(Cx - Radius)))
    X1 = min(Canvas, int(math.ceil(Cx + Radius)) + 1)
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    Disc = (XX - Cx) ** 2 + (YY - Cy) ** 2 <= Radius ** 2
    return Y0, Y1, X0, X1, Disc


# Default movement ranges for a joint the rig does not
# range, matched by name fragment in order. The values
# are the anatomical limits of the estate battery.
# Source: the Section 2 limits tables in
# Run_Redraw_Battery_V2.PY (Kevin), copied from
# Pose_Fix_List_V1.TXT Section 2, with the tail's
# range from Paper_Duke_Rig_V1.JSON (Kevin).
Default_Ranges = [
    ("eyes", (0, 0)), ("eye", (0, 0)),
    ("head", (-35, 35)), ("neck", (-35, 35)),
    ("arm_upper", (-170, 55)), ("arm_fore", (-5, 145)),
    ("shoulder", (-170, 55)), ("elbow", (-5, 145)),
    ("wrist", (-70, 80)), ("hand", (-70, 80)),
    ("arm", (-170, 55)),
    ("thigh", (-45, 30)), ("hip", (-45, 30)),
    ("shin", (-5, 135)), ("knee", (-5, 135)),
    ("foot_leg", (-50, 20)), ("foot", (-50, 20)),
    ("ankle", (-50, 20)),
    ("torso_middle", (-20, 20)), ("torso_top", (-20, 20)),
    ("waist", (-20, 20)), ("spine", (-20, 20)),
    ("tail", (-67, 67)), ("wing", (-70, 70)),
    ("ear", (-35, 35)),
]


# The default range for one joint or part name.
def Default_Range(Name):
    Low = Name.lower()
    for Frag, Range in Default_Ranges:
        if Frag in Low:
            return Range
    return (-45, 45)


# A part's short name: Part_Arm_Upper_V1 reads Arm_Upper.
def Short_Name(Part):
    Name = Part
    if Name.startswith("Part_"):
        Name = Name[5:]
    if Name.endswith("_V1"):
        Name = Name[:-3]
    return Name


# Bring one rig joint record to the module's shape,
# whichever key spelling the rig uses.
def Normalize_Joint(Rec, Parts):
    Child = Rec["child"]
    Min = Rec.get("angle_min_deg", Rec.get("min_deg"))
    Max = Rec.get("angle_max_deg", Rec.get("max_deg"))
    if Min is None and Child in Parts:
        Min = Parts[Child].get("angle_min_deg")
        Max = Parts[Child].get("angle_max_deg")
    if Min is None or Max is None:
        Min, Max = Default_Range(Rec.get("name", Child))
    return {
        "name": Rec.get("name", Short_Name(Child)),
        "pin": [float(Rec["pin"][0]), float(Rec["pin"][1])],
        "radius": float(Rec.get("radius", 60)),
        "parent": Rec["parent"],
        "child": Child,
        "min_deg": float(Min),
        "max_deg": float(Max),
        "disc_radius": (float(Rec["disc_radius"])
                        if Rec.get("disc_radius") else None),
    }


# Derive the joints of a rig that lists none: every
# part that hangs from a parent turns about its own
# pin, and that turning is its joint.
def Derive_Joints(Parts, Order):
    Joints = []
    for Name in Order:
        Part = Parts[Name]
        if Part["parent"] is None or Part["pin"] is None:
            continue
        Min, Max = Default_Range(Name)
        Joints.append({
            "name": Short_Name(Name),
            "pin": [float(Part["pin"][0]), float(Part["pin"][1])],
            "radius": 60.0,
            "parent": Part["parent"],
            "child": Name,
            "min_deg": float(Min),
            "max_deg": float(Max),
            "disc_radius": None,
        })
    return Joints


# Load a rig file in either estate form: the multi-
# view form (Redrawn_Rig_V1.JSON) whose views carry
# parts and joints, or the flat form
# (Rig_Points_Humanoid_Side_V1.JSON) whose parts sit
# at the top level and whose joints are derived.
# Returns one job per view.
def Load_Rig(Rig_Path):
    with open(Rig_Path) as Handle:
        Data = json.load(Handle)
    Jobs = []

    def Make_Job(View, Raw):
        Parts = {}
        for Name, Rec in Raw["parts"].items():
            Pin = Rec.get("pin")
            Parts[Name] = {
                "pin": ([float(Pin[0]), float(Pin[1])]
                        if Pin is not None else None),
                "parent": Rec.get("parent"),
                "file": Rec.get("file"),
                "angle_min_deg": Rec.get("angle_min_deg"),
                "angle_max_deg": Rec.get("angle_max_deg"),
            }
        Order = Raw.get("layer_order_back_to_front") or list(Parts)
        if Raw.get("joints"):
            Joints = [Normalize_Joint(Rec, Parts)
                      for Rec in Raw["joints"]]
        else:
            Joints = Derive_Joints(Parts, Order)
        Jobs.append({"view": View, "parts": Parts,
                     "order": Order, "joints": Joints})

    if "views" in Data:
        for View, Raw in Data["views"].items():
            Make_Job(View, Raw)
    else:
        Make_Job("", Data)
    return Jobs


# Find one part's PNG: the view subfolder first, then
# the parts folder itself, then the rig's own file
# field, read the way Complete_Duke_Circles_V1.PY
# reads it - against the workspace root two levels
# above the rig file.
# Source: the file resolution of Complete_View in
# Complete_Duke_Circles_V1.PY (Duke), widened with
# the two folder candidates.
def Part_Path(Job, Name, Parts_Root, Rig_Path):
    Candidates = []
    if Job["view"]:
        Candidates.append(os.path.join(
            Parts_Root, Job["view"], Name + ".PNG"))
    Candidates.append(os.path.join(Parts_Root, Name + ".PNG"))
    Filed = Job["parts"][Name].get("file")
    if Filed:
        Candidates.append(Filed)
        Workspace = os.path.dirname(os.path.dirname(
            os.path.abspath(Rig_Path)))
        Candidates.append(os.path.join(Workspace, Filed))
        Candidates.append(os.path.join(
            os.path.dirname(os.path.abspath(Rig_Path)), Filed))
    for Path in Candidates:
        if os.path.isfile(Path):
            return Path
    raise FileNotFoundError("part file not found: " + Name)


# Load one view's parts as RGBA canvases and alpha
# images, and set the shared canvas size.
def Load_Parts(Job, Parts_Root, Rig_Path):
    global Canvas
    Canvases = {}
    for Name in Job["order"]:
        Path = Part_Path(Job, Name, Parts_Root, Rig_Path)
        Arr = np.array(Image.open(Path).convert("RGBA"))
        if Canvas == 0:
            Canvas = Arr.shape[0]
        if Arr.shape[0] != Canvas or Arr.shape[1] != Canvas:
            raise ValueError("part is not on the shared canvas: " + Name)
        Canvases[Name] = Arr
    return Canvases


# One part set's coverage masks, at the battery's
# threshold: alpha over 8 counts as drawn.
# Source: the mask threshold of Complete_View in
# Complete_Duke_Circles_V1.PY (Duke).
def Masks_Of(Canvases):
    return {Name: Arr[:, :, 3] > 8 for Name, Arr in Canvases.items()}


# The union of a mask set: the figure's silhouette.
def Union_Of(Masks, Order):
    Union = np.zeros((Canvas, Canvas), dtype=bool)
    for Name in Order:
        Union |= Masks[Name]
    return Union


# The children table of a view's parts.
def Children_Of(Job):
    Table = {}
    for Name, Part in Job["parts"].items():
        Table.setdefault(Part["parent"], []).append(Name)
    return Table


# How deep one part hangs in the rig tree: the root
# is depth 0, its children depth 1, and so on.
def Part_Depth(Job, Name):
    Depth = 0
    Part = Job["parts"][Name]
    while Part["parent"] is not None:
        Depth += 1
        Part = Job["parts"][Part["parent"]]
    return Depth


# The radius of one joint's child disc: the rig's own
# disc radius when the rig carries one (the redrawn
# rig's radii were seeded from the reveal bitmaps);
# else the parts' own local thickness at the pin -
# the distance from the pin to the nearest edge of
# each part's drawing, the larger of the two sides -
# grown by half and the 3 px resampling margin. A
# disc sized from the joint's exposure radius instead
# (the audit's radius, up to 402 px on Duke) ballooned
# Duke's wing by 995,002 added pixels on one part
# (measured 2026-11-16); the thickness at the pin is
# what a disc has to round out, and no more.
# Source: the disc radius practice of
# Redraw_Circles_V1.PY (Duke) - the rig's disc_radius
# first, a computed radius behind it - with the
# computed form replaced as the comment records.
def Child_Disc_Radius(Joint, Disc_Scale, Masks):
    if Joint["disc_radius"]:
        return Joint["disc_radius"] * Disc_Scale
    Base = 0.0
    for Name in (Joint["parent"], Joint["child"]):
        Dist = ndimage.distance_transform_edt(Masks[Name])
        X = min(Canvas - 1, max(0, int(round(Joint["pin"][0]))))
        Y = min(Canvas - 1, max(0, int(round(Joint["pin"][1]))))
        Base = max(Base, float(Dist[Y, X]))
    if Base < 8:
        Base = Joint["radius"]
    return (Base * 1.5 + 3) * Disc_Scale


# Grow the child side of one joint on a working set,
# in place: a complete disc of the child's own
# substance centred on the pin, clipped to the
# resting silhouette's apron and to the joint's
# counting zone. Returns the pixels added and the
# disc radius used.
def Fill_Child_Side(Job, Work, Masks, Silhouette_D, Joint, Disc_Scale):
    Pin = Joint["pin"]
    Reach = Joint["radius"] + 300
    Y0, Y1, X0, X1, Zone = Disc_Window(Pin, Reach)
    R_Child = Child_Disc_Radius(Joint, Disc_Scale, Masks)
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    Child_Disc = (XX - Pin[0]) ** 2 + (YY - Pin[1]) ** 2 <= R_Child ** 2
    Child = Joint["child"]
    Want = np.zeros((Canvas, Canvas), dtype=bool)
    Want[Y0:Y1, X0:X1] = Child_Disc & Silhouette_D[Y0:Y1, X0:X1] & \
        Zone & ~Masks[Child][Y0:Y1, X0:X1]
    Added = Fill_Region(Work[Child], Masks[Child], Want, Pin,
                        Joint["radius"] + 60)
    return Added, R_Child


# Grow the parent side of one joint on a working set,
# in place: the parent grows under the moving
# subtree's whole resting footprint, plus the child's
# disc, clipped to the resting silhouette's apron and
# to the joint's counting zone. The footprint is read
# from the masks as they stand when this runs, so the
# caller runs it only after every fill inside the
# subtree is final. Returns the pixels added.
def Fill_Parent_Side(Job, Work, Masks, Silhouette_D, Joint,
                     Margin, R_Child, Children):
    Pin = Joint["pin"]
    Reach = Joint["radius"] + 300
    Y0, Y1, X0, X1, Zone = Disc_Window(Pin, Reach)
    Sub = Subtree(Joint["child"], Children)
    Footprint = np.zeros((Canvas, Canvas), dtype=bool)
    for Name in Sub:
        Footprint |= Masks[Name]
    Footprint_D = Dilate(Footprint, Margin)
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    Child_Disc = (XX - Pin[0]) ** 2 + (YY - Pin[1]) ** 2 <= R_Child ** 2
    Parent = Joint["parent"]
    Want = np.zeros((Canvas, Canvas), dtype=bool)
    Want[Y0:Y1, X0:X1] = (Footprint_D[Y0:Y1, X0:X1] | Child_Disc) & \
        Silhouette_D[Y0:Y1, X0:X1] & Zone & ~Masks[Parent][Y0:Y1, X0:X1]
    return Fill_Region(Work[Parent], Masks[Parent], Want, Pin,
                       Joint["radius"] + 60)


# Complete every joint of one view on a working copy
# of its parts, in two passes. Pass one grows every
# child disc. Pass two grows the parent sides,
# deepest joints first, so a parent side is always
# measured against the final footprint of the subtree
# it must carry - a fill added inside a subtree after
# its parent side was measured would rotate with the
# subtree and uncover itself. The silhouette that
# bounds every fill is the input set's own, so
# completion can never widen the figure. Returns the
# working canvases, the pixels added per part, and
# the per-joint record.
def Complete_View(Job, Canvases, Margin=3):
    Work = {Name: Arr.copy() for Name, Arr in Canvases.items()}
    Masks = Masks_Of(Work)
    Silhouette_D = Dilate(Union_Of(Masks_Of(Canvases), Job["order"]), Margin)
    Children = Children_Of(Job)
    Added = {Name: 0 for Name in Job["order"]}
    Info = {}
    Active = [Joint for Joint in Job["joints"]
              if not (Joint["min_deg"] == 0 and Joint["max_deg"] == 0)]
    Radii = {}
    for Joint in Active:
        Added_C, R_Child = Fill_Child_Side(
            Job, Work, Masks, Silhouette_D, Joint, 1.0)
        Radii[Joint["name"]] = R_Child
        Added[Joint["child"]] += Added_C
        Info[Joint["name"]] = {
            "added_parent_px": 0,
            "added_child_px": Added_C,
            "child_disc_radius": R_Child,
            "growths": 0,
        }
    Deepest = sorted(Active,
                     key=lambda J: -Part_Depth(Job, J["child"]))
    for Joint in Deepest:
        Added_P = Fill_Parent_Side(
            Job, Work, Masks, Silhouette_D, Joint, Margin,
            Radii[Joint["name"]], Children)
        Added[Joint["parent"]] += Added_P
        Info[Joint["name"]]["added_parent_px"] = Added_P
    return Work, Masks, Added, Info, Silhouette_D, Children


# The stepped angles of one joint's sweep: the rig's
# own range in Step-degree steps, both ends exact,
# rest included when the range crosses it.
def Sweep_Angles(Joint, Step):
    Lo, Hi = Joint["min_deg"], Joint["max_deg"]
    Angles = [Lo]
    A = Lo + Step
    while A < Hi:
        Angles.append(A)
        A += Step
    if Hi != Lo:
        Angles.append(Hi)
    if Lo < 0 < Hi and 0 not in Angles:
        Angles.append(0)
    return sorted(set(Angles))


# Sweep one joint on one part set: the joint's subtree
# turns, everything else stands at rest, and the count
# is background revealed inside the resting silhouette
# within the joint's counting zone (its radius plus
# 300 px, the estate battery's reach, as in
# Pose_Audit_V1.PY's Trapped window). The composite is
# the full figure's, so parts pinned at the joint that
# do not move with the child stand on the static side,
# the correction Run_Redraw_Battery_V2.PY records.
# Returns the steps run and the worst count.
def Sweep_Joint(Job, Joint, Canvases, Masks, Silhouette,
                Rig, Alpha_Imgs, Children, Step):
    Angles = Sweep_Angles(Joint, Step)
    Pin = Joint["pin"]
    Reach = Joint["radius"] + 300
    Y0, Y1, X0, X1, _ = Disc_Window(Pin, Reach + 48)
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    Zone = (XX - Pin[0]) ** 2 + (YY - Pin[1]) ** 2 <= Reach ** 2
    Silhouette_W = Silhouette[Y0:Y1, X0:X1]
    Sub = set(Subtree(Joint["child"], Children))
    Static = np.zeros((Y1 - Y0, X1 - X0), dtype=bool)
    for Name in Job["order"]:
        if Name not in Sub:
            Static |= Masks[Name][Y0:Y1, X0:X1]
    Worst = 0
    for Deg in Angles:
        World, _ = World_And_Pins(Rig, {Joint["child"]: float(Deg)})
        Comp = Static.copy()
        for Name in Job["order"]:
            if Name in Sub:
                Warped = Warp_Window(Alpha_Imgs[Name], World[Name],
                                     X0, Y0, X1 - X0, Y1 - Y0)
                Comp |= np.asarray(Warped) > 8
        Revealed = Silhouette_W & ~Comp & Zone
        Worst = max(Worst, int(Revealed.sum()))
    return len(Angles), Worst


# Sweep every joint of one view on one part set.
# Returns the per-joint steps and worst counts.
def Sweep_View(Job, Canvases, Step):
    Masks = Masks_Of(Canvases)
    Silhouette = Union_Of(Masks, Job["order"])
    Rig = {}
    for Name, Part in Job["parts"].items():
        Pin = Part["pin"] if Part["pin"] is not None else (0.0, 0.0)
        Rig[Name] = (Pin, Part["parent"])
    Alpha_Imgs = {Name: Image.fromarray(Canvases[Name][:, :, 3])
                  for Name in Job["order"]}
    Children = Children_Of(Job)
    Results = {}
    for Joint in Job["joints"]:
        if Joint["min_deg"] == 0 and Joint["max_deg"] == 0:
            Results[Joint["name"]] = {"steps": 0, "worst": 0}
            continue
        Steps, Worst = Sweep_Joint(Job, Joint, Canvases, Masks,
                                   Silhouette, Rig, Alpha_Imgs,
                                   Children, Step)
        Results[Joint["name"]] = {"steps": Steps, "worst": Worst}
    return Results


# Measure one joint's overlap extents on a part set,
# the way Solomon's PSD reference was measured: along
# the limb axis through the pin, inside a corridor of
# the joint's radius, how far the parent part reaches
# past the joint toward the child, and how far the
# child part reaches back past it. Their sum is the
# overlap run.
# Source: Duke, original work; the measure follows
# the Overlap_Table of Rig_Points_Reference_V1.JSON
# (the estate's PSD measurement, 2026-11-16).
def Measure_Overlap(Job, Masks, Joint):
    Pin = np.array(Joint["pin"], float)
    Child = Joint["child"]
    Far = None
    for Other in Job["joints"]:
        if Other["parent"] == Child:
            Far = np.array(Other["pin"], float)
            break
    if Far is None:
        Ys, Xs = np.where(Masks[Child])
        if len(Xs) == 0:
            return None
        Far = np.array([Xs.mean(), Ys.mean()])
    Axis = Far - Pin
    Length = float(np.linalg.norm(Axis))
    if Length < 1:
        return None
    U = Axis / Length
    Corridor = max(Joint["radius"], 30.0)
    Y0, Y1, X0, X1, _ = Disc_Window(Pin, Length + Corridor + 20)

    def Reach_Past(Mask, Sign):
        Ys, Xs = np.where(Mask[Y0:Y1, X0:X1])
        if len(Xs) == 0:
            return None
        Px = Xs + X0 - Pin[0]
        Py = Ys + Y0 - Pin[1]
        T = Px * U[0] + Py * U[1]
        S = np.abs(Px * -U[1] + Py * U[0])
        Keep = S <= Corridor
        if not Keep.any():
            return None
        return float((Sign * T[Keep]).max())

    Prox = Reach_Past(Masks[Joint["parent"]], 1.0)
    Distal = Reach_Past(Masks[Child], -1.0)
    if Prox is None or Distal is None:
        return None
    return {
        "proximal_extends_past_joint_px": round(Prox, 1),
        "distal_extends_past_joint_px": round(Distal, 1),
        "overlap_run_px": round(Prox + Distal, 1),
    }


# Compare a completed view's overlap extents against
# Solomon's PSD reference measurements, joint by
# joint, scaled to this canvas. His figure is a
# stride pose and ours stands at rest, so the numbers
# are read as scale, not as a pass mark.
def Compare_Psd(Job, Masks, Psd_Path):
    with open(Psd_Path) as Handle:
        Psd = json.load(Handle)
    Scale = Canvas / float(Psd["canvas"]["width"])
    By_Name = {Joint["name"]: Joint for Joint in Job["joints"]}
    Rows = []
    for Rec in Psd.get("Overlap_Table", []):
        Name = Rec.get("estate_joint")
        if Name not in By_Name:
            continue
        Ours = Measure_Overlap(Job, Masks, By_Name[Name])
        if Ours is None:
            continue
        Rows.append({
            "joint": Name,
            "psd_proximal_px": round(
                Rec["proximal_extends_past_joint_px"] * Scale, 1),
            "ours_proximal_px": Ours["proximal_extends_past_joint_px"],
            "psd_distal_px": round(
                Rec["distal_extends_past_joint_px"] * Scale, 1),
            "ours_distal_px": Ours["distal_extends_past_joint_px"],
            "psd_run_px": round(Rec["overlap_run_px"] * Scale, 1),
            "ours_run_px": Ours["overlap_run_px"],
        })
    return Rows


# Which part shows at each pixel, by paint order: the
# rest-appearance drift measure between two part sets.
def Top_Map(Masks, Order):
    Top = np.full((Canvas, Canvas), -1, dtype=np.int32)
    for Index, Name in enumerate(Order):
        Top[Masks[Name]] = Index
    return Top


# Write one view's completed parts into the output
# folder. Untouched pixels keep their input values;
# only the completion's added pixels are new.
def Write_View(Job, Work, Out_Root):
    Folder = os.path.join(Out_Root, Job["view"]) if Job["view"] else Out_Root
    os.makedirs(Folder, exist_ok=True)
    for Name in Job["order"]:
        Image.fromarray(Work[Name], "RGBA").save(
            os.path.join(Folder, Name + ".PNG"))


# Run one view end to end: sweep the input, complete
# it, sweep the result, and grow any joint that still
# reveals (a wider apron and a larger child disc, the
# estate's own escalation: a joint whose circle still
# traps grows its radius and is redrawn -
# Redraw_Circles_V1.PY). Returns the view's report.
def Process_View(Job, Parts_Root, Rig_Path, Out_Root, Step, Psd_Path):
    global Canvas
    Canvas = 0
    Canvases = Load_Parts(Job, Parts_Root, Rig_Path)
    Before = Sweep_View(Job, Canvases, Step)
    Work, Masks, Added, Info, Silhouette_D, Children = \
        Complete_View(Job, Canvases)
    After = Sweep_View(Job, Work, Step)
    Base_Silhouette = Union_Of(Masks_Of(Canvases), Job["order"])
    for Round in (1, 2):
        Failing = [Joint for Joint in Job["joints"]
                   if After[Joint["name"]]["worst"] > 0]
        if not Failing:
            break
        Silhouette_D = Dilate(Base_Silhouette, 3 + 3 * Round)
        Masks = Masks_Of(Work)
        Deepest = sorted(Failing,
                         key=lambda J: -Part_Depth(Job, J["child"]))
        Radii = {}
        for Joint in Deepest:
            Added_C, R_Child = Fill_Child_Side(
                Job, Work, Masks, Silhouette_D, Joint, 1.5 ** Round)
            Radii[Joint["name"]] = R_Child
            Added[Joint["child"]] += Added_C
            Info[Joint["name"]]["added_child_px"] += Added_C
            Info[Joint["name"]]["child_disc_radius"] = R_Child
            Info[Joint["name"]]["growths"] = Round
        for Joint in Deepest:
            Added_P = Fill_Parent_Side(
                Job, Work, Masks, Silhouette_D, Joint,
                3 + 3 * Round, Radii[Joint["name"]], Children)
            Added[Joint["parent"]] += Added_P
            Info[Joint["name"]]["added_parent_px"] += Added_P
        After = Sweep_View(Job, Work, Step)
    Drift = int((Top_Map(Masks_Of(Canvases), Job["order"]) !=
                 Top_Map(Masks_Of(Work), Job["order"])).sum())
    Write_View(Job, Work, Out_Root)
    Joints_Report = {}
    Passed = True
    for Joint in Job["joints"]:
        Name = Joint["name"]
        Rec = {
            "steps": After[Name]["steps"],
            "worst_before": Before[Name]["worst"],
            "worst_after": After[Name]["worst"],
        }
        if Name in Info:
            Rec.update(Info[Name])
        Rec["pass"] = After[Name]["worst"] == 0
        Passed = Passed and Rec["pass"]
        Joints_Report[Name] = Rec
    Report = {
        "view": Job["view"] or "Main",
        "canvas": Canvas,
        "joints": Joints_Report,
        "added_per_part": Added,
        "rest_drift_px": Drift,
        "pass": Passed,
    }
    if Psd_Path:
        Report["psd_comparison"] = Compare_Psd(
            Job, Masks_Of(Work), Psd_Path)
    return Report


# The plain-words form of a run's report.
def Report_Text(Reports):
    Lines = ["Full Layers completion report", ""]
    for Report in Reports:
        Lines.append("View: %s (canvas %d)" % (Report["view"],
                                               Report["canvas"]))
        for Name, Rec in Report["joints"].items():
            Lines.append(
                "  %s: %d steps, worst revealed before %d, "
                "after %d - %s" % (Name, Rec["steps"],
                                   Rec["worst_before"],
                                   Rec["worst_after"],
                                   "PASS" if Rec["pass"] else "FAIL"))
        Lines.append(
            "  Rest appearance drift: %d px changed which "
            "part shows at rest." % Report["rest_drift_px"])
        Lines.append("  Pass: %s" % ("YES" if Report["pass"] else "NO"))
        if Report.get("psd_comparison"):
            Lines.append(
                "  Overlap extents against Solomon's PSD "
                "reference (px on this canvas):")
            for Row in Report["psd_comparison"]:
                Lines.append(
                    "    %s: PSD proximal %.0f, ours %.0f; "
                    "PSD distal %.0f, ours %.0f; PSD run %.0f, "
                    "ours %.0f" % (Row["joint"], Row["psd_proximal_px"],
                                   Row["ours_proximal_px"],
                                   Row["psd_distal_px"],
                                   Row["ours_distal_px"],
                                   Row["psd_run_px"], Row["ours_run_px"]))
        Lines.append("")
    return "\n".join(Lines)


# The selftest figure: a torso bar and an arm bar that
# overlaps it by 8 px, pinned at the arm's top. At rest
# the arm's strip beside the torso is covered by the
# arm alone, so the sweep must find revealed background
# before completion and none after.
def Selftest():
    Root = tempfile.mkdtemp(prefix="Full_Layers_Selftest_")
    Parts = os.path.join(Root, "Parts")
    os.makedirs(Parts)
    Torso = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    Draw = ImageDraw.Draw(Torso)
    Draw.rectangle([88, 40, 128, 216], fill=(70, 140, 90, 255))
    Torso.save(os.path.join(Parts, "Part_Torso_V1.PNG"))
    Arm = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    Draw = ImageDraw.Draw(Arm)
    Draw.rectangle([120, 64, 168, 200], fill=(200, 120, 60, 255))
    Arm.save(os.path.join(Parts, "Part_Arm_V1.PNG"))
    Rig = {
        "canvas": 256,
        "layer_order_back_to_front": ["Part_Torso_V1", "Part_Arm_V1"],
        "parts": {
            "Part_Torso_V1": {"pin": [108, 128], "parent": None},
            "Part_Arm_V1": {"pin": [124, 64],
                            "parent": "Part_Torso_V1"},
        },
    }
    Rig_Path = os.path.join(Root, "Rig_V1.JSON")
    with open(Rig_Path, "w") as Handle:
        json.dump(Rig, Handle)

    def Hash(Path):
        with open(Path, "rb") as Handle:
            return hashlib.md5(Handle.read()).hexdigest()

    Before_Hash = {Name: Hash(os.path.join(Parts, Name + ".PNG"))
                   for Name in Rig["parts"]}
    Out = os.path.join(Root, "Out")
    Job = Load_Rig(Rig_Path)[0]
    Report = Process_View(Job, Parts, Rig_Path, Out, 5, None)
    Joint = Report["joints"]["Arm"]
    Ok = (Joint["worst_before"] > 0 and Joint["worst_after"] == 0
          and Report["pass"])
    for Name, Digest in Before_Hash.items():
        Ok = Ok and Hash(os.path.join(Parts, Name + ".PNG")) == Digest
        Ok = Ok and os.path.isfile(os.path.join(Out, Name + ".PNG"))
    print("Full_Layers selftest: %s (arm worst before %d, after %d)"
          % ("PASS" if Ok else "FAIL", Joint["worst_before"],
             Joint["worst_after"]))
    return 0 if Ok else 1


def Main():
    Parser = argparse.ArgumentParser(
        description="Complete a part layer set to full "
                    "layers and prove it with the sweep test.")
    Parser.add_argument("--parts")
    Parser.add_argument("--rig")
    Parser.add_argument("--view")
    Parser.add_argument("--out")
    Parser.add_argument("--report")
    Parser.add_argument("--step", type=int, default=5)
    Parser.add_argument("--compare-psd")
    Parser.add_argument("--selftest", action="store_true")
    Args = Parser.parse_args()
    if Args.selftest:
        return Selftest()
    if not Args.parts or not Args.rig or not Args.out:
        Parser.error("--parts, --rig and --out are required "
                     "unless --selftest is used")
    if os.path.abspath(Args.out) == os.path.abspath(Args.parts):
        Parser.error("--out must be a new folder, never the "
                     "input folder")
    Jobs = Load_Rig(Args.rig)
    if Args.view:
        Jobs = [Job for Job in Jobs if Job["view"] == Args.view]
        if not Jobs:
            Parser.error("no such view in the rig: " + Args.view)
    os.makedirs(Args.out, exist_ok=True)
    Reports = []
    for Job in Jobs:
        Reports.append(Process_View(Job, Args.parts, Args.rig,
                                    Args.out, Args.step,
                                    Args.compare_psd))
    Report_Path = Args.report or os.path.join(
        Args.out, "Completion_Report_V1.JSON")
    with open(Report_Path, "w") as Handle:
        json.dump(Reports, Handle, indent=1)
    with open(os.path.join(Args.out, "Completion_Report_V1.TXT"),
              "w") as Handle:
        Handle.write(Report_Text(Reports))
    Passed = True
    for Report in Reports:
        Worst_Before = max(Rec["worst_before"]
                           for Rec in Report["joints"].values())
        Worst_After = max(Rec["worst_after"]
                          for Rec in Report["joints"].values())
        Passed = Passed and Report["pass"]
        print("Full_Layers %s: worst before %d, worst after %d, %s"
              % (Report["view"], Worst_Before, Worst_After,
                 "PASS" if Report["pass"] else "FAIL"))
    return 0 if Passed else 1


if __name__ == "__main__":
    sys.exit(Main())
