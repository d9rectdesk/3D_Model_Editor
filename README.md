# 3D Model Editor

The Model Editor is a rigging and model-editing tool that runs entirely in a web browser as a single page. Version 19 opens with nothing loaded — no model is built into the app. You open a glTF binary (.glb) file to start editing. A rigged GLB carries its own rig inside it: every part of the model carries the point it turns on and the part it hangs from, written into the file itself. Opening one shows the model in 3D with its joint points already placed, and builds a 2D paper-parts view for every view inside the file (front, back, side), with the points already on the parts. You check the points, drag them right if one is off, test the movement joint by joint, blacklist any angle a joint must never sit at, and save the rig — points, parents, limits, blacklists, and a written description for every point — as one small file.

Version 19 also builds a paper doll by itself: pick a character's front, back, and side pictures in one pick, and the editor cuts them out clean, splits them into parts, completes the parts and grows their buffers, writes the rig points into a paper GLB, assembles the 3D paper model, and generates a walk page from that GLB — saying what it is doing while it works, and downloading the GLB, the walk page, and the full set of its working files.

Everything runs on your own computer. There is nothing to install and no account to make: download the Model Editor Version 19 HTML file and open it in a browser. The page loads the Three.js library from a public content delivery network, so it needs an internet connection the first time it opens.

## The included example model

The human man in this repository is a complete paper character: front, back, and side views standing side by side in one GLB file, 41 parts, every part cut from its own view's base picture and rigged with its points inside the file. Open the Model Editor, choose Load files, and pick Human_Man_Paper.GLB to see him, check his points, and test his movement.

## Files in this repository

- Model_Editor_V19.HTML — the complete tool as one self-contained page, with no model inside it. Open it in a browser and open a GLB file to begin. Front, back, and side are edited as separate views; layers can be reordered in the app; paper rig points move on X and Y only; the model loads in the centre of the window; the 3D stage background follows the light or dark appearance; the app is tuned for Chrome; the 3D points can be played in motion - a snake wave along their depth, or a spiral around it; every point carries a written description that saves into its points file; and the angle range a point reaches while its sliders are tested can be approved as its limits with one click. Version 19 adds the paper doll build: one pick of a character's front, back, and side pictures, and the editor makes the finished paper doll itself — cutouts, parts, completion and buffers, the rigged GLB, the assembled 3D paper model, and a walk page generated from that GLB.
- Model_Editor_V19_Spec_V1.TXT — exactly what changed in Version 19.
- Model_Editor_V18_Spec_V1.TXT — exactly what changed in Version 18.
- Model_Editor_V17_Spec_V1.TXT — exactly what changed in Version 17.
- Model_Editor_V16_Spec_V1.TXT — exactly what changed in Version 16.
- Model_Editor_V15_Spec_V1.TXT — exactly what changed in Version 15.
- Model_Editor_V14_Spec_V1.TXT — exactly what changed in Version 14.
- Model_Editor_V11_Spec_V1.TXT — exactly what changed in Version 11.
- Model_Editor_V10_Spec_V1.TXT — what changed in Version 10 and how the GLB rig format works.
- Human_Man_Paper.GLB — the human man: front, back, and side paper layer sets in one rigged file.
- GLB_To_PNG_V1.PY — a small program that takes a paper GLB file and saves every paper layer inside it as its own transparent PNG picture, so the layers can be opened and edited one by one in any other program.
- Build_Human_GLB_V1.PY — the program that built Human_Man_Paper.GLB from the layer sets and their rig files.
- Separate_Humanoid_V1.PY, Separate_Humanoid_Back_V1.PY, Separate_Humanoid_Side_V1.PY — the programs that cut the man's front, back, and side layer sets, each from its own base picture.
- Rig_Points_Humanoid_V1.JSON, Rig_Points_Humanoid_Back_V1.JSON, Rig_Points_Humanoid_Side_V1.JSON, Rig_Points_Humanoid_Side_Back_V1.JSON — the man's rig files: every part's turning point and parent, per view. The same rig also rides inside the GLB itself.
- Duke_3D.glb — Duke the dragon as a standalone 3D model file, kept from earlier work.
- Joint_Points_3D_V1.JSON — a 3D joint-points file in the format the editor saves and loads, kept from earlier work.
- README.md — this file.

## Roadmap

Work is tracked in this repository's Issues, grouped by version.

Version 21 is frozen and in progress (issue #57): the parts-list defect fix, the Models list, picture intake at any count of three or more, and wording that keeps language-model abilities honestly described as plugin-only.

The next version carries the larger build-out: a single emoji or a short description becomes a 3D model, the colour, erase, and sculpt brushes, torrent-logic operations, loading more models alongside the open one, the triangle-count slider, and the open plugin point for language-model helpers. Throughout, the theme stays modern and not overly cluttered, and the app never presents language-model abilities as built in.

## Asking for features

Feature requests live in this repository's Issues, each written in plain language with the enhancement label.

## License

3D Model Editor is open source under the MIT License — see the LICENSE file. Anyone may use, copy, modify, and share it, including for commercial purposes, as long as the copyright notice stays with it.
