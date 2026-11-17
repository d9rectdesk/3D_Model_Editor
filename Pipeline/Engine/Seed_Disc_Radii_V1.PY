# Seed_Disc_Radii_V1.PY
# Source: Kevin, original work. Census before
# writing (2026-11-16): no estate program measures a
# joint's local part width to seed a radius - the
# redraw engine's Disc_Radius is a formula over a
# stored base radius, not a measurement, so it cannot
# do this job; the perpendicular cross-section measure
# below was written for this seeding.
# Model Editor V21, the seeding (Solomon, 2026-11-16):
# "All of the circles should not be the same size
# either. The circles for the wrists and the ankles I
# would assume would be some of the smallest, until we
# add fingers." So each joint's completion-disc radius
# is seeded from the joint's own artwork, not from the
# old near-uniform formula ((base radius + 300) * 1.42
# + 4, which landed every joint between 486 and 534).
# THE MEASURE: at each joint, the cross-section width
# of the PARENT part at the pin, taken on the line
# through the pin perpendicular to the bone axis (the
# axis runs to the next joint down the chain, or from
# the joint above when the joint ends a chain). The
# width is measured on the pre-completion split parts
# (the stitch folder's Doll_Parts_V1): the completed
# parts carry the old discs themselves, so measuring
# there would read the old circles back. A pin sits at
# its parent part's very end, where a cross-section
# catches only a sliver, so the measure probes back
# into the parent part along the bone axis (0 to 160
# px in 8 px steps) and keeps the widest cross-section
# found - the limb's own width near its joint. The
# seed is the width's half times root two, plus 4 -
# the corner of the limb's end cross-section sits at
# half-width times root two from the pin - with the
# old formula's margin kept and its +300 counting-
# window term dropped. Wrists and ankles measure
# narrow, hips, shoulders, neck and waist wide, so
# the ordering comes out of the model itself. Nothing
# is floored per joint name: a smaller point added
# later (fingers) measures smaller and seeds smaller.
# The seeds land in Redrawn_Rig_V1.JSON as each
# joint's "disc_radius"; the full table is written to
# Seed_Disc_Radii_Report_V1.JSON beside it and printed.
# Original work - Kevin.

import json
import math
import os

import numpy as np
from PIL import Image

Home = os.path.dirname(os.path.abspath(__file__))
Rig_Root = os.path.join(Home, "Paper_Doll_Redraw_V2")
Rig_Path = os.path.join(Rig_Root, "Redrawn_Rig_V1.JSON")
Report_Path = os.path.join(Rig_Root,
                           "Seed_Disc_Radii_Report_V1.JSON")
# The pre-completion split parts the widths are
# measured on (the redraw engine's own Bit 2 root).
Parts_Root = os.path.join(Home, "Paper_Doll_Stitch_V1",
                          "Doll_Parts_V1")
Canvas = 2048


# The old computed disc radius, kept for the report's
# contrast column. Source: Redraw_Circles_V1.PY
# Disc_Radius (Kevin).
def Old_Disc_Radius(Joint):
    return int((Joint["radius"] + 300) * 1.42) + 4


# The bone axis at one joint: toward the next joint
# down the chain (the joint whose parent part is this
# joint's child part); for a chain's last joint, from
# the joint above (the joint whose child part is this
# joint's parent part). Falls back to straight down.
def Bone_Axis(Joint, Joints):
    Pin = np.array(Joint["pin"], dtype=float)
    for Other in Joints:
        if Other["parent"] == Joint["child"]:
            Axis = np.array(Other["pin"], dtype=float) - Pin
            if np.linalg.norm(Axis) > 0:
                return Axis / np.linalg.norm(Axis)
    for Other in Joints:
        if Other["child"] == Joint["parent"]:
            Axis = Pin - np.array(Other["pin"], dtype=float)
            if np.linalg.norm(Axis) > 0:
                return Axis / np.linalg.norm(Axis)
    return np.array([0.0, 1.0])


# The width of one part's drawn substance on the line
# through the pin perpendicular to the axis. The
# part's runs of alpha over 8 on the line are bridged
# into clusters across gaps of up to 160 px - the
# torso's two shoulder masses across its neck notch
# are one width, not two slivers - and the width is
# the span of the cluster that contains the pin, or
# of the nearest cluster when the pin sits just off
# the substance (the back view's arm pins stand off
# the torso's edge). Returns (width, offset of the
# cluster's centre from the pin).
def Cross_Section_Width(Alpha, Pin, Axis):
    Perp = np.array([-Axis[1], Axis[0]])
    Ts = np.arange(-700.0, 700.5, 0.5)
    Pts = np.array(Pin, dtype=float)[None, :] + Ts[:, None] * Perp[None, :]
    Xs = np.clip(np.round(Pts[:, 0]).astype(int), 0, Canvas - 1)
    Ys = np.clip(np.round(Pts[:, 1]).astype(int), 0, Canvas - 1)
    On = Alpha[Ys, Xs] > 8
    # Runs of substance along the line.
    Runs = []
    Start = None
    for I, Hit in enumerate(On):
        if Hit and Start is None:
            Start = I
        if not Hit and Start is not None:
            Runs.append((Ts[Start], Ts[I - 1]))
            Start = None
    if Start is not None:
        Runs.append((Ts[Start], Ts[-1]))
    if not Runs:
        return 0.0, 0.0
    # Bridge the runs into clusters across small gaps.
    Clusters = [list(Runs[0])]
    for A, B in Runs[1:]:
        if A - Clusters[-1][1] <= 160.0:
            Clusters[-1][1] = B
        else:
            Clusters.append([A, B])
    Chosen = None
    for A, B in Clusters:
        if A <= 0.0 <= B:
            Chosen = (A, B)
            break
    if Chosen is None:
        Chosen = min(Clusters,
                     key=lambda C: min(abs(C[0]), abs(C[1])))
        if min(abs(Chosen[0]), abs(Chosen[1])) > 450.0:
            return 0.0, 0.0
    A, B = Chosen
    return float(B - A), float((A + B) / 2.0)


def Main():
    with open(Rig_Path) as F:
        Rig = json.load(F)
    Report = {"method": "parent part cross-section width at the "
                        "pin, perpendicular to the bone axis; "
                        "seed = round(1.42 * width / 2) + 4",
              "views": {}}
    for View, View_Data in Rig["views"].items():
        Joints = View_Data["joints"]
        Alphas = {}
        Rows = []
        for Joint in Joints:
            Parent = Joint["parent"]
            if Parent not in Alphas:
                Path = os.path.join(Parts_Root, View, Parent + ".PNG")
                Alphas[Parent] = np.array(
                    Image.open(Path).convert("RGBA"))[:, :, 3]
            Axis = Bone_Axis(Joint, Joints)
            Pin = np.array(Joint["pin"], dtype=float)
            Width, Offset, Probe = 0.0, 0.0, 0
            for Back in range(0, 161, 8):
                Centre = Pin - Axis * Back
                W, O = Cross_Section_Width(
                    Alphas[Parent], Centre, Axis)
                if W > Width:
                    Width, Offset, Probe = W, O, Back
            Seed = max(12, int(round(1.42 * Width / 2.0)) + 4)
            Joint["disc_radius"] = Seed
            Rows.append({
                "joint": Joint["name"], "parent_part": Parent,
                "child_part": Joint["child"],
                "pin": Joint["pin"],
                "measured_width_px": round(Width, 1),
                "run_centre_offset_px": round(Offset, 1),
                "probe_back_px": Probe,
                "seeded_disc_radius": Seed,
                "old_computed_disc_radius": Old_Disc_Radius(Joint),
            })
            print("%s %-12s width %6.1f  seed %4d  (old %4d)"
                  % (View, Joint["name"], Width, Seed,
                     Old_Disc_Radius(Joint)))
        Report["views"][View] = Rows
    with open(Rig_Path, "w") as F:
        json.dump(Rig, F, indent=1)
    with open(Report_Path, "w") as F:
        json.dump(Report, F, indent=1)
    print("seeded disc_radius written into " + Rig_Path)
    print("table written to " + Report_Path)


if __name__ == "__main__":
    Main()
