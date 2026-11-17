// Source: Duke, original work for Solomon (2026-11-16).
// What this harness does: proves the staged GQ-01 part (glTF-Transform core,
// WebIO + Document) stands on its own. It builds a skinned model in a
// Document, writes it to a binary GLB with WebIO, reads the GLB back with
// WebIO, and checks that the scene, the mesh, the skin and its joints, and
// the vertex data all survive the round trip.
// Source: the calls used here are copied from the project's own tests in
// the pulled repo - packages/core/test/properties/skin.test.ts (skin,
// joints, inverse bind matrices) and packages/core/test/io/platform-io.test.ts
// (writeBinary / readBinary round trip), commit
// 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f, MIT.
import assert from 'node:assert/strict';
import { Accessor, Document, VERSION, WebIO } from '../packages/core/dist/index.js';

assert.ok(VERSION.startsWith('v'), `VERSION present: ${VERSION}`);
console.log(`VERSION: ${VERSION}`);

const document = new Document();
const buffer = document.createBuffer('main');
const scene = document.createScene('Scene');
document.getRoot().setDefaultScene(scene);

const joints = [
	document.createNode('joint1'),
	document.createNode('joint2'),
	document.createNode('joint3'),
];
const ibm = document
	.createAccessor('ibm')
	.setType(Accessor.Type.MAT4)
	.setArray(
		new Float32Array([
			1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1,
			1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1,
			1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 0, 0, 1,
		]),
	)
	.setBuffer(buffer);
const skin = document
	.createSkin('testSkin')
	.addJoint(joints[0])
	.addJoint(joints[1])
	.addJoint(joints[2])
	.setSkeleton(joints[0])
	.setInverseBindMatrices(ibm);

const positions = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]);
const positionAccessor = document
	.createAccessor('positions')
	.setType(Accessor.Type.VEC3)
	.setArray(positions)
	.setBuffer(buffer);
const jointsAccessor = document
	.createAccessor('joints')
	.setType(Accessor.Type.VEC4)
	.setArray(new Uint16Array([0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0]))
	.setBuffer(buffer);
const weightsAccessor = document
	.createAccessor('weights')
	.setType(Accessor.Type.VEC4)
	.setArray(new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]))
	.setBuffer(buffer);
const primitive = document
	.createPrimitive()
	.setAttribute('POSITION', positionAccessor)
	.setAttribute('JOINTS_0', jointsAccessor)
	.setAttribute('WEIGHTS_0', weightsAccessor);
const mesh = document.createMesh('triangle').addPrimitive(primitive);
const armature = document
	.createNode('armature')
	.addChild(joints[0])
	.addChild(joints[1])
	.addChild(joints[2])
	.setSkin(skin)
	.setMesh(mesh);
scene.addChild(armature);

const io = new WebIO();
const glb = await io.writeBinary(document);
assert.ok(glb.byteLength > 100, `GLB has size: ${glb.byteLength} bytes`);
const magic = new DataView(glb.buffer, glb.byteOffset).getUint32(0, true);
assert.equal(magic, 0x46546c67, 'GLB magic is glTF');
const declaredLength = new DataView(glb.buffer, glb.byteOffset).getUint32(8, true);
assert.equal(declaredLength, glb.byteLength, 'GLB header length matches byte length');
console.log(`GLB written: ${glb.byteLength} bytes, magic glTF, header length matches`);

const back = await io.readBinary(glb);
const root = back.getRoot();
assert.equal(root.listScenes().length, 1, 'one scene survives');
assert.equal(root.listMeshes().length, 1, 'one mesh survives');
assert.equal(root.listSkins().length, 1, 'one skin survives');
assert.equal(root.listSkins()[0].listJoints().length, 3, 'three joints survive');
assert.equal(root.listSkins()[0].getName(), 'testSkin', 'skin name survives');
const backPositions = root
	.listMeshes()[0]
	.listPrimitives()[0]
	.getAttribute('POSITION')
	.getArray();
assert.deepEqual(Array.from(backPositions), Array.from(positions), 'positions survive');
const backSceneNode = root.listScenes()[0].listChildren()[0];
assert.equal(backSceneNode.getName(), 'armature', 'armature node survives');
assert.ok(backSceneNode.getSkin(), 'armature still carries its skin');
console.log(
	`Round trip: scenes=${root.listScenes().length} meshes=${root.listMeshes().length} ` +
		`skins=${root.listSkins().length} joints=${root.listSkins()[0].listJoints().length} ` +
		`positions=${Array.from(backPositions).join(',')}`,
);
console.log('HARNESS PASS');
