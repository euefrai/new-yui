-- Migration: estender tabela messages para IA avançada
-- Execute no SQL Editor do Supabase (Dashboard -> SQL Editor)
-- Permite: replay de ferramentas, memória estruturada, histórico por tipo.

-- Coluna type: text | tool_call | tool_result (default 'text' para mensagens atuais)
ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'text'
  CHECK (type IN ('text', 'tool_call', 'tool_result'));

-- Coluna metadata: JSON livre (ex.: nome da tool, args, resultado resumido)
ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Coluna status: streaming | done | error (útil para UI e replay)
ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'done'
  CHECK (status IN ('streaming', 'done', 'error'));

-- Índice opcional para filtrar por type
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);

COMMENT ON COLUMN messages.type IS 'text = mensagem normal; tool_call = chamada a ferramenta; tool_result = resultado de ferramenta';
COMMENT ON COLUMN messages.metadata IS 'JSON livre: tool_name, args, result_summary, etc.';
COMMENT ON COLUMN messages.status IS 'streaming = em envio; done = finalizada; error = falha';
