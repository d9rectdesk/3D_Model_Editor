# Redraw_Circles_V1.PY
# Half A, the circle construction (Solomon's method
# change, 2026-11-16): "There just needs to be a
# circle around every point where is going to be a
# joint, and the joint needs to be placed properly,
# and the images behind need to have all the details
# for the areas that the images in front of layer
# allow to show." This script supersedes the fan
# construction of Redraw_Fans_V1/V2 whole. What it
# keeps from that work: the Step 1 measurement audit
# (the battery's per-joint groups and the corrected
# Run_Redraw_Battery_V2), the disc stripping, the
# section 6 splits S1 to S3, the section 5 corrected
# paint orders, the section 2 limits, the clothing
# fence, the edge finish, and the rest proof.
# THE CIRCLE: at every joint, each participating
# part carries a complete disc of its own drawn
# substance centred on the pin - the parent side on
# the parent part or its split carrier (the
# waistband carries the pelvis's waist disc, the
# yoke the torso top's neck disc, the webs the torso
# top's shoulder discs), the child side on the child
# part. A disc centred on the pin is unchanged by
# the joint's own rotation, so at every angle in the
# section 2 range both sides cover the whole disc
# and the rotating part's edge always stays over
# completed drawing. The hip fence stands: the thigh
# draws no disc at the hip; the pelvis's disc there
# is cloth only.
# THE RADIUS, derived from the measurement (Diag_V1,
# 2026-11-15): in the baseline the new trapped
# background reached the battery's counting window
# corners at every joint and angle sampled - radii
# to (joint radius plus 300) times root two. The
# circle's radius is that figure plus a margin:
# (joint radius plus 300) times 1.42 plus 4. A joint
# whose circle still traps in the battery grows its
# radius and is redrawn, or is reported impossible
# with numbers.
# THE PINS, verified before drawing (2026-11-16):
# the completed set's in-disc census and circle fits
# on the pre-buffer art's joint caps were run per
# joint and view. The one true ball end, the head's
# underside at the neck, fits a circle centred 1.3 px
# from the neck pin (fit radius 65 against the rig's
# 60). The limb ends are overlap joints whose art
# reaches through the pin (boundary distance 1 px at
# the elbows, wrists, and knees), and stage 1's
# flexion probes on these pins measured sane; no pin
# is proven off-centre, so no pin moves and the
# census is unchanged.
# COMPLETE UNDER-IMAGES: the discs complete every
# part at its joints, and the rest proof below adds
# the under-image check - the redrawn rest assembly's
# alpha must be a superset of the original's, pixel
# for pixel, so no area the front layers covered is
# left undrawn behind them.
# Inputs are read, never edited: the completed parts
# in Paper_Doll_Stitch_V1/Doll_Parts_Completed_V1 and
# the pre-buffer Bit 2 parts in the same stitch
# folder's Doll_Parts_V1. Output is the folder
# Paper_Doll_Redraw_V2, per the crew rule.
# Disc removal: a Bit 3 disc pixel is a completed-set
# pixel that the Bit 2 mask does not have, inside a
# disc of a joint the part takes part in. Those pixels
# are stripped first; everything Bit 3 added outside
# its joint discs (the torso bridges, the side shorts
# capsule, the head's feature fills) is kept.
# V21 (Model Editor V21's per-point radius control):
# a joint's disc radius can be set by hand. The
# radius a joint is drawn with - its effective disc
# radius - is decided by Disc_Radius_For: first a
# per-run override file named by the environment
# variable REDRAW_DISC_RADII_JSON (a JSON object of
# view -> joint name -> radius, written by the
# editor pipeline's redraw step from the radii tuned
# in the page), then the joint's own "disc_radius"
# field when the input rig carries one, then the
# computed Disc_Radius below. The effective radius is
# recorded on every joint of the rig this script
# writes, so what was drawn is what the rig says.
# The reveal bitmaps (Solomon, 2026-11-16 - "that is
# the whole key behind building the 3D model
# first"): where the 3D lane has swept a joint in
# 5-degree steps on the posed 3D model and composited
# the pixels the model itself shows behind the moving
# part, that composite - a full-canvas RGBA PNG per
# view and joint at <REDRAW_REVEAL_DIR>/<View>/
# Reveal_<joint name>_V1.PNG - IS the fill for the
# joint: its alpha is the fill shape and its RGB the
# fill colours, on both sides of the joint, and NO
# disc is drawn for that joint at all. Fill-source
# precedence per joint, highest first: (1) the reveal
# bitmap (the data path - the model's own truth);
# (2) the disc at the per-point radius (the manual
# path - the editor slider's override, the rig's
# disc_radius field, then the computed Disc_Radius).
# The rig and census this script writes record each
# joint's fill_source so a run states which path
# filled which joint.
# Source: Kevin, original work (the reveal
# consumer, 2026-11-16) - census found no estate
# precedent for bitmap fill (the only "Reveal_"
# names elsewhere are an unrelated chat-bubble
# timer in Persona_Windows).
# Two more environment knobs serve the callers and
# the proofs, both defaulting to today's behaviour:
# REDRAW_VIEWS (a comma list) runs only those views,
# and REDRAW_OUT_ROOT writes the redrawn set to
# another folder instead of Paper_Doll_Redraw_V2.
# Original work - Kevin, except where a source is
# named in place.


import json
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage


# The folder this script lives in is the source home.
Home = os.path.dirname(os.path.abspath(__file__))
Canvas = 2048
In_Root = os.path.join(
    Home, "Paper_Doll_Stitch_V1", "Doll_Parts_Completed_V1")
Bit2_Root = os.path.join(
    Home, "Paper_Doll_Stitch_V1", "Doll_Parts_V1")
Out_Root = os.environ.get("REDRAW_OUT_ROOT") or \
    os.path.join(Home, "Paper_Doll_Redraw_V2")

# The per-run disc radius overrides (V21): view ->
# joint name -> radius, from the JSON file the
# REDRAW_DISC_RADII_JSON environment variable names.
Disc_Overrides = {}
_Override_Path = os.environ.get("REDRAW_DISC_RADII_JSON")
if _Override_Path and os.path.exists(_Override_Path):
    with open(_Override_Path) as _F:
        Disc_Overrides = json.load(_F)

# The reveal bitmaps (see the header): the folder
# the REDRAW_REVEAL_DIR environment variable names,
# laid out <folder>/<View>/Reveal_<joint>_V1.PNG.
# Loaded lazily and cached; Reveal_For returns
# (array, mask) or None when no bitmap exists for
# the joint - None is the disc path's signal.
Reveal_Dir = os.environ.get("REDRAW_REVEAL_DIR") or None
Reveal_Cache = {}


def Reveal_For(View, Joint_Name):
    if not Reveal_Dir:
        return None
    Key = (View, Joint_Name)
    if Key not in Reveal_Cache:
        Path = os.path.join(
            Reveal_Dir, View, "Reveal_" + Joint_Name + "_V1.PNG")
        if os.path.exists(Path):
            Arr = np.array(Image.open(Path).convert("RGBA"))
            Reveal_Cache[Key] = (Arr, Arr[:, :, 3] > 0)
            print("%s %s: reveal bitmap is the fill source "
                  "(%d px, no disc drawn)"
                  % (View, Joint_Name,
                     int(Reveal_Cache[Key][1].sum())))
        else:
            Reveal_Cache[Key] = None
    return Reveal_Cache[Key]

# Section 2 limits, front and back views, rig degrees
# as [min, max] per joint (Pose_Fix_List_V1.TXT).
Limits_Front_Back = {
    "waist": (-20, 20), "spine": (-20, 20),
    "neck": (-35, 35),
    "shoulder_l": (-170, 55), "shoulder_r": (-55, 170),
    "elbow_l": (-5, 145), "elbow_r": (-5, 145),
    "wrist_l": (-70, 80), "wrist_r": (-80, 70),
    "hip_l": (-45, 30), "hip_r": (-30, 45),
    "knee_l": (-5, 135), "knee_r": (-135, 5),
    "ankle_l": (-50, 20), "ankle_r": (-20, 50),
}

# Section 2 spans mapped onto the side views' Near
# and Far joints, signs from the pin probes recorded
# in the header.
Limits_Side = {
    "SideRight": {
        "waist": (-20, 20), "spine": (-20, 20),
        "neck": (-35, 35),
        "shoulder_n": (-170, 55), "shoulder_f": (-170, 55),
        "elbow_n": (-145, 5), "elbow_f": (-5, 145),
        "wrist_n": (-70, 80), "wrist_f": (-70, 80),
        "hip_n": (-45, 30), "hip_f": (-45, 30),
        "knee_n": (-5, 135), "knee_f": (-5, 135),
        "ankle_n": (-20, 50), "ankle_f": (-20, 50),
    },
    "SideLeft": {
        "waist": (-20, 20), "spine": (-20, 20),
        "neck": (-35, 35),
        "shoulder_n": (-55, 170), "shoulder_f": (-55, 170),
        "elbow_n": (-5, 145), "elbow_f": (-145, 5),
        "wrist_n": (-80, 70), "wrist_f": (-80, 70),
        "hip_n": (-30, 45), "hip_f": (-30, 45),
        "knee_n": (-135, 5), "knee_f": (-135, 5),
        "ankle_n": (-50, 20), "ankle_f": (-50, 20),
    },
}

# The split parts of section 6, front and back views:
# short name, pin joint, parent short name, and the
# joint whose parent-side disc the split part carries.
Splits = {
    "Armpit_Web_Left": ("shoulder_l", "Torso_Top"),
    "Armpit_Web_Right": ("shoulder_r", "Torso_Top"),
    "Trapezius_Yoke": ("neck", "Torso_Top"),
    "Waistband": ("waist", "Pelvis"),
}
# Corrected paint orders, back to front, from section
# 5, with the split parts placed by section 5's
# closing note: the waistband over the torso middle
# and under the torso top, the yoke over the torso top
# and under the head and the arms, the webs between
# the torso top and the upper arms.
Corrected_Order = {
    "Front": [
        "Foot_Left", "Foot_Right", "Shin_Left", "Shin_Right",
        "Thigh_Left", "Thigh_Right", "Pelvis", "Torso_Middle",
        "Waistband", "Torso_Top", "Trapezius_Yoke", "Head",
        "Eye_Right", "Eye_Left", "Mouth",
        "Armpit_Web_Left", "Armpit_Web_Right",
        "Arm_Upper_Left", "Arm_Upper_Right",
        "Arm_Fore_Left", "Arm_Fore_Right",
        "Hand_Left", "Hand_Right",
    ],
    "Back": [
        "Foot_Left", "Foot_Right", "Shin_Left", "Shin_Right",
        "Thigh_Left", "Thigh_Right", "Pelvis", "Torso_Middle",
        "Waistband", "Torso_Top", "Trapezius_Yoke",
        "Armpit_Web_Left", "Armpit_Web_Right",
        "Arm_Upper_Left", "Arm_Upper_Right",
        "Arm_Fore_Left", "Arm_Fore_Right",
        "Hand_Left", "Hand_Right", "Head",
    ],
    "SideRight": [
        "Foot_Far", "Shin_Far", "Thigh_Far", "Hand_Far",
        "Arm_Fore_Far", "Arm_Upper_Far",
        "Foot_Near", "Shin_Near", "Thigh_Near", "Pelvis",
        "Torso_Middle", "Torso_Top", "Head", "Eye_Side",
        "Arm_Upper_Near", "Arm_Fore_Near", "Hand_Near",
    ],
}
Corrected_Order["SideLeft"] = list(Corrected_Order["SideRight"])

# The face features ride the head and are never
# redrawn (section 4, last line).
Feature_Parts = {"Eye_Left", "Eye_Right", "Mouth", "Eye_Side"}


def Short(Full_Name):
    # Part_Torso_Top_V1 -> Torso_Top
    return Full_Name[5:-3]


def Full(Short_Name):
    return f"Part_{Short_Name}_V1"


def Segment_Distance(Points, A, B):
    AB = B - A
    T = np.clip(((Points - A) @ AB) / (AB @ AB), 0.0, 1.0)
    Closest = A + T[:, None] * AB
    return np.sqrt(((Points - Closest) ** 2).sum(axis=1))


def Cloth_Sources(Window, Lum_W):
    Cloth = (Window[:, :, 3] >= 250) & \
        (Window[:, :, 2] - Window[:, :, 0] > 12) & \
        (Lum_W >= 45) & (Lum_W <= 90)
    if Cloth.sum() < 24:
        Cloth = (Window[:, :, 3] >= 250) & \
            (Window[:, :, 2] - Window[:, :, 0] > 12) & \
            (Lum_W < 120)
    return Cloth


def Local_Tone(Canvas_Arr, Mask, Pin, Radius, Cloth_Only=False):
    Pad = int(Radius * 2 + 8)
    Y0 = max(0, int(Pin[1] - Pad)); Y1 = min(Canvas, int(Pin[1] + Pad + 1))
    X0 = max(0, int(Pin[0] - Pad)); X1 = min(Canvas, int(Pin[0] + Pad + 1))
    Window = Canvas_Arr[Y0:Y1, X0:X1].astype(np.int32)
    Have = Mask[Y0:Y1, X0:X1]
    Lum_W = Window[:, :, :3].mean(axis=2)
    Spread_W = Window[:, :, :3].max(axis=2) - \
        Window[:, :, :3].min(axis=2)
    Interior = Have & (Window[:, :, 3] >= 250) & \
        (Lum_W >= 110) & (Lum_W <= 232) & (Spread_W > 24)
    if Cloth_Only:
        Interior = Have & Cloth_Sources(Window, Lum_W)
    if Interior.sum() < 24:
        Interior = Have
    Source = Window[Interior, :3].astype(np.float64)
    return np.median(Source, axis=0).astype(np.uint8)


def Outline_Tone(Canvas_Arr, Mask):
    Window = Canvas_Arr.astype(np.int32)
    Lum_W = Window[:, :, :3].mean(axis=2)
    Dark = Mask & (Window[:, :, 3] >= 250) & (Lum_W < 110)
    if Dark.sum() < 24:
        Tone = np.median(
            Window[Mask, :3].astype(np.float64), axis=0)
        return (Tone * 0.4).astype(np.uint8)
    return np.median(
        Window[Dark, :3].astype(np.float64), axis=0).astype(np.uint8)


def Disc_Window(Pin, Radius):
    Cx, Cy = int(round(Pin[0])), int(round(Pin[1]))
    Y0 = max(0, Cy - Radius); Y1 = min(Canvas, Cy + Radius + 1)
    X0 = max(0, Cx - Radius); X1 = min(Canvas, Cx + Radius + 1)
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    Disc = (XX - Pin[0]) ** 2 + (YY - Pin[1]) ** 2 <= Radius ** 2
    return Disc, Y0, Y1, X0, X1


def Close_Disc(Win, K):
    Pad_W = int(K) + 4
    Dil = ndimage.distance_transform_edt(~Win) <= float(K)
    Pad = np.pad(Dil, Pad_W, constant_values=False)
    Ero = ndimage.distance_transform_edt(Pad) > float(K)
    return Ero[Pad_W:-Pad_W, Pad_W:-Pad_W]


def Load_View(View, Part_Names):
    Canvases, Masks, Bit2 = {}, {}, {}
    for Name in Part_Names:
        Arr = np.array(Image.open(os.path.join(
            In_Root, View, Full(Name) + ".PNG")).convert("RGBA"))
        Canvases[Name] = Arr
        Masks[Name] = Arr[:, :, 3] > 0
        Arr2 = np.array(Image.open(os.path.join(
            Bit2_Root, View, Full(Name) + ".PNG")).convert("RGBA"))
        Bit2[Name] = Arr2[:, :, 3] > 0
    return Canvases, Masks, Bit2


def View_Joints(View, Rig_Data, Limits):
    Joints = []
    for J in Rig_Data["views"][View]["joints"]:
        Lo, Hi = Limits[J["name"]]
        Joints.append({
            "name": J["name"], "pin": tuple(J["pin"]),
            "radius": int(J["radius"]),
            "disc_radius": Disc_Radius_For(View, J),
            "has_reveal": Reveal_For(View, J["name"]) is not None,
            "parent": Short(J["parent"]), "child": Short(J["child"]),
            "low": Lo, "high": Hi,
        })
    return Joints


def Carve_Splits(View, Work_Masks, Joints):
    By_Name = {J["name"]: J for J in Joints}
    Neck = By_Name["neck"]
    Sh_L = By_Name["shoulder_l"]
    Sh_R = By_Name["shoulder_r"]
    Waist = By_Name["waist"]
    TT = Work_Masks["Torso_Top"]
    # The yoke: torso top substance within one neck
    # radius of either neck-to-shoulder segment, plus
    # the torso top's own neck disc.
    Ys, Xs = np.where(TT)
    Pts = np.stack([Xs, Ys], axis=1).astype(np.float64)
    Neck_P = np.array(Neck["pin"], float)
    D_L = Segment_Distance(Pts, Neck_P, np.array(Sh_L["pin"], float))
    D_R = Segment_Distance(Pts, Neck_P, np.array(Sh_R["pin"], float))
    Near = (D_L <= Neck["radius"]) | (D_R <= Neck["radius"])
    Disc, Y0, Y1, X0, X1 = Disc_Window(Neck["pin"], Neck["radius"] + 3)
    In_Disc = np.zeros(len(Ys), dtype=bool)
    Sel = (Ys >= Y0) & (Ys < Y1) & (Xs >= X0) & (Xs < X1)
    In_Disc[Sel] = Disc[Ys[Sel] - Y0, Xs[Sel] - X0]
    Yoke = np.zeros((Canvas, Canvas), dtype=bool)
    Yoke[Ys[Near | In_Disc], Xs[Near | In_Disc]] = True
    # The webs: torso top substance within the
    # shoulder disc grown 45 px, on the shoulder's own
    # side of the neck line, outside the yoke.
    Webs = {}
    for Side_Name, Joint in (("Armpit_Web_Left", Sh_L),
                             ("Armpit_Web_Right", Sh_R)):
        Disc, Y0, Y1, X0, X1 = Disc_Window(
            Joint["pin"], Joint["radius"] + 45)
        Web = np.zeros((Canvas, Canvas), dtype=bool)
        Web[Y0:Y1, X0:X1] = Disc
        YY, XX = np.mgrid[0:Canvas, 0:Canvas]
        Same_Side = (XX - Neck_P[0]) * (Joint["pin"][0] - Neck_P[0]) >= 0
        Webs[Side_Name] = Web & TT & Same_Side & ~Yoke
    # The waistband: the pelvis top band, from one
    # waist radius above the waist pin to 28 px below
    # it, the band the torso middle's swing stays in.
    Pelvis = Work_Masks["Pelvis"]
    Rows = np.zeros((Canvas, Canvas), dtype=bool)
    Top = max(0, int(Waist["pin"][1] - (Waist["radius"] + 3)))
    Bottom = min(Canvas, int(Waist["pin"][1] + 28 + 1))
    Rows[Top:Bottom, :] = True
    Waistband = Pelvis & Rows
    Split_Masks = {
        "Armpit_Web_Left": Webs["Armpit_Web_Left"],
        "Armpit_Web_Right": Webs["Armpit_Web_Right"],
        "Trapezius_Yoke": Yoke,
        "Waistband": Waistband,
    }
    Work_Masks["Torso_Top"] = TT & ~Yoke \
        & ~Webs["Armpit_Web_Left"] & ~Webs["Armpit_Web_Right"]
    Work_Masks["Pelvis"] = Pelvis & ~Waistband
    return Split_Masks, {K: int(V.sum()) for K, V in Split_Masks.items()}


def Write_View(View, Work_Canvases, Work_Masks, Order):
    Folder = os.path.join(Out_Root, View)
    os.makedirs(Folder, exist_ok=True)
    for Name in Order:
        Out = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
        M = Work_Masks[Name]
        Out[M] = Work_Canvases[Name][M]
        Out[M, 3] = 255
        Image.fromarray(Out, "RGBA").save(
            os.path.join(Folder, Full(Name) + ".PNG"))


def Assemble(Root, View, Order, Name_Index):
    Frame = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
    Top = np.full((Canvas, Canvas), -1, dtype=np.int32)
    for Name in Order:
        Arr = np.array(Image.open(os.path.join(
            Root, View, Full(Name) + ".PNG")).convert("RGBA"))
        Hit = Arr[:, :, 3] > 8
        Frame[Hit] = Arr[Hit]
        Top[Hit] = Name_Index[Name]
    return Frame, Top


def Build_Rig_View(View, Rig_Data, Joints, Split_Names):
    View_Data = Rig_Data["views"][View]
    Parts = {}
    Joint_By_Child = {J["child"]: J for J in Joints}
    for Full_Name, P in View_Data["parts"].items():
        Name = Short(Full_Name)
        Entry = {"pin": P["pin"], "parent": P["parent"]}
        if Name in Feature_Parts:
            Entry["angle_min_deg"] = 0
            Entry["angle_max_deg"] = 0
        elif Name in Joint_By_Child:
            J = Joint_By_Child[Name]
            Entry["angle_min_deg"] = J["low"]
            Entry["angle_max_deg"] = J["high"]
        else:
            Entry["angle_min_deg"] = None
            Entry["angle_max_deg"] = None
        Parts[Full_Name] = Entry
    Pin_By_Joint = {J["name"]: J for J in Joints}
    for Name in Split_Names:
        Joint_Name, Parent = Splits[Name]
        J = Pin_By_Joint[Joint_Name]
        Parts[Full(Name)] = {
            "pin": [J["pin"][0], J["pin"][1]],
            "parent": Full(Parent),
            "angle_min_deg": J["low"],
            "angle_max_deg": J["high"],
        }
    Effective = {J["name"]: J["disc_radius"] for J in Joints}
    Sources = {J["name"]: ("reveal_bitmap" if J["has_reveal"]
                           else "disc") for J in Joints}
    Joint_Out = []
    for J in Rig_Data["views"][View]["joints"]:
        Entry = dict(J)
        Lo, Hi = (Limits_Front_Back if View in ("Front", "Back")
                  else Limits_Side[View])[J["name"]]
        Entry["angle_min_deg"] = Lo
        Entry["angle_max_deg"] = Hi
        # The radius the discs were drawn with (V21),
        # so the written rig states what was drawn.
        Entry["disc_radius"] = Effective[J["name"]]
        # And which fill path the joint took (V21):
        # the reveal bitmap where one exists, else
        # the disc at that radius.
        Entry["fill_source"] = Sources[J["name"]]
        Joint_Out.append(Entry)
    return {
        "layer_order_back_to_front": [Full(N) for N in
                                      Corrected_Order[View]],
        "parts": Parts,
        "joints": Joint_Out,
    }


# The circle radius of one joint: (joint radius
# plus 300) times 1.42 plus 4. The battery counts
# trapped background in the square of half width
# (joint radius plus 300) about the pin, and the
# baseline's trapped background reached that
# square's corners (Diag_V1) - the corners sit at
# (radius plus 300) times root two - so the circle
# covers the whole counted square, with margin.
def Disc_Radius(Joint):
    return int((Joint["radius"] + 300) * 1.42) + 4


# The radius a joint's discs are actually drawn
# with (V21): a per-run override for this view and
# joint first, then the joint's own disc_radius
# field when the input rig carries one, then the
# computed Disc_Radius above.
def Disc_Radius_For(View, Joint):
    Override = Disc_Overrides.get(View, {}).get(Joint["name"])
    if Override is not None:
        print("%s %s: disc radius override %d (computed %d)"
              % (View, Joint["name"], int(round(float(Override))),
                 Disc_Radius(Joint)))
        return int(round(float(Override)))
    if Joint.get("disc_radius") is not None:
        return int(round(float(Joint["disc_radius"])))
    return Disc_Radius(Joint)


# Which split part, if any, carries one part's disc
# at one joint in a front or back view: the torso
# top's shoulder discs ride in the webs, its neck
# disc in the yoke, and the pelvis waist disc in
# the waistband.
def Disc_Target(View, Joint_Name, Part):
    if View in ("SideRight", "SideLeft"):
        return Part
    if Part == "Torso_Top" and Joint_Name == "neck":
        return "Trapezius_Yoke"
    if Part == "Torso_Top" and Joint_Name == "shoulder_l":
        return "Armpit_Web_Left"
    if Part == "Torso_Top" and Joint_Name == "shoulder_r":
        return "Armpit_Web_Right"
    if Part == "Pelvis" and Joint_Name == "waist":
        return "Waistband"
    return Part


def Redraw_View(View, Rig_Data):
    View_Data = Rig_Data["views"][View]
    Part_Names = [Short(N) for N in View_Data["layer_order_back_to_front"]]
    if View in ("Front", "Back"):
        Limits = Limits_Front_Back
    else:
        Limits = Limits_Side[View]
    Joints = View_Joints(View, Rig_Data, Limits)
    Canvases, Masks, Bit2 = Load_View(View, Part_Names)
    # Strip the Bit 3 discs: completed pixels the Bit
    # 2 mask does not have, inside a disc of a joint
    # the part takes part in. The stripped silhouette
    # is the disc's source and the part's new base.
    Discs_Of = {Name: [] for Name in Part_Names}
    for J in Joints:
        Discs_Of[J["parent"]].append(J)
        Discs_Of[J["child"]].append(J)
    Work_Masks, Work_Canvases = {}, {}
    Stripped = {}
    for Name in Part_Names:
        Keep = Bit2[Name].copy()
        if Name not in Feature_Parts:
            Added = Masks[Name] & ~Bit2[Name]
            Drop = np.zeros((Canvas, Canvas), dtype=bool)
            for J in Discs_Of[Name]:
                Disc, Y0, Y1, X0, X1 = Disc_Window(
                    J["pin"], J["radius"] + 3)
                Drop[Y0:Y1, X0:X1] |= Disc
            Keep |= Added & ~Drop
            Stripped[Name] = int((Masks[Name] & ~Keep).sum())
        else:
            Keep = Masks[Name].copy()
            Stripped[Name] = 0
        Work_Masks[Name] = Keep
        Arr = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
        Arr[Keep] = Canvases[Name][Keep]
        Arr[Keep, 3] = 255
        Work_Canvases[Name] = Arr
    # Split bases are carved before the discs are
    # grown, so a split part's disc lands on its own
    # carved substance. Every part's stripped
    # silhouette is captured before the carve: the
    # disc sources are these silhouettes, so a split
    # part's substance still counts in its source
    # part's side of a joint's union neighbourhood.
    Stripped_Source = {N: Work_Masks[N].copy() for N in Work_Masks}
    Split_Names = []
    Carved = {}
    if View in ("Front", "Back"):
        Split_Masks, Carved = Carve_Splits(View, Work_Masks, Joints)
        Split_Names = list(Split_Masks)
        Source_Of = {"Armpit_Web_Left": "Torso_Top",
                     "Armpit_Web_Right": "Torso_Top",
                     "Trapezius_Yoke": "Torso_Top",
                     "Waistband": "Pelvis"}
        for Name in Split_Names:
            Work_Masks[Name] = Split_Masks[Name]
            Arr = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
            Src = Source_Of[Name]
            Arr[Split_Masks[Name]] = Canvases[Src][Split_Masks[Name]]
            Arr[Split_Masks[Name], 3] = 255
            Work_Canvases[Name] = Arr
    # Grow the fills, one per part per joint. The
    # fill source is decided per joint (see the
    # header): a reveal bitmap where one exists -
    # its own pixels, shape and colours, and no disc
    # at all for that joint - else the disc at the
    # joint's effective radius, in the part's own
    # flat local tone.
    Added_Disc = {Name: np.zeros((Canvas, Canvas), dtype=bool)
                 for Name in Work_Masks}
    Added_Bitmap = {Name: np.zeros((Canvas, Canvas), dtype=bool)
                    for Name in Work_Masks}
    Disc_Counts = {}
    Fill_Sources = {}
    for J in Joints:
        Parent = J["parent"]
        Child = J["child"]
        Reveal = Reveal_For(View, J["name"])
        if Reveal is not None:
            Fill_Mask = Reveal[1]
            Fill_Arr = Reveal[0]
            Fill_Sources[J["name"]] = "reveal_bitmap"
        else:
            Disc, Y0, Y1, X0, X1 = Disc_Window(
                J["pin"], J["disc_radius"])
            Fill_Mask = np.zeros((Canvas, Canvas), dtype=bool)
            Fill_Mask[Y0:Y1, X0:X1] = Disc
            Fill_Arr = None
            Fill_Sources[J["name"]] = "disc"
        # Parent side: the complete fill on the parent
        # part or its split carrier (cloth only for
        # the pelvis on the disc path).
        P_Target = Disc_Target(View, J["name"], Parent)
        New = Fill_Mask & ~Work_Masks[P_Target]
        Disc_Counts[f"{J['name']}:{Parent}"] = int(New.sum())
        if New.any():
            if Fill_Arr is not None:
                Work_Canvases[P_Target][New, :3] = Fill_Arr[New, :3]
                Added_Bitmap[P_Target] |= New
            else:
                Tone = Local_Tone(
                    Canvases[Parent], Masks[Parent], J["pin"],
                    J["radius"] + 3, Cloth_Only=(Parent == "Pelvis"))
                Work_Canvases[P_Target][New, :3] = Tone
                Added_Disc[P_Target] |= New
            Work_Canvases[P_Target][New, 3] = 255
            Work_Masks[P_Target] |= Fill_Mask
        # Clothing fence: the thigh draws no fill at
        # the hip; the pelvis fills alone there.
        if J["name"].startswith("hip"):
            continue
        # Child side: the complete fill on the child
        # part.
        New = Fill_Mask & ~Work_Masks[Child]
        Disc_Counts[f"{J['name']}:{Child}"] = int(New.sum())
        if New.any():
            if Fill_Arr is not None:
                Work_Canvases[Child][New, :3] = Fill_Arr[New, :3]
                Added_Bitmap[Child] |= New
            else:
                Tone = Local_Tone(
                    Canvases[Child], Masks[Child], J["pin"],
                    J["radius"] + 3, Cloth_Only=False)
                Work_Canvases[Child][New, :3] = Tone
                Added_Disc[Child] |= New
            Work_Canvases[Child][New, 3] = 255
            Work_Masks[Child] |= Fill_Mask
    # Edge finish: inside the union of the
    # neighbourhoods of the joints a part takes part
    # in, the part's mask is closed by a 4 px disc, so
    # 1 px bays and spikes along its edges - the
    # resampling dust Diag3 measured - are finished
    # before any warp resamples them. Pixels the
    # closing adds take the part's flat local tone at
    # its own pin and join the disc rim step below.
    Neigh_Of = {Name: np.zeros((Canvas, Canvas), dtype=bool)
                for Name in Work_Masks}
    for J in Joints:
        Disc_Z, Y0, Y1, X0, X1 = Disc_Window(
            J["pin"], J["disc_radius"] + 3)
        Zone = np.zeros((Canvas, Canvas), dtype=bool)
        Zone[Y0:Y1, X0:X1] = Disc_Z
        Reveal = Reveal_For(View, J["name"])
        if Reveal is not None:
            Zone |= Reveal[1]
        for Name in {J["parent"], J["child"],
                     Disc_Target(View, J["name"], J["parent"]),
                     Disc_Target(View, J["name"], J["child"])}:
            Neigh_Of[Name] |= Zone
    for Name in Work_Masks:
        if Name in Feature_Parts or not Neigh_Of[Name].any():
            continue
        M = Work_Masks[Name]
        Closed = Close_Disc(M, 4)
        New_M = M.copy()
        New_M[Neigh_Of[Name]] = Closed[Neigh_Of[Name]]
        Added = New_M & ~M
        if Added.any():
            if Name in Splits:
                Pin = next(J["pin"] for J in Joints
                           if J["name"] == Splits[Name][0])
            else:
                Pin = Rig_Data["views"][View]["parts"][Full(Name)]["pin"]
            Tone = Local_Tone(Work_Canvases[Name], M, Pin, 90)
            Work_Canvases[Name][Added, :3] = Tone
            Work_Canvases[Name][Added, 3] = 255
            Added_Disc[Name] |= Added
        Work_Masks[Name] = New_M
    # Outline the discs: a disc-added pixel on the
    # part's outer boundary takes the part's outline
    # tone, so the disc reads as drawn substance, not
    # as a flat pad. Bitmap-added pixels (Added_Bitmap)
    # are never outlined: their colours are the
    # model's own, edge included.
    for Name in Work_Masks:
        if not Added_Disc[Name].any():
            continue
        M = Work_Masks[Name]
        Outside = np.ones((Canvas, Canvas), dtype=bool)
        Outside[1:-1, 1:-1] = ~(M[:-2, 1:-1] & M[2:, 1:-1]
                                & M[1:-1, :-2] & M[1:-1, 2:])
        Rim = Added_Disc[Name] & Outside
        if Rim.any():
            Tone = Outline_Tone(Work_Canvases[Name], M)
            Work_Canvases[Name][Rim, :3] = Tone
    Report = {"stripped_disc_pixels": Stripped,
              "disc_added_pixels": Disc_Counts,
              "fill_sources": Fill_Sources,
              "carved_split_pixels": Carved}
    return Work_Canvases, Work_Masks, Joints, Report, Split_Names


def Prove_View(View, Rig_Data, Joints):
    Orig_Order = [Short(N) for N in
                  Rig_Data["views"][View]["layer_order_back_to_front"]]
    New_Order = Corrected_Order[View]
    All_Names = list(dict.fromkeys(Orig_Order + New_Order))
    Name_Index = {N: I for I, N in enumerate(All_Names)}
    Orig_Frame, Orig_Top = Assemble(In_Root, View, Orig_Order, Name_Index)
    New_Frame, New_Top = Assemble(Out_Root, View, New_Order, Name_Index)
    # The redraw-only order: the original order with
    # the split parts inserted where section 5's
    # closing note puts them relative to their
    # neighbours in that order.
    Proof_Order = list(Orig_Order)
    if View in ("Front", "Back"):
        Proof_Order.insert(Proof_Order.index("Torso_Middle") + 1,
                           "Waistband")
        Proof_Order.insert(Proof_Order.index("Torso_Top") + 1,
                           "Trapezius_Yoke")
        Proof_Order.insert(Proof_Order.index("Trapezius_Yoke") + 1,
                           "Armpit_Web_Left")
        Proof_Order.insert(Proof_Order.index("Armpit_Web_Left") + 1,
                           "Armpit_Web_Right")
    Proof_Frame, Proof_Top = Assemble(
        Out_Root, View, Proof_Order, Name_Index)
    # Allowed zones: every joint's disc, and the
    # split parts' own areas.
    Disc_Zone = np.zeros((Canvas, Canvas), dtype=bool)
    for J in Joints:
        Disc, Y0, Y1, X0, X1 = Disc_Window(J["pin"], J["disc_radius"] + 3)
        Disc_Zone[Y0:Y1, X0:X1] |= Disc
    # A reveal joint's allowed zone is its bitmap
    # (dilated 3 px, the disc zone's own margin):
    # the redraw differs from the original exactly
    # where the bitmap filled.
    for J in Joints:
        if J.get("has_reveal"):
            Reveal = Reveal_For(View, J["name"])
            if Reveal is not None:
                Disc_Zone |= ndimage.binary_dilation(
                    Reveal[1], structure=np.ones((7, 7), dtype=bool))
    Split_Zone = np.zeros((Canvas, Canvas), dtype=bool)
    for Name in New_Order:
        if Name in Splits:
            Arr = np.array(Image.open(os.path.join(
                Out_Root, View, Full(Name) + ".PNG")).convert("RGBA"))
            Split_Zone |= Arr[:, :, 3] > 8
    # Part pairs whose relative order section 5
    # flipped, for the corrected-order comparison.
    Common = [N for N in Orig_Order if N in New_Order]
    Flipped = set()
    for I, A in enumerate(Common):
        for B in Common[I + 1:]:
            if (Orig_Order.index(A) < Orig_Order.index(B)) != \
                    (New_Order.index(A) < New_Order.index(B)):
                Flipped.add((Name_Index[A], Name_Index[B]))
                Flipped.add((Name_Index[B], Name_Index[A]))

    def Diff_Report(Frame, Top, Allow_Flips):
        Diff = np.any(Frame != Orig_Frame, axis=2)
        In_Disc = Diff & Disc_Zone
        In_Split = Diff & Split_Zone & ~Disc_Zone
        Rest = Diff & ~Disc_Zone & ~Split_Zone
        In_Flip = np.zeros((Canvas, Canvas), dtype=bool)
        if Allow_Flips and Rest.any():
            Ys, Xs = np.where(Rest)
            for Y, X in zip(Ys, Xs):
                if (Orig_Top[Y, X], Top[Y, X]) in Flipped:
                    In_Flip[Y, X] = True
        Unexplained = Rest & ~In_Flip
        return {
            "diff_pixels": int(Diff.sum()),
            "diff_in_disc_zones": int(In_Disc.sum()),
            "diff_in_split_areas": int(In_Split.sum()),
            "diff_from_order_flips": int(In_Flip.sum()),
            "unexplained_diff_pixels": int(Unexplained.sum()),
        }

    Redraw_Only = Diff_Report(Proof_Frame, Proof_Top, False)
    Corrected = Diff_Report(New_Frame, New_Top, True)
    # The under-image check of the header: no pixel
    # the original rest assembly covers may be left
    # uncovered in the redrawn rest assembly.
    Missing = int(((Orig_Top >= 0) & (New_Top < 0)).sum())
    Redraw_Only["orig_pixels_missing_in_new"] = Missing
    Corrected["orig_pixels_missing_in_new"] = Missing
    return Redraw_Only, Corrected


def Main():
    with open(os.path.join(In_Root, "Completed_Rig_V1.JSON")) as F:
        Rig_Data = json.load(F)
    os.makedirs(Out_Root, exist_ok=True)
    Rig_Out = {"canvas": Canvas, "views": {}}
    Census = {"views": {}}
    Failed = False
    # REDRAW_VIEWS (V21) may name a comma list of the
    # views to run; the default is all four, as before.
    Only_Views = [V.strip() for V in
                  os.environ.get("REDRAW_VIEWS", "").split(",")
                  if V.strip()]
    for View in ("Front", "Back", "SideRight", "SideLeft"):
        if Only_Views and View not in Only_Views:
            continue
        Canvases, Masks, Joints, Report, Split_Names = \
            Redraw_View(View, Rig_Data)
        Write_View(View, Canvases, Masks, Corrected_Order[View])
        Rig_Out["views"][View] = Build_Rig_View(
            View, Rig_Data, Joints, Split_Names)
        Redraw_Only, Corrected = Prove_View(View, Rig_Data, Joints)
        Report["part_count"] = len(Corrected_Order[View])
        Report["rest_proof_redraw_only_order"] = Redraw_Only
        Report["rest_proof_corrected_order"] = Corrected
        Census["views"][View] = Report
        print(f"{View}: {len(Corrected_Order[View])} parts, "
              f"disc added {sum(Report['disc_added_pixels'].values())} px, "
              f"rest diff redraw-only {Redraw_Only['diff_pixels']} "
              f"(unexplained {Redraw_Only['unexplained_diff_pixels']}, "
              f"missing {Redraw_Only['orig_pixels_missing_in_new']}), "
              f"corrected {Corrected['diff_pixels']} "
              f"(unexplained {Corrected['unexplained_diff_pixels']})")
        if Redraw_Only["unexplained_diff_pixels"] or \
                Corrected["unexplained_diff_pixels"] or \
                Corrected["orig_pixels_missing_in_new"]:
            Failed = True
    with open(os.path.join(Out_Root, "Redrawn_Rig_V1.JSON"), "w") as F:
        json.dump(Rig_Out, F, indent=1)
    with open(os.path.join(Out_Root, "Redraw_Census_V1.JSON"), "w") as F:
        json.dump(Census, F, indent=1)
    if Failed:
        print("REDRAW PROOF FAILED")
        sys.exit(1)
    print("REDRAW DONE, PROOF PASSED")


if __name__ == "__main__":
    Main()
