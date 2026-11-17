// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/io/reader-context.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import type { JSONDocument } from '../json-document.js';
import type {
	Accessor,
	Animation,
	Buffer,
	Camera,
	Material,
	Mesh,
	Node,
	Scene,
	Skin,
	Texture,
	TextureInfo,
} from '../properties/index.js';
import type { GLTF } from '../types/gltf.js';

/**
 * Model class providing glTF Transform objects representing each definition in the glTF file, used
 * by a {@link GLTFReader} and its {@link Extension} implementations. Indices of all properties will be
 * consistent with the glTF file.
 *
 * @hidden
 */
export class ReaderContext {
	public buffers: Buffer[] = [];
	public bufferViews: Uint8Array<ArrayBuffer>[] = [];
	public bufferViewBuffers: Buffer[] = [];
	public accessors: Accessor[] = [];
	public textures: Texture[] = [];
	public textureInfos: Map<TextureInfo, GLTF.ITextureInfo> = new Map();
	public materials: Material[] = [];
	public meshes: Mesh[] = [];
	public cameras: Camera[] = [];
	public nodes: Node[] = [];
	public skins: Skin[] = [];
	public animations: Animation[] = [];
	public scenes: Scene[] = [];

	constructor(public readonly jsonDoc: JSONDocument) {}

	public setTextureInfo(textureInfo: TextureInfo, textureInfoDef: GLTF.ITextureInfo): void {
		this.textureInfos.set(textureInfo, textureInfoDef);

		if (textureInfoDef.texCoord !== undefined) {
			textureInfo.setTexCoord(textureInfoDef.texCoord);
		}
		if (textureInfoDef.extras !== undefined) {
			textureInfo.setExtras(textureInfoDef.extras);
		}

		const textureDef = this.jsonDoc.json.textures![textureInfoDef.index];

		if (textureDef.sampler === undefined) return;

		const samplerDef = this.jsonDoc.json.samplers![textureDef.sampler];

		if (samplerDef.magFilter !== undefined) {
			textureInfo.setMagFilter(samplerDef.magFilter);
		}
		if (samplerDef.minFilter !== undefined) {
			textureInfo.setMinFilter(samplerDef.minFilter);
		}
		if (samplerDef.wrapS !== undefined) {
			textureInfo.setWrapS(samplerDef.wrapS);
		}
		if (samplerDef.wrapT !== undefined) {
			textureInfo.setWrapT(samplerDef.wrapT);
		}
	}
}
