"""
Engine central da Yui: processa mensagens com histórico e persiste no Supabase.
"""
import os

from openai import OpenAI

from core.memory import get_messages, save_message

OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Modelo: gpt-4o disponível; gpt-5.2 não existe ainda
MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def process_message(user_id, chat_id, message):
    save_message(chat_id, "user", message)
    history = get_messages(chat_id)
    msgs = [{"role": m["role"], "content": m["content"] or ""} for m in history]
    if not client:
        return "⚠️ Configure OPENAI_API_KEY no servidor para respostas da Yui."
    response = client.chat.completions.create(
        model=MODEL,
        messages=msgs
    )
    reply = response.choices[0].message.content or ""
    save_message(chat_id, "assistant", reply)
    return reply
