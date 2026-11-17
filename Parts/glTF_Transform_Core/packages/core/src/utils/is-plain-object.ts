// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/utils/is-plain-object.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
// Reference: https://github.com/jonschlinkert/is-plain-object

function isObject(o: unknown): o is object {
	return Object.prototype.toString.call(o) === '[object Object]';
}

export function isPlainObject(o: unknown): o is object {
	if (isObject(o) === false) return false;

	// If has modified constructor
	const ctor = o.constructor;
	if (ctor === undefined) return true;

	// If has modified prototype
	const prot = ctor.prototype;
	if (isObject(prot) === false) return false;

	// If constructor does not have an Object-specific method
	if (Object.hasOwn(prot, 'isPrototypeOf') === false) {
		return false;
	}

	// Most likely a plain Object
	return true;
}
