import vscode_regexp_languagedetection from 'vscode-regexp-languagedetection';

let o = {}; // what's this? extract weighting?
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
`, o) ?? null;

console.log(result);
