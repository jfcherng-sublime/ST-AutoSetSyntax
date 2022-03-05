import vscode_regexp_languagedetection from '../vendor/vscode-regexp-languagedetection/dist/index.js';

let bias = {}; // how do we use this?
let result = vscode_regexp_languagedetection.detect(`
function makeThing(): Thing {
    let size = 0;
    return {
        get size(): number {
        return size;
        },
        set size(value: string | number | boolean) {
        let num = Number(value);
        // Don't allow NaN and stuff.
        if (!Number.isFinite(num)) {
            size = 0;
            return;
        }
        size = num;
        },
    };
}
`, bias) ?? null;

console.log(result);
