import json, os, struct

# Build_Human_3D_GLB_V1.PY
# The human man for the Model Editor's 3D view: his front,
# back, and side standing side by side as three separate
# groups - never overlapped into one figure (Solomon's
# ruling, 2026-11-14: the views are edited separately, and
# overlapping them made the model unusable). The build is
# Build_Human_GLB_V1.PY's proven construction unchanged,
# writing the 3D file instead of the paper file. Duke.
# The human man as ONE paper GLB: his front, back, and side
# standing side by side, every view cut from its own base image
# (Solomon's ruling, 2026-11-14). Each part is two paper layers
# back to back - the part on the front, its other-view namesake
# on the back - and every part node carries its rig in extras:
# the pin it turns on and the part it hangs from, so the Model
# Editor reads the points from this file and nothing else.
# Built on Build_Duke_GLB_V1.PY's proven GLB writer. Duke.
Home = os.path.dirname(os.path.abspath(__file__))
OUT = Home
PAGE_GAP = 0.03
GROUP_X = {"Front": -2.3, "Back": 0.0, "Side": 2.3}

# (view, parts folder, rig file, back folder, back name change,
#  back rig file, back-order name -> this view's part name)
# The back pages stack by the BACK source's own layer order,
# so each group also reads right from behind - a stack that
# only follows the front order inverts from behind (Solomon's
# catch, 2026-11-14: the neck sat in front of the face).
VIEWS = [
    ("Front", "Parts_V1", "Rig_Points_Humanoid_V1.JSON",
     "Parts_Back_V1", lambda n: n,
     "Rig_Points_Humanoid_Back_V1.JSON", lambda n: n),
    ("Back", "Parts_Back_V1", "Rig_Points_Humanoid_Back_V1.JSON",
     "Parts_V1", lambda n: n,
     "Rig_Points_Humanoid_V1.JSON", lambda n: n),
    ("Side", "Parts_Side_V1", "Rig_Points_Humanoid_Side_V1.JSON",
     "Parts_Side_Back_V1", lambda n: n.replace("_V1", "_Side_Back_V1"),
     "Rig_Points_Humanoid_Side_Back_V1.JSON",
     lambda n: n.replace("_Side_Back_V1", "_V1")),
]

bin_parts, views, accessors, meshes, materials, images, nodes = [], [], [], [], [], [], []

def add_view(data, target=None):
    off = sum(len(b) for b, _ in bin_parts)
    bin_parts.append((data + b"\x00" * ((-len(data)) % 4), target))
    v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
    if target: v["target"] = target
    views.append(v)
    return len(views) - 1

def quad(name, png_path, z, ox, back=False, ds=False, extras=None):
    # Textures ride at 1024: crisp on a two-unit model, a quarter
    # of the bytes of the 2048 masters.
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
    if not back:
        pos = struct.pack("<12f", ox - 1, -1, z, ox + 1, -1, z, ox + 1, 1, z, ox - 1, 1, z)
        nor = struct.pack("<12f", *([0, 0, 1] * 4))
        uv = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
        idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3)
    else:
        pos = struct.pack("<12f", ox + 1, 1, z, ox - 1, 1, z, ox - 1, -1, z, ox + 1, -1, z)
        nor = struct.pack("<12f", *([0, 0, -1] * 4))
        uv = struct.pack("<8f", 0, 0, 1, 0, 1, 1, 0, 1)
        idx = struct.pack("<6H", 0, 2, 1, 0, 3, 2)
    pv, nv, tv, iv = add_view(pos, 34962), add_view(nor, 34962), add_view(uv, 34962), add_view(idx, 34963)
    base = len(accessors)
    accessors.extend([
        {"bufferView": pv, "componentType": 5126, "count": 4, "type": "VEC3",
         "min": [ox - 1, -1, z], "max": [ox + 1, 1, z]},
        {"bufferView": nv, "componentType": 5126, "count": 4, "type": "VEC3"},
        {"bufferView": tv, "componentType": 5126, "count": 4, "type": "VEC2"},
        {"bufferView": iv, "componentType": 5123, "count": 6, "type": "SCALAR"}])
    meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": base, "NORMAL": base + 1, "TEXCOORD_0": base + 2}, "indices": base + 3, "material": len(materials) - 1}]})
    node = {"mesh": len(meshes) - 1, "name": name}
    if extras:
        node["extras"] = extras
    nodes.append(node)

total_parts = 0
for view_name, folder, rig_file, back_folder, back_name, back_rig_file, back_to_part in VIEWS:
    rig = json.load(open(os.path.join(Home, rig_file)))
    order = rig["layer_order_back_to_front"]
    brig = json.load(open(os.path.join(Home, back_rig_file)))
    back_z = {back_to_part(p): -0.0015 - j * PAGE_GAP
              for j, p in enumerate(brig["layer_order_back_to_front"])}
    ox = GROUP_X[view_name]
    for i, part in enumerate(order):
        z = i * PAGE_GAP
        info = rig["parts"][part]
        extras = {"view": view_name, "part": part,
                  "pin": info["pin"], "parent": info["parent"]}
        back_png = os.path.join(Home, back_folder, back_name(part) + ".PNG")
        has_back = os.path.exists(back_png)
        # No back picture: the page shows its front from behind.
        quad(view_name + "_" + part, os.path.join(Home, folder, part + ".PNG"),
             z, ox, ds=not has_back, extras=extras)
        if has_back:
            quad(view_name + "Back_" + part, back_png, back_z[part], ox, back=True)
        total_parts += 1

bin_data = b"".join(b for b, _ in bin_parts)
gltf = {"asset": {"version": "2.0", "generator": "Duke Human GLB Builder V1"},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes,
        "meshes": meshes, "materials": materials, "images": images,
        "textures": [{"source": i} for i in range(len(images))],
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(bin_data)}],
        "extras": {"character": "Human_Man", "canvas": 2048,
                   "views": ["Front", "Back", "Side"],
                   "rig": "each part node carries extras.pin (canvas pixels) and extras.parent"}}
json_data = json.dumps(gltf).encode()
json_data += b" " * ((-len(json_data)) % 4)
glb = (b"glTF" + struct.pack("<II", 2, 12 + 8 + len(json_data) + 8 + len(bin_data))
       + struct.pack("<I", len(json_data)) + b"JSON" + json_data
       + struct.pack("<I", len(bin_data)) + b"BIN\x00" + bin_data)
path = os.path.join(OUT, "Human_Man_3D.GLB")
open(path, "wb").write(glb)
print(f"Human_Man_3D.GLB written: {path} {len(glb)} bytes, "
      f"{total_parts} parts, {len(meshes)} layers ({len(images)} pictures)")
