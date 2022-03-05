import vscode_languagedetection from '@vscode/vscode-languagedetection';
import vscode_regexp_languagedetection from './vendor/vscode-regexp-languagedetection/dist/index.js';

async function run_vscode_languagedetection(content) {
  const model_operations = new vscode_languagedetection.ModelOperations();
  return await model_operations.runModel(content);
}

async function run_vscode_regexp_languagedetection(content, bias = {}) {
  const languageId = vscode_regexp_languagedetection.detect(content, bias) ?? null;
  return languageId ? [{ languageId, confidence: -1.0 /* unknown */ }] : [];
}

export { run_vscode_languagedetection, run_vscode_regexp_languagedetection };
