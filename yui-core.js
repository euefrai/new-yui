#!/usr/bin/env node
/**
 * Yui Core — Operações de arquivo do workspace.
 * Listar, ler, escrever. Backup automático antes de modificar.
 * Nunca altera node_modules ou .git.
 */

const fs = require("fs");
const path = require("path");

const LOG_FILE = ".yui-log.txt";
const BACKUP_DIR = ".yui-backups";

// Pastas proibidas
const FORBIDDEN = new Set(["node_modules", ".git", "dist", "build", ".next", "coverage"]);

/**
 * Registra ação no log
 */
function log(action, detail) {
  const line = `[${new Date().toISOString()}] ${action}: ${detail}\n`;
  const logPath = path.join(process.cwd(), LOG_FILE);
  fs.appendFileSync(logPath, line, "utf8");
}

/**
 * Verifica se o caminho é permitido
 */
function isAllowed(filePath) {
  const normalized = path.normalize(filePath).replace(/\\/g, "/");
  const parts = normalized.split("/");
  for (const p of parts) {
    if (FORBIDDEN.has(p.toLowerCase())) return false;
  }
  return true;
}

/**
 * Resolve caminho relativo ao cwd
 */
function resolvePath(relativePath) {
  const root = process.cwd();
  const full = path.resolve(root, relativePath);
  if (!full.startsWith(root)) {
    throw new Error("Caminho fora do workspace");
  }
  return full;
}

/**
 * Lista arquivos recursivamente
 * @param {string} dir - Diretório (relativo ao cwd)
 * @param {string[]} extensions - Extensões permitidas (opcional)
 * @returns {string[]} Caminhos relativos
 */
function listFiles(dir = ".", extensions = null) {
  const fullDir = resolvePath(dir);
  if (!fs.existsSync(fullDir) || !fs.statSync(fullDir).isDirectory()) {
    return [];
  }

  const root = process.cwd();
  const result = [];

  function scan(d) {
    let items;
    try {
      items = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      return;
    }

    for (const item of items) {
      const full = path.join(d, item.name);
      const rel = path.relative(root, full).replace(/\\/g, "/");

      if (item.isDirectory()) {
        if (FORBIDDEN.has(item.name.toLowerCase())) continue;
        if (rel.startsWith(BACKUP_DIR) || rel === LOG_FILE) continue;
        scan(full);
      } else if (item.isFile()) {
        if (extensions) {
          const ext = path.extname(item.name).toLowerCase();
          if (!extensions.includes(ext)) continue;
        }
        result.push(rel);
      }
    }
  }

  scan(fullDir);
  return result.sort();
}

/**
 * Lê conteúdo de um arquivo
 * @param {string} filePath - Caminho relativo
 * @returns {string} Conteúdo
 */
function readFile(filePath) {
  if (!isAllowed(filePath)) throw new Error("Acesso negado: " + filePath);
  const full = resolvePath(filePath);
  if (!fs.existsSync(full)) throw new Error("Arquivo não existe: " + filePath);
  if (!fs.statSync(full).isFile()) throw new Error("Não é arquivo: " + filePath);
  return fs.readFileSync(full, "utf8");
}

/**
 * Cria backup antes de modificar
 */
function createBackup(filePath) {
  const full = resolvePath(filePath);
  if (!fs.existsSync(full)) return null;

  const root = process.cwd();
  const backupRoot = path.join(root, BACKUP_DIR);
  if (!fs.existsSync(backupRoot)) fs.mkdirSync(backupRoot, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const safeName = filePath.replace(/[\/\\]/g, "_");
  const backupPath = path.join(backupRoot, `${safeName}.${timestamp}.bak`);
  fs.copyFileSync(full, backupPath);
  log("BACKUP", backupPath);
  return path.relative(root, backupPath).replace(/\\/g, "/");
}

/**
 * Escreve em um arquivo (com backup automático)
 * @param {string} filePath - Caminho relativo
 * @param {string} content - Novo conteúdo
 * @returns {{ backup: string|null, written: boolean }}
 */
function writeFile(filePath, content) {
  if (!isAllowed(filePath)) throw new Error("Acesso negado: " + filePath);
  const full = resolvePath(filePath);

  const backup = createBackup(filePath);

  fs.writeFileSync(full, content, "utf8");
  log("WRITE", filePath);
  return { backup, written: true };
}

/**
 * CLI para testes
 */
if (require.main === module) {
  const cmd = process.argv[2];
  const arg = process.argv[3];

  if (cmd === "list") {
    console.log(JSON.stringify(listFiles(arg || "."), null, 2));
  } else if (cmd === "read" && arg) {
    console.log(readFile(arg));
  } else {
    console.log("Uso: node yui-core.js list [dir] | read <file>");
  }
} else {
  module.exports = { listFiles, readFile, writeFile, createBackup, log, isAllowed };
}
