// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/index.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
export { Graph, GraphEdge, type Ref, RefList, RefMap, RefSet } from 'property-graph';
export {
	type bbox,
	ComponentTypeToTypedArray,
	Format,
	GLB_BUFFER,
	type mat3,
	type mat4,
	type Nullable,
	PropertyType,
	TextureChannel,
	type TypedArray,
	type TypedArrayConstructor,
	VERSION,
	VertexLayout,
	type vec2,
	type vec3,
	type vec4,
} from './constants.js';
export { Document, type Transform, type TransformContext } from './document.js';
export { Extension } from './extension.js';
export { DenoIO, NodeIO, PlatformIO, ReaderContext, WebIO, WriterContext } from './io/index.js';
export type { JSONDocument } from './json-document.js';
export {
	Accessor,
	Animation,
	AnimationChannel,
	AnimationSampler,
	Buffer,
	Camera,
	COPY_IDENTITY,
	ExtensibleProperty,
	ExtensionProperty,
	type IProperty,
	Material,
	Mesh,
	Node,
	Primitive,
	PrimitiveTarget,
	Property,
	type PropertyResolver,
	Root,
	Scene,
	Skin,
	Texture,
	TextureInfo,
} from './properties/index.js';
export type { GLTF } from './types/gltf.js';
export {
	BufferUtils,
	ColorUtils,
	FileUtils,
	getBounds,
	HTTPUtils,
	type ILogger,
	ImageUtils,
	type ImageUtilsFormat,
	Logger,
	MathUtils,
	uuid,
	Verbosity,
} from './utils/index.js';
