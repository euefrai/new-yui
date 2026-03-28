-- Execute no SQL Editor do Supabase (Dashboard do projeto -> SQL Editor)
-- Arquitetura: auth.users → users_profile → chats → messages
-- Cada usuário só acessa seus próprios dados via RLS e validação no backend.

-- Extensão necessária para UUIDs seguros.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Perfil do usuário (opcional; pode usar só auth.users do Supabase Auth)
CREATE TABLE IF NOT EXISTS users_profile (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  nome TEXT,
  nivel_tecnico TEXT DEFAULT 'desconhecido'
    CHECK (nivel_tecnico IN ('iniciante', 'intermediario', 'avancado', 'desconhecido')),
  linguagens_pref TEXT DEFAULT '',
  modo_resposta TEXT DEFAULT 'dev'
    CHECK (modo_resposta IN ('dev', 'explicativo', 'resumido')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Chats por usuário
CREATE TABLE IF NOT EXISTS chats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  titulo TEXT NOT NULL DEFAULT 'Novo chat',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at DESC);

-- Mensagens de cada chat
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL DEFAULT '',
  type TEXT NOT NULL DEFAULT 'text'
    CHECK (type IN ('text', 'tool_call', 'tool_result')),
  metadata JSONB DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'done'
    CHECK (status IN ('streaming', 'done', 'error')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);

-- Memória contextual por usuário (eventos)
CREATE TABLE IF NOT EXISTS memory_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL CHECK (tipo IN ('curta', 'longa', 'tecnica')),
  conteudo TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_events_user_id ON memory_events(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_events_chat_id ON memory_events(chat_id);
CREATE INDEX IF NOT EXISTS idx_memory_events_created_at ON memory_events(created_at DESC);

-- Memória de longo prazo (RAG): resumos de decisões e conclusões
CREATE TABLE IF NOT EXISTS memoria_ia (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  resumo TEXT NOT NULL,
  tags TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memoria_ia_user_id ON memoria_ia(user_id);
CREATE INDEX IF NOT EXISTS idx_memoria_ia_chat_id ON memoria_ia(chat_id);
CREATE INDEX IF NOT EXISTS idx_memoria_ia_created_at ON memoria_ia(created_at DESC);

-- Habilita RLS para todas as tabelas que armazenam dados de usuários.
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE memoria_ia ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;

-- Políticas de acesso
CREATE POLICY IF NOT EXISTS "Usuário acessa só seus chats"
  ON chats FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Usuário acessa mensagens dos seus chats"
  ON messages FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM chats
      WHERE chats.id = messages.chat_id
        AND chats.user_id = auth.uid()
    )
  );

CREATE POLICY IF NOT EXISTS "Usuário acessa só seus eventos de memória"
  ON memory_events FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Usuário acessa só sua memoria_ia"
  ON memoria_ia FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Usuário acessa só seu perfil"
  ON users_profile FOR ALL
  USING (auth.uid() = id);

COMMENT ON COLUMN messages.type IS 'text = mensagem normal; tool_call = chamada a ferramenta; tool_result = resultado de ferramenta';
COMMENT ON COLUMN messages.metadata IS 'JSON livre: tool_name, args, result_summary, etc.';
COMMENT ON COLUMN messages.status IS 'streaming = em envio; done = finalizada; error = falha';
