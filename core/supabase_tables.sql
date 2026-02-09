-- Schema de referência para o core (chats + messages).
-- O projeto usa supabase_schema.sql na raiz (com RLS e auth.users).
-- Este arquivo documenta as tabelas usadas por core/memory.py e core/engine.py.

-- Chats por usuário (campo titulo usado pelo core)
-- create table chats (
--   id uuid primary key default uuid_generate_v4(),
--   user_id text not null,
--   titulo text default 'Novo chat',
--   created_at timestamp default now()
-- );

-- Mensagens do chat (sem user_id; vínculo é por chat_id)
-- create table messages (
--   id uuid primary key default uuid_generate_v4(),
--   chat_id uuid not null references chats(id) on delete cascade,
--   role text not null check (role in ('user', 'assistant')),
--   content text not null default '',
--   created_at timestamp default now()
-- );

-- Índices recomendados
-- create index idx_chats_user_id on chats(user_id);
-- create index idx_messages_chat_id on messages(chat_id);
