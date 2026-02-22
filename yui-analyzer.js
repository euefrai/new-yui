#!/usr/bin/env node
/**
 * Yui Analyzer — Analisa o projeto com contexto mínimo.
 * Recebe pergunta do usuário, busca arquivos relevantes, gera resumo técnico.
 * Nunca carrega o projeto inteiro. Preparado para integração com OpenAI.
 */

const fs = require("fs");
const path = require("path");
const { search } = require("./yui-search.js");

const INDEX_FILE = ".yui-index.json";

/**
 * Extrai termos de busca da pergunta do usuário
 */
function extractKeywords(question) {
  const stop = new Set([
    "o", "a", "os", "as", "um", "uma", "de", "da", "do", "em", "no", "na",
    "que", "como", "qual", "quais", "por", "para", "com", "sem", "se", "é",
    "são", "foi", "ser", "estar", "ter", "pode", "deve", "quero", "preciso",
    "meu", "minha", "esse", "essa", "isso", "isso", "código", "arquivo",
  ]);
  const words = question.toLowerCase().replace(/[^\w\sáàâãéêíóôõúç]/g, " ").split(/\s+/);
  return words.filter((w) => w.length > 2 && !stop.has(w));
}

/**
 * Carrega conteúdo dos arquivos encontrados (apenas preview do índice)
 */
function loadFileContexts(fileEntries) {
  return fileEntries.map((f) => ({
    path: f.path,
    size: f.size,
    preview: f.preview,
  }));
}

/**
 * Monta contexto mínimo para análise
 */
function buildContext(fileContexts) {
  const parts = fileContexts.map((f) => {
    return `--- ${f.path} (${f.size} bytes) ---\n${f.preview}`;
  });
  return parts.join("\n\n");
}

/**
 * Gera resumo técnico (estrutura para futura IA)
 * Por ora, gera análise heurística simples
 */
function generateSummary(question, fileContexts) {
  const context = buildContext(fileContexts);
  const lines = context.split("\n");

  const summary = {
    pergunta: question,
    arquivos_analisados: fileContexts.map((f) => f.path),
    resumo: [],
  };

  // Heurísticas simples (economia de tokens)
  const issues = [];

  for (const ctx of fileContexts) {
    const preview = ctx.preview;
    const pathLower = ctx.path.toLowerCase();

    // Organização
    if (preview.includes("TODO") || preview.includes("FIXME")) {
      issues.push({ tipo: "organização", arquivo: ctx.path, nota: "TODO/FIXME encontrado" });
    }

    // Segurança
    if (preview.includes("eval(") || preview.includes("exec(")) {
      issues.push({ tipo: "segurança", arquivo: ctx.path, nota: "Uso de eval/exec" });
    }
    if (preview.includes("password") && preview.includes("=") && !preview.includes("env")) {
      issues.push({ tipo: "segurança", arquivo: ctx.path, nota: "Possível senha em texto" });
    }

    // Performance
    if (preview.includes("for (") && preview.includes("for (")) {
      const nested = (preview.match(/for\s*\(/g) || []).length;
      if (nested >= 2) {
        issues.push({ tipo: "performance", arquivo: ctx.path, nota: "Loops aninhados" });
      }
    }

    // Legibilidade
    const longLines = preview.split("\n").filter((l) => l.length > 120);
    if (longLines.length > 2) {
      issues.push({ tipo: "legibilidade", arquivo: ctx.path, nota: "Linhas muito longas" });
    }
  }

  summary.resumo = issues.length > 0 ? issues : [{ tipo: "info", arquivo: "-", nota: "Nenhum problema óbvio nos arquivos analisados" }];

  return summary;
}

/**
 * Main: pergunta via argumento ou stdin
 */
async function main() {
  let question = process.argv.slice(2).join(" ").trim();

  if (!question && process.stdin.isTTY) {
    console.log("Uso: node yui-analyzer.js <pergunta>");
    console.log("Ex: node yui-analyzer.js \"onde está a autenticação?\"");
    process.exit(1);
  }

  if (!question) {
    question = await new Promise((resolve) => {
      let data = "";
      process.stdin.on("data", (c) => (data += c));
      process.stdin.on("end", () => resolve(data.trim()));
    });
  }

  if (!question) {
    console.error("Pergunta vazia.");
    process.exit(1);
  }

  try {
    const keywords = extractKeywords(question);
    const query = keywords.length > 0 ? keywords.join(" ") : question.slice(0, 50);
    const files = search(query);

    if (files.length === 0) {
      console.log(JSON.stringify({
        pergunta: question,
        arquivos_analisados: [],
        resumo: [{ tipo: "info", arquivo: "-", nota: "Nenhum arquivo relevante encontrado. Execute: npm run yui:index" }],
      }, null, 2));
      return;
    }

    const contexts = loadFileContexts(files);
    const summary = generateSummary(question, contexts);

    console.log(JSON.stringify(summary, null, 2));
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}

main();
