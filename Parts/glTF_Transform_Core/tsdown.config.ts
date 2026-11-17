// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file tsdown.config.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import { defineConfig } from 'tsdown';

export default defineConfig({
	format: ['esm', 'cjs'],
	platform: 'neutral',
	treeshake: { moduleSideEffects: false },
	// For gl-matrix bundling. See: https://tsdown.dev/options/platform#module-resolution
	inputOptions: { resolve: { mainFields: ['module', 'main'] } },
	sourcemap: true,
});
