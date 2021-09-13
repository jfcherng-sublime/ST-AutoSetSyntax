import vscode_languagedetection from '@vscode/vscode-languagedetection';

const { ModelOperations } = vscode_languagedetection;
const model_operations = new ModelOperations();

const result = await model_operations.runModel(`
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
`);

console.log(result);
