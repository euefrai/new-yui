-- Execute no SQL Editor do Supabase (Dashboard do projeto -> SQL Editor)
-- Tabelas para login e chats por usuário

-- Perfil do usuário (opcional; pode usar só auth.users do Supabase Auth)
CREATE TABLE IF NOT EXISTS users_profile (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  nome TEXT
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
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- RLS (Row Level Security): cada usuário só acessa seus próprios dados
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuário acessa só seus chats"
  ON chats FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Usuário acessa mensagens dos seus chats"
  ON messages FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM chats
      WHERE chats.id = messages.chat_id AND chats.user_id = auth.uid()
    )
  );

-- Opcional: policy para users_profile
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuário acessa só seu perfil"
  ON users_profile FOR ALL
  USING (auth.uid() = id);
