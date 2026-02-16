-- =============================================================================
-- Schema profissional: user → chat_sessions (chats) → messages
-- =============================================================================
-- O backend SEMPRE valida que o chat pertence ao user_id antes de ler/escrever.
-- Tabela no Supabase: "chats" (equivale a chat_sessions). Coluna título: "titulo".
-- Execute o DDL completo em: supabase_schema.sql (raiz do projeto).
-- =============================================================================

-- users: já existe no Supabase Auth (auth.users). Não criar tabela extra.

-- chat_sessions (no projeto: tabela "chats")
-- Cada sessão de chat pertence a um único usuário.
-- create table chats (
--   id uuid primary key default gen_random_uuid(),
--   user_id uuid not null references auth.users(id) on delete cascade,
--   titulo text not null default 'Novo chat',
--   created_at timestamptz default now()
-- );
-- create index idx_chats_user_id on chats(user_id);
-- create index idx_chats_created_at on chats(created_at desc);

-- messages: sempre vinculadas a uma sessão (chat_id). NÃO têm user_id direto.
-- O dono da mensagem é o dono do chat (chats.user_id).
-- create table messages (
--   id uuid primary key default gen_random_uuid(),
--   chat_id uuid not null references chats(id) on delete cascade,
--   role text not null check (role in ('user', 'assistant')),
--   content text not null default '',
--   created_at timestamptz default now()
-- );
-- create index idx_messages_chat_id on messages(chat_id);
-- create index idx_messages_created_at on messages(created_at);

-- RLS: chats e messages com políticas por auth.uid() / user_id.
-- Backend (service role) ignora RLS; por isso core/memory.py valida
-- chat_belongs_to_user(chat_id, user_id) e message_belongs_to_user(message_id, user_id)
-- em todas as operações que recebem chat_id ou message_id.
