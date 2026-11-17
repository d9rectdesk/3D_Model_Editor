// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/json-document.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import type { GLTF } from './types/gltf.js';

/**
 * *Raw glTF asset, with its JSON and binary resources.*
 *
 * A JSONDocument is a plain object containing the raw JSON of a glTF file, and any binary or image
 * resources referenced by that file. When modifying the file, it should generally be first
 * converted to the more useful {@link Document} wrapper.
 *
 * When loading glTF data that is in memory, or which the I/O utilities cannot otherwise access,
 * you might assemble the JSONDocument yourself, then convert it to a Document with
 * {@link PlatformIO.readJSON}(jsonDocument).
 *
 * Usage:
 *
 * ```ts
 * import fs from 'node:fs/promises';
 *
 * const jsonDocument = {
 * 	// glTF JSON schema.
 * 	json: {
 * 		asset: {version: '2.0'},
 * 		images: [{uri: 'image1.png'}, {uri: 'image2.png'}]
 * 	},
 *
 * 	// URI → Uint8Array mapping.
 * 	resources: {
 * 		'image1.png': await fs.readFile('image1.png'),
 * 		'image2.png': await fs.readFile('image2.png'),
 * 	}
 * };
 *
 * const document = await new NodeIO().readJSON(jsonDocument);
 * ```
 *
 * @category Documents
 */
export interface JSONDocument {
	json: GLTF.IGLTF;
	resources: { [s: string]: Uint8Array<ArrayBuffer> };
}
