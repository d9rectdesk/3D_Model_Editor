import json, os, struct, sys

# GLB_To_PNG_V1.PY
# Takes a paper GLB file and saves every paper layer inside it
# as its own transparent PNG, named for the layer, in a folder
# beside the GLB - so the layers can be opened and edited one
# by one in any other app (Solomon's order, 2026-11-14).
# Usage: python3 GLB_To_PNG_V1.PY <file.GLB>
# Original work - Duke.

def Main():
    if len(sys.argv) != 2:
        print("usage: GLB_To_PNG_V1.PY <file.GLB>")
        return 1
    Path = sys.argv[1]
    Data = open(Path, "rb").read()
    if Data[:4] != b"glTF":
        print("not a GLB file:", Path)
        return 1
    Json_Len = struct.unpack("<I", Data[12:16])[0]
    Gltf = json.loads(Data[20:20 + Json_Len])
    Bin_Off = 20 + Json_Len + 8
    Stem = os.path.splitext(os.path.basename(Path))[0]
    Out_Dir = os.path.join(os.path.dirname(os.path.abspath(Path)),
                           Stem + "_Layers_V1")
    os.makedirs(Out_Dir, exist_ok=True)
    Saved = 0
    for I, Image in enumerate(Gltf.get("images", [])):
        View = Gltf["bufferViews"][Image["bufferView"]]
        Start = Bin_Off + View.get("byteOffset", 0)
        Bytes = Data[Start:Start + View["byteLength"]]
        if Bytes[:8] != b"\x89PNG\r\n\x1a\n":
            print("skip (not a PNG):", Image.get("name", I))
            continue
        Name = Image.get("name", "Layer_" + str(I + 1))
        Out = os.path.join(Out_Dir, Name + ".PNG")
        open(Out, "wb").write(Bytes)
        Saved += 1
        print("saved:", Name + ".PNG", len(Bytes), "bytes")
    print("done:", Saved, "layers in", Out_Dir)
    return 0

if __name__ == "__main__":
    sys.exit(Main())
