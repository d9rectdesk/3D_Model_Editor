// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/utils/uuid.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
const ALPHABET = '23456789abdegjkmnpqrvwxyzABDEGJKMNPQRVWXYZ';
const UNIQUE_RETRIES = 999;
const ID_LENGTH = 6;

const previousIDs = new Set();

const generateOne = function (): string {
	let rtn = '';
	for (let i = 0; i < ID_LENGTH; i++) {
		rtn += ALPHABET.charAt(Math.floor(Math.random() * ALPHABET.length));
	}
	return rtn;
};

/**
 * Short ID generator.
 *
 * Generated IDs are short, easy to type, and unique for the duration of the program's execution.
 * Uniqueness across multiple program executions, or on other devices, is not guaranteed. Based on
 * [Short ID Generation in JavaScript](https://tomspencer.dev/blog/2014/11/16/short-id-generation-in-javascript/),
 * with alterations.
 *
 * @category Utilities
 * @hidden
 */
export const uuid = function (): string {
	for (let retries = 0; retries < UNIQUE_RETRIES; retries++) {
		const id = generateOne();
		if (!previousIDs.has(id)) {
			previousIDs.add(id);
			return id;
		}
	}
	return '';
};
