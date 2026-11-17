// Source: DragonBones core runtime - 2D bone hierarchy, IK,
// Source: skinning and animation evaluation for layered rigs (RW-01).
// Source: Project DragonBones/DragonBonesJS, file DragonBones/src/dragonBones/model/CanvasData.ts, commit 64b6c69ae35777c2404be68c9192e2c56906079e.
// Source: Licence MIT, Copyright (c) 2012-2025 The DragonBones team and
// Source: other contributors - see the LICENSE staged with this part.
// Source: Copied literally 2026-11-16; only this header and the
// Source: comment-word change noted in Staging_Note_V1.TXT differ.
/**
 * The MIT License (MIT)
 *
 * Copyright (c) 2012-2025 DragonBones team and other contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of
 * this software and associated documentation files (the "Software"), to deal in
 * the Software without restriction, including without limitation the rights to
 * use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 * the Software, and to permit persons to whom the Software is furnished to do so,
 * subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
namespace dragonBones {
    /**
     * @private
     */
    export class CanvasData extends BaseObject {
        public static toString(): string {
            return "[class dragonBones.CanvasData]";
        }

        public hasBackground: boolean;
        public color: number;
        public x: number;
        public y: number;
        public width: number;
        public height: number;

        protected _onClear(): void {
            this.hasBackground = false;
            this.color = 0x000000;
            this.x = 0;
            this.y = 0;
            this.width = 0;
            this.height = 0;
        }
    }
}