# Build_Redrawn_GLB_V2.PY
# Source: Kevin, original work (the estate's
# redrawn-set GLB builder; the V2 rewrite and the
# Model Editor V21 disc_radius stamping included).
# Version 2 (Fix A, Defect 3, 2026-11-16): a view may
# have several root parts. V1 refused any view with
# other than exactly one root ("FAIL: Front has 4
# roots" on Duke's rig, Harness_V20 check 7a); V2
# writes each root as a scene-level node at its
# place in the layer (paint) order and the census
# and round-trip treat roots as a set. The same
# rewrite carries the three facts Duke's rig proved
# and V1 assumed away: a rig may carry fewer than
# the four views (Duke carries Front and Back), a
# root part may carry no pin of its own (Duke's
# Torso - written with the no-pin sentinel [0, 0]),
# a part's picture may live at the path its rig
# entry names in "file" when the parts folder does
# not hold it (Duke's Head_Eyes, left untouched by
# the circle completion and never copied in), and
# a joint may carry its own name and range instead
# of a Section 2 name (Duke's tail_base and kin).
# Everything else is V1, copied whole: on a rig in
# V1's contract (the man's redrawn set) V2's GLBs
# are byte-identical to V1's - the generator label
# inside the GLB is V1's, unchanged on purpose, so
# the bytes can prove it.
# Half A, Piece 2 of the paper man doll redraw
# (Solomon's Orders, 2026-11-15): build the flat
# paper GLB and the assembled 3D GLB from any parts
# folder and rig JSON, in exactly the stitch
# builders' format, then prove the flat GLB by the
# Bit 4 round-trip.
# Usage:
#   python3 Build_Redrawn_GLB_V2.PY <parts folder>
#       <rig JSON> [output folder]
# Outputs, in the output folder (this script's own
# folder when none is given):
#   Redrawn_Paper_Doll_V1.GLB - the flat paper GLB,
#     one double-sided page per part, the four views
#     standing side by side (Build_Paper_Doll_GLB_V1
#     form).
#   Redrawn_Paper_Doll_3D_V1.GLB - the one assembled
#     figure at the origin (Build_Paper_Doll_3D_V1
#     form).
#   Redrawn_Paper_Doll_Edited_V1.GLB - the round-trip
#     product: the flat GLB after the edit cycle.
#   Build_Redrawn_GLB_Report_V1.JSON - the census and
#     round-trip counts.
# Format truth: the GLB writer blocks, the page
# constructions, Pretty, and Describe are copied from
# Build_Paper_Doll_GLB_V1.PY and Build_Paper_Doll_3D_V1.PY
# (Kevin, proven in Bits 4 and 5) - each part node
# carries its rig in extras in the Model Editor's own
# form: view, part, pin, parent, label, and desc. One
# addition, stated plainly: a part that is a joint's
# child also carries extras.joint and extras.limits,
# the joint's Section 2 range from
# Pose_Fix_List_V1.TXT, and the top-level joints table
# carries the same limits per joint, so the limits
# travel with the model. The editor's own keys are
# unchanged in name and value.
# V21 addition, stated plainly the same way: a part
# that carries a joint's completion disc - the joint's
# child, or a split carrier sharing the joint's pin
# and parent (the waistband, the yoke, the webs) -
# also carries extras.disc_radius, the joint's seeded
# or tuned fill radius from the rig, and the top-level
# joints table carries disc_radius per joint with it
# (Model Editor V21's per-point radius control reads
# and writes this key).
# The round-trip is Check_Paper_Doll_Bit4_V1.JS's
# edit cycle (Kevin) carried into this script's own
# read/write of the GLB, in the editor's form: open
# the flat GLB and read its rig points from the node
# extras, move one point, add one connected point,
# remove one part (its child re-parents to the part's
# parent, the editor's rule), save with the binary
# chunk untouched, reopen, and prove every edit is
# present and the binary chunk is byte-identical.
# Original work - Kevin, except where a source is
# named above.
import io
import json
import os
import struct
import sys

from PIL import Image

# The folder this script lives in is the source home.
Home = os.path.dirname(os.path.abspath(__file__))
Page_Gap = 0.03
Shell_Gap = 0.0015
Group_X = {"Front": -3.45, "Back": -1.15,
           "SideRight": 1.15, "SideLeft": 3.45}
View_Order = ["Front", "Back", "SideRight", "SideLeft"]
Joint_Words = {
    "waist": "waist", "spine": "spine", "neck": "neck",
    "shoulder_l": "left shoulder", "shoulder_r": "right shoulder",
    "shoulder_n": "near shoulder", "shoulder_f": "far shoulder",
    "elbow_l": "left elbow", "elbow_r": "right elbow",
    "elbow_n": "near elbow", "elbow_f": "far elbow",
    "wrist_l": "left wrist", "wrist_r": "right wrist",
    "wrist_n": "near wrist", "wrist_f": "far wrist",
    "hip_l": "left hip", "hip_r": "right hip",
    "hip_n": "near hip", "hip_f": "far hip",
    "knee_l": "left knee", "knee_r": "right knee",
    "knee_n": "near knee", "knee_f": "far knee",
    "ankle_l": "left ankle", "ankle_r": "right ankle",
    "ankle_n": "near ankle", "ankle_f": "far ankle",
}
# Section 2 limits, rig degrees, [min, max] per joint.
# Copied from Pose_Fix_List_V1.TXT Section 2; the side
# views take the same table by near/far analogue.
Limits_Front_Back = {
    "neck": [-35, 35], "spine": [-20, 20], "waist": [-20, 20],
    "shoulder_l": [-170, 55], "shoulder_r": [-55, 170],
    "elbow_l": [-5, 145], "elbow_r": [-5, 145],
    "wrist_l": [-70, 80], "wrist_r": [-80, 70],
    "hip_l": [-45, 30], "hip_r": [-30, 45],
    "knee_l": [-5, 135], "knee_r": [-135, 5],
    "ankle_l": [-50, 20], "ankle_r": [-20, 50],
}
Limits_Side = {
    "neck": [-35, 35], "spine": [-20, 20], "waist": [-20, 20],
    "shoulder_n": [-170, 55], "shoulder_f": [-55, 170],
    "elbow_n": [-5, 145], "elbow_f": [-5, 145],
    "wrist_n": [-70, 80], "wrist_f": [-80, 70],
    "hip_n": [-45, 30], "hip_f": [-30, 45],
    "knee_n": [-5, 135], "knee_f": [-135, 5],
    "ankle_n": [-50, 20], "ankle_f": [-20, 50],
}


# The limits table that serves one view.
def Limits_For(View):
    if View in ("Front", "Back"):
        return Limits_Front_Back
    return Limits_Side


# A part name in plain words.
# Copied from Build_Paper_Doll_GLB_V1.PY (Kevin, Bit 4).
def Pretty(part):
    Text = part
    if Text.startswith("Part_"):
        Text = Text[5:]
    if Text.endswith("_V1"):
        Text = Text[:-3]
    return Text.replace("_", " ")


# The pin a part node carries. A rig part whose
# pin is None (Duke's Torso, the root the other
# Front parts hang from, carries no pin of its own
# in Duke_Rig_Completed_V1.JSON) is written with
# the no-pin sentinel [0, 0]; the census expects
# exactly that sentinel for a pinless part. Rigs
# whose parts all carry pins never see it.
# Source: Duke_Rig_Completed_V1.JSON (Part_Torso_V1
# pin is None) - Kevin, Fix A.
def Pin_Of(Info):
    if Info["pin"] is None:
        return [0, 0]
    return Info["pin"]


# The limits one joint carries. A joint named in
# the view's Section 2 table takes the table's
# range, exactly as V1 wrote it. A joint the table
# does not name (Duke's tail_base, wing_left, and
# the rest of his own joint names) takes the range
# its own rig entry carries (min_deg / max_deg, or
# angle_min_deg / angle_max_deg), and a joint with
# neither takes the full turn.
# Source: Build_Redrawn_GLB_V1.PY Limits_For
# (Kevin) for the table rule;
# Duke_Rig_Completed_V1.JSON joint entries for the
# own-range rule - Kevin, Fix A.
def Limits_For_Joint(View, Joint):
    Table = Limits_For(View)
    Name = Joint["name"]
    if Name in Table:
        return list(Table[Name])
    if "min_deg" in Joint and "max_deg" in Joint:
        return [Joint["min_deg"], Joint["max_deg"]]
    if "angle_min_deg" in Joint and "angle_max_deg" in Joint:
        return [Joint["angle_min_deg"], Joint["angle_max_deg"]]
    return [-180, 180]


# A joint's name in plain words: the word table
# where it names the joint, the joint's own name
# with underscores as spaces where it does not
# (Duke's joints).
# Source: Build_Redrawn_GLB_V1.PY Joint_Words
# (Kevin) - Kevin, Fix A.
def Joint_Word(Name):
    if Name in Joint_Words:
        return Joint_Words[Name]
    return Name.replace("_", " ")


# The written description a rig point carries.
# Copied from Build_Paper_Doll_GLB_V1.PY (Kevin, Bit 4);
# V2 reads the pin through Pin_Of and the joint
# word through Joint_Word, so a pinless root and a
# joint outside the word table still describe.
def Describe(view, part, info, joint_by_child):
    Words = Pretty(part)
    Pin = Pin_Of(info)
    Pin_Text = "%d, %d" % (round(Pin[0]), round(Pin[1]))
    if info["parent"] is None:
        return ("Root rig point of the " + view + " view. The " + Words +
                " part turns on the waist joint at " + Pin_Text +
                " and carries every part connected under it.")
    Parent_Words = Pretty(info["parent"])
    if part in joint_by_child:
        Joint = Joint_Word(joint_by_child[part]["name"])
        return ("Rig point for the " + Words + " part in the " + view +
                " view. It turns on the " + Joint + " joint at " + Pin_Text +
                ", connected to its parent part " + Parent_Words + ".")
    return ("Rig point for the " + Words + " part in the " + view +
            " view. It rides on its parent part " + Parent_Words +
            ", sharing that part's joint pin at " + Pin_Text + ".")


# The extras one part node carries: the editor's own
# form from Build_Paper_Doll_GLB_V1.PY, plus the
# joint name and Section 2 limits on a joint's child.
# The part's joint is the joint it is the child of,
# or - for a split carrier like the waistband - the
# joint whose pin the part shares and whose parent
# is the part's own parent. A resolved joint that
# carries a disc radius in the rig (V21) stamps it
# into the extras as disc_radius.
def Extras_For(View, Part, Info, Joint_By_Child, Joints):
    Pin = Pin_Of(Info)
    Extras = {"view": View, "part": Part,
              "pin": [float(Pin[0]), float(Pin[1])],
              "parent": Info["parent"],
              "label": View + " " + Pretty(Part),
              "desc": Describe(View, Part, Info, Joint_By_Child)}
    Joint = Joint_By_Child.get(Part)
    if Joint is None:
        for Cand in Joints:
            if Cand["parent"] == Info["parent"] and \
                    [round(float(Cand["pin"][0])),
                     round(float(Cand["pin"][1]))] == \
                    [round(float(Pin[0])), round(float(Pin[1]))]:
                Joint = Cand
                break
    if Joint is not None:
        Extras["joint"] = Joint["name"]
        Extras["limits"] = Limits_For_Joint(View, Joint)
        if Joint.get("disc_radius") is not None:
            Extras["disc_radius"] = Joint["disc_radius"]
    return Extras


# The joints table for the GLB's top-level extras,
# with each joint's Section 2 limits riding in it.
def Joints_Out_For(View, View_Data):
    Out = []
    for Joint in View_Data["joints"]:
        Entry = dict(Joint)
        Entry["limits"] = Limits_For_Joint(View, Joint)
        Out.append(Entry)
    return Out


# The picture file for one part. The parts
# folder's own <View>/<Part>.PNG is the rule. A
# part whose picture is not in the folder but
# whose rig entry names its picture in "file"
# (Duke's Head_Eyes: the circle completion left
# it untouched, so it was never copied into the
# completed folder and its rig entry still names
# the Webchat source picture) is read from that
# named file, resolved against the parts folder,
# this script's folder, and that folder's parent
# in turn. A rig whose parts all sit in the
# folder never takes the fallback.
# Source: Duke_Rig_Completed_V1.JSON "file"
# fields and Duke_Completion_Census_V1.JSON
# (Head_Eyes listed untouched) - Kevin, Fix A.
def Part_Png_Path(Parts_Root, View_Name, Part, Info):
    Local = os.path.join(Parts_Root, View_Name, Part + ".PNG")
    if os.path.exists(Local):
        return Local
    Named = Info.get("file")
    if not Named:
        return None
    for Base in (Parts_Root, Home, os.path.dirname(Home)):
        Cand = os.path.join(Base, Named)
        if os.path.exists(Cand):
            return Cand
    if os.path.exists(Named):
        return Named
    return None


# Build one GLB. Mode "flat" writes the four views
# side by side as double-sided pages
# (Build_Paper_Doll_GLB_V1.PY); mode "3d" assembles
# one figure at the origin (Build_Paper_Doll_3D_V1.PY).
# Returns the part count, or None on a failed check.
def Build_GLB(Parts_Root, Rig, Mode, Out_Path):
    Canvas = Rig["canvas"]
    Bin_Parts = []
    Views = []
    Accessors = []
    Meshes = []
    Materials = []
    Images = []
    Nodes = []

    # One binary chunk builder, copied from
    # Build_Paper_Doll_GLB_V1.PY (Kevin, Bit 4).
    def Add_View(data, target=None):
        Offset = sum(len(b) for b, _ in Bin_Parts)
        Bin_Parts.append((data + b"\x00" * ((-len(data)) % 4), target))
        Entry = {"buffer": 0, "byteOffset": Offset,
                 "byteLength": len(data)}
        if target:
            Entry["target"] = target
        Views.append(Entry)
        return len(Views) - 1

    # One paper page. The flat construction is copied
    # from Build_Paper_Doll_GLB_V1.PY; the front, back,
    # and two profile constructions are copied from
    # Build_Paper_Doll_3D_V1.PY (Kevin, Bit 5).
    def Quad(name, png_path, kind, off, ox, extras):
        Image_Data = Image.open(png_path).convert("RGBA")
        if Image_Data.width > 1024:
            Image_Data = Image_Data.resize((1024, 1024), Image.LANCZOS)
        Buffer = io.BytesIO()
        Image_Data.save(Buffer, "PNG")
        Image_View = Add_View(Buffer.getvalue())
        Images.append({"bufferView": Image_View,
                       "mimeType": "image/png", "name": name})
        Texture_Index = len(Images) - 1
        Double = kind == "flat"
        Materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": Texture_Index},
                "metallicFactor": 0.0, "roughnessFactor": 1.0},
            "alphaMode": "MASK", "alphaCutoff": 0.35,
            "doubleSided": Double})
        if kind == "flat":
            Pos = struct.pack("<12f", ox - 1, -1, off, ox + 1, -1, off,
                              ox + 1, 1, off, ox - 1, 1, off)
            Nor = struct.pack("<12f", *([0, 0, 1] * 4))
            Uv = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
            Idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
            Low = [ox - 1, -1, off]
            High = [ox + 1, 1, off]
        elif kind == "front":
            Pos = struct.pack("<12f", -1, -1, off, 1, -1, off,
                              1, 1, off, -1, 1, off)
            Nor = struct.pack("<12f", *([0, 0, 1] * 4))
            Uv = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
            Idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
            Low = [-1, -1, off]
            High = [1, 1, off]
        elif kind == "back":
            Pos = struct.pack("<12f", 1, 1, off, -1, 1, off,
                              -1, -1, off, 1, -1, off)
            Nor = struct.pack("<12f", *([0, 0, -1] * 4))
            Uv = struct.pack("<8f", 0, 0, 1, 0, 1, 1, 0, 1)
            Idx = struct.pack("<6H", 0, 2, 1, 0, 3, 2)
            Low = [-1, -1, off]
            High = [1, 1, off]
        elif kind == "sideright":
            Pos = struct.pack("<12f", off, -1, -1, off, -1, 1,
                              off, 1, 1, off, 1, -1)
            Nor = struct.pack("<12f", *([-1, 0, 0] * 4))
            Uv = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
            Idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
            Low = [off, -1, -1]
            High = [off, 1, 1]
        else:
            Pos = struct.pack("<12f", off, -1, 1, off, -1, -1,
                              off, 1, -1, off, 1, 1)
            Nor = struct.pack("<12f", *([1, 0, 0] * 4))
            Uv = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
            Idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
            Low = [off, -1, -1]
            High = [off, 1, 1]
        Pos_View = Add_View(Pos, 34962)
        Nor_View = Add_View(Nor, 34962)
        Uv_View = Add_View(Uv, 34962)
        Idx_View = Add_View(Idx, 34963)
        Base = len(Accessors)
        Accessors.extend([
            {"bufferView": Pos_View, "componentType": 5126, "count": 4,
             "type": "VEC3", "min": Low, "max": High},
            {"bufferView": Nor_View, "componentType": 5126, "count": 4,
             "type": "VEC3"},
            {"bufferView": Uv_View, "componentType": 5126, "count": 4,
             "type": "VEC2"},
            {"bufferView": Idx_View, "componentType": 5123, "count": 6,
             "type": "SCALAR"}])
        Meshes.append({"name": name, "primitives": [
            {"attributes": {"POSITION": Base, "NORMAL": Base + 1,
                            "TEXCOORD_0": Base + 2},
             "indices": Base + 3, "material": len(Materials) - 1}]})
        Node = {"mesh": len(Meshes) - 1, "name": name}
        if extras:
            Node["extras"] = extras
        Nodes.append(Node)

    # Plane kind and signed stack offset for one view
    # of the 3D assembly. Copied from
    # Build_Paper_Doll_3D_V1.PY (Kevin, Bit 5).
    def Placement(view, index):
        if view == "Front":
            return "front", Shell_Gap + index * Page_Gap
        if view == "Back":
            return "back", -Shell_Gap - index * Page_Gap
        if view == "SideRight":
            return "sideright", -Shell_Gap - index * Page_Gap
        return "sideleft", Shell_Gap + index * Page_Gap

    # The views this rig actually carries, in the
    # estate's view order. V1 looped over all four
    # View_Order views and so refused any rig that
    # does not carry all four; V2 builds the views
    # the rig has (Duke carries Front and Back).
    # Source: Build_Redrawn_GLB_V1.PY Build_GLB
    # view loop (Kevin), rewritten whole, Fix A.
    Views_Present = [V for V in View_Order if V in Rig["views"]]
    Views_Present += [V for V in Rig["views"] if V not in View_Order]
    Total_Parts = 0
    Joints_Out = {}
    for View_Name in Views_Present:
        View_Data = Rig["views"][View_Name]
        Parts = View_Data["parts"]
        Order = View_Data["layer_order_back_to_front"]
        Joint_By_Child = {}
        for Joint in View_Data["joints"]:
            Joint_By_Child[Joint["child"]] = Joint
        # Multi-root rule (Fix A, Defect 3): a view
        # may have several root parts - Duke's
        # Front has four (Tail, Thigh_Left,
        # Thigh_Right, Torso). Each root is
        # written as a scene-level node at its
        # place in the layer (paint) order,
        # exactly where V1 wrote the single root;
        # no synthetic super-root is added, so a
        # single-root rig's GLB stays byte-
        # identical to V1's. A view with no root
        # at all is still refused.
        Roots = [N for N, Info in Parts.items() if Info["parent"] is None]
        if len(Roots) < 1:
            print("FAIL: " + View_Name + " has no roots")
            return None
        for Name, Info in Parts.items():
            if Info["parent"] is not None and Info["parent"] not in Parts:
                print("FAIL: " + View_Name + " " + Name + " parent missing")
                return None
            Pin = Pin_Of(Info)
            if not (0 <= Pin[0] <= Canvas
                    and 0 <= Pin[1] <= Canvas):
                print("FAIL: " + View_Name + " " + Name +
                      " pin outside canvas")
                return None
        Joints_Out[View_Name] = Joints_Out_For(View_Name, View_Data)
        for Index, Part in enumerate(Order):
            Info = Parts[Part]
            Extras = Extras_For(View_Name, Part, Info, Joint_By_Child,
                                View_Data["joints"])
            Png_Path = Part_Png_Path(Parts_Root, View_Name, Part, Info)
            if Png_Path is None:
                print("FAIL: missing part picture " +
                      os.path.join(Parts_Root, View_Name, Part + ".PNG"))
                return None
            if Mode == "flat":
                Quad(View_Name + "_" + Part, Png_Path, "flat",
                     Index * Page_Gap, Group_X.get(View_Name, 0.0), Extras)
            else:
                Kind, Off = Placement(View_Name, Index)
                Quad(View_Name + "_" + Part, Png_Path, Kind, Off, 0, Extras)
            Total_Parts += 1

    Bin_Data = b"".join(b for b, _ in Bin_Parts)
    Generator = ("Kevin Redrawn Paper Doll Builder V1 (flat)"
                 if Mode == "flat" else
                 "Kevin Redrawn Paper Doll Builder V1 (3D)")
    Top_Extras = {"character": "Human_Man", "canvas": Canvas,
                  "views": Views_Present,
                  "rig": "each part node carries extras.pin, "
                         "extras.parent, extras.label and extras.desc "
                         "in the Model Editor's own form",
                  "joints": Joints_Out}
    if Mode == "3d":
        Top_Extras["assembly"] = (
            "one figure at the origin: Front pages on the front "
            "plane facing +Z, Back pages on the back plane facing "
            "-Z mirrored true, SideRight pages on the profile "
            "plane facing -X, SideLeft pages on the profile "
            "plane facing +X mirrored true")
    Gltf = {"asset": {"version": "2.0", "generator": Generator},
            "scene": 0,
            "scenes": [{"nodes": list(range(len(Nodes)))}],
            "nodes": Nodes, "meshes": Meshes, "materials": Materials,
            "images": Images,
            "textures": [{"source": i} for i in range(len(Images))],
            "accessors": Accessors, "bufferViews": Views,
            "buffers": [{"byteLength": len(Bin_Data)}],
            "extras": Top_Extras}
    Json_Data = json.dumps(Gltf).encode()
    Json_Data += b" " * ((-len(Json_Data)) % 4)
    Glb = (b"glTF" + struct.pack(
        "<II", 2, 12 + 8 + len(Json_Data) + 8 + len(Bin_Data))
        + struct.pack("<I", len(Json_Data)) + b"JSON" + Json_Data
        + struct.pack("<I", len(Bin_Data)) + b"BIN\x00" + Bin_Data)
    with open(Out_Path, "wb") as Handle:
        Handle.write(Glb)
    print(Out_Path + " written: " + str(len(Glb)) + " bytes, " +
          str(Total_Parts) + " rigged parts, " +
          str(len(Nodes)) + " nodes")
    return Total_Parts


# Read one GLB back: its JSON, its binary chunk with
# its header, and its rig points by view and part -
# the parse of Check_Paper_Doll_Bit4_V1.JS (Kevin),
# carried into Python.
def Parse_GLB(Path):
    with open(Path, "rb") as Handle:
        Buf = Handle.read()
    Json_Len = struct.unpack("<I", Buf[12:16])[0]
    Gltf = json.loads(Buf[20:20 + Json_Len].decode("utf-8"))
    Bin_Start = 20 + Json_Len
    Bin_Len = struct.unpack("<I", Buf[Bin_Start:Bin_Start + 4])[0]
    Bin_Chunk = Buf[Bin_Start:Bin_Start + 8 + Bin_Len]
    By_Key = {}
    for I, Node in enumerate(Gltf["nodes"]):
        Ex = Node.get("extras") or {}
        if Ex.get("view") and Ex.get("part"):
            By_Key[Ex["view"] + "|" + Ex["part"]] = I
    return Buf, Gltf, Bin_Chunk, By_Key


# The Bit 4 P checks on one built GLB, read back
# against the caller's rig: census per view, every
# pin and parent exact, a label and a written
# description on every point, limits on every joint's
# child, and the roots of each view as a set - V2
# (Fix A, Defect 3): a view may have several roots
# (Duke's Front has four), so the check compares the
# built GLB's root set per view against the rig's
# root set per view, where V1 demanded exactly one
# root per view. A pinless rig part (pin None) is
# expected at the no-pin sentinel Pin_Of writes.
# Source: Build_Redrawn_GLB_V1.PY Census_Check
# (Kevin), rewritten whole for Fix A.
def Census_Check(Path, Rig):
    Buf, Gltf, Bin_Chunk, By_Key = Parse_GLB(Path)
    Counts = {}
    Mismatch = []
    No_Label_Desc = []
    No_Limits = []
    Bad_Parent = []
    Roots = {}
    for Node in Gltf["nodes"]:
        Ex = Node.get("extras") or {}
        Counts[Ex.get("view")] = Counts.get(Ex.get("view"), 0) + 1
        Want = Rig["views"].get(Ex.get("view"), {}).get(
            "parts", {}).get(Ex.get("part"))
        if Want is None:
            Mismatch.append(Ex.get("view", "?") + "|" + str(Ex.get("part")))
        else:
            Want_Pin = Pin_Of(Want)
            if (abs(Ex["pin"][0] - Want_Pin[0]) > 0.01
                    or abs(Ex["pin"][1] - Want_Pin[1]) > 0.01
                    or (Ex.get("parent") or None)
                    != (Want["parent"] or None)):
                Mismatch.append(
                    Ex.get("view", "?") + "|" + str(Ex.get("part")))
        if not Ex.get("label") or not Ex.get("desc") \
                or len(Ex.get("desc", "")) < 30:
            No_Label_Desc.append(Ex.get("view", "?") + "|" + str(Ex.get("part")))
        if Ex.get("parent") and (Ex["view"] + "|" + Ex["parent"]) not in By_Key:
            Bad_Parent.append(Ex.get("view", "?") + "|" + str(Ex.get("part")))
        if not Ex.get("parent"):
            Roots.setdefault(Ex.get("view"), []).append(Ex.get("part"))
    Joint_Children = set()
    for View, View_Data in Rig["views"].items():
        for Joint in View_Data["joints"]:
            Joint_Children.add(View + "|" + Joint["child"])
    for Key in Joint_Children:
        if Key not in By_Key:
            No_Limits.append(Key)
            continue
        Ex = Gltf["nodes"][By_Key[Key]].get("extras") or {}
        if "limits" not in Ex or "joint" not in Ex:
            No_Limits.append(Key)
    Expected = {V: len(D["parts"]) for V, D in Rig["views"].items()}
    Expected_Roots = {
        V: sorted(N for N, I in D["parts"].items() if I["parent"] is None)
        for V, D in Rig["views"].items()}
    Roots_Out = {V: sorted(Names) for V, Names in Roots.items()}
    Pass = bool(Counts == Expected and not Mismatch
                and not No_Label_Desc and not No_Limits
                and not Bad_Parent
                and Roots_Out == Expected_Roots)
    return {"path": Path, "nodes": len(Gltf["nodes"]), "counts": Counts,
            "expected": Expected, "pin_parent_mismatches": Mismatch,
            "missing_label_or_desc": No_Label_Desc,
            "missing_limits": No_Limits, "bad_parents": Bad_Parent,
            "roots": Roots_Out, "expected_roots": Expected_Roots,
            "pass": Pass}


# The Bit 4 round-trip on the flat GLB, in the
# editor's own form: move one point, add one
# connected point, remove one part (its child
# re-parents to the part's parent), save with the
# binary chunk untouched, reopen, and prove every
# edit is in the saved file. Target choice (V2,
# Fix A): a rig carrying the man's Front foot /
# shin chain takes exactly V1's targets, so the
# man's round-trip is unchanged in every number.
# Any other rig (Duke) takes the first chain its
# GLB carries - a part with a parent and a child,
# in node order - moves that part's first child,
# removes the part, and proves the child re-
# parented to the part's parent; the untouched
# witness is the first point of another view, or
# of the same view outside the chain when the
# rig has a single view.
# Source: Build_Redrawn_GLB_V1.PY Round_Trip
# (Kevin), rewritten whole for Fix A.
def Round_Trip(Flat_Path, Edited_Path):
    Buf, Gltf, Bin_Chunk, By_Key = Parse_GLB(Flat_Path)
    Nodes_Before = len(Gltf["nodes"])
    if ("Front|Part_Foot_Left_V1" in By_Key
            and "Front|Part_Shin_Left_V1" in By_Key
            and "Back|Part_Head_V1" in By_Key):
        Move_Key = "Front|Part_Foot_Left_V1"
        Remove_Key = "Front|Part_Shin_Left_V1"
        Untouched_Key = "Back|Part_Head_V1"
        Add_View = "Front"
        Add_Parent = "Part_Head_V1"
    else:
        Move_Key = Remove_Key = Untouched_Key = None
        Add_View = Add_Parent = None
        Children = {}
        for Node in Gltf["nodes"]:
            Ex = Node.get("extras") or {}
            if Ex.get("parent"):
                Children.setdefault(
                    Ex["view"] + "|" + Ex["parent"], []).append(
                    Ex["view"] + "|" + Ex["part"])
        for Node in Gltf["nodes"]:
            Ex = Node.get("extras") or {}
            Key = Ex.get("view", "") + "|" + Ex.get("part", "")
            if Ex.get("parent") and Children.get(Key):
                Remove_Key = Key
                Move_Key = Children[Key][0]
                Add_View = Ex.get("view")
                Add_Parent = Ex.get("parent")
                break
        for Node in Gltf["nodes"]:
            Ex = Node.get("extras") or {}
            Key = Ex.get("view", "") + "|" + Ex.get("part", "")
            if Ex.get("view") != Add_View:
                Untouched_Key = Key
                break
        if Untouched_Key is None:
            for Node in Gltf["nodes"]:
                Ex = Node.get("extras") or {}
                Key = Ex.get("view", "") + "|" + Ex.get("part", "")
                if Key not in (Move_Key, Remove_Key):
                    Untouched_Key = Key
                    break
    Move_Ex = Gltf["nodes"][By_Key[Move_Key]]["extras"]
    Moved_Pin = [Move_Ex["pin"][0] + 137.0, Move_Ex["pin"][1] + 89.0]
    Untouched_Before = dict(
        Gltf["nodes"][By_Key[Untouched_Key]]["extras"])
    # Move: the child's pin takes the dragged place.
    Move_Ex["pin"] = list(Moved_Pin)
    # Remove: the part goes; its child re-parents
    # to the part's parent, the editor's rule.
    Remove_Ex = Gltf["nodes"][By_Key[Remove_Key]]["extras"]
    Expected_Parent = Remove_Ex["parent"]
    Move_Ex["parent"] = Expected_Parent
    Remove_Index = By_Key[Remove_Key]
    del Gltf["nodes"][Remove_Index]
    # Add: one bare point connected under a part of
    # the edited view, carrying label, description,
    # parent, and pin, as the editor writes a point.
    Added_Extras = {"view": Add_View, "part": "Point_Test_V1",
                    "pin": [640.0, 640.0], "parent": Add_Parent,
                    "label": "Marker Beta",
                    "desc": "harness marker two"}
    Gltf["nodes"].append({"name": Add_View + "_Point_Test_V1",
                          "extras": Added_Extras})
    Gltf["scenes"][0]["nodes"] = list(range(len(Gltf["nodes"])))
    Json_Data = json.dumps(Gltf).encode()
    Json_Data += b" " * ((-len(Json_Data)) % 4)
    Bin_Data = Bin_Chunk[8:]
    Glb = (b"glTF" + struct.pack(
        "<II", 2, 12 + 8 + len(Json_Data) + 8 + len(Bin_Data))
        + struct.pack("<I", len(Json_Data)) + b"JSON" + Json_Data
        + Bin_Chunk)
    with open(Edited_Path, "wb") as Handle:
        Handle.write(Glb)
    # Reopen the saved file and prove the edits.
    Buf2, Gltf2, Bin_Chunk2, By_Key2 = Parse_GLB(Edited_Path)
    Move2 = Gltf2["nodes"][By_Key2[Move_Key]]["extras"] \
        if Move_Key in By_Key2 else {}
    Added_Key = Add_View + "|Point_Test_V1"
    Added2 = Gltf2["nodes"][By_Key2[Added_Key]]["extras"] \
        if Added_Key in By_Key2 else {}
    Untouched_After = Gltf2["nodes"][By_Key2[Untouched_Key]]["extras"] \
        if Untouched_Key in By_Key2 else {}
    Checks = {
        "bin_chunk_byte_identical": Bin_Chunk2 == Bin_Chunk,
        "node_count_before": Nodes_Before,
        "node_count_after": len(Gltf2["nodes"]),
        "moved_pin_present": bool(
            Move2 and abs(Move2["pin"][0] - Moved_Pin[0]) <= 0.01
            and abs(Move2["pin"][1] - Moved_Pin[1]) <= 0.01),
        "moved_pin": Move2.get("pin"),
        "moved_part": Move_Key,
        "removed_part": Remove_Key,
        "removed_part_gone": Remove_Key not in By_Key2,
        "child_reparented_to": Move2.get("parent"),
        "child_reparented": Move2.get("parent") == Expected_Parent,
        "added_point_present": bool(Added2),
        "added_point_extras": Added2,
        "added_point_ok": bool(
            Added2.get("label") == "Marker Beta"
            and Added2.get("desc") == "harness marker two"
            and Added2.get("parent") == Add_Parent
            and Added2.get("pin") == [640.0, 640.0]),
        "untouched_view_unchanged": Untouched_After == Untouched_Before,
        "untouched_part": Untouched_Key,
        "scene_indices_valid": all(
            0 <= I < len(Gltf2["nodes"])
            for I in Gltf2["scenes"][0]["nodes"]),
    }
    Checks["pass"] = bool(
        Checks["bin_chunk_byte_identical"]
        and Checks["node_count_after"] == Nodes_Before
        and Checks["moved_pin_present"]
        and Checks["removed_part_gone"]
        and Checks["child_reparented"]
        and Checks["added_point_ok"]
        and Checks["untouched_view_unchanged"]
        and Checks["scene_indices_valid"])
    return Checks


# The builder's entry point.
def Main(Argv):
    Args = Argv[1:]
    if len(Args) < 2:
        print("usage: Build_Redrawn_GLB_V2.PY <parts folder> "
              "<rig JSON> [output folder]")
        return 2
    Parts_Root = os.path.abspath(Args[0])
    Rig_Path = os.path.abspath(Args[1])
    Out_Dir = os.path.abspath(Args[2]) if len(Args) > 2 else Home
    os.makedirs(Out_Dir, exist_ok=True)
    with open(Rig_Path) as F:
        Rig = json.load(F)
    Flat_Path = os.path.join(Out_Dir, "Redrawn_Paper_Doll_V1.GLB")
    Path_3D = os.path.join(Out_Dir, "Redrawn_Paper_Doll_3D_V1.GLB")
    Edited_Path = os.path.join(Out_Dir, "Redrawn_Paper_Doll_Edited_V1.GLB")
    if Build_GLB(Parts_Root, Rig, "flat", Flat_Path) is None:
        return 1
    if Build_GLB(Parts_Root, Rig, "3d", Path_3D) is None:
        return 1
    Report = {"parts_folder": Parts_Root, "rig_json": Rig_Path,
              "flat": Census_Check(Flat_Path, Rig),
              "three_d": Census_Check(Path_3D, Rig),
              "round_trip": Round_Trip(Flat_Path, Edited_Path)}
    Report["pass"] = bool(Report["flat"]["pass"]
                          and Report["three_d"]["pass"]
                          and Report["round_trip"]["pass"])
    Report_Path = os.path.join(
        Out_Dir, "Build_Redrawn_GLB_Report_V1.JSON")
    with open(Report_Path, "w") as F:
        json.dump(Report, F, indent=1)
    RT = Report["round_trip"]
    print(f"round-trip: nodes {RT['node_count_before']} -> "
          f"{RT['node_count_after']}, bin identical "
          f"{RT['bin_chunk_byte_identical']}, moved "
          f"{RT['moved_pin_present']}, added {RT['added_point_ok']}, "
          f"removed {RT['removed_part_gone']}, reparented "
          f"{RT['child_reparented']}, pass {RT['pass']}")
    print(f"BUILD {'PASS' if Report['pass'] else 'FAIL'}: {Report_Path}")
    return 0 if Report["pass"] else 1


if __name__ == "__main__":
    sys.exit(Main(sys.argv))
