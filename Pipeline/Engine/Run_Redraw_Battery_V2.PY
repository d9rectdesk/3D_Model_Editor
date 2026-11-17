# Run_Redraw_Battery_V2.PY
# Source: Kevin, original work - the redraw engine's
# full verification battery for the estate Humanoid_Rig
# set (Half A, 2026-11-15; gate-format mark retrofitted
# 2026-11-17). What the code does is described in the
# header below; the instruments it reuses are named
# there and at their blocks.
# Half A iteration (2026-11-15): V2 differs from V1 in
# ONE place - the per-joint test group in Joint_Sweep.
# V1's group was the parent part alone plus the child
# part's subtree. That was exact for the unsplit
# baseline, but a redrawn set's split parts (the
# waistband, the trapezius yoke, the armpit webs) are
# parented to the parent part and pinned at the joint
# pin: they belong to the joint's static side, yet V1
# counted neither them nor their fans, so the waist,
# neck, and shoulder tests measured a pair the fix
# list never proposed. V2 adds every part pinned at
# the joint's pin that does not move with the child
# to the static side, warped by its own world matrix
# (the identity in these sweeps). On the baseline no
# part qualifies, so the baseline numbers reproduce
# V1 exactly - proven by re-running V2 on the
# completed set against Baseline_Battery_V1.JSON.
# Everything else is V1 unchanged.
# Half A, Piece 2 of the paper man doll redraw
# (Solomon's Orders, 2026-11-15): the INDEPENDENT
# battery that proves a redrawn part set against the
# fix list's standard - zero new trapped background at
# every 1-degree step, zero pockets and zero disc
# background at every combined ladder step, the one
# genuine see-through exception at plus/minus 5
# verified by location and shape class, and the
# hands-in-front-of-face layer test per view.
# Usage:
#   python3 Run_Redraw_Battery_V2.PY <parts folder>
#       <rig JSON> [output JSON] [--views Front,Back]
# The parts folder holds one subfolder per view named
# for the view, with one PNG per part, and the rig
# JSON is the Completed_Rig_V1.JSON form: canvas,
# views, each view with layer_order_back_to_front,
# parts (pin, parent), and joints (name, pin, radius,
# parent, child).
# Reuse, not rebuild: the posing machinery is
# Complete_And_Buffer_V1.PY's forward kinematics and
# warp (Kevin), imported through Pose_Census_V1.PY;
# the trapped-background measure is Pose_Audit_V1.PY's
# Trapped (Kevin) - its 18 px closing disc, its reach
# of joint radius plus 300, and its rest subtraction;
# the disc count is Pose_Census_V1.PY's Census_Disc
# (Kevin); the layer test is Pose_Audit_V1.PY's
# Hand_Face_Test method and Probe_Sign (Kevin),
# carried onto the caller's own folder and rig.
# Two speed changes, both proven bit-identical to the
# stage-1 instruments before this battery was built:
# warps are computed only inside the trapped window
# (the same PIL affine and resampling, restricted to
# the window the measure reads), and the 18 px disc
# closing is computed by distance transform with a
# 20 px false pad, which reproduced the stage-1
# per-joint series exactly on the neck, waist, and
# left shoulder (rest counts and the 1, 2, 5, and 10
# degree rows, both directions) in pre-build tests.
# The anatomical limits are Pose_Fix_List_V1.TXT
# Section 2, copied verbatim for the front and back
# views; the side views take the same table by
# near/far analogue (near as left, far as right),
# recorded here because Section 2 names only the
# front view's joints.
# Original work - Kevin, except where a source is
# named above.
import importlib.machinery
import importlib.util
import json
import os
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

# The folder this script lives in is the source home.
Home = os.path.dirname(os.path.abspath(__file__))
Canvas = 2048

# The stage-1 instruments, imported whole.
Loader = importlib.machinery.SourceFileLoader(
    "Pose_Census_V1", os.path.join(Home, "Pose_Census_V1.PY"))
Spec = importlib.util.spec_from_loader("Pose_Census_V1", Loader)
PC = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(PC)
Loader_A = importlib.machinery.SourceFileLoader(
    "Pose_Audit_V1", os.path.join(Home, "Pose_Audit_V1.PY"))
Spec_A = importlib.util.spec_from_loader("Pose_Audit_V1", Loader_A)
PA = importlib.util.module_from_spec(Spec_A)
Spec_A.loader.exec_module(PA)
CB = PC.CB

# Section 2 limits, rig degrees, [min, max] per joint.
# Copied from Pose_Fix_List_V1.TXT Section 2.
Limits_Front_Back = {
    "neck": [-35, 35], "spine": [-20, 20], "waist": [-20, 20],
    "shoulder_l": [-170, 55], "shoulder_r": [-55, 170],
    "elbow_l": [-5, 145], "elbow_r": [-5, 145],
    "wrist_l": [-70, 80], "wrist_r": [-80, 70],
    "hip_l": [-45, 30], "hip_r": [-30, 45],
    "knee_l": [-5, 135], "knee_r": [-135, 5],
    "ankle_l": [-50, 20], "ankle_r": [-20, 50],
}
# The side views by near/far analogue of the same
# table: near reads as left, far reads as right.
Limits_Side = {
    "neck": [-35, 35], "spine": [-20, 20], "waist": [-20, 20],
    "shoulder_n": [-170, 55], "shoulder_f": [-55, 170],
    "elbow_n": [-5, 145], "elbow_f": [-5, 145],
    "wrist_n": [-70, 80], "wrist_f": [-80, 70],
    "hip_n": [-45, 30], "hip_f": [-30, 45],
    "knee_n": [-5, 135], "knee_f": [-135, 5],
    "ankle_n": [-50, 20], "ankle_f": [-20, 50],
}
View_Names = ["Front", "Back", "SideRight", "SideLeft"]


# The limits table that serves one view.
# Source: Kevin, original work.
def Limits_For(View):
    if View in ("Front", "Back"):
        return Limits_Front_Back
    return Limits_Side


# Load one view from the caller's folder and rig:
# the rig in Complete_And_Buffer_V1.PY's form, the
# paint order, the joint table, and the alpha images.
# Source: Kevin, original work.
def Load_View(Parts_Root, Rig_Data, View):
    Data = Rig_Data["views"][View]
    Rig = {Name: (tuple(P["pin"]), P["parent"])
           for Name, P in Data["parts"].items()}
    Alphas = {}
    for Name in Data["layer_order_back_to_front"]:
        Arr = np.array(Image.open(os.path.join(
            Parts_Root, View, Name + ".PNG")).convert("RGBA"))
        Alphas[Name] = Image.fromarray(Arr[:, :, 3])
    Joints = [(J["name"], tuple(J["pin"]), J["radius"],
               J["parent"], J["child"]) for J in Data["joints"]]
    return Rig, Data["layer_order_back_to_front"], Joints, Alphas


# The descendants of one part in one view's rig, the
# part itself included: Pose_Census_V1.PY's Subtree
# (Kevin), carried onto any view's parent table.
# Source: Kevin, original work.
def Subtree(Rig, Root):
    Children_Of = {}
    for Name, (Pin, Parent) in Rig.items():
        Children_Of.setdefault(Parent, []).append(Name)
    Out = []
    Stack = [Root]
    while Stack:
        Part = Stack.pop()
        Out.append(Part)
        Stack.extend(Children_Of.get(Part, []))
    return Out


# Warp one alpha image by a world matrix, computed
# only inside one window: Complete_And_Buffer_V1.PY's
# Warp_Alpha (Kevin) - PIL affine takes the inverse
# map - with the output restricted to the window and
# the translation shifted by the window's origin, so
# every pixel inside the window is the full warp's
# own value.
# Source: Kevin, original work.
def Warp_Window(Img, M, Box):
    X0, Y0, X1, Y1 = Box
    Inv = np.linalg.inv(M)
    A, B, C = Inv[0, 0], Inv[0, 1], Inv[0, 2]
    D, E, F = Inv[1, 0], Inv[1, 1], Inv[1, 2]
    return Img.transform(
        (X1 - X0, Y1 - Y0), Image.AFFINE,
        (A, B, C + A * X0 + B * Y0, D, E, F + D * X0 + E * Y0),
        resample=Image.BILINEAR)


# Closing by the 18 px disc of Pose_Audit_V1.PY's
# Trapped (Kevin), computed by distance transform:
# dilation is every pixel within 18 of the figure,
# erosion is every pixel whose nearest outside pixel
# is more than 18 away, with a 20 px false pad so the
# window's edge behaves as background, exactly as the
# direct closing on the cropped window does. Proven
# bit-identical to the direct closing in pre-build
# tests (see the header).
# Source: Kevin, original work.
def Close_Disc_18(Win):
    Dil = ndimage.distance_transform_edt(~Win) <= 18.0
    Pad = np.pad(Dil, 20, constant_values=False)
    Ero = ndimage.distance_transform_edt(Pad) > 18.0
    return Ero[20:-20, 20:-20]


# Background trapped inside a composite window:
# Pose_Audit_V1.PY's Trapped (Kevin) carried onto a
# window whose origin is (X0, Y0) - close the
# silhouette, fill what is left, keep what the
# closing and filling covered but the composite does
# not, counted inside the reach square about the pin.
# Source: Kevin, original work.
def Trapped_Window(Win, Centre, Reach, X0, Y0):
    Filled = ndimage.binary_fill_holes(Close_Disc_18(Win))
    Trap = Filled & ~Win
    Oy = int(round(Centre[1])) - Y0
    Ox = int(round(Centre[0])) - X0
    Inner = np.zeros_like(Trap)
    Iy0 = max(0, Oy - Reach)
    Iy1 = min(Trap.shape[0], Oy + Reach + 1)
    Ix0 = max(0, Ox - Reach)
    Ix1 = min(Trap.shape[1], Ox + Reach + 1)
    Inner[Iy0:Iy1, Ix0:Ix1] = Trap[Iy0:Iy1, Ix0:Ix1]
    return Inner


# One view's loaded state, shared by every check.
# Source: Kevin, original work.
class View_State:
    # Build the view's tables once.
    def __init__(self, Parts_Root, Rig_Data, View):
        self.View = View
        self.Rig, self.Order, self.Joints, self.Alphas = \
            Load_View(Parts_Root, Rig_Data, View)
        self.Joint_Child = {N: C for N, Pn, R, P, C in self.Joints}
        self.Joint_Radius = {N: R for N, Pn, R, P, C in self.Joints}
        self.Joint_Pin = {N: Pn for N, Pn, R, P, C in self.Joints}
        self.Limits = Limits_For(View)
        self.Subtrees = {C: set(Subtree(self.Rig, C))
                         for C in set(self.Joint_Child.values())}
        self.Alpha_Bool = {N: np.asarray(I) > 8
                           for N, I in self.Alphas.items()}

    # Turn a table of joint angles into per-part angles.
    def Part_Angles(self, Joint_Angles):
        return {self.Joint_Child[N]: float(D)
                for N, D in Joint_Angles.items()}

    # The posed union of the whole view, full canvas,
    # by Complete_And_Buffer_V1.PY's own warp.
    def Union_At(self, Joint_Angles, Skip=()):
        World, Pins = CB.World_And_Pins(
            self.Rig, self.Part_Angles(Joint_Angles))
        Union = np.zeros((Canvas, Canvas), dtype=bool)
        for Name in self.Order:
            if Name in Skip:
                continue
            Union |= np.asarray(
                CB.Warp_Alpha(self.Alphas[Name], World[Name])) > 8
        Posed = {N: Pins[C] for N, Pn, R, P, C in self.Joints}
        return Union, Posed, World


# Check (a): one joint's trapped background at every
# 1-degree step of its Section 2 range, both
# directions - Pose_Audit_V1.PY's Joint_First_Background
# method (Kevin): the parent side stands, the child's
# subtree turns, the group is read by the trapped
# measure, and only what rest does not trap is new.
# The group (V2, rewritten whole): the parent part,
# every part pinned at this joint's pin that does not
# move with the child (the split parts a redraw parks
# on the static side - the waistband at the waist,
# the yoke at the neck, the webs at the shoulders),
# and the child's whole subtree turning. A part
# pinned at the pin but moving with the child (the
# child part itself, the face features at the neck)
# is already in the subtree and is not counted twice.
# Source: Kevin, original work.
def Joint_Sweep(State, Joint_Name):
    Child = State.Joint_Child[Joint_Name]
    Parent = next(P for N, Pn, R, P, C in State.Joints
                  if N == Joint_Name)
    Pin = State.Joint_Pin[Joint_Name]
    Radius = State.Joint_Radius[Joint_Name]
    Moving = State.Subtrees[Child]
    Static_Extra = [Name for Name in State.Order
                    if Name != Parent and Name not in Moving
                    and tuple(State.Rig[Name][0]) == tuple(Pin)]
    Reach = Radius + 300
    Cx, Cy = int(round(Pin[0])), int(round(Pin[1]))
    R = Reach + 40
    X0, X1 = max(0, Cx - R), min(Canvas, Cx + R + 1)
    Y0, Y1 = max(0, Cy - R), min(Canvas, Cy + R + 1)
    Box = (X0, Y0, X1, Y1)
    Parent_Win = State.Alpha_Bool[Parent][Y0:Y1, X0:X1]

    # The trapped window of the group at one angle.
    def Trap_At(Deg):
        World, Pins = CB.World_And_Pins(
            State.Rig, State.Part_Angles({Joint_Name: float(Deg)}))
        Comp = Parent_Win.copy()
        for Name in State.Order:
            if Name in Moving or Name in Static_Extra:
                Comp |= np.asarray(Warp_Window(
                    State.Alphas[Name], World[Name], Box)) > 8
        return Trapped_Window(Comp, Pin, Reach, X0, Y0)

    Rest = Trap_At(0)
    Lo, Hi = State.Limits[Joint_Name]
    Out = {"rest_trapped": int(Rest.sum()), "range": [Lo, Hi],
           "plus": {}, "minus": {}}
    for Deg in range(1, Hi + 1):
        Out["plus"][str(Deg)] = int((Trap_At(Deg) & ~Rest).sum())
    for Deg in range(-1, Lo - 1, -1):
        Out["minus"][str(Deg)] = int((Trap_At(Deg) & ~Rest).sum())
    for Key in ("plus", "minus"):
        Series = Out[Key]
        First = None
        for Deg in sorted(Series, key=lambda D: abs(int(D))):
            if Series[Deg] > 0:
                First = int(Deg)
                break
        Out[Key + "_first_angle"] = First
        Out[Key + "_max"] = max(Series.values()) if Series else 0
        Out[Key + "_pass"] = all(V == 0 for V in Series.values())
    Out["pass"] = Out["plus_pass"] and Out["minus_pass"]
    return Out


# Enclosed pockets of one posed union, charged to the
# nearest joint pin: Pose_Census_V1.PY's Census_Pose
# pocket count (Kevin), carried onto any view.
# Source: Kevin, original work.
def Pockets_Of(Union, Posed, Joint_Names):
    Seeds = np.zeros((Canvas, Canvas), dtype=np.int32)
    for I, Name in enumerate(Joint_Names):
        Px = int(round(Posed[Name][0]))
        Py = int(round(Posed[Name][1]))
        Seeds[Py, Px] = I + 1
    Dist, Indices = ndimage.distance_transform_edt(
        Seeds == 0, return_indices=True)
    Nearest = Seeds[Indices[0], Indices[1]]
    Mask = ndimage.binary_fill_holes(Union) & ~Union
    Counts = {}
    for I, Name in enumerate(Joint_Names):
        Counts[Name] = int((Mask & (Nearest == I + 1)).sum())
    return Mask, Counts


# Check (c)'s shape reading of one pocket component:
# where it sits, how big it is, how triangular it is,
# which posed parts border it, and whether it is the
# arm that forms it - the component stops being a
# pocket when the arm chain is removed, which is
# what open to the outside means for this triangle.
# Source: Kevin, original work.
def Classify_Component(State, Comp, Union, Posed_World):
    Ys, Xs = np.nonzero(Comp)
    Area = int(Comp.sum())
    Border = ndimage.binary_dilation(
        Comp, structure=np.ones((3, 3), dtype=bool), iterations=2)
    Touch = Border & Union
    Parts = []
    for Name in State.Order:
        Warped = np.asarray(
            CB.Warp_Alpha(State.Alphas[Name], Posed_World[Name])) > 8
        if (Touch & Warped).any():
            Parts.append(Name)
    Hull_Area = 0
    if Area >= 3:
        from scipy.spatial import ConvexHull
        Pts = np.stack([Xs, Ys], axis=1).astype(np.float64)
        try:
            Hull_Area = float(ConvexHull(Pts).volume)
        except Exception:
            Hull_Area = 0.0
    Arm_Names = [N for N in State.Order if "Arm_" in N or "Hand_" in N]
    Union_No_Arm = np.zeros((Canvas, Canvas), dtype=bool)
    for Name in State.Order:
        if Name in Arm_Names:
            continue
        Union_No_Arm |= np.asarray(
            CB.Warp_Alpha(State.Alphas[Name], Posed_World[Name])) > 8
    Still = ndimage.binary_fill_holes(Union_No_Arm) & ~Union_No_Arm
    Formed_By_Arm = int((Comp & Still).sum()) <= max(10, Area // 10)
    Has_Arm = any(N in Parts for N in Arm_Names)
    Has_Torso = any("Torso" in N for N in Parts)
    Has_Pelvis = any("Pelvis" in N for N in Parts)
    Solidity = Area / Hull_Area if Hull_Area > 0 else 0.0
    Triangle = bool(Has_Arm and Has_Torso and Has_Pelvis
                    and Formed_By_Arm and 3000 <= Area <= 60000
                    and 0.30 <= Solidity <= 0.90)
    return {
        "area": Area,
        "centroid": [float(Xs.mean()), float(Ys.mean())],
        "bbox": [int(Xs.min()), int(Ys.min()),
                 int(Xs.max()), int(Ys.max())],
        "convex_solidity": Solidity,
        "bordering_parts": Parts,
        "borders_arm": Has_Arm, "borders_torso": Has_Torso,
        "borders_pelvis": Has_Pelvis,
        "formed_by_arm_open_to_outside": bool(Formed_By_Arm),
        "triangle_class": Triangle,
    }


# Checks (b), (c), and (e): the combined ladder at
# 5-degree steps, every joint clamped to its Section
# 2 limit - trapped background and enclosed pockets
# per step, the plus/minus 5 exception read by shape
# class, and the pin-disc count at every step.
# Source: Kevin, original work.
def Combined_Ladder(State):
    Joint_Names = [N for N, Pn, R, P, C in State.Joints]
    Rest_Union, Rest_Posed, Rest_World = State.Union_At(
        {N: 0.0 for N in Joint_Names})
    Rest_Trap = Trapped_Window(
        Rest_Union, (1024, 1024), 1500, 0, 0)
    Steps = {}
    Exception = {}
    Disc_All_Zero = True
    for G in (5, 10, 15, 20, 25, 30, 35, 40,
              -5, -10, -15, -20, -25, -30, -35, -40):
        Pose = {}
        for N in Joint_Names:
            Lo, Hi = State.Limits[N]
            Pose[N] = float(max(Lo, min(Hi, G)))
        Union, Posed, World = State.Union_At(Pose)
        Trap = Trapped_Window(Union, (1024, 1024), 1500, 0, 0)
        New_Trap = int((Trap & ~Rest_Trap).sum())
        Pocket_Mask, Pocket_Counts = Pockets_Of(Union, Posed, Joint_Names)
        Disc = {}
        Disc_Total = 0
        for N, Pn, R, P, C in State.Joints:
            Got = PC.Census_Disc(Union, Posed[N], R)
            Disc[N] = Got["disc_plus_0"]
            Disc_Total += Got["disc_plus_0"]
        if Disc_Total != 0:
            Disc_All_Zero = False
        Entry = {
            "pose_clamped": Pose, "new_trapped": New_Trap,
            "pockets_total": int(Pocket_Mask.sum()),
            "pockets_by_joint": Pocket_Counts,
            "disc_total": Disc_Total, "disc_by_joint": Disc,
        }
        if abs(G) == 5:
            Labels, Count = ndimage.label(Pocket_Mask)
            Comps = []
            Triangle_Area = 0
            for I in range(1, Count + 1):
                Comp = Labels == I
                if int(Comp.sum()) < 1000:
                    continue
                Info = Classify_Component(State, Comp, Union, World)
                Comps.append(Info)
                if Info["triangle_class"]:
                    Triangle_Area += Info["area"]
            Residual = int(Pocket_Mask.sum()) - Triangle_Area
            Entry["exception_components"] = Comps
            Entry["exception_triangle_area"] = Triangle_Area
            Entry["exception_residual_pockets"] = Residual
            Entry["exception_pass"] = bool(
                Triangle_Area > 0 and Residual == 0)
            Exception[str(G)] = Entry["exception_pass"]
        Entry["pass"] = bool(
            New_Trap == 0 and Disc_Total == 0 and (
                Entry["pockets_total"] == 0
                or (abs(G) == 5 and Entry.get("exception_pass"))))
        Steps[str(G)] = Entry
        print(f"  ladder {State.View} {G:+d}: trapped "
              f"{New_Trap}, pockets {Entry['pockets_total']}, "
              f"disc {Disc_Total}, pass {Entry['pass']}")
    return {"steps": Steps, "exception": Exception,
            "disc_all_zero": Disc_All_Zero,
            "pass": all(S["pass"] for S in Steps.values())}


# Check (d): the named layer test for one view -
# Pose_Audit_V1.PY's Hand_Face_Test (Kevin) carried
# onto this view's own rig and parts: raise the arm
# beside the head, fold the forearm so the hand
# crosses the face, paint in the view's own order
# keeping the topmost part per pixel, and count
# where hand and head overlap and which one wins.
# Source: Kevin, original work.
def Hand_Face_Test(State):
    View = State.View
    if View in ("Front", "Back"):
        Shoulder, Elbow = "shoulder_l", "elbow_l"
        Hand = "Part_Hand_Left_V1"
        Fore = "Part_Arm_Fore_Left_V1"
    else:
        Shoulder, Elbow = "shoulder_n", "elbow_n"
        Hand = "Part_Hand_Near_V1"
        Fore = "Part_Arm_Fore_Near_V1"
    Head = "Part_Head_V1"
    Sh_Child = State.Joint_Child[Shoulder]
    El_Child = State.Joint_Child[Elbow]
    Sh_Pin = np.array(State.Joint_Pin[Shoulder], float)
    Raise = PA.Probe_Sign(State.Rig, Sh_Child, Fore, lambda P: -P[1])
    Flex = PA.Probe_Sign(
        State.Rig, El_Child, Hand,
        lambda P: -float(np.linalg.norm(P - Sh_Pin)))
    Angles = {Sh_Child: Raise * 115.0, El_Child: Flex * 125.0}
    World, Pins = CB.World_And_Pins(State.Rig, Angles)
    Presence = {}
    Topmost = np.full((Canvas, Canvas), -1, dtype=np.int32)
    for I, Name in enumerate(State.Order):
        W = np.asarray(CB.Warp_Alpha(
            State.Alphas[Name], World[Name])) > 8
        Presence[Name] = W
        Topmost[W] = I
    Overlap = Presence[Hand] & Presence[Head]
    Hand_I = State.Order.index(Hand)
    Head_I = State.Order.index(Head)
    Can_Cover = bool(Hand_I > Head_I)
    if View == "Back":
        # From behind, the head must cover a hand that
        # passes in front of the face: perspective.
        Pass = bool(Head_I > Hand_I)
        Expect = "head_over_hand"
    else:
        Pass = Can_Cover
        Expect = "hand_over_head"
    return {
        "view": View, "raise_sign": int(Raise), "flex_sign": int(Flex),
        "order_index_hand": Hand_I, "order_index_head": Head_I,
        "order_index_fore": State.Order.index(Fore),
        "order": State.Order,
        "overlap_px": int(Overlap.sum()),
        "overlap_topmost_hand": int(
            (Overlap & (Topmost == Hand_I)).sum()),
        "overlap_topmost_head": int(
            (Overlap & (Topmost == Head_I)).sum()),
        "hand_can_cover_face": Can_Cover,
        "expected": Expect, "pass": bool(Pass),
    }


# Run every check for one view and print its verdict.
# Source: Kevin, original work.
def Run_View(Parts_Root, Rig_Data, View):
    Start = time.time()
    State = View_State(Parts_Root, Rig_Data, View)
    print(f"view {View}: {len(State.Order)} parts, "
          f"{len(State.Joints)} joints")
    Per_Joint = {}
    for Name, Pn, R, P, C in State.Joints:
        Per_Joint[Name] = Joint_Sweep(State, Name)
        Got = Per_Joint[Name]
        print(f"  joint {Name}: +1 {Got['plus'].get('1')} / "
              f"-1 {Got['minus'].get('-1')}, first "
              f"{Got['plus_first_angle']} / "
              f"{Got['minus_first_angle']}, pass {Got['pass']} "
              f"({round(time.time() - Start)}s)")
    Ladder = Combined_Ladder(State)
    Layer = Hand_Face_Test(State)
    print(f"  layer {View}: hand {Layer['order_index_hand']}, "
          f"head {Layer['order_index_head']}, overlap "
          f"{Layer['overlap_px']}, pass {Layer['pass']}")
    Pass = bool(all(J["pass"] for J in Per_Joint.values())
                and Ladder["pass"] and Layer["pass"])
    return {"per_joint_trapped": Per_Joint, "combined": Ladder,
            "layer_order": Layer, "pass": Pass}


# The battery's entry point.
# Source: Kevin, original work.
def Main(Argv):
    Args = [A for A in Argv[1:] if not A.startswith("--")]
    Views = View_Names
    for A in Argv[1:]:
        if A.startswith("--views="):
            Views = A.split("=", 1)[1].split(",")
    if len(Args) < 2:
        print("usage: Run_Redraw_Battery_V2.PY <parts folder> "
              "<rig JSON> [output JSON] [--views Front,Back,...]")
        return 2
    Parts_Root = os.path.abspath(Args[0])
    Rig_Path = os.path.abspath(Args[1])
    Out_Path = (os.path.abspath(Args[2]) if len(Args) > 2 else
                os.path.join(Home, "Redraw_Battery_V2.JSON"))
    with open(Rig_Path) as F:
        Rig_Data = json.load(F)
    Report = {"parts_folder": Parts_Root, "rig_json": Rig_Path,
              "standard": "zero new trapped background at every "
                          "1-degree step; zero pockets, trapped, "
                          "and disc background at every combined "
                          "ladder step except the verified "
                          "plus/minus 5 arm-torso triangle",
              "views": {}}
    Start = time.time()
    for View in Views:
        Report["views"][View] = Run_View(Parts_Root, Rig_Data, View)
    Report["pass"] = all(V["pass"] for V in Report["views"].values())
    Report["elapsed_seconds"] = round(time.time() - Start, 1)
    with open(Out_Path, "w") as F:
        json.dump(PA.Sanitize(Report), F, indent=1)
    print(f"BATTERY {'PASS' if Report['pass'] else 'FAIL'}: "
          f"{Out_Path} in {Report['elapsed_seconds']}s")
    return 0 if Report["pass"] else 1


if __name__ == "__main__":
    sys.exit(Main(sys.argv))
