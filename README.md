# 3D Model Editor

The 3D Model Editor is a rigging and model-editing tool that runs entirely in a web browser as a single page. It opens with Duke, a small dragon, already loaded as the included model. You place named points on the model to build its rig, face each point's forward arrow so the rig knows which way is front, bend the rig in Test Movement to prove the points work, sculpt the model's shape with push and pull brushes, and paint the model with a palette brush. Your points, forward facings, and movement limits save together in one small file that the tool loads back, and an edited model saves out as a standard glTF binary (.glb) file that other programs can open.

Everything runs on your own computer. There is nothing to install and no account to make: download the Duke Joint Placer Version 5 HTML file and open it in a browser. The page does load the Three.js library from a public content delivery network, so it needs an internet connection the first time it opens.

## What it does

- Place Points mode: drag thirty labeled points — pelvis, spine, chest, neck, head, ears, shoulders, elbows, wrists, wing bases, wing bends, wing middle folds, wing tips, hips, knees, ankles, tail base, tail middle, and tail tip — onto the model. Every point is colored by body group and the panel says, in plain words, where each point goes.
- Forward arrows: every point carries a solid arrow showing which way is forward for that point. Click a point and face its arrow with the snap buttons (Front, Back, Left, Right, Up, Down) or the yaw and pitch sliders. A large yellow arrow labeled FRONT stands on the floor at the model's front. Facings save with the points, ready for animation mapping later.
- Wing bend and wing middle fold points: each wing is a four-point chain — base, bend, middle fold, tip — so wings can fold the way real wings do.
- Custom points: add your own points, name them, hang them under any parent point, rename them, or delete them. Saved files load as complete rigs, so a rig you design can be shared as one small JSON file.
- Movement limits: for every point, set an allow range (the whitelist — the degrees a joint may use) and deny bands (the blacklist — degrees it must never enter), per axis. Limits save with the points, per model, and are enforced while you test movement.
- Test Movement mode: the rig is skinned to the model and rebuilt from your points every time you enter it. Bend any joint with the X, Y, and Z sliders, or play preset motions — Wave Right Arm, Tail Wag, Flap Wings, Head Turn, and Walk.
- Edit Model mode: sculpt the model itself. Left click pushes the surface in, right click pulls it out, with brush size and strength controls. Paint mode colors the model with a palette brush — twelve ready colors plus any color you pick, with brush size and hardness controls; right click paints white to clear the tint. Save Edited Model writes your edited model out as a .glb file.
- Load Model: bring your own .glb model, place the points on it, and test its movements in the same tool.

## Files in this repository

- Duke_Joint_Placer_V5.HTML — the complete tool as one self-contained page, with Duke embedded inside it. Open it in a browser and everything works.
- Duke_3D.glb — Duke, the included model, as a standalone file, so you can also load him through Load Model or use him in other programs.
- Joint_Points_3D_V1.JSON — the starting rig: Duke's thirty points with their forward facings, in the exact format the tool saves and loads.
- README.md — this file.

## Asking for features

Feature requests live in this repository's Issues, each written in plain language with the enhancement label. Paint, push and pull sculpting, the forward arrows, custom points, and the rest of the good stuff each have their own request there — add yours the same way.

## Model Editor V6

One editor that recognizes what you hand it:

* **2D paper model — separated parts**: place each part's pin (Edit Points, drag, Set), turn parts with live degrees, set limits, and blacklist angles a joint must never sit at. Connections and labels ride with every point.
* **2D paper model — one image to rig**: the two-stop flow. Stop 1, place the points on the picture. Stop 2, name each point and connect it to its parent. Save the rig data and the separated files get built from it. The bald eagle rig image is built in as the worked example; Paper Duke's separated parts are built in too.
* **3D model — GLB**: Duke_3D.glb with his joint points; click a point, drag it in the view, fine-tune with the sliders, save the updated Joint Points file.

Open `Model_Editor_V6.HTML` in a browser. The 3D mode loads `Duke_3D.glb` from the same folder.
