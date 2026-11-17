// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/utils/file-utils.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import { ImageUtils } from './image-utils.js';

/**
 * *Utility class for working with file systems and URI paths.*
 *
 * @category Utilities
 */
export class FileUtils {
	/**
	 * Extracts the basename from a file path, e.g. "folder/model.glb" -> "model".
	 * See: {@link HTTPUtils.basename}
	 */
	static basename(uri: string): string {
		const fileName = uri.split(/[\\/]/).pop()!;
		return fileName.substring(0, fileName.lastIndexOf('.'));
	}

	/**
	 * Extracts the extension from a file path, e.g. "folder/model.glb" -> "glb".
	 * See: {@link HTTPUtils.extension}
	 */
	static extension(uri: string): string {
		if (uri.startsWith('data:image/')) {
			const mimeType = uri.match(/data:(image\/\w+)/)![1];
			return ImageUtils.mimeTypeToExtension(mimeType);
		} else if (uri.startsWith('data:model/gltf+json')) {
			return 'gltf';
		} else if (uri.startsWith('data:model/gltf-binary')) {
			return 'glb';
		} else if (uri.startsWith('data:application/')) {
			return 'bin';
		}
		return uri.split(/[\\/]/).pop()!.split(/[.]/).pop()!;
	}
}
