#!/usr/bin/env node
/**
 * Yui Diff — Comparação linha a linha.
 * Mostra diferenças entre conteúdo antigo e novo.
 * Sem bibliotecas externas.
 */

/**
 * Gera diff linha a linha (algoritmo simples)
 * @param {string} oldContent - Conteúdo antigo
 * @param {string} newContent - Conteúdo novo
 * @returns {{ lines: Array<{type: string, oldLine?: number, newLine?: number, content: string}>, summary: object }}
 */
function diff(oldContent, newContent) {
  const oldLines = (oldContent || "").split(/\r?\n/);
  const newLines = (newContent || "").split(/\r?\n/);

  const result = [];
  let i = 0;
  let j = 0;

  while (i < oldLines.length || j < newLines.length) {
    const oldLine = oldLines[i];
    const newLine = newLines[j];

    if (i >= oldLines.length) {
      result.push({ type: "add", newLine: j + 1, content: newLine });
      j++;
      continue;
    }
    if (j >= newLines.length) {
      result.push({ type: "remove", oldLine: i + 1, content: oldLine });
      i++;
      continue;
    }

    if (oldLine === newLine) {
      result.push({ type: "same", oldLine: i + 1, newLine: j + 1, content: oldLine });
      i++;
      j++;
      continue;
    }

    // Linhas diferentes: busca próxima coincidência
    const nextOldIdx = newLines.indexOf(oldLine, j + 1);
    const nextNewIdx = oldLines.indexOf(newLine, i + 1);

    if (nextOldIdx === j + 1) {
      result.push({ type: "add", newLine: j + 1, content: newLine });
      j++;
    } else if (nextNewIdx === i + 1) {
      result.push({ type: "remove", oldLine: i + 1, content: oldLine });
      i++;
    } else if (nextOldIdx >= 0 && (nextNewIdx < 0 || nextOldIdx - j <= nextNewIdx - i)) {
      for (let k = j; k < nextOldIdx; k++) {
        result.push({ type: "add", newLine: k + 1, content: newLines[k] });
      }
      result.push({ type: "same", oldLine: i + 1, newLine: nextOldIdx + 1, content: oldLine });
      i++;
      j = nextOldIdx + 1;
    } else if (nextNewIdx >= 0 && (nextOldIdx < 0 || nextNewIdx - i <= nextOldIdx - j)) {
      for (let k = i; k < nextNewIdx; k++) {
        result.push({ type: "remove", oldLine: k + 1, content: oldLines[k] });
      }
      result.push({ type: "same", oldLine: nextNewIdx + 1, newLine: j + 1, content: newLine });
      i = nextNewIdx + 1;
      j++;
    } else {
      result.push({ type: "change", oldLine: i + 1, newLine: j + 1, oldContent: oldLine, content: newLine });
      i++;
      j++;
    }
  }

  const summary = {
    added: result.filter((r) => r.type === "add").length,
    removed: result.filter((r) => r.type === "remove").length,
    changed: result.filter((r) => r.type === "change").length,
    same: result.filter((r) => r.type === "same").length,
  };

  return { lines: result, summary };
}

/**
 * Formata diff para exibição em texto
 * @param {object} diffResult - Resultado de diff()
 * @param {string} filePath - Nome do arquivo (opcional)
 * @returns {string}
 */
function formatDiff(diffResult, filePath = "") {
  const { lines, summary } = diffResult;
  const out = [];

  if (filePath) out.push(`--- ${filePath}`);
  out.push("");

  for (const line of lines) {
    if (line.type === "change") {
      out.push(`- ${line.oldLine || ""} | ${(line.oldContent || "").replace(/\t/g, "  ")}`);
      out.push(`+ ${line.newLine || ""} | ${(line.content || "").replace(/\t/g, "  ")}`);
    } else {
      const prefix = line.type === "add" ? "+" : line.type === "remove" ? "-" : " ";
      const num = line.oldLine || line.newLine || "";
      out.push(`${prefix} ${num} | ${(line.content || "").replace(/\t/g, "  ")}`);
    }
  }

  out.push("");
  out.push(`Resumo: +${summary.added} -${summary.removed} ~${summary.changed}`);
  return out.join("\n");
}

/**
 * CLI
 */
if (require.main === module) {
  const oldFile = process.argv[2];
  const newFile = process.argv[3];

  if (!oldFile || !newFile) {
    console.log("Uso: node yui-diff.js <arquivo-antigo> <arquivo-novo>");
    process.exit(1);
  }

  const fs = require("fs");
  const oldContent = fs.existsSync(oldFile) ? fs.readFileSync(oldFile, "utf8") : "";
  const newContent = fs.existsSync(newFile) ? fs.readFileSync(newFile, "utf8") : "";

  const result = diff(oldContent, newContent);
  console.log(formatDiff(result, `${oldFile} -> ${newFile}`));
} else {
  module.exports = { diff, formatDiff };
}
