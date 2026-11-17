# Brushes_V1.PY
# Standalone brush operations for the Model Editor.
# Three operations work directly on GLB geometry:
# a colour brush with size and hardness, an eraser that
# restores only brush-selected edited vertices to an
# original GLB, and a sculpt brush with size, hardness,
# and strength that pushes or pulls the surface and then
# adaptively splits or collapses local triangles.
# Smoothness is measured, not asserted: for every edge
# shared by two faces, the angle between the two face
# normals is a dihedral angle. A jagged edge is defined
# here as a dihedral angle above 120 degrees. Sculpt
# proofs report the maximum, mean, and 95th percentile
# dihedral angles and the jagged-edge count.
# Scope: geometry and COLOR_0 are preserved; skinning,
# animation, and textures are not carried into the
# rewritten geometry.
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
        "asset": {"version": "2.0", "generator": "Brushes_V1"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "BrushMesh"}],
        "meshes": [{"name": "BrushMesh", "primitives": [{
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


# Split the two faces sharing one edge at its midpoint.
# Source: Duke, original work.
def Split_Shared_Edge(Mesh, Edge):
    Faces = [list(map(int, Face)) for Face in Mesh["faces"]]
    Users = Edge_Map(Mesh["faces"]).get(tuple(Edge), [])
    if len(Users) != 2:
        raise ValueError("shared-edge split needs exactly two faces")
    A, B = [int(V) for V in Edge]
    Mid_Pos = (Mesh["positions"][A] + Mesh["positions"][B]) / 2.0
    Positions = np.vstack([Mesh["positions"], Mid_Pos])
    Colours = Mesh.get("colours")
    if Colours is not None:
        Colours = np.vstack([Colours, (Colours[A] + Colours[B]) / 2.0])
    Mid = len(Positions) - 1
    Remove = set(Users)
    New_Faces = [Face for Index, Face in enumerate(Faces)
                 if Index not in Remove]
    for Face_Index in Users:
        Face = Faces[Face_Index]
        Other = [V for V in Face if V not in (A, B)][0]
        for Start in range(3):
            X, Y, Z = Face[Start], Face[(Start + 1) % 3], Face[(Start + 2) % 3]
            if {X, Y} == {A, B} and Z == Other:
                New_Faces.append([X, Mid, Z])
                New_Faces.append([Mid, Y, Z])
                break
        else:
            raise ValueError("could not orient a face for edge split")
    return {"positions": Positions,
            "faces": np.array(New_Faces, dtype=np.int64),
            "colours": Colours}


# Test whether collapsing one edge preserves topology.
# Source: Duke, original work. The link condition is
# the standard manifold edge-collapse guard: the two
# endpoints may share only the neighbours opposite
# the faces that use the edge.
def Collapse_Is_Safe(Mesh, Edge):
    A, B = [int(V) for V in Edge]
    Faces = Mesh["faces"]
    Neighbours_A = set()
    Neighbours_B = set()
    Opposites = set()
    for Face in Faces:
        Face_Set = set(int(V) for V in Face)
        if A in Face_Set:
            Neighbours_A.update(Face_Set - {A})
        if B in Face_Set:
            Neighbours_B.update(Face_Set - {B})
        if A in Face_Set and B in Face_Set:
            Opposites.update(Face_Set - {A, B})
    return Neighbours_A.intersection(Neighbours_B) == Opposites


# Collapse one edge to its midpoint and compact vertices.
# Source: Duke, original work.
def Collapse_Edge(Mesh, Edge):
    A, B = [int(V) for V in Edge]
    Pos = Mesh["positions"].copy()
    Pos[A] = (Pos[A] + Pos[B]) / 2.0
    Colours = Mesh.get("colours")
    if Colours is not None:
        Colours = Colours.copy()
        Colours[A] = (Colours[A] + Colours[B]) / 2.0
    Faces = []
    for Face in Mesh["faces"]:
        New = [A if int(V) == B else int(V) for V in Face]
        if len(set(New)) == 3:
            Faces.append(New)
    Faces = np.array(Faces, dtype=np.int64)
    Used = sorted(set(int(V) for V in Faces.reshape(-1)))
    Remap = {Old: New for New, Old in enumerate(Used)}
    Faces = np.array([[Remap[int(V)] for V in Face] for Face in Faces])
    return {"positions": Pos[Used], "faces": Faces,
            "colours": None if Colours is None else Colours[Used]}


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




# Compute brush falloff weights for mesh vertices.
# Source: Duke, original work. Hardness is the fully
# weighted core fraction of the radius; beyond it the
# weight follows a cubic smoothstep to zero at the rim.
def Brush_Weights(Positions, Centre, Size, Hardness):
    if Size <= 0:
        raise ValueError("brush size must be positive")
    if not 0 <= Hardness <= 1:
        raise ValueError("brush hardness must be between 0 and 1")
    Distance = np.linalg.norm(Positions - np.array(Centre), axis=1)
    T = Distance / float(Size)
    Weights = np.zeros(len(Positions), dtype=np.float64)
    if Hardness >= 1.0:
        Weights[T < 1.0] = 1.0
        return Weights, Distance
    Core = float(Hardness)
    Weights[T <= Core] = 1.0
    Middle = (T > Core) & (T < 1.0)
    X = (1.0 - T[Middle]) / (1.0 - Core)
    Weights[Middle] = X * X * (3.0 - 2.0 * X)
    return Weights, Distance


# Paint vertex colours inside a brush falloff.
# Source: Duke, original work.
def Paint_Brush(Mesh, Centre, Size, Hardness, Colour):
    Positions = Mesh["positions"].copy()
    Colours = Mesh.get("colours")
    if Colours is None:
        Colours = np.ones((len(Positions), 4), dtype=np.float64)
    else:
        Colours = Colours.copy()
    Paint = np.array(Colour, dtype=np.float64)
    if len(Paint) < Colours.shape[1]:
        Paint = np.concatenate([Paint, np.ones(Colours.shape[1] - len(Paint))])
    Paint = Paint[:Colours.shape[1]]
    Weights, _ = Brush_Weights(Positions, Centre, Size, Hardness)
    Before = Colours.copy()
    Colours = Colours * (1 - Weights[:, None]) + Paint[None, :] * Weights[:, None]
    Changed = np.where(
        (Weights > 0) & np.any(np.abs(Colours - Before) > 1e-12, axis=1))[0]
    Out = {"positions": Positions, "faces": Mesh["faces"].copy(),
           "colours": Colours}
    Report = {
        "falloff_vertices": int(np.sum(Weights > 0)),
        "changed_vertices": int(len(Changed)),
        "changed_indices": [int(V) for V in Changed],
        "max_weight": float(Weights.max()) if len(Weights) else 0.0,
    }
    return Out, Report


# Erase edited vertices inside a brush to the original.
# Source: Duke, original work. Selection is the brush
# disc; selected positions and colours are assigned
# from the original arrays, so their written float32
# values are byte-equal to the original values.
def Erase_Brush(Mesh, Original, Centre, Size):
    if Mesh["positions"].shape != Original["positions"].shape:
        raise ValueError("erase needs the original vertex count")
    if not np.array_equal(Mesh["faces"], Original["faces"]):
        raise ValueError("erase needs the original triangle order")
    Positions = Mesh["positions"].copy()
    Colours = None if Mesh.get("colours") is None else Mesh["colours"].copy()
    Distance = np.linalg.norm(
        Positions - np.array(Centre), axis=1)
    Selected = np.where(Distance <= float(Size))[0]
    Changed = []
    for Index in Selected:
        if (not np.array_equal(Positions[Index], Original["positions"][Index])
                or (Colours is not None and Original.get("colours") is not None
                    and not np.array_equal(
                        Colours[Index], Original["colours"][Index]))):
            Changed.append(int(Index))
    Positions[Selected] = Original["positions"][Selected]
    if Colours is not None and Original.get("colours") is not None:
        Colours[Selected] = Original["colours"][Selected]
    Out = {"positions": Positions, "faces": Mesh["faces"].copy(),
           "colours": Colours}
    Report = {
        "selected_vertices": int(len(Selected)),
        "selected_indices": [int(V) for V in Selected],
        "restored_vertices": int(len(Changed)),
        "restored_indices": Changed,
    }
    return Out, Report


# Measure adjacent-face dihedral angles.
# Source: Duke, original work.
def Smoothness_Metrics(Mesh):
    Normals, _ = Face_Geometry(Mesh)
    Angles = []
    for Users in Edge_Map(Mesh["faces"]).values():
        if len(Users) != 2:
            continue
        Dot = float(np.clip(
            np.dot(Normals[Users[0]], Normals[Users[1]]), -1.0, 1.0))
        Angles.append(math.degrees(math.acos(Dot)))
    if not Angles:
        return {"shared_edges": 0, "max_dihedral_degrees": 0.0,
                "mean_dihedral_degrees": 0.0,
                "p95_dihedral_degrees": 0.0,
                "jagged_edges_over_120_degrees": 0}
    Values = np.array(Angles)
    return {
        "shared_edges": int(len(Values)),
        "max_dihedral_degrees": float(Values.max()),
        "mean_dihedral_degrees": float(Values.mean()),
        "p95_dihedral_degrees": float(np.percentile(Values, 95)),
        "jagged_edges_over_120_degrees": int(np.sum(Values > 120.0)),
    }


# Build a vertex-neighbour map from faces.
# Source: Duke, original work.
def Vertex_Neighbours(Faces):
    Neighbours = {}
    for A, B, C in Faces:
        A, B, C = int(A), int(B), int(C)
        Neighbours.setdefault(A, set()).update([B, C])
        Neighbours.setdefault(B, set()).update([A, C])
        Neighbours.setdefault(C, set()).update([A, B])
    return Neighbours


# Adaptively split and collapse triangles near a brush.
# Source: Duke, original work.
def Adaptive_Remesh(Mesh, Centre, Size):
    Out = {"positions": Mesh["positions"].copy(),
           "faces": Mesh["faces"].copy(),
           "colours": None if Mesh.get("colours") is None else Mesh["colours"].copy()}
    Centre = np.array(Centre, dtype=np.float64)
    Lengths = []
    for A, B in Edge_Map(Out["faces"]):
        Lengths.append(float(np.linalg.norm(
            Out["positions"][A] - Out["positions"][B])))
    Desired = float(np.median(Lengths))
    Splits = 0
    for _ in range(2000):
        Pos = Out["positions"]
        Candidates = []
        for Edge in Edge_Map(Out["faces"]):
            Length = float(np.linalg.norm(Pos[Edge[0]] - Pos[Edge[1]]))
            Mid = (Pos[Edge[0]] + Pos[Edge[1]]) / 2.0
            if Length > 1.3 * Desired and np.linalg.norm(Mid - Centre) <= Size * 1.2:
                Candidates.append((Length, Edge))
        if not Candidates:
            break
        Candidates.sort(reverse=True)
        Out = Split_Shared_Edge(Out, Candidates[0][1])
        Splits += 1
    Collapses = 0
    for _ in range(500):
        Pos = Out["positions"]
        Distance = np.linalg.norm(Pos - Centre, axis=1)
        Candidates = []
        for Edge in Edge_Map(Out["faces"]):
            Length = float(np.linalg.norm(Pos[Edge[0]] - Pos[Edge[1]]))
            if (Length < 0.45 * Desired and Distance[Edge[0]] <= Size
                    and Distance[Edge[1]] <= Size):
                Candidates.append((Length, Edge))
        if not Candidates:
            break
        Candidates.sort()
        Done = False
        for _, Edge in Candidates:
            if not Collapse_Is_Safe(Out, Edge):
                continue
            Trial = Collapse_Edge(Out, Edge)
            if Validate_Mesh(Trial)["watertight"]:
                Out = Trial
                Collapses += 1
                Done = True
                break
        if not Done:
            break
    return Out, {"edge_splits": int(Splits),
                 "edge_collapses": int(Collapses),
                 "desired_edge_length": Desired}


# Smooth only the brush-weighted vertices.
# Source: Duke, original work.
def Smooth_Brush_Area(Mesh, Centre, Size, Hardness, Passes=2):
    Out = {"positions": Mesh["positions"].copy(),
           "faces": Mesh["faces"].copy(),
           "colours": Mesh.get("colours")}
    Weights, _ = Brush_Weights(Out["positions"], Centre, Size, Hardness)
    Neighbours = Vertex_Neighbours(Out["faces"])
    for _ in range(Passes):
        Pos = Out["positions"]
        New = Pos.copy()
        for Index, Weight in enumerate(Weights):
            if Weight <= 0 or Index not in Neighbours:
                continue
            Around = sorted(Neighbours[Index])
            Average = Pos[Around].mean(axis=0)
            New[Index] = Pos[Index] + 0.22 * Weight * (Average - Pos[Index])
        Out["positions"] = New
    return Out


# Push or pull a surface region along vertex normals.
# Source: Duke, original work. Direction is +1 for a
# push outward along the normal and -1 for a pull in.
def Sculpt_Brush(Mesh, Centre, Size, Hardness, Strength, Direction):
    if Direction not in (-1, 1):
        raise ValueError("sculpt direction must be +1 or -1")
    Weights, _ = Brush_Weights(Mesh["positions"], Centre, Size, Hardness)
    Normals = Vertex_Normals(Mesh)
    Positions = Mesh["positions"] + Normals * (
        float(Direction) * float(Strength) * Weights)[:, None]
    Out = {"positions": Positions, "faces": Mesh["faces"].copy(),
           "colours": None if Mesh.get("colours") is None else Mesh["colours"].copy()}
    Out, Remesh = Adaptive_Remesh(Out, Centre, Size)
    Out = Smooth_Brush_Area(Out, Centre, Size, Hardness)
    Report = {
        "displaced_vertices_before_remesh": int(np.sum(Weights > 0)),
        "direction": int(Direction),
        "strength": float(Strength),
        "remesh": Remesh,
        "smoothness": Smoothness_Metrics(Out),
        "validation": Validate_Mesh(Out),
    }
    return Out, Report


# Convert a set of rows to raw float32 byte strings.
# Source: Duke, original work.
def Float32_Bytes(Array):
    return set(
        Row.astype("<f4").tobytes() for Row in np.array(Array))


# Run the offline proof for this module.
# Source: Duke, original work.
def Selftest(Report_Path=None):
    Source = Make_Test_Sphere(3)
    Centre_Index = int(np.argmax(Source["positions"][:, 0]))
    Centre = Source["positions"][Centre_Index]
    Size = 0.5
    Painted, Paint_Report = Paint_Brush(
        Source, Centre, Size, 0.35, [0.05, 0.15, 0.95, 1.0])
    Distance = np.linalg.norm(Source["positions"] - Centre, axis=1)
    Outside = Distance > Size
    if not np.array_equal(Painted["colours"][Outside], Source["colours"][Outside]):
        raise ValueError("paint changed a vertex outside the brush")
    if not np.array_equal(Painted["positions"], Source["positions"]):
        raise ValueError("paint moved a vertex")
    Changed_Set = set(Paint_Report["changed_indices"])
    if not Changed_Set or not Changed_Set.issubset(
            set(np.where(Distance <= Size)[0].tolist())):
        raise ValueError("paint changed the wrong vertex set")
    Edited = {"positions": Painted["positions"].copy(),
              "faces": Painted["faces"].copy(),
              "colours": Painted["colours"].copy()}
    Far_Index = int(np.argmax(Distance))
    Edited["positions"][Centre_Index] += np.array([0.01, 0.0, 0.0])
    Edited["positions"][Far_Index] += np.array([0.02, 0.0, 0.0])
    Erased, Erase_Report = Erase_Brush(Edited, Source, Centre, Size)
    Selected = np.array(Erase_Report["selected_indices"], dtype=np.int64)
    if Erased["positions"][Selected].astype("<f4").tobytes() != (
            Source["positions"][Selected].astype("<f4").tobytes()):
        raise ValueError("erase did not restore selected positions byte-equal")
    if Erased["colours"][Selected].astype("<f4").tobytes() != (
            Source["colours"][Selected].astype("<f4").tobytes()):
        raise ValueError("erase did not restore selected colours byte-equal")
    if np.array_equal(Erased["positions"][Far_Index], Source["positions"][Far_Index]):
        raise ValueError("erase disturbed an edited vertex outside the brush")
    Sculpted, Sculpt_Report = Sculpt_Brush(
        Source, Centre, Size, 0.3, 0.28, -1)
    if not Sculpt_Report["validation"]["watertight"]:
        raise ValueError("sculpt output is not watertight")
    if Sculpt_Report["smoothness"]["jagged_edges_over_120_degrees"] != 0:
        raise ValueError("sculpt output has jagged edges")
    Outside_Bytes = Float32_Bytes(Source["positions"][Outside])
    Sculpt_Bytes = Float32_Bytes(Sculpted["positions"])
    if not Outside_Bytes.issubset(Sculpt_Bytes):
        raise ValueError("sculpt changed geometry outside the brush")
    Results = {
        "source": Validate_Mesh(Source),
        "paint": Paint_Report,
        "paint_outside_unchanged": True,
        "erase": Erase_Report,
        "erase_selected_byte_equal": True,
        "erase_outside_edit_preserved": True,
        "sculpt": Sculpt_Report,
        "sculpt_outside_geometry_preserved": True,
        "proof": "PASS",
    }
    if Report_Path:
        with open(Report_Path, "w", encoding="utf-8") as Handle:
            json.dump(Results, Handle, indent=2)
    return Results


# Run the command line form of the module.
# Source: Duke, original work.
def Main():
    Parser = argparse.ArgumentParser(description="Apply a GLB brush operation.")
    Parser.add_argument("mode", nargs="?", choices=["paint", "erase", "sculpt"])
    Parser.add_argument("input", nargs="?")
    Parser.add_argument("output", nargs="?")
    Parser.add_argument("--original")
    Parser.add_argument("--center", type=float, nargs=3, required=False)
    Parser.add_argument("--size", type=float, default=0.5)
    Parser.add_argument("--hardness", type=float, default=0.35)
    Parser.add_argument("--strength", type=float, default=0.2)
    Parser.add_argument(
        "--direction", choices=["push", "pull"], default="push")
    Parser.add_argument(
        "--colour", type=float, nargs=4,
        default=[0.05, 0.15, 0.95, 1.0])
    Parser.add_argument("--report")
    Parser.add_argument("--selftest", action="store_true")
    Args = Parser.parse_args()
    if Args.selftest:
        Results = Selftest(Args.report)
        print("Brushes selftest: PASS (paint "
              + str(Results["paint"]["changed_vertices"]) + ", erase "
              + str(Results["erase"]["restored_vertices"])
              + " byte-equal, sculpt watertight, max dihedral "
              + str(round(
                  Results["sculpt"]["smoothness"]["max_dihedral_degrees"], 1))
              + " degrees)")
        return 0
    if not Args.mode or not Args.input or not Args.output or Args.center is None:
        Parser.error("mode, input, output, and --center are required unless --selftest is used")
    Mesh = Read_Mesh(Args.input)
    if Args.mode == "paint":
        Out, Report = Paint_Brush(
            Mesh, Args.center, Args.size, Args.hardness, Args.colour)
    elif Args.mode == "erase":
        if not Args.original:
            Parser.error("erase requires --original")
        Out, Report = Erase_Brush(
            Mesh, Read_Mesh(Args.original), Args.center, Args.size)
    else:
        Out, Report = Sculpt_Brush(
            Mesh, Args.center, Args.size, Args.hardness, Args.strength,
            1 if Args.direction == "push" else -1)
    Written = Write_GLB(Args.output, Out, {"brush_report": Report})
    Report["output"] = os.path.abspath(Args.output)
    Report["written"] = Written
    if Args.report:
        with open(Args.report, "w", encoding="utf-8") as Handle:
            json.dump(Report, Handle, indent=2)
    if Args.mode == "paint":
        print("Brushes paint: " + str(Report["changed_vertices"])
              + " vertices coloured")
    elif Args.mode == "erase":
        print("Brushes erase: " + str(Report["restored_vertices"])
              + " vertices restored")
    else:
        print("Brushes sculpt: "
              + str(Report["validation"]["triangles"]) + " triangles, "
              + "watertight, max dihedral "
              + str(round(
                  Report["smoothness"]["max_dihedral_degrees"], 1))
              + " degrees")
    if Args.mode == "sculpt":
        return 0 if Report["validation"]["watertight"] and (
            Report["smoothness"]["jagged_edges_over_120_degrees"] == 0) else 2
    return 0


if __name__ == "__main__":
    sys.exit(Main())
