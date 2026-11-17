# Detail_And_Slider_V1.PY
# Standalone triangle-count engine for the Model Editor.
# It reads one GLB, merges its triangle geometry, changes
# the triangle count toward a requested target, and writes
# one clean GLB. Decimation uses topology-checked shortest
# edge collapses. Growth uses Loop subdivision when a full
# level fits under the target and topology-checked shared
# edge splits when a smaller increase is needed.
# The slider contract is data, not a widget: the report
# names the input count, target count, achieved count,
# tolerance, slider top, and knob position. A request to
# make a model more detailed raises both the top and knob.
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
import tempfile

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
        "asset": {"version": "2.0", "generator": "Detail_And_Slider_V1"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "DetailMesh"}],
        "meshes": [{"name": "DetailMesh", "primitives": [{
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


# Perform one Loop subdivision level.
# Source: Duke, original work, implementing the Loop
# subdivision weights stated in Charles Loop's 1987
# master's thesis, Smooth Subdivision Surfaces Based
# on Triangles (University of Utah).
def Loop_Subdivide(Mesh):
    Pos = Mesh["positions"]
    Faces = Mesh["faces"]
    Edges = Edge_Map(Faces)
    Neighbours = {Index: set() for Index in range(len(Pos))}
    Edge_Mid = {}
    New_Pos = []
    New_Col = [] if Mesh.get("colours") is not None else None
    for A, B in Edges:
        Neighbours[A].add(B)
        Neighbours[B].add(A)
    for Index, Point in enumerate(Pos):
        Around = sorted(Neighbours[Index])
        N = len(Around)
        Beta = (0.625 - (0.375 + 0.25 * math.cos(2 * math.pi / N)) ** 2) / N
        New_Point = (1 - N * Beta) * Point + Beta * Pos[Around].sum(axis=0)
        New_Pos.append(New_Point)
        if New_Col is not None:
            Col = Mesh["colours"]
            New_Col.append(
                (1 - N * Beta) * Col[Index] + Beta * Col[Around].sum(axis=0))
    for Edge, Users in Edges.items():
        if len(Users) != 2:
            raise ValueError("Loop subdivision needs a closed manifold")
        A, B = Edge
        Opposites = []
        for Face_Index in Users:
            Opposites.extend(
                V for V in Faces[Face_Index] if int(V) not in Edge)
        C, D = [int(V) for V in Opposites]
        Edge_Mid[Edge] = len(New_Pos)
        New_Pos.append(0.375 * (Pos[A] + Pos[B]) + 0.125 * (Pos[C] + Pos[D]))
        if New_Col is not None:
            Col = Mesh["colours"]
            New_Col.append(
                0.375 * (Col[A] + Col[B]) + 0.125 * (Col[C] + Col[D]))
    New_Faces = []
    for A, B, C in Faces:
        A, B, C = int(A), int(B), int(C)
        AB = Edge_Mid[(min(A, B), max(A, B))]
        BC = Edge_Mid[(min(B, C), max(B, C))]
        CA = Edge_Mid[(min(C, A), max(C, A))]
        New_Faces.extend([
            [A, AB, CA], [AB, B, BC], [CA, BC, C], [AB, BC, CA]])
    return {"positions": np.array(New_Pos),
            "faces": np.array(New_Faces, dtype=np.int64),
            "colours": None if New_Col is None else np.array(New_Col)}


# Grow a mesh to a target with subdivision and splits.
# Source: Duke, original work.
def Grow_To_Target(Mesh, Target):
    Out = Mesh
    Actions = {"loop_levels": 0, "edge_splits": 0}
    while len(Out["faces"]) * 4 <= Target:
        Out = Loop_Subdivide(Out)
        Actions["loop_levels"] += 1
    while len(Out["faces"]) < Target:
        if Target - len(Out["faces"]) == 1:
            break
        Edges = Edge_Map(Out["faces"])
        Pos = Out["positions"]
        Longest = max(
            Edges, key=lambda E: float(np.linalg.norm(Pos[E[0]] - Pos[E[1]])))
        Out = Split_Shared_Edge(Out, Longest)
        Actions["edge_splits"] += 1
    return Out, Actions


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


# Shrink a mesh by safe shortest-edge collapses.
# Source: Duke, original work.
def Shrink_To_Target(Mesh, Target):
    Out = Mesh
    Collapses = 0
    while len(Out["faces"]) > Target:
        if Target - len(Out["faces"]) == -1:
            break
        Pos = Out["positions"]
        Edges = sorted(
            Edge_Map(Out["faces"]),
            key=lambda E: float(np.linalg.norm(Pos[E[0]] - Pos[E[1]])))
        Done = False
        for Edge in Edges:
            if not Collapse_Is_Safe(Out, Edge):
                continue
            Trial = Collapse_Edge(Out, Edge)
            Check = Validate_Mesh(Trial)
            if Check["watertight"]:
                Out = Trial
                Collapses += 1
                Done = True
                break
        if not Done:
            break
    return Out, {"edge_collapses": Collapses}


# Change a mesh to a requested triangle count.
# Source: Duke, original work.
def Change_Detail(Mesh, Target):
    if Target < 4:
        raise ValueError("target triangle count must be at least 4")
    if len(Mesh["faces"]) < Target:
        Out, Actions = Grow_To_Target(Mesh, Target)
    elif len(Mesh["faces"]) > Target:
        Out, Actions = Shrink_To_Target(Mesh, Target)
    else:
        Out, Actions = Mesh, {"unchanged": True}
    Tolerance = max(2, int(math.ceil(Target * 0.01)))
    Report = {
        "input_triangles": int(len(Mesh["faces"])),
        "target_triangles": int(Target),
        "output_triangles": int(len(Out["faces"])),
        "difference": int(len(Out["faces"]) - Target),
        "tolerance_triangles": int(Tolerance),
        "within_tolerance": bool(abs(len(Out["faces"]) - Target) <= Tolerance),
        "slider_top": int(max(len(Mesh["faces"]), Target)),
        "slider_knob": int(len(Out["faces"])),
        "actions": Actions,
        "validation": Validate_Mesh(Out),
    }
    return Out, Report


# Make a subdivided icosphere test mesh.
# Source: Duke, original work.
def Make_Test_Sphere(Level=3):
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
        Mesh = Loop_Subdivide(Mesh)
        Mesh["positions"] = Mesh["positions"] / np.linalg.norm(
            Mesh["positions"], axis=1)[:, None]
    Colours = np.hstack([
        (Mesh["positions"] + 1) / 2,
        np.ones((len(Mesh["positions"]), 1))])
    Mesh["colours"] = Colours
    return Mesh


# Run the offline proof for this module.
# Source: Duke, original work.
def Selftest(Report_Path=None):
    Source = Make_Test_Sphere(3)
    Results = {"source": Validate_Mesh(Source), "cases": []}
    for Target in (500, 2000):
        Out, Report = Change_Detail(Source, Target)
        if not Report["within_tolerance"]:
            raise ValueError("target missed: " + json.dumps(Report))
        if not Report["validation"]["watertight"]:
            raise ValueError("output is not watertight: " + json.dumps(Report))
        Results["cases"].append(Report)
    Results["proof"] = "PASS"
    if Report_Path:
        with open(Report_Path, "w", encoding="utf-8") as Handle:
            json.dump(Results, Handle, indent=2)
    return Results


# Run the command line form of the module.
# Source: Duke, original work.
def Main():
    Parser = argparse.ArgumentParser(description="Change a GLB triangle count.")
    Parser.add_argument("input", nargs="?")
    Parser.add_argument("output", nargs="?")
    Parser.add_argument("--target", type=int)
    Parser.add_argument("--more-detailed", action="store_true")
    Parser.add_argument("--report")
    Parser.add_argument("--selftest", action="store_true")
    Args = Parser.parse_args()
    if Args.selftest:
        Results = Selftest(Args.report)
        Cases = Results["cases"]
        print("Detail_And_Slider selftest: PASS ("
              + str(Cases[0]["input_triangles"]) + " -> "
              + str(Cases[0]["output_triangles"]) + " and -> "
              + str(Cases[1]["output_triangles"])
              + ", exact, watertight)")
        return 0
    if not Args.input or not Args.output:
        Parser.error("input and output are required unless --selftest is used")
    Mesh = Read_Mesh(Args.input)
    Target = Args.target
    if Args.more_detailed:
        Target = int(math.ceil(len(Mesh["faces"]) * 1.5))
    if Target is None:
        Parser.error("--target or --more-detailed is required")
    Out, Report = Change_Detail(Mesh, Target)
    Written = Write_GLB(Args.output, Out, {"detail_report": Report})
    Report["output"] = os.path.abspath(Args.output)
    Report["written"] = Written
    if Args.report:
        with open(Args.report, "w", encoding="utf-8") as Handle:
            json.dump(Report, Handle, indent=2)
    Passed = Report["within_tolerance"] and Report["validation"]["watertight"]
    print("Detail_And_Slider: " + str(Report["input_triangles"]) + " -> "
          + str(Report["output_triangles"]) + " triangles (target "
          + str(Report["target_triangles"]) + "), watertight, "
          + ("PASS" if Passed else "CHECK"))
    return 0 if Passed else 2


if __name__ == "__main__":
    sys.exit(Main())
