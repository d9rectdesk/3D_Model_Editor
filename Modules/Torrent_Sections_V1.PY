# Torrent_Sections_V1.PY
# Standalone torrent-logic engine for the Model Editor.
# It partitions one GLB mesh into spatial sections, runs
# one named pointwise operation on each section in turn,
# and finishes with a whole-model stitch pass. The stitch
# pass proves that every shared seam vertex received the
# same result in every section and that the joined mesh
# is a closed two-manifold with no boundary edges.
# Scope: geometry is preserved; skinning, animation, and
# textures are not carried into the rewritten geometry.
# Dependencies: Python 3 standard library and NumPy.
# Source: Duke, original work, except the GLB container
# and accessor blocks below, which name their sources.
import argparse
import json
import math
import os
import struct
import sys

import numpy as np


# Read a GLB header, JSON chunk, and binary chunk.
# Source: Parse_GLB in Rig_Mesh_V1.PY (Duke,
# Paper_Creator_V1), copied in structure with the
# return values narrowed to this module's needs.
def Parse_GLB(Path):
    with open(Path, "rb") as Handle:
        Buf = Handle.read()
    if len(Buf) < 20 or Buf[:4] != b"glTF":
        raise ValueError("not a GLB file: " + Path)
    Json_Len = struct.unpack("<I", Buf[12:16])[0]
    Gltf = json.loads(Buf[20:20 + Json_Len].decode("utf-8"))
    Bin_Start = 20 + Json_Len
    Bin_Len = struct.unpack("<I", Buf[Bin_Start:Bin_Start + 4])[0]
    Bin_Off = Bin_Start + 8
    return Gltf, Buf[Bin_Off:Bin_Off + Bin_Len]


# The glTF accessor component table.
# Source: Khronos glTF 2.0 specification, accessor
# componentType and type tables (Khronos Group).
Component_Info = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
Type_Count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3,
              "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


# Decode one accessor as a NumPy array.
# Source: Read_Accessor in Rig_Mesh_V1.PY (Duke,
# Paper_Creator_V1), copied with names shortened.
def Read_Accessor(Gltf, Bin_Data, Index):
    Acc = Gltf["accessors"][Index]
    View = Gltf["bufferViews"][Acc["bufferView"]]
    Fmt, Size = Component_Info[Acc["componentType"]]
    Per = Type_Count[Acc["type"]]
    Count = Acc["count"]
    Start = View.get("byteOffset", 0) + Acc.get("byteOffset", 0)
    Stride = View.get("byteStride")
    Dtype = np.dtype("<" + Fmt)
    if Stride and Stride != Size * Per:
        Raw = np.empty(Count * Per, dtype=Dtype)
        Row = Size * Per
        for Row_Index in range(Count):
            Off = Start + Row_Index * Stride
            Raw[Row_Index * Per:(Row_Index + 1) * Per] = np.frombuffer(
                Bin_Data, dtype=Dtype, count=Per, offset=Off)
    else:
        Raw = np.frombuffer(
            Bin_Data, dtype=Dtype, count=Count * Per,
            offset=Start).copy()
    return Raw.reshape(Count, Per)


# Build one node-local matrix from glTF node fields.
# Source: Duke, original work, written against the
# Khronos glTF 2.0 node transformation rules.
def Node_Matrix(Node):
    if "matrix" in Node:
        return np.array(Node["matrix"], dtype=np.float64).reshape(4, 4).T
    Trans = np.array(Node.get("translation", [0, 0, 0]), dtype=np.float64)
    Scale = np.array(Node.get("scale", [1, 1, 1]), dtype=np.float64)
    X, Y, Z, W = [float(V) for V in Node.get("rotation", [0, 0, 0, 1])]
    Rot = np.array([
        [1 - 2 * (Y * Y + Z * Z), 2 * (X * Y - Z * W), 2 * (X * Z + Y * W)],
        [2 * (X * Y + Z * W), 1 - 2 * (X * X + Z * Z), 2 * (Y * Z - X * W)],
        [2 * (X * Z - Y * W), 2 * (Y * Z + X * W), 1 - 2 * (X * X + Y * Y)]],
        dtype=np.float64)
    Mat = np.eye(4)
    Mat[:3, :3] = Rot @ np.diag(Scale)
    Mat[:3, 3] = Trans
    return Mat


# Collect world transforms for every node.
# Source: Duke, original work.
def World_Matrices(Gltf):
    Nodes = Gltf.get("nodes", [])
    Parents = {}
    for Index, Node in enumerate(Nodes):
        for Child in Node.get("children", []):
            Parents[Child] = Index
    Cache = {}

    # Resolve one node's world transform recursively.
    # Source: Duke, original work.
    def Resolve(Index):
        if Index in Cache:
            return Cache[Index]
        Local = Node_Matrix(Nodes[Index])
        if Index in Parents:
            Cache[Index] = Resolve(Parents[Index]) @ Local
        else:
            Cache[Index] = Local
        return Cache[Index]

    return {Index: Resolve(Index) for Index in range(len(Nodes))}


# Read and merge all indexed or sequential triangles.
# Source: Duke, original work, on Parse_GLB and
# Read_Accessor above. COLOR_0 is preserved when a
# primitive carries it.
def Read_Mesh(Path):
    Gltf, Bin_Data = Parse_GLB(Path)
    Worlds = World_Matrices(Gltf)
    Mesh_Nodes = {}
    for Node_Index, Node in enumerate(Gltf.get("nodes", [])):
        if "mesh" in Node:
            Mesh_Nodes.setdefault(Node["mesh"], []).append(Node_Index)
    Pos_Blocks = []
    Face_Blocks = []
    Color_Blocks = []
    Colour_Width = None
    Mesh_List = list(enumerate(Gltf.get("meshes", [])))
    if not Mesh_List:
        raise ValueError("the input GLB carries no meshes")
    for Mesh_Index, Mesh in Mesh_List:
        Instances = Mesh_Nodes.get(Mesh_Index, [None])
        for Instance in Instances:
            World = np.eye(4) if Instance is None else Worlds[Instance]
            Normal_Mat = np.linalg.inv(World[:3, :3]).T
            for Prim in Mesh["primitives"]:
                if Prim.get("mode", 4) != 4:
                    continue
                Attrs = Prim["attributes"]
                Pos = Read_Accessor(
                    Gltf, Bin_Data, Attrs["POSITION"]).astype(np.float64)
                Pos = (World[:3, :3] @ Pos.T).T + World[:3, 3]
                if "indices" in Prim:
                    Idx = Read_Accessor(
                        Gltf, Bin_Data, Prim["indices"]).reshape(-1)
                else:
                    Idx = np.arange(len(Pos))
                Idx = Idx.reshape(-1, 3).astype(np.int64)
                Offset = sum(len(Block) for Block in Pos_Blocks)
                Pos_Blocks.append(Pos)
                Face_Blocks.append(Idx + Offset)
                if "COLOR_0" in Attrs:
                    Col = Read_Accessor(
                        Gltf, Bin_Data, Attrs["COLOR_0"]).astype(np.float64)
                    if Col.max() > 1.0:
                        Col = Col / 65535.0 if Col.max() > 255.0 else Col / 255.0
                    if Colour_Width is None:
                        Colour_Width = Col.shape[1]
                    if Col.shape[1] != Colour_Width:
                        raise ValueError("mixed COLOR_0 widths are not supported")
                    Color_Blocks.append(Col)
                elif Color_Blocks:
                    raise ValueError("mixed coloured and uncoloured primitives")
    if not Pos_Blocks:
        raise ValueError("the input GLB carries no triangle geometry")
    Positions = np.vstack(Pos_Blocks)
    Faces = np.vstack(Face_Blocks)
    Colours = np.vstack(Color_Blocks) if Color_Blocks else None
    return Weld_Mesh(Positions, Faces, Colours)


# Weld vertices with exactly equal stored coordinates.
# Source: Duke, original work.
def Weld_Mesh(Positions, Faces, Colours=None):
    Keys = {}
    Remap = np.empty(len(Positions), dtype=np.int64)
    Kept = []
    Colour_Rows = []
    for Index, Point in enumerate(Positions):
        Key = Point.astype(np.float64).tobytes()
        if Key not in Keys:
            Keys[Key] = len(Kept)
            Kept.append(Point)
            if Colours is not None:
                Colour_Rows.append(Colours[Index])
        Remap[Index] = Keys[Key]
    New_Faces = Remap[Faces]
    Good = np.array([
        len(set(Face)) == 3 for Face in New_Faces], dtype=bool)
    return {
        "positions": np.array(Kept, dtype=np.float64),
        "faces": New_Faces[Good],
        "colours": None if Colours is None else np.array(Colour_Rows),
    }


# Compute unit face normals and doubled areas.
# Source: Duke, original work.
def Face_Geometry(Mesh):
    Pos = Mesh["positions"]
    Faces = Mesh["faces"]
    Cross = np.cross(
        Pos[Faces[:, 1]] - Pos[Faces[:, 0]],
        Pos[Faces[:, 2]] - Pos[Faces[:, 0]])
    Double_Area = np.linalg.norm(Cross, axis=1)
    Normals = np.zeros_like(Cross)
    Good = Double_Area > 0
    Normals[Good] = Cross[Good] / Double_Area[Good, None]
    return Normals, Double_Area


# Compute smooth vertex normals from face normals.
# Source: Duke, original work.
def Vertex_Normals(Mesh):
    Pos = Mesh["positions"]
    Faces = Mesh["faces"]
    Cross = np.cross(
        Pos[Faces[:, 1]] - Pos[Faces[:, 0]],
        Pos[Faces[:, 2]] - Pos[Faces[:, 0]])
    Out = np.zeros_like(Pos)
    for Corner in range(3):
        np.add.at(Out, Faces[:, Corner], Cross)
    Length = np.linalg.norm(Out, axis=1)
    Good = Length > 0
    Out[Good] = Out[Good] / Length[Good, None]
    return Out


# Build an undirected edge-to-faces map.
# Source: Duke, original work.
def Edge_Map(Faces):
    Edges = {}
    for Face_Index, Face in enumerate(Faces):
        for A, B in ((Face[0], Face[1]), (Face[1], Face[2]),
                     (Face[2], Face[0])):
            Key = (int(min(A, B)), int(max(A, B)))
            Edges.setdefault(Key, []).append(Face_Index)
    return Edges


# Prove whether a mesh is a closed two-manifold.
# Source: Duke, original work.
def Validate_Mesh(Mesh):
    Faces = Mesh["faces"]
    _, Double_Area = Face_Geometry(Mesh)
    Edges = Edge_Map(Faces)
    Boundary = [Edge for Edge, Users in Edges.items() if len(Users) == 1]
    Nonmanifold = [Edge for Edge, Users in Edges.items() if len(Users) > 2]
    Face_Keys = [tuple(sorted(int(V) for V in Face)) for Face in Faces]
    return {
        "vertices": int(len(Mesh["positions"])),
        "triangles": int(len(Faces)),
        "degenerate_triangles": int(np.sum(Double_Area <= 1e-14)),
        "boundary_edges": int(len(Boundary)),
        "nonmanifold_edges": int(len(Nonmanifold)),
        "duplicate_triangles": int(len(Face_Keys) - len(set(Face_Keys))),
        "watertight": bool(
            len(Boundary) == 0 and len(Nonmanifold) == 0
            and np.sum(Double_Area <= 1e-14) == 0
            and len(Face_Keys) == len(set(Face_Keys))),
    }


# Write one unskinned GLB with computed normals.
# Source: the binary chunk assembly pattern in
# Build_Paper_Doll_GLB_V1.PY (Kevin, Humanoid_Rig_V1),
# adapted from paper pages to one solid mesh.
def Write_GLB(Path, Mesh, Extras=None):
    Check = Validate_Mesh(Mesh)
    if Check["degenerate_triangles"]:
        raise ValueError("refusing to write a mesh with degenerate triangles")
    Pos = Mesh["positions"].astype(np.float64)
    Faces = Mesh["faces"].astype(np.int64)
    Normals = Vertex_Normals(Mesh)
    Bin_Parts = []
    Views = []
    Accessors = []

    # Append one aligned binary buffer view.
    # Source: Add_View in Build_Paper_Doll_GLB_V1.PY
    # (Kevin, Humanoid_Rig_V1). This function was
    # rewritten whole on 2026-11-16 after external
    # GLB proofs exposed the accessor-count trap:
    # a glTF accessor count is a count of elements,
    # where one element is a whole vector for VEC
    # types and one number for SCALAR. The caller
    # now states the element count, the array is
    # flattened for its bytes, and the two are
    # cross-checked before anything is written.
    def Add_Array(Data, Target, Component, Type, Count, Min_Max=None):
        Flat = np.asarray(Data).reshape(-1)
        Expected = int(Count) * Type_Count[Type]
        if Flat.size != Expected:
            raise ValueError(
                "accessor element count does not match its array")
        Raw = Flat.tobytes()
        Offset = sum(len(Part) for Part in Bin_Parts)
        Bin_Parts.append(Raw + b"\x00" * ((-len(Raw)) % 4))
        Views.append({"buffer": 0, "byteOffset": Offset,
                      "byteLength": len(Raw), "target": Target})
        Acc = {"bufferView": len(Views) - 1,
               "componentType": Component,
               "count": int(Count), "type": Type}
        if Min_Max is not None:
            Acc["min"] = [float(V) for V in Min_Max[0]]
            Acc["max"] = [float(V) for V in Min_Max[1]]
        Accessors.append(Acc)
        return len(Accessors) - 1

    Pos_Acc = Add_Array(
        Pos.astype("<f4"), 34962, 5126, "VEC3", len(Pos),
        (Pos.min(axis=0), Pos.max(axis=0)))
    Nor_Acc = Add_Array(
        Normals.astype("<f4"), 34962, 5126, "VEC3", len(Normals))
    Attrs = {"POSITION": Pos_Acc, "NORMAL": Nor_Acc}
    if Mesh.get("colours") is not None:
        Col = np.clip(Mesh["colours"], 0.0, 1.0)
        Col_Acc = Add_Array(
            Col.astype("<f4"), 34962, 5126,
            "VEC3" if Col.shape[1] == 3 else "VEC4", len(Col))
        Attrs["COLOR_0"] = Col_Acc
    Index_Type = 5125 if len(Pos) > 65535 else 5123
    Index_Data = Faces.reshape(-1).astype(
        "<u4" if Index_Type == 5125 else "<u2")
    Idx_Acc = Add_Array(
        Index_Data, 34963, Index_Type, "SCALAR", len(Index_Data))
    Bin_Data = b"".join(Bin_Parts)
    Gltf = {
        "asset": {"version": "2.0", "generator": "Torrent_Sections_V1"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TorrentMesh"}],
        "meshes": [{"name": "TorrentMesh", "primitives": [{
            "attributes": Attrs, "indices": Idx_Acc}]}],
        "accessors": Accessors, "bufferViews": Views,
        "buffers": [{"byteLength": len(Bin_Data)}],
        "extras": Extras or {},
    }
    Json_Data = json.dumps(Gltf, separators=(",", ":")).encode()
    Json_Data += b" " * ((-len(Json_Data)) % 4)
    Glb = (
        b"glTF"
        + struct.pack("<II", 2, 12 + 8 + len(Json_Data) + 8 + len(Bin_Data))
        + struct.pack("<I", len(Json_Data)) + b"JSON" + Json_Data
        + struct.pack("<I", len(Bin_Data)) + b"BIN\x00" + Bin_Data)
    with open(Path, "wb") as Handle:
        Handle.write(Glb)
    return {"bytes": len(Glb), "validation": Check}




# Subdivide a sphere mesh by edge midpoints.
# Source: Duke, original work.
def Subdivide_Sphere(Mesh):
    Pos = list(Mesh["positions"])
    Colours = None
    if Mesh.get("colours") is not None:
        Colours = list(Mesh["colours"])
    Cache = {}

    # Return the projected midpoint vertex for an edge.
    # Source: Duke, original work.
    def Midpoint(A, B):
        Key = (int(min(A, B)), int(max(A, B)))
        if Key not in Cache:
            Point = (Pos[A] + Pos[B]) / 2.0
            Point = Point / np.linalg.norm(Point)
            Cache[Key] = len(Pos)
            Pos.append(Point)
            if Colours is not None:
                Colours.append((Colours[A] + Colours[B]) / 2.0)
        return Cache[Key]

    New_Faces = []
    for A, B, C in Mesh["faces"]:
        A, B, C = int(A), int(B), int(C)
        AB = Midpoint(A, B)
        BC = Midpoint(B, C)
        CA = Midpoint(C, A)
        New_Faces.extend([
            [A, AB, CA], [AB, B, BC], [CA, BC, C], [AB, BC, CA]])
    return {"positions": np.array(Pos),
            "faces": np.array(New_Faces, dtype=np.int64),
            "colours": None if Colours is None else np.array(Colours)}


# Make a subdivided icosphere test mesh.
# Source: Duke, original work.
def Make_Test_Sphere(Level=2):
    T = (1 + math.sqrt(5)) / 2
    Verts = np.array([
        [-1, T, 0], [1, T, 0], [-1, -T, 0], [1, -T, 0],
        [0, -1, T], [0, 1, T], [0, -1, -T], [0, 1, -T],
        [T, 0, -1], [T, 0, 1], [-T, 0, -1], [-T, 0, 1]], dtype=np.float64)
    Verts = Verts / np.linalg.norm(Verts, axis=1)[:, None]
    Faces = np.array([
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    Mesh = {"positions": Verts, "faces": Faces, "colours": None}
    for _ in range(Level):
        Mesh = Subdivide_Sphere(Mesh)
    Mesh["colours"] = np.hstack([
        (Mesh["positions"] + 1) / 2,
        np.ones((len(Mesh["positions"]), 1))])
    return Mesh


# Partition faces into spatial sections.
# Source: Duke, original work. Recursive median splits
# on face centroids keep neighbouring faces together
# while balancing the section sizes.
def Partition_Faces(Mesh, Section_Count):
    Faces = Mesh["faces"]
    if Section_Count < 1 or Section_Count > len(Faces):
        raise ValueError("section count must be between 1 and the face count")
    Centres = Mesh["positions"][Faces].mean(axis=1)
    Groups = [list(range(len(Faces)))]
    while len(Groups) < Section_Count:
        Best = None
        for Group_Index, Group in enumerate(Groups):
            if len(Group) < 2:
                continue
            Points = Centres[Group]
            Spread = Points.max(axis=0) - Points.min(axis=0)
            Score = float(Spread.max()) * len(Group)
            if Best is None or Score > Best[0]:
                Best = (Score, Group_Index, int(np.argmax(Spread)))
        if Best is None:
            raise ValueError("could not split the mesh into the requested sections")
        _, Group_Index, Axis = Best
        Group = Groups.pop(Group_Index)
        Ordered = sorted(Group, key=lambda F: (float(Centres[F][Axis]), int(F)))
        Half = len(Ordered) // 2
        Groups.extend([Ordered[:Half], Ordered[Half:]])
    return [np.array(Group, dtype=np.int64) for Group in Groups]


# Extract one section as a local indexed mesh.
# Source: Duke, original work. Global vertex numbers
# travel with the section so the stitch pass can prove
# every seam result instead of guessing by position.
def Extract_Section(Mesh, Face_Indices):
    Faces = Mesh["faces"][Face_Indices]
    Global_Ids = []
    Local_Of = {}
    Local_Faces = []
    for Face in Faces:
        New_Face = []
        for Global in Face:
            Global = int(Global)
            if Global not in Local_Of:
                Local_Of[Global] = len(Global_Ids)
                Global_Ids.append(Global)
            New_Face.append(Local_Of[Global])
        Local_Faces.append(New_Face)
    Global_Ids = np.array(Global_Ids, dtype=np.int64)
    return {
        "global_ids": Global_Ids,
        "positions": Mesh["positions"][Global_Ids].copy(),
        "faces": np.array(Local_Faces, dtype=np.int64),
        "colours": None if Mesh.get("colours") is None else Mesh["colours"][Global_Ids].copy(),
        "source_faces": np.array(Face_Indices, dtype=np.int64),
    }


# Apply one named operation to positions.
# Source: Duke, original work. Every operation is a
# function of the source position alone, which is the
# property that makes section work and whole work
# directly comparable in the proof.
def Apply_Operation(Positions, Operation, Params, Centre):
    Pos = np.array(Positions, dtype=np.float64)
    if Operation == "translate":
        return Pos + np.array(Params["vector"], dtype=np.float64)
    if Operation == "scale":
        return Centre + float(Params["factor"]) * (Pos - Centre)
    if Operation == "rotate":
        Angle = math.radians(float(Params["angle"]))
        Cos = math.cos(Angle)
        Sin = math.sin(Angle)
        Rel = Pos - Centre
        Out = Pos.copy()
        Out[:, 0] = Centre[0] + Cos * Rel[:, 0] - Sin * Rel[:, 1]
        Out[:, 1] = Centre[1] + Sin * Rel[:, 0] + Cos * Rel[:, 1]
        return Out
    if Operation == "wave":
        Out = Pos.copy()
        Out[:, 2] += float(Params["amplitude"]) * np.sin(
            float(Params["frequency"]) * Pos[:, 0] + float(Params["phase"]))
        return Out
    raise ValueError("unknown operation: " + Operation)


# Process each section one at a time.
# Source: Duke, original work.
def Process_Sections(Mesh, Groups, Operation, Params):
    Centre = Mesh["positions"].mean(axis=0)
    Sections = []
    Log = []
    for Index, Group in enumerate(Groups):
        Section = Extract_Section(Mesh, Group)
        Section["positions"] = Apply_Operation(
            Section["positions"], Operation, Params, Centre)
        Sections.append(Section)
        Log.append({
            "section": int(Index),
            "triangles": int(len(Section["faces"])),
            "vertices": int(len(Section["positions"])),
            "status": "complete",
        })
    return Sections, Log


# Join processed sections and collect seam errors.
# Source: Duke, original work.
def Stitch_Sections(Source, Sections, Tolerance=1e-9):
    Joined = np.empty_like(Source["positions"], dtype=np.float64)
    Seen = np.zeros(len(Source["positions"]), dtype=bool)
    Owner = np.full(len(Source["positions"]), -1, dtype=np.int64)
    Errors = []
    for Section_Index, Section in enumerate(Sections):
        for Local_Index, Global in enumerate(Section["global_ids"]):
            Global = int(Global)
            Point = Section["positions"][Local_Index]
            if Seen[Global]:
                Diff = float(np.max(np.abs(Joined[Global] - Point)))
                if Diff > Tolerance:
                    Errors.append({
                        "global_vertex": Global,
                        "sections": [int(Owner[Global]), int(Section_Index)],
                        "max_difference": Diff,
                    })
            else:
                Joined[Global] = Point
                Seen[Global] = True
                Owner[Global] = Section_Index
    Missing = np.where(~Seen)[0]
    for Global in Missing:
        Errors.append({"global_vertex": int(Global), "sections": [],
                       "max_difference": None, "missing": True})
    Mesh = {"positions": Joined, "faces": Source["faces"].copy(),
            "colours": Source.get("colours")}
    return Mesh, Errors


# Run the whole-model stitch pass over joined sections.
# Source: Duke, original work.
def Stitch_Pass(Source, Sections):
    Mesh, Errors = Stitch_Sections(Source, Sections)
    Check = Validate_Mesh(Mesh)
    Report = {
        "seam_mismatches": int(len(Errors)),
        "seam_errors": Errors[:20],
        "validation": Check,
        "pass": bool(len(Errors) == 0 and Check["watertight"]),
    }
    return Mesh, Report


# Run one operation by torrent sections and stitch it.
# Source: Duke, original work.
def Run_Torrent(Mesh, Section_Count, Operation, Params, Verify_Whole=False):
    Groups = Partition_Faces(Mesh, Section_Count)
    Sections, Log = Process_Sections(Mesh, Groups, Operation, Params)
    Out, Stitch = Stitch_Pass(Mesh, Sections)
    Report = {
        "operation": Operation,
        "params": Params,
        "sections": Log,
        "section_count": int(Section_Count),
        "stitch_pass": Stitch,
    }
    if Verify_Whole:
        Centre = Mesh["positions"].mean(axis=0)
        Whole_Pos = Apply_Operation(Mesh["positions"], Operation, Params, Centre)
        Report["whole_model_compare"] = {
            "faces_equal": bool(np.array_equal(Out["faces"], Mesh["faces"])),
            "max_position_difference": float(
                np.max(np.abs(Out["positions"] - Whole_Pos))),
        }
        Report["pass"] = bool(
            Stitch["pass"] and Report["whole_model_compare"]["faces_equal"]
            and Report["whole_model_compare"]["max_position_difference"] <= 1e-12)
    else:
        Report["pass"] = bool(Stitch["pass"])
    return Out, Report


# Find a vertex shared by at least two sections.
# Source: Duke, original work.
def Find_Seam_Vertex(Sections):
    Counts = {}
    for Section in Sections:
        for Global in Section["global_ids"]:
            Counts[int(Global)] = Counts.get(int(Global), 0) + 1
    for Global, Count in sorted(Counts.items()):
        if Count > 1:
            return Global
    raise ValueError("the sections share no seam vertex")


# Run the offline proof for this module.
# Source: Duke, original work.
def Selftest(Report_Path=None):
    Source = Make_Test_Sphere(2)
    Params = {"amplitude": 0.08, "frequency": 3.0, "phase": 0.2}
    Out, Report = Run_Torrent(Source, 6, "wave", Params, Verify_Whole=True)
    if not Report["pass"]:
        raise ValueError("torrent proof failed: " + json.dumps(Report))
    Groups = Partition_Faces(Source, 6)
    Sections, _ = Process_Sections(Source, Groups, "wave", Params)
    Seam = Find_Seam_Vertex(Sections)
    Broken = []
    Offset_Done = False
    for Section in Sections:
        Copy = {
            "global_ids": Section["global_ids"].copy(),
            "positions": Section["positions"].copy(),
            "faces": Section["faces"].copy(),
            "colours": Section["colours"],
            "source_faces": Section["source_faces"],
        }
        if not Offset_Done and Seam in Copy["global_ids"]:
            Local = int(np.where(Copy["global_ids"] == Seam)[0][0])
            Copy["positions"][Local] = Copy["positions"][Local] + np.array(
                [0.01, 0.0, 0.0])
            Offset_Done = True
        Broken.append(Copy)
    _, Broken_Report = Stitch_Pass(Source, Broken)
    if Broken_Report["pass"] or Broken_Report["seam_mismatches"] < 1:
        raise ValueError("the stitch pass missed a broken seam")
    Results = {
        "source": Validate_Mesh(Source),
        "torrent": Report,
        "broken_join": {
            "seam_vertex": int(Seam),
            "caught": True,
            "stitch_pass": Broken_Report,
        },
        "proof": "PASS",
    }
    if Report_Path:
        with open(Report_Path, "w", encoding="utf-8") as Handle:
            json.dump(Results, Handle, indent=2)
    return Results


# Run the command line form of the module.
# Source: Duke, original work.
def Main():
    Parser = argparse.ArgumentParser(
        description="Run a GLB operation by sections, then stitch and prove it.")
    Parser.add_argument("input", nargs="?")
    Parser.add_argument("output", nargs="?")
    Parser.add_argument("--sections", type=int, default=6)
    Parser.add_argument(
        "--operation", choices=["translate", "scale", "rotate", "wave"],
        default="wave")
    Parser.add_argument("--vector", type=float, nargs=3, default=[0.0, 0.0, 0.1])
    Parser.add_argument("--factor", type=float, default=1.05)
    Parser.add_argument("--angle", type=float, default=15.0)
    Parser.add_argument("--amplitude", type=float, default=0.08)
    Parser.add_argument("--frequency", type=float, default=3.0)
    Parser.add_argument("--phase", type=float, default=0.0)
    Parser.add_argument("--verify-whole", action="store_true")
    Parser.add_argument("--report")
    Parser.add_argument("--selftest", action="store_true")
    Args = Parser.parse_args()
    if Args.selftest:
        Selftest(Args.report)
        print("Torrent_Sections selftest: PASS (6 sections, "
              "whole-model difference 0.0, broken join caught)")
        return 0
    if not Args.input or not Args.output:
        Parser.error("input and output are required unless --selftest is used")
    Params = {
        "vector": Args.vector, "factor": Args.factor, "angle": Args.angle,
        "amplitude": Args.amplitude, "frequency": Args.frequency,
        "phase": Args.phase,
    }
    Mesh = Read_Mesh(Args.input)
    Out, Report = Run_Torrent(
        Mesh, Args.sections, Args.operation, Params, Args.verify_whole)
    Written = Write_GLB(Args.output, Out, {"torrent_report": Report})
    Report["output"] = os.path.abspath(Args.output)
    Report["written"] = Written
    if Args.report:
        with open(Args.report, "w", encoding="utf-8") as Handle:
            json.dump(Report, Handle, indent=2)
    print("Torrent_Sections: " + str(Report["section_count"])
          + " sections, stitch "
          + ("PASS" if Report["pass"] else "CHECK"))
    return 0 if Report["pass"] else 2


if __name__ == "__main__":
    sys.exit(Main())
