import json, os, struct

# Build_Human_3D_GLB_V1.PY
# The human man as ONE assembled figure in a single GLB
# (Solomon's order, 2026-11-14): the front layers stacked in
# their order at graded depths with the back layers behind
# them, and the side layers standing on the profile plane with
# their mirrored backs facing the other way - so he can be
# orbited and seen from the front, the back, and both sides,
# and every part node carries its rig pin and parent in extras
# for the Model Editor. Built on Build_Human_GLB_V1.PY's proven
# GLB writer. Duke.
Home = os.path.dirname(os.path.abspath(__file__))
OUT = Home

bin_parts, views, accessors, meshes, materials, images, nodes = [], [], [], [], [], [], []

def add_view(data, target=None):
    off = sum(len(b) for b, _ in bin_parts)
    bin_parts.append((data + b"\x00" * ((-len(data)) % 4), target))
    v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
    if target: v["target"] = target
    views.append(v)
    return len(views) - 1

def add_mesh(name, png_path, pos, nor, uv, idx, lo, hi, extras=None, ds=False):
    import io
    from PIL import Image
    im = Image.open(png_path).convert("RGBA")
    if im.width > 1024:
        im = im.resize((1024, 1024), Image.LANCZOS)
    bio = io.BytesIO(); im.save(bio, "PNG")
    img_view = add_view(bio.getvalue())
    images.append({"bufferView": img_view, "mimeType": "image/png", "name": name})
    ti = len(images) - 1
    materials.append({"name": name, "pbrMetallicRoughness":
                      {"baseColorTexture": {"index": ti}, "metallicFactor": 0.0, "roughnessFactor": 1.0},
                      "alphaMode": "MASK", "alphaCutoff": 0.35, "doubleSided": ds})
    pv = add_view(struct.pack("<12f", *pos), 34962)
    nv = add_view(struct.pack("<12f", *nor), 34962)
    tv = add_view(struct.pack("<8f", *uv), 34962)
    iv = add_view(struct.pack("<6H", *idx), 34963)
    base = len(accessors)
    accessors.extend([
        {"bufferView": pv, "componentType": 5126, "count": 4, "type": "VEC3",
         "min": lo, "max": hi},
        {"bufferView": nv, "componentType": 5126, "count": 4, "type": "VEC3"},
        {"bufferView": tv, "componentType": 5126, "count": 4, "type": "VEC2"},
        {"bufferView": iv, "componentType": 5123, "count": 6, "type": "SCALAR"}])
    meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": base, "NORMAL": base + 1, "TEXCOORD_0": base + 2}, "indices": base + 3, "material": len(materials) - 1}]})
    node = {"mesh": len(meshes) - 1, "name": name}
    if extras:
        node["extras"] = extras
    nodes.append(node)

def front_quad(name, png, z, extras=None, ds=False):
    pos = [-1, -1, z, 1, -1, z, 1, 1, z, -1, 1, z]
    add_mesh(name, png, pos, [0, 0, 1] * 4, [0, 1, 1, 1, 1, 0, 0, 0],
             [0, 1, 2, 0, 2, 3], [-1, -1, z], [1, 1, z], extras, ds)

def back_quad(name, png, z):
    pos = [1, 1, z, -1, 1, z, -1, -1, z, 1, -1, z]
    add_mesh(name, png, pos, [0, 0, -1] * 4, [0, 0, 1, 0, 1, 1, 0, 1],
             [0, 2, 1, 0, 3, 2], [-1, -1, z], [1, 1, z])

def side_quad(name, png, x, extras=None, ds=False):
    # Profile plane, toe toward +Z (the way the figure faces).
    pos = [x, -1, 1, x, -1, -1, x, 1, -1, x, 1, 1]
    add_mesh(name, png, pos, [1, 0, 0] * 4, [0, 1, 1, 1, 1, 0, 0, 0],
             [0, 1, 2, 0, 2, 3], [x, -1, -1], [x, 1, 1], extras, ds)

def side_back_quad(name, png, x):
    pos = [x, 1, 1, x, 1, -1, x, -1, -1, x, -1, 1]
    add_mesh(name, png, pos, [-1, 0, 0] * 4, [0, 0, 1, 0, 1, 1, 0, 1],
             [0, 2, 1, 0, 3, 2], [x, -1, -1], [x, 1, 1])

total = 0
# The front figure: front layers in paint order at graded
# depths, each with its true back layer behind it. The back
# layers stack by the BACK view's own order, so the figure
# reads right from behind too - a stack that only follows the
# front order inverts from behind (Solomon's catch, 2026-11-14:
# the neck sat in front of the face from behind).
brig = json.load(open(os.path.join(Home, "Rig_Points_Humanoid_Back_V1.JSON")))
back_index = {p: j for j, p in enumerate(brig["layer_order_back_to_front"])}
rig = json.load(open(os.path.join(Home, "Rig_Points_Humanoid_V1.JSON")))
order = rig["layer_order_back_to_front"]
for i, part in enumerate(order):
    z = (i - (len(order) - 1) / 2) * 0.004
    info = rig["parts"][part]
    extras = {"view": "Figure", "part": part,
              "pin": info["pin"], "parent": info["parent"]}
    back_png = os.path.join(Home, "Parts_Back_V1", part + ".PNG")
    has_back = os.path.exists(back_png)
    front_quad("Figure_" + part, os.path.join(Home, "Parts_V1", part + ".PNG"),
               z, extras, ds=not has_back)
    if has_back:
        back_quad("FigureBack_" + part, back_png,
                  -0.02 - back_index[part] * 0.004)
    total += 1

# The profile: side layers on the YZ plane, mirrored backs
# facing the other way, so both sides read as the man.
sbrig = json.load(open(os.path.join(Home, "Rig_Points_Humanoid_Side_Back_V1.JSON")))
sback_index = {p.replace("_Side_Back_V1", "_V1"): j
               for j, p in enumerate(sbrig["layer_order_back_to_front"])}
srig = json.load(open(os.path.join(Home, "Rig_Points_Humanoid_Side_V1.JSON")))
sorder = srig["layer_order_back_to_front"]
for i, part in enumerate(sorder):
    x = 0.002 + i * 0.0012
    info = srig["parts"][part]
    extras = {"view": "FigureSide", "part": part,
              "pin": info["pin"], "parent": info["parent"]}
    back_png = os.path.join(Home, "Parts_Side_Back_V1",
                            part.replace("_V1", "_Side_Back_V1") + ".PNG")
    has_back = os.path.exists(back_png)
    side_quad("FigureSide_" + part,
              os.path.join(Home, "Parts_Side_V1", part + ".PNG"),
              x, extras, ds=not has_back)
    if has_back:
        side_back_quad("FigureSideBack_" + part, back_png,
                       -(0.002 + sback_index[part] * 0.0012))
    total += 1

bin_data = b"".join(b for b, _ in bin_parts)
gltf = {"asset": {"version": "2.0", "generator": "Duke Human 3D GLB Builder V1"},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes,
        "meshes": meshes, "materials": materials, "images": images,
        "textures": [{"source": i} for i in range(len(images))],
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(bin_data)}],
        "extras": {"character": "Human_Man", "canvas": 2048,
                   "views": ["Figure", "FigureSide"],
                   "build": "one assembled figure: front layers in order at graded depths with true backs behind, side layers on the profile plane with mirrored backs",
                   "rig": "each part node carries extras.pin (canvas pixels) and extras.parent"}}
json_data = json.dumps(gltf).encode()
json_data += b" " * ((-len(json_data)) % 4)
glb = (b"glTF" + struct.pack("<II", 2, 12 + 8 + len(json_data) + 8 + len(bin_data))
       + struct.pack("<I", len(json_data)) + b"JSON" + json_data
       + struct.pack("<I", len(bin_data)) + b"BIN\x00" + bin_data)
path = os.path.join(OUT, "Human_Man_3D.GLB")
open(path, "wb").write(glb)
print(f"Human_Man_3D.GLB written: {path} {len(glb)} bytes, "
      f"{total} parts, {len(meshes)} layers ({len(images)} pictures)")
