#!/usr/bin/env node
/**
 * Yui Indexer — Escaneia o workspace e gera índice econômico.
 * Cria .yui-index.json com path, tamanho e preview (40 linhas) por arquivo.
 * Focado em economia de tokens para futura integração com IA.
 */

const fs = require("fs");
const path = require("path");

// Pastas a ignorar (economia de tokens)
const IGNORE_DIRS = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".next",
  "coverage",
  "__pycache__",
  ".venv",
  "venv",
  ".env",
]);

// Extensões permitidas
const EXTENSIONS = new Set([".js", ".ts", ".tsx", ".jsx", ".py", ".json"]);

// Máximo de linhas de preview por arquivo
const PREVIEW_LINES = 40;

// Arquivo de saída
const INDEX_FILE = ".yui-index.json";

/**
 * Verifica se o arquivo deve ser indexado
 */
function shouldIndex(filePath) {
  const name = path.basename(filePath);
  if (name === ".yui-index.json") return false;
  const ext = path.extname(filePath).toLowerCase();
  return EXTENSIONS.has(ext);
}

/**
 * Lê as primeiras N linhas de um arquivo
 */
function readPreview(filePath) {
  try {
    const content = fs.readFileSync(filePath, "utf8");
    const lines = content.split(/\r?\n/).slice(0, PREVIEW_LINES);
    return lines.join("\n");
  } catch {
    return "";
  }
}

/**
 * Escaneia recursivamente um diretório
 */
function scanDir(dir, root, entries = []) {
  let items;
  try {
    items = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return entries;
  }

  for (const item of items) {
    const fullPath = path.join(dir, item.name);
    const relativePath = path.relative(root, fullPath);

    if (item.isDirectory()) {
      if (IGNORE_DIRS.has(item.name.toLowerCase())) continue;
      scanDir(fullPath, root, entries);
    } else if (item.isFile() && shouldIndex(item.name)) {
      const stats = fs.statSync(fullPath);
      const preview = readPreview(fullPath);
      entries.push({
        path: relativePath.replace(/\\/g, "/"),
        size: stats.size,
        preview: preview.trim(),
      });
    }
  }

  return entries;
}

/**
 * Main
 */
function main() {
  const root = process.cwd();
  console.log("[Yui] Indexando workspace:", root);

  const entries = scanDir(root, root);
  const index = {
    generated: new Date().toISOString(),
    root,
    count: entries.length,
    files: entries,
  };

  const outPath = path.join(root, INDEX_FILE);
  fs.writeFileSync(outPath, JSON.stringify(index, null, 0), "utf8");

  console.log("[Yui] Índice criado:", outPath);
  console.log("[Yui] Arquivos indexados:", entries.length);
}

main();
