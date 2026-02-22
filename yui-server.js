/**
 * YUI Server — Base segura para agente de IA com controle do workspace.
 * Usa Node.js puro: fs, path, child_process.
 * Regras: nunca acessar node_modules/.git, bloquear comandos destrutivos,
 * validar caminhos, backup antes de sobrescrever, trabalhar só em process.cwd().
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// Diretório raiz do workspace (imutável)
const WORKSPACE_ROOT = process.cwd();

// Pastas proibidas
const FORBIDDEN_DIRS = new Set(["node_modules", ".git"]);

// Comandos perigosos bloqueados
const DANGEROUS_PATTERNS = [
  /\brm\s+-rf?\b/i,
  /\brm\s+-fr\b/i,
  /\brm\s+.*\*+/,
  /\bdel\s+/i,
  /\bformat\s+/i,
  /\bshutdown\s+/i,
  /\bmkfs\./i,
  /\bdd\s+if=/i,
  /\b:(){.*};:/,  // fork bomb
];

/**
 * Resolve e valida caminho dentro do workspace.
 * Bloqueia path traversal (..) e acesso fora do cwd.
 * @param {string} rawPath - Caminho relativo ou absoluto
 * @returns {string} Caminho absoluto resolvido e validado
 * @throws {Error} Se caminho inválido ou fora do workspace
 */
function resolveAndValidate(rawPath) {
  if (!rawPath || typeof rawPath !== "string") {
    throw new Error("Caminho inválido ou vazio");
  }
  const normalized = path.normalize(rawPath.trim());
  const resolved = path.isAbsolute(normalized)
    ? path.resolve(normalized)
    : path.resolve(WORKSPACE_ROOT, normalized);

  const relative = path.relative(WORKSPACE_ROOT, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Caminho fora do workspace");
  }
  if ([...FORBIDDEN_DIRS].some((d) => relative.includes(d))) {
    throw new Error("Acesso a pasta proibida (node_modules, .git)");
  }
  return resolved;
}

/**
 * Lista arquivos e pastas do diretório.
 * Ignora node_modules e .git.
 * @param {string} dir - Caminho do diretório (relativo ao cwd)
 * @returns {string[]} Array de nomes de arquivos/pastas
 */
function listFiles(dir) {
  const resolved = resolveAndValidate(dir || ".");
  if (!fs.existsSync(resolved)) {
    throw new Error("Diretório não existe");
  }
  if (!fs.statSync(resolved).isDirectory()) {
    throw new Error("Não é um diretório");
  }
  const entries = fs.readdirSync(resolved, { withFileTypes: true });
  return entries
    .filter((e) => !FORBIDDEN_DIRS.has(e.name))
    .map((e) => e.name);
}

/**
 * Lê conteúdo de arquivo em texto.
 * Valida caminho e limita a 2000 linhas.
 * @param {string} filePath - Caminho do arquivo
 * @returns {string} Conteúdo do arquivo
 */
function readFile(filePath) {
  const resolved = resolveAndValidate(filePath);
  if (!fs.existsSync(resolved)) {
    throw new Error("Arquivo não existe");
  }
  if (!fs.statSync(resolved).isFile()) {
    throw new Error("Não é um arquivo");
  }
  const content = fs.readFileSync(resolved, "utf8");
  const lines = content.split("\n");
  if (lines.length > 2000) {
    return lines.slice(0, 2000).join("\n") + "\n// ... (truncado em 2000 linhas)";
  }
  return content;
}

/**
 * Escreve conteúdo em arquivo.
 * Cria backup (.bak) se o arquivo já existir.
 * @param {string} filePath - Caminho do arquivo
 * @param {string} content - Conteúdo a escrever
 */
function writeFile(filePath, content) {
  const resolved = resolveAndValidate(filePath);
  if (typeof content !== "string") {
    content = String(content);
  }

  if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
    const backupPath = resolved + ".bak";
    fs.copyFileSync(resolved, backupPath);
  }

  const dir = path.dirname(resolved);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(resolved, content, "utf8");
}

/**
 * Executa comando com child_process.execSync.
 * Bloqueia comandos perigosos (rm, del, format, shutdown, etc).
 * @param {string} command - Comando a executar
 * @returns {string} stdout do comando
 */
function runCommand(command) {
  if (!command || typeof command !== "string") {
    throw new Error("Comando inválido ou vazio");
  }
  const trimmed = command.trim();
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(trimmed)) {
      throw new Error("Comando bloqueado por segurança");
    }
  }
  try {
    const result = execSync(trimmed, {
      encoding: "utf8",
      cwd: WORKSPACE_ROOT,
      maxBuffer: 10 * 1024 * 1024, // 10MB
    });
    return result || "";
  } catch (err) {
    if (err.stdout) return String(err.stdout);
    throw err;
  }
}

module.exports = {
  listFiles,
  readFile,
  writeFile,
  runCommand,
  WORKSPACE_ROOT,
};
