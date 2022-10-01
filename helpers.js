import vscode_regexp_languagedetection from './vendor/vscode-regexp-languagedetection/dist/index.js';

async function run_vscode_regexp_languagedetection(content, bias = {}) {
  const languageId = vscode_regexp_languagedetection.detect(content, bias) ?? null;
  return languageId ? [{ languageId, confidence: -1.0 /* unknown */ }] : [];
}

export { run_vscode_regexp_languagedetection };
