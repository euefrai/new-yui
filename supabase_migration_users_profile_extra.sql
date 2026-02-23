-- Migration: estender users_profile para preferências da IA
-- Execute no SQL Editor do Supabase (Dashboard -> SQL Editor)
-- Usado por: perfil do usuário, personalidade adaptativa, painel Admin (email para verificar admin)

-- Colunas de preferência (personalidade adaptativa)
ALTER TABLE users_profile
  ADD COLUMN IF NOT EXISTS nivel_tecnico TEXT DEFAULT 'desconhecido'
  CHECK (nivel_tecnico IN ('iniciante', 'intermediario', 'avancado', 'desconhecido'));

ALTER TABLE users_profile
  ADD COLUMN IF NOT EXISTS linguagens_pref TEXT DEFAULT '';

ALTER TABLE users_profile
  ADD COLUMN IF NOT EXISTS modo_resposta TEXT DEFAULT 'dev'
  CHECK (modo_resposta IN ('dev', 'explicativo', 'resumido'));

COMMENT ON COLUMN users_profile.nivel_tecnico IS 'Nível técnico: iniciante, intermediario, avancado';
COMMENT ON COLUMN users_profile.linguagens_pref IS 'Linguagens preferidas (ex: python, js)';
COMMENT ON COLUMN users_profile.modo_resposta IS 'Modo de resposta: dev, explicativo, resumido';
