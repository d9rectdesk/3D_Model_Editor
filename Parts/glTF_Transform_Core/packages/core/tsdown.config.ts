// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/tsdown.config.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import { defineConfig } from 'tsdown';
import baseConfig from '../../tsdown.config.ts';

export default defineConfig({
	...baseConfig,
	deps: {
		onlyBundle: ['gl-matrix'],

		// Omit `node:` scheme in packages/core/src/**/*.ts for Webpack 5.
		// See: packages/core/package.json#browser
		// See: https://github.com/donmccurdy/glTF-Transform/pull/1860
		neverBundle: ['fs', 'path'],
	},
});
