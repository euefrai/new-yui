#!/usr/bin/env node
/**
 * Yui Search — Busca arquivos no índice por palavra-chave.
 * Retorna no máximo 5 arquivos mais relevantes.
 * Extremamente simples e econômico em tokens.
 */

const fs = require("fs");
const path = require("path");

const INDEX_FILE = ".yui-index.json";
const MAX_RESULTS = 5;

/**
 * Carrega o índice
 */
function loadIndex() {
  const indexPath = path.join(process.cwd(), INDEX_FILE);
  if (!fs.existsSync(indexPath)) {
    throw new Error(".yui-index.json não encontrado. Execute: npm run yui:index");
  }
  const raw = fs.readFileSync(indexPath, "utf8");
  return JSON.parse(raw);
}

/**
 * Calcula score de relevância (palavra no path ou preview)
 * Quanto mais ocorrências, maior o score
 */
function scoreFile(file, keywords) {
  const text = `${file.path} ${file.preview}`.toLowerCase();
  let score = 0;
  for (const kw of keywords) {
    const lower = kw.toLowerCase();
    if (file.path.toLowerCase().includes(lower)) score += 3; // path é mais relevante
    const matches = text.split(lower).length - 1;
    score += matches;
  }
  return score;
}

/**
 * Busca arquivos por palavra-chave
 * @param {string} query - Palavras separadas por espaço
 * @returns {Array} Até 5 arquivos mais relevantes
 */
function search(query) {
  const index = loadIndex();
  const keywords = query.trim().split(/\s+/).filter(Boolean);
  if (keywords.length === 0) return [];

  const scored = index.files.map((file) => ({
    ...file,
    score: scoreFile(file, keywords),
  }));

  return scored
    .filter((f) => f.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_RESULTS);
}

/**
 * CLI: node yui-search.js "palavra1 palavra2"
 */
function main() {
  const query = process.argv.slice(2).join(" ") || "";
  if (!query) {
    console.log("Uso: node yui-search.js <palavra-chave>");
    process.exit(1);
  }

  try {
    const results = search(query);
    console.log(JSON.stringify(results, null, 0));
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}

// Export para uso como módulo (yui-analyzer)
if (require.main === module) {
  main();
} else {
  module.exports = { search, loadIndex };
}
