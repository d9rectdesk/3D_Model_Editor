# Separate_Humanoid_V1.PY
# Cuts the human man source picture into a complete paper-doll layer set.
# Duke's way, from Character_Cutting_Rules_V1: full canvas, assembled position,
# every part drawn complete with its round joint ends, soft edges, one part
# per layer, eyes on their own layer over a head drawn whole underneath.
# The neck is its own layer behind the head, cut long, so a turning head
# reveals neck, never background. Solomon's fence (2026-11-14): draw the
# features the photo does not show so the layers stack complete — but never
# draw under his clothing; the shorts belong to the torso layer whole.
# Original work — Duke.
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

# The source picture the image model drew, in this folder.
Home = os.path.dirname(os.path.abspath(__file__))
Source_Name = "media-generation-human-man-front-v1-0-9ef3f3bb-ed33-4c05-b010-ca90476d8c81.png"
Canvas = 2048
Parts_Dir = os.path.join(Home, "Parts_V1")

# Joint points measured on the source picture, in thousandths of its size.
# Grounding pass, 2026-11-14. Left is the figure's own left.
Pins_Rel = {
    "neck": (498, 238),
    "shoulder_l": (713, 283), "shoulder_r": (288, 283),
    "elbow_l": (807, 396), "elbow_r": (221, 397),
    "wrist_l": (865, 503), "wrist_r": (130, 503),
    "hip_l": (608, 609), "hip_r": (378, 610),
    "knee_l": (656, 691), "knee_r": (320, 692),
    "ankle_l": (704, 856), "ankle_r": (262, 857),
    "eye_l": (548, 137), "eye_r": (451, 137),
    "toe_l": (898, 923), "toe_r": (106, 924),
    "head_top": (498, 120), "pelvis": (493, 610), "chest": (498, 302),
    "hand_tip_l": (915, 590), "hand_tip_r": (80, 588),
}

# Each part is the run of the figure nearest its bone, shoulder to elbow and
# so on. The torso bone runs pelvis to neck and carries the shorts whole.
Bones = {
    "Part_Torso_V1": ("pelvis", "chest"),
    "Part_Neck_V1": ("chest", "neck"),
    "Part_Head_V1": ("neck", "head_top"),
    "Part_Arm_Upper_Left_V1": ("shoulder_l", "elbow_l"),
    "Part_Arm_Upper_Right_V1": ("shoulder_r", "elbow_r"),
    "Part_Arm_Fore_Left_V1": ("elbow_l", "wrist_l"),
    "Part_Arm_Fore_Right_V1": ("elbow_r", "wrist_r"),
    "Part_Hand_Left_V1": ("wrist_l", "hand_tip_l"),
    "Part_Hand_Right_V1": ("wrist_r", "hand_tip_r"),
    "Part_Thigh_Left_V1": ("hip_l", "knee_l"),
    "Part_Thigh_Right_V1": ("hip_r", "knee_r"),
    "Part_Shin_Left_V1": ("knee_l", "ankle_l"),
    "Part_Shin_Right_V1": ("knee_r", "ankle_r"),
    "Part_Foot_Left_V1": ("ankle_l", "toe_l"),
    "Part_Foot_Right_V1": ("ankle_r", "toe_r"),
}

# Joints where both parts grow a round end centred on the pin, so the pair
# turns without tearing. Radius in thousandths of the picture height — about
# half the limb's width at that joint, no more.
# The hips are NOT here: nothing is drawn under the clothing.
Joint_Discs = [
    ("neck", 58, "Part_Head_V1", "Part_Neck_V1"),
    ("chest", 28, "Part_Neck_V1", "Part_Torso_V1"),
    ("shoulder_l", 30, "Part_Arm_Upper_Left_V1", "Part_Torso_V1"),
    ("shoulder_r", 30, "Part_Arm_Upper_Right_V1", "Part_Torso_V1"),
    ("elbow_l", 24, "Part_Arm_Fore_Left_V1", "Part_Arm_Upper_Left_V1"),
    ("elbow_r", 24, "Part_Arm_Fore_Right_V1", "Part_Arm_Upper_Right_V1"),
    ("wrist_l", 18, "Part_Hand_Left_V1", "Part_Arm_Fore_Left_V1"),
    ("wrist_r", 18, "Part_Hand_Right_V1", "Part_Arm_Fore_Right_V1"),
    ("knee_l", 30, "Part_Shin_Left_V1", "Part_Thigh_Left_V1"),
    ("knee_r", 30, "Part_Shin_Right_V1", "Part_Thigh_Right_V1"),
    ("ankle_l", 20, "Part_Foot_Left_V1", "Part_Shin_Left_V1"),
    ("ankle_r", 20, "Part_Foot_Right_V1", "Part_Shin_Right_V1"),
]

# Paint order, back to front. A child sits behind its parent at skin joints;
# the torso covers the thigh tops because the shorts are the torso's.
Layer_Order = [
    "Part_Foot_Left_V1", "Part_Foot_Right_V1",
    "Part_Shin_Left_V1", "Part_Shin_Right_V1",
    "Part_Thigh_Left_V1", "Part_Thigh_Right_V1",
    "Part_Neck_V1",
    "Part_Head_V1",
    "Part_Hand_Left_V1", "Part_Hand_Right_V1",
    "Part_Arm_Fore_Left_V1", "Part_Arm_Fore_Right_V1",
    "Part_Torso_V1",
    "Part_Arm_Upper_Left_V1", "Part_Arm_Upper_Right_V1",
    "Part_Head_Eyes_V1",
]

# Which pin each part turns on, and the part it hangs from.
Rig = {
    "Part_Torso_V1": ("pelvis", None),
    "Part_Neck_V1": ("neck", "Part_Torso_V1"),
    "Part_Head_V1": ("neck", "Part_Neck_V1"),
    "Part_Head_Eyes_V1": ("neck", "Part_Head_V1"),
    "Part_Arm_Upper_Left_V1": ("shoulder_l", "Part_Torso_V1"),
    "Part_Arm_Upper_Right_V1": ("shoulder_r", "Part_Torso_V1"),
    "Part_Arm_Fore_Left_V1": ("elbow_l", "Part_Arm_Upper_Left_V1"),
    "Part_Arm_Fore_Right_V1": ("elbow_r", "Part_Arm_Upper_Right_V1"),
    "Part_Hand_Left_V1": ("wrist_l", "Part_Arm_Fore_Left_V1"),
    "Part_Hand_Right_V1": ("wrist_r", "Part_Arm_Fore_Right_V1"),
    "Part_Thigh_Left_V1": ("hip_l", "Part_Torso_V1"),
    "Part_Thigh_Right_V1": ("hip_r", "Part_Torso_V1"),
    "Part_Shin_Left_V1": ("knee_l", "Part_Thigh_Left_V1"),
    "Part_Shin_Right_V1": ("knee_r", "Part_Thigh_Right_V1"),
    "Part_Foot_Left_V1": ("ankle_l", "Part_Shin_Left_V1"),
    "Part_Foot_Right_V1": ("ankle_r", "Part_Shin_Right_V1"),
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
    Placed.save(os.path.join(Home, "Human_Man_Canvas_V1.PNG"))
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

    # The eyes are one layer, carved from the head by place and dark.
    Head = Masks["Part_Head_V1"]
    Eyes = np.zeros(Figure.shape, dtype=bool)
    for Key in ("eye_l", "eye_r"):
        Cx, Cy = Pins[Key]
        YY, XX = np.mgrid[0:Canvas, 0:Canvas]
        Zone = ((XX - Cx) / (0.030 * NW)) ** 2 + ((YY - Cy) / (0.016 * NH)) ** 2 <= 1
        Eyes |= Zone & Head & (Lum < 95)
    Masks["Part_Head_Eyes_V1"] = Eyes
    Eye_Canvas = np.zeros((Canvas, Canvas, 4), dtype=np.uint8)
    Eye_Canvas[Eyes] = RGBA[Eyes]
    Canvases["Part_Head_Eyes_V1"] = Eye_Canvas
    # The head is drawn whole underneath: the eye places are filled back in
    # with the head's own face colours, so the eyes can move and blink over
    # a complete head, never over holes.
    Masks["Part_Head_V1"] = Head & ~Eyes
    for Key in ("eye_l", "eye_r"):
        Masks["Part_Head_V1"] = Complete_Disc(
            Canvases["Part_Head_V1"], Masks["Part_Head_V1"], Pins[Key], 0.020 * Canvas, Figure)

    # Write every layer as its own full-canvas transparent picture.
    for Name in Layer_Order:
        Out = Canvases[Name].copy()
        Out[:, :, 3] = np.where(Masks[Name], Out[:, :, 3], 0)
        Image.fromarray(Out, "RGBA").save(os.path.join(Parts_Dir, Name + ".PNG"))

    # The assembled preview, layers stacked in paint order on light ground.
    Preview = Image.new("RGBA", (Canvas, Canvas), (246, 246, 246, 255))
    for Name in Layer_Order:
        Preview.alpha_composite(Image.open(os.path.join(Parts_Dir, Name + ".PNG")))
    Preview.convert("RGB").save(os.path.join(Home, "Preview_Assembled_V1.PNG"))

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
    with open(os.path.join(Home, "Rig_Points_Humanoid_V1.JSON"), "w") as F:
        json.dump(Rig_Out, F, indent=1)
    print("layers:", len(Layer_Order), "written to", Parts_Dir)


if __name__ == "__main__":
    Main()
