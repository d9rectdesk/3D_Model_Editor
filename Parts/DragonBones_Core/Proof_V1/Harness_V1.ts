// Source: Harness for the DragonBones core part (RW-01): builds a two-bone
// Source: armature from skeleton JSON through a display-less factory,
// Source: poses the shoulder bone with a held animation frame, and
// Source: checks the elbow bone's evaluated pose against the value
// Source: computed by hand from the core's own matrix convention.
// Source: Duke - original work, 2026-11-16. No outside source.
namespace harness {
    import db = dragonBones;

    export class EventDispatcher implements db.IEventDispatcher {
        private _listeners: { [type: string]: Array<{ listener: Function, thisObject: any }> } = {};

        public hasEventListener(type: string): boolean {
            return type in this._listeners && this._listeners[type].length > 0;
        }

        public addEventListener(type: string, listener: Function, thisObject: any): void {
            if (!(type in this._listeners)) {
                this._listeners[type] = [];
            }
            this._listeners[type].push({ listener: listener, thisObject: thisObject });
        }

        public removeEventListener(type: string, listener: Function, thisObject: any): void {
            if (type in this._listeners) {
                const list = this._listeners[type];
                for (let i = list.length - 1; i >= 0; --i) {
                    if (list[i].listener === listener && list[i].thisObject === thisObject) {
                        list.splice(i, 1);
                    }
                }
            }
        }

        public hasDBEventListener(type: string): boolean {
            return this.hasEventListener(type);
        }

        public addDBEventListener(type: string, listener: Function, thisObject: any): void {
            this.addEventListener(type, listener, thisObject);
        }

        public removeDBEventListener(type: string, listener: Function, thisObject: any): void {
            this.removeEventListener(type, listener, thisObject);
        }

        public dispatchDBEvent(type: string, eventObject: db.EventObject): void {
            this.dispatchEvent(eventObject);
        }

        public dispatchEvent(event: db.EventObject): void {
            const list = this._listeners[event.type];
            if (list) {
                for (const entry of list.slice()) {
                    entry.listener.call(entry.thisObject, event);
                }
            }
        }
    }

    export class TextureData extends db.TextureData {
        public static toString(): string {
            return "[class harness.TextureData]";
        }

        protected _onClear(): void {
            super._onClear();
        }
    }

    export class TextureAtlasData extends db.TextureAtlasData {
        public static toString(): string {
            return "[class harness.TextureAtlasData]";
        }

        public createTexture(): db.TextureData {
            return db.BaseObject.borrowObject(TextureData);
        }

        protected _onClear(): void {
            super._onClear();
        }
    }

    export class Slot extends db.Slot {
        public static toString(): string {
            return "[class harness.Slot]";
        }

        protected _initDisplay(value: any, isRetain: boolean): void {
            this._display = value;
        }

        protected _disposeDisplay(value: any, isRelease: boolean): void {
        }

        protected _onUpdateDisplay(): void {
        }

        protected _addDisplay(): void {
        }

        protected _replaceDisplay(value: any): void {
        }

        protected _removeDisplay(): void {
        }

        protected _updateZOrder(): void {
        }

        public _updateVisible(): void {
        }

        protected _updateBlendMode(): void {
        }

        protected _updateColor(): void {
        }

        protected _updateFrame(): void {
        }

        protected _updateMesh(): void {
        }

        protected _updateTransform(): void {
        }

        protected _identityTransform(): void {
        }
    }

    export class ArmatureProxy extends EventDispatcher implements db.IArmatureProxy {
        private _armature: db.Armature = null as any;

        public get armature(): db.Armature {
            return this._armature;
        }

        public get animation(): db.Animation {
            return this._armature !== null ? this._armature.animation : null as any;
        }

        public dbInit(armature: db.Armature): void {
            this._armature = armature;
        }

        public dbClear(): void {
        }

        public dbUpdate(): void {
        }

        public dispose(disposeProxy: boolean): void {
        }

        public getDisplay(): any {
            return this;
        }
    }

    export class Factory extends db.BaseFactory {
        public constructor() {
            super();
            this._dragonBones = new db.DragonBones(new EventDispatcher());
        }

        protected _buildTextureAtlasData(textureAtlasData: db.TextureAtlasData | null, textureAtlas: any): db.TextureAtlasData {
            return textureAtlasData !== null ? textureAtlasData : db.BaseObject.borrowObject(TextureAtlasData);
        }

        protected _buildArmature(dataPackage: db.BuildArmaturePackage): db.Armature {
            const armature = db.BaseObject.borrowObject(db.Armature);
            const proxy = new ArmatureProxy();
            armature.init(dataPackage.armature, proxy, proxy, this._dragonBones);
            return armature;
        }

        protected _buildSlot(dataPackage: db.BuildArmaturePackage, slotData: db.SlotData, armature: db.Armature): db.Slot {
            // The adapter-side step the engine factories also
            // perform: a borrowed slot joins its armature only
            // through Slot.init (Slot.ts, init()).
            const slot = db.BaseObject.borrowObject(Slot);
            const display = { name: slotData.name };
            slot.init(slotData, armature, display, display);
            return slot;
        }
    }
}

// The proof figure: a shoulder bone at the origin, an elbow
// bone 100 units along +x, one rigid display on the elbow.
// The "swing" animation holds the shoulder at +90 degrees.
const SKELETON = {
    frameRate: 24,
    name: "proof",
    version: "5.5",
    compatibleVersion: "5.5",
    armature: [
        {
            name: "arm",
            type: "Armature",
            bone: [
                { name: "shoulder" },
                { name: "elbow", parent: "shoulder", transform: { x: 100, y: 0 } }
            ],
            slot: [
                { name: "armSlot", parent: "elbow" }
            ],
            skin: [
                {
                    name: "default",
                    slot: [
                        {
                            name: "armSlot",
                            display: [
                                { name: "armTex", type: "image", transform: { x: 0, y: 0 } }
                            ]
                        }
                    ]
                }
            ],
            animation: [
                {
                    name: "swing",
                    duration: 10,
                    playTimes: 1,
                    bone: [
                        {
                            name: "shoulder",
                            rotateFrame: [
                                { duration: 10, tweenEasing: null, rotate: 90 }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
};

const ATLAS = {
    name: "proofTex",
    imagePath: "proof.png",
    width: 128,
    height: 32,
    SubTexture: [
        { name: "armTex", x: 0, y: 0, width: 100, height: 20 }
    ]
};

function Close(a: number, b: number): boolean {
    return Math.abs(a - b) < 0.01;
}

const factory = new harness.Factory();
factory.parseTextureAtlasData(ATLAS, null);
factory.parseDragonBonesData(SKELETON);
const armature = factory.buildArmature("arm");
if (armature === null) {
    throw new Error("buildArmature returned null");
}
const elbow = armature.getBone("elbow");
if (elbow === null) {
    throw new Error("elbow bone missing");
}

// Rest pose first: the elbow sits at (100, 0), unrotated.
armature.advanceTime(0.0);
console.log("rest: elbow global x=" + elbow.global.x.toFixed(3) +
    " y=" + elbow.global.y.toFixed(3) +
    " rotation=" + elbow.global.rotation.toFixed(4));
if (!Close(elbow.global.x, 100) || !Close(elbow.global.y, 0) || !Close(elbow.global.rotation, 0)) {
    throw new Error("rest pose mismatch");
}

// Posed: shoulder held at +90 degrees. By the core's own
// matrix convention the elbow lands at (0, 100) and its
// evaluated pose matrix is the +90 degree rotation. (In
// this runtime a bone's global.rotation field carries the
// locally composed rotation; the full evaluated pose lives
// in globalTransformMatrix, which is what a renderer
// consumes - see Bone._updateGlobalTransformMatrix.)
armature.animation.play("swing");
armature.advanceTime(0.05);
const m = elbow.globalTransformMatrix;
console.log("posed: elbow matrix a=" + m.a.toFixed(3) +
    " b=" + m.b.toFixed(3) + " c=" + m.c.toFixed(3) +
    " d=" + m.d.toFixed(3) + " tx=" + m.tx.toFixed(3) +
    " ty=" + m.ty.toFixed(3));
if (!Close(m.a, 0) || !Close(m.b, 1) || !Close(m.c, -1) || !Close(m.d, 0) ||
    !Close(m.tx, 0) || !Close(m.ty, 100)) {
    throw new Error("posed mismatch");
}

armature.advanceTime(0.0);
const slot = armature.getSlot("armSlot");
if (slot === null) {
    throw new Error("armSlot missing");
}
slot.updateGlobalTransform();
console.log("posed: slot global x=" + slot.global.x.toFixed(3) +
    " y=" + slot.global.y.toFixed(3) +
    " rotation=" + slot.global.rotation.toFixed(4));
// fromMatrix may report the angle as -3pi/2 instead of
// +pi/2; compare the angle's cosine and sine, not its raw
// value.
if (!Close(slot.global.x, 0) || !Close(slot.global.y, 100) ||
    !Close(Math.cos(slot.global.rotation), 0) || !Close(Math.sin(slot.global.rotation), 1)) {
    throw new Error("slot pose mismatch");
}

console.log("HARNESS PASS");
