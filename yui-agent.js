#!/usr/bin/env node
/**
 * Yui Agent — Agente com controle do workspace.
 * Recebe instrução, identifica arquivos, sugere modificação, mostra diff, confirma antes de aplicar.
 * Nunca modifica sem backup. Nunca altera node_modules ou .git.
 * Log em .yui-log.txt. Preparado para integração com OpenAI.
 */

const fs = require("fs");
const path = require("path");
const readline = require("readline");

const { search } = require("./yui-search.js");
const { readFile, writeFile, log, isAllowed } = require("./yui-core.js");
const { diff, formatDiff } = require("./yui-diff.js");

/**
 * Extrai termos de busca da instrução
 */
function extractKeywords(instruction) {
  const stop = new Set([
    "o", "a", "os", "as", "um", "uma", "de", "da", "do", "em", "no", "na",
    "que", "como", "qual", "quais", "por", "para", "com", "sem", "se", "é",
    "são", "arquivo", "arquivos", "código", "adicionar", "remover", "modificar",
  ]);
  const words = instruction.toLowerCase().replace(/[^\w\sáàâãéêíóôõúç]/g, " ").split(/\s+/);
  return words.filter((w) => w.length > 2 && !stop.has(w));
}

/**
 * Identifica arquivos relevantes para a instrução
 */
function findRelevantFiles(instruction) {
  const keywords = extractKeywords(instruction);
  const query = keywords.length > 0 ? keywords.join(" ") : instruction.slice(0, 50);
  return search(query);
}

/**
 * Carrega modificações de um arquivo JSON
 * Formato: [{ path: "caminho/arquivo", content: "novo conteúdo" }]
 */
function loadModifications(filePath) {
  const full = path.resolve(process.cwd(), filePath);
  if (!fs.existsSync(full)) return null;
  const raw = fs.readFileSync(full, "utf8");
  try {
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : data.modifications || [data];
  } catch {
    return null;
  }
}

/**
 * Mostra diff e pergunta confirmação
 */
function confirmWithUser(filePath, diffResult) {
  return new Promise((resolve) => {
    console.log("\n" + "=".repeat(60));
    console.log("Arquivo:", filePath);
    console.log("=".repeat(60));
    console.log(formatDiff(diffResult, filePath));
    console.log("");

    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question("Aplicar esta modificação? (s/n): ", (answer) => {
      rl.close();
      resolve(/^s|sim|y|yes$/i.test(answer.trim()));
    });
  });
}

/**
 * Executa o agente
 */
async function run(instruction, modificationsPath, autoConfirm = false) {
  log("AGENT_START", instruction);

  const files = findRelevantFiles(instruction);
  if (files.length === 0) {
    console.log("Nenhum arquivo relevante encontrado. Execute: npm run yui:index");
    log("AGENT_END", "no files");
    return;
  }

  console.log("\n[Yui] Arquivos relevantes:");
  files.forEach((f, i) => console.log(`  ${i + 1}. ${f.path} (score: ${f.score})`));

  if (!modificationsPath) {
    console.log("\n[Yui] Para aplicar modificações, crie um JSON com o formato:");
    console.log('  [{ "path": "caminho/arquivo", "content": "novo conteúdo" }]');
    console.log("  Execute: node yui-agent.js \"instrução\" --apply modificacoes.json");
    log("AGENT_END", "no modifications");
    return;
  }

  const modifications = loadModifications(modificationsPath);
  if (!modifications || modifications.length === 0) {
    console.log("Arquivo de modificações inválido ou vazio.");
    log("AGENT_END", "invalid modifications");
    return;
  }

  let applied = 0;
  for (const mod of modifications) {
    const filePath = mod.path || mod.file;
    const newContent = mod.content;

    if (!filePath || newContent === undefined) {
      console.log("Modificação inválida (falta path ou content):", mod);
      continue;
    }

    if (!isAllowed(filePath)) {
      console.log("Acesso negado:", filePath);
      log("AGENT_DENIED", filePath);
      continue;
    }

    let oldContent;
    try {
      oldContent = fs.existsSync(path.resolve(process.cwd(), filePath))
        ? readFile(filePath)
        : "";
    } catch (e) {
      console.log("Erro ao ler:", filePath, e.message);
      continue;
    }

    const diffResult = diff(oldContent, newContent);
    const hasChanges =
      diffResult.summary.added > 0 || diffResult.summary.removed > 0 || diffResult.summary.changed > 0;

    if (!hasChanges) {
      console.log("Sem alterações em:", filePath);
      continue;
    }

    let ok = autoConfirm;
    if (!autoConfirm) {
      ok = await confirmWithUser(filePath, diffResult);
    }

    if (ok) {
      try {
        writeFile(filePath, newContent);
        console.log("Aplicado:", filePath);
        log("AGENT_APPLY", filePath);
        applied++;
      } catch (e) {
        console.log("Erro ao escrever:", filePath, e.message);
        log("AGENT_ERROR", `${filePath}: ${e.message}`);
      }
    } else {
      console.log("Ignorado:", filePath);
      log("AGENT_SKIP", filePath);
    }
  }

  console.log("\n[Yui] Modificações aplicadas:", applied);
  log("AGENT_END", `applied=${applied}`);
}

/**
 * CLI
 */
function main() {
  const args = process.argv.slice(2);
  let instruction = "";
  let modificationsPath = null;
  let autoConfirm = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--apply" && args[i + 1]) {
      modificationsPath = args[i + 1];
      i++;
    } else if (args[i] === "--yes" || args[i] === "-y") {
      autoConfirm = true;
    } else {
      instruction += (instruction ? " " : "") + args[i];
    }
  }

  instruction = instruction.trim();

  if (!instruction) {
    console.log("Uso: node yui-agent.js \"instrução\" [--apply modificacoes.json] [--yes]");
    console.log("Ex:  node yui-agent.js \"melhorar auth\" --apply suggested.json");
    process.exit(1);
  }

  run(instruction, modificationsPath, autoConfirm).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

if (require.main === module) {
  main();
} else {
  module.exports = { run, findRelevantFiles, loadModifications };
}
