# Separate_Humanoid_Side_V1.PY
# Cuts the human man SIDE picture into a complete paper-doll layer set.
# The same method as Separate_Humanoid_V1.PY, on the profile picture
# Solomon ordered with the arms fully out, so the parts overlap the
# least and each part needs the least extra drawing. Full canvas,
# assembled position, round joint ends filled from each part's own
# interior, eyes on their own layer, the shorts whole on the torso.
# Original work - Duke.
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

# The side picture the image model drew, in this folder.
Home = os.path.dirname(os.path.abspath(__file__))
Source_Name = "media-generation-human-man-side-v1-0-28ced04d-b38d-4339-9881-601f10377fdf.png"
Canvas = 2048
Parts_Dir = os.path.join(Home, "Parts_Side_V1")

# Joint points measured on the side picture, in thousandths of its
# size. Grounding pass on the gridded picture, 2026-11-14. The man
# faces right; the arm runs straight out in front of him.
Pins_Rel = {
    "neck": (481, 216),
    "shoulder": (500, 291), "elbow": (584, 300),
    "wrist": (719, 303), "hand_tip": (816, 306),
    "hip": (484, 494),
    "knee": (484, 706), "ankle": (481, 875),
    "eye": (528, 147),
    "toe": (553, 919),
    "head_top": (494, 72), "pelvis": (481, 481), "chest": (481, 250),
}

# Each part is the run of the figure nearest its bone. The torso
# bone runs pelvis to chest and carries the shorts whole.
Bones = {
    "Part_Torso_V1": ("pelvis", "chest"),
    "Part_Neck_V1": ("chest", "neck"),
    "Part_Head_V1": ("neck", "head_top"),
    "Part_Arm_Upper_V1": ("shoulder", "elbow"),
    "Part_Arm_Fore_V1": ("elbow", "wrist"),
    "Part_Hand_V1": ("wrist", "hand_tip"),
    "Part_Thigh_V1": ("hip", "knee"),
    "Part_Shin_V1": ("knee", "ankle"),
    "Part_Foot_V1": ("ankle", "toe"),
}

# Joints where both parts grow a round end centred on the pin.
# The hip is NOT here: nothing is drawn under the clothing.
Joint_Discs = [
    ("neck", 58, "Part_Head_V1", "Part_Neck_V1"),
    ("chest", 28, "Part_Neck_V1", "Part_Torso_V1"),
    ("shoulder", 34, "Part_Arm_Upper_V1", "Part_Torso_V1"),
    ("elbow", 26, "Part_Arm_Fore_V1", "Part_Arm_Upper_V1"),
    ("wrist", 18, "Part_Hand_V1", "Part_Arm_Fore_V1"),
    ("knee", 30, "Part_Shin_V1", "Part_Thigh_V1"),
    ("ankle", 20, "Part_Foot_V1", "Part_Shin_V1"),
]

# Paint order, back to front: a child sits behind its parent at
# skin joints; the torso covers the thigh top (the shorts), and
# the arm hangs in front of the torso in profile.
Layer_Order = [
    "Part_Foot_V1", "Part_Shin_V1", "Part_Thigh_V1",
    "Part_Neck_V1", "Part_Head_V1",
    "Part_Torso_V1",
    "Part_Arm_Upper_V1", "Part_Arm_Fore_V1", "Part_Hand_V1",
    "Part_Head_Eyes_V1",
]

# Which pin each part turns on, and the part it hangs from.
Rig = {
    "Part_Torso_V1": ("pelvis", None),
    "Part_Neck_V1": ("neck", "Part_Torso_V1"),
    "Part_Head_V1": ("neck", "Part_Neck_V1"),
    "Part_Head_Eyes_V1": ("neck", "Part_Head_V1"),
    "Part_Arm_Upper_V1": ("shoulder", "Part_Torso_V1"),
    "Part_Arm_Fore_V1": ("elbow", "Part_Arm_Upper_V1"),
    "Part_Hand_V1": ("wrist", "Part_Arm_Fore_V1"),
    "Part_Thigh_V1": ("hip", "Part_Torso_V1"),
    "Part_Shin_V1": ("knee", "Part_Thigh_V1"),
    "Part_Foot_V1": ("ankle", "Part_Shin_V1"),
}


# Distance from every pixel to a segment, vectorised over the figure only.
def Segment_Distance(Points, A, B):
    AB = B - A
    T = np.clip(((Points - A) @ AB) / (AB @ AB), 0.0, 1.0)
    Closest = A + T[:, None] * AB
    return np.sqrt(((Points - Closest) ** 2).sum(axis=1))


# Fill a part's missing round end inside one disc. The fill takes
# the part's own NEAREST interior colour for every new pixel, so
# the drawn end keeps the exact local tone - a blend averages in
# distant pale highlights and reads as a patch that is not the
# part's own art (Solomon's correctness ruling, 2026-11-14).
# Outline strokes and pale edge pixels are never a source.
# The new rim is feathered soft.
def Complete_Disc(RGBA, Part_Mask, Centre, Radius, Silhouette):
    Pad = int(Radius * 2 + 8)
    Y0 = max(0, int(Centre[1] - Pad)); Y1 = min(Canvas, int(Centre[1] + Pad + 1))
    X0 = max(0, int(Centre[0] - Pad)); X1 = min(Canvas, int(Centre[0] + Pad + 1))
    YY, XX = np.mgrid[Y0:Y1, X0:X1]
    In_Disc = (XX - Centre[0]) ** 2 + (YY - Centre[1]) ** 2 <= Radius ** 2
    Want = In_Disc & Silhouette[Y0:Y1, X0:X1] & ~Part_Mask[Y0:Y1, X0:X1]
    if not Want.any():
        return Part_Mask
    Have = Part_Mask[Y0:Y1, X0:X1]
    if not Have.any():
        return Part_Mask
    Window = RGBA[Y0:Y1, X0:X1].astype(np.int32)
    Lum_W = Window[:, :, :3].mean(axis=2)
    # Interior sources only: fully opaque, neither outline-dark nor edge-pale.
    Spread_W = Window[:, :, :3].max(axis=2) - Window[:, :, :3].min(axis=2)
    Interior = Have & (Window[:, :, 3] >= 250) & (Lum_W >= 110) & (Lum_W <= 232) & (Spread_W > 24)
    if Interior.sum() < 24:
        Interior = Have
    Hy, Hx = np.where(Interior)
    Source = Window[Hy, Hx, :3].astype(np.float64)
    Wy, Wx = np.where(Want)
    # Distance-weighted blend of the nearest interior colours, chunked.
    Filled = np.zeros((len(Wy), 4), dtype=np.uint8)
    for Start in range(0, len(Wy), 256):
        Dy = Wy[Start:Start + 256, None] - Hy[None, :]
        Dx = Wx[Start:Start + 256, None] - Hx[None, :]
        D2 = Dy * Dy + Dx * Dx
        Near = np.argmin(D2, axis=1)
        Filled[Start:Start + 256, :3] = Source[Near].astype(np.uint8)
        Filled[Start:Start + 256, 3] = 255
    Patch = np.zeros((Y1 - Y0, X1 - X0, 4), dtype=np.uint8)
    Patch[Wy, Wx] = Filled
    # Feather the patch's own rim so the drawn end has no hard sticker edge.
    Rim = Image.fromarray(Patch[:, :, 3]).filter(ImageFilter.GaussianBlur(1.2))
    Patch[:, :, 3] = np.minimum(Patch[:, :, 3], np.array(Rim))
    Region = RGBA[Y0:Y1, X0:X1]
    Take = Patch[:, :, 3:4].astype(np.float32) / 255.0
    RGBA[Y0:Y1, X0:X1] = (Patch * Take + Region * (1 - Take)).astype(np.uint8)
    Part_Mask[Y0:Y1, X0:X1] |= Want
    return Part_Mask


# Keep only the pieces of a part that touch its own bone — no strays.
def Clean_Part(Mask, A, B):
    Bone_Img = Image.new("L", (Canvas, Canvas), 0)
    Draw = ImageDraw.Draw(Bone_Img)
    Draw.line([A, B], fill=255, width=26)
    Near = np.array(Bone_Img) > 0
    Lab, Count = ndimage.label(Mask)
    Keep = [I for I in range(1, Count + 1) if (Near & (Lab == I)).any()]
    return np.isin(Lab, Keep) if Keep else Mask


def Main():
    os.makedirs(Parts_Dir, exist_ok=True)
    Source = Image.open(os.path.join(Home, Source_Name)).convert("RGB")
    SW, SH = Source.size
    # Place the figure on the full canvas, height fitted with a small margin.
    Scale = (Canvas - 48) / SH
    NW, NH = int(SW * Scale), int(SH * Scale)
    OX, OY = (Canvas - NW) // 2, (Canvas - NH) // 2
    Placed = Image.new("RGB", (Canvas, Canvas), (246, 246, 246))
    Placed.paste(Source.resize((NW, NH), Image.LANCZOS), (OX, OY))
    Placed.save(os.path.join(Home, "Human_Man_Side_Canvas_V1.PNG"))
    RGB = np.array(Placed).astype(np.int32)

    # Cut the figure out of the near-white ground with a soft alpha ramp.
    Lum = RGB.mean(axis=2)
    Alpha = np.clip((244 - Lum) / 14.0, 0, 1)
    Figure = Alpha > 0.02
    # Drop the faint grey smudges the source picture carries in
    # its background: a real body piece holds saturated paint, a
    # smudge is small and grey. (Solomon's correctness ruling.)
    Spread_All = RGB.max(axis=2) - RGB.min(axis=2)
    Lab_F, Count_F = ndimage.label(Figure)
    Keep_F = []
    for I in range(1, Count_F + 1):
        Comp = Lab_F == I
        if (Spread_All[Comp] > 24).sum() >= 200 or Comp.sum() >= 5000:
            Keep_F.append(I)
    Figure = np.isin(Lab_F, Keep_F)
    RGBA = np.dstack([RGB, (Alpha * 255).astype(np.uint8)]).astype(np.uint8)

    # Pins in canvas coordinates.
    Pins = {K: (OX + V[0] / 1000 * NW, OY + V[1] / 1000 * NH) for K, V in Pins_Rel.items()}
    Fy, Fx = np.where(Figure)
    Points = np.stack([Fx, Fy], axis=1).astype(np.float64)

    # The shorts are the torso's whole: dark blue cloth never leaves it.
    Cloth = Figure & (RGB[:, :, 2] - RGB[:, :, 0] > 12) & (Lum < 120)
    Owner = np.full(Figure.shape, "", dtype=object)
    Best = np.full(len(Points), 1e18)
    Names = list(Bones)
    for Name in Names:
        A = np.array(Pins[Bones[Name][0]]); B = np.array(Pins[Bones[Name][1]])
        D = Segment_Distance(Points, A, B)
        Take = D < Best
        Best[Take] = D[Take]
        Owner[Fy[Take], Fx[Take]] = Name
    Owner[Cloth] = "Part_Torso_V1"

    # Keep, per part, only the pieces that touch its own bone — no strays.
    Masks = {}
    for Name in Names:
        Mask = Owner == Name
        Bone_Img = Image.new("L", (Canvas, Canvas), 0)
        Draw = ImageDraw.Draw(Bone_Img)
        A = Pins[Bones[Name][0]]; B = Pins[Bones[Name][1]]
        Draw.line([A, B], fill=255, width=26)
        Near = np.array(Bone_Img) > 0
        Lab, Count = ndimage.label(Mask)
        Keep = [I for I in range(1, Count + 1) if (Near & (Lab == I)).any()]
        Masks[Name] = np.isin(Lab, Keep) if Keep else Mask

    # Every part gets its own canvas, so a completion fill can never bleed
    # another part's colours into this one.
    Canvases = {}
    for Name in Names:
        Own = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
        Own[Masks[Name]] = RGBA[Masks[Name]]
        Canvases[Name] = Own

    # Draw the round joint ends the photo does not show, both sides of every
    # skin joint, each filled with its own part's colours. The neck's end at
    # the head is cut wide on purpose: when the head turns, neck shows behind
    # it, never the background.
    for Pin_Name, Radius_Rel, Child, Parent in Joint_Discs:
        Radius = Radius_Rel / 1000 * NH
        Centre = Pins[Pin_Name]
        # Grow the silhouette a breath so a disc can round a straight cut.
        Wide = np.array(Image.fromarray((Figure * 255).astype(np.uint8)).filter(
            ImageFilter.MaxFilter(9))) > 0
        for Part in (Child, Parent):
            Masks[Part] = Complete_Disc(Canvases[Part], Masks[Part], Centre, Radius, Wide)

    # Second cleanup: a disc can leave a floating shard where it rounded a
    # cut outside the figure — anything not touching its bone goes.
    for Name in Names:
        Masks[Name] = Clean_Part(Masks[Name], Pins[Bones[Name][0]], Pins[Bones[Name][1]])

    # The eye is one layer, carved from the head by place and dark.
    Head = Masks["Part_Head_V1"]
    Eyes = np.zeros(Figure.shape, dtype=bool)
    Cx, Cy = Pins["eye"]
    YY, XX = np.mgrid[0:Canvas, 0:Canvas]
    Zone = ((XX - Cx) / (0.020 * NW)) ** 2 + ((YY - Cy) / (0.013 * NH)) ** 2 <= 1
    Eyes = Zone & Head & (Lum < 95)
    Masks["Part_Head_Eyes_V1"] = Eyes
    Eye_Canvas = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
    Eye_Canvas[Eyes] = RGBA[Eyes]
    Canvases["Part_Head_Eyes_V1"] = Eye_Canvas
    # The head is drawn whole underneath: the eye places are filled back in
    # with the head's own face colours, so the eyes can move and blink over
    # a complete head, never over holes.
    Masks["Part_Head_V1"] = Head & ~Eyes
    Masks["Part_Head_V1"] = Complete_Disc(
        Canvases["Part_Head_V1"], Masks["Part_Head_V1"], Pins["eye"], 0.020 * Canvas, Figure)

    # Write every layer as its own full-canvas transparent picture.
    for Name in Layer_Order:
        Out = Canvases[Name].copy()
        Out[:, :, 3] = np.where(Masks[Name], Out[:, :, 3], 0)
        Image.fromarray(Out, "RGBA").save(os.path.join(Parts_Dir, Name + ".PNG"))

    # The assembled preview, layers stacked in paint order on light ground.
    Preview = Image.new("RGBA", (Canvas, Canvas), (246, 246, 246, 255))
    for Name in Layer_Order:
        Preview.alpha_composite(Image.open(os.path.join(Parts_Dir, Name + ".PNG")))
    Preview.convert("RGB").save(os.path.join(Home, "Preview_Side_Assembled_V1.PNG"))

    # Proof: the stacked layers against the cutout they came from.
    Stack = np.array(Preview.convert("RGB")).astype(np.int32)
    Diff = np.abs(Stack - RGB).mean(axis=2)
    print("rebuild difference:", round(float(Diff[Figure].mean()) / 255, 4))

    # The rig: pins, parents, and paint order, in canvas coordinates.
    Rig_Out = {"canvas": Canvas, "layer_order_back_to_front": Layer_Order, "parts": {}}
    for Name, (Pin_Key, Parent) in Rig.items():
        Rig_Out["parts"][Name] = {
            "pin": [round(Pins[Pin_Key][0], 1), round(Pins[Pin_Key][1], 1)],
            "parent": Parent,
        }
    with open(os.path.join(Home, "Rig_Points_Humanoid_Side_V1.JSON"), "w") as F:
        json.dump(Rig_Out, F, indent=1)
    print("layers:", len(Layer_Order), "written to", Parts_Dir)


if __name__ == "__main__":
    Main()
