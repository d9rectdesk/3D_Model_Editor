// Source: glTF-Transform core (WebIO + Document) - browser-side GLB read and
// Source: write including skins; the Model Editor save path foundation (GQ-01).
// Source: Project donmccurdy/glTF-Transform, file packages/core/src/properties/extensible-property.ts, commit 8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f.
// Source: Licence MIT, Copyright (c) 2024 Don McCurdy - see the LICENSE.md
// Source: staged with this part. Copied literally 2026-11-16; only this
// Source: header and the comment-word change noted in Staging_Note_V1.TXT
// Source: differ from the original file.
import { RefMap } from 'property-graph';
import type { Nullable } from '../constants.js';
import type { ExtensionProperty } from './extension-property.js';
import { type IProperty, Property } from './property.js';

export interface IExtensibleProperty extends IProperty {
	extensions: RefMap<ExtensionProperty>;
}

/**
 * *A {@link Property} that can have {@link ExtensionProperty} instances attached.*
 *
 * Most properties are extensible. See the {@link Extension} documentation for information about
 * how to use extensions.
 *
 * @category Properties
 */
export abstract class ExtensibleProperty<T extends IExtensibleProperty = IExtensibleProperty> extends Property<T> {
	protected getDefaults(): Nullable<T> {
		return Object.assign(super.getDefaults(), { extensions: new RefMap<ExtensionProperty>() });
	}

	/** Returns an {@link ExtensionProperty} attached to this Property, if any. */
	public getExtension<Prop extends ExtensionProperty>(name: string): Prop | null {
		return (this as ExtensibleProperty).getRefMap('extensions', name) as Prop;
	}

	/**
	 * Attaches the given {@link ExtensionProperty} to this Property. For a given extension, only
	 * one ExtensionProperty may be attached to any one Property at a time.
	 */
	public setExtension<Prop extends ExtensionProperty>(name: string, extensionProperty: Prop | null): this {
		if (extensionProperty) extensionProperty._validateParent(this as ExtensibleProperty);
		return (this as ExtensibleProperty).setRefMap('extensions', name, extensionProperty) as this;
	}

	/** Lists all {@link ExtensionProperty} instances attached to this Property. */
	public listExtensions(): ExtensionProperty[] {
		return (this as ExtensibleProperty).listRefMapValues('extensions');
	}
}
