"""Persistência de memória e estado."""

from yui_ai.memory.chat_memory import ChatMemory, get_chat_memory

# Singleton: from yui_ai.memory import chat_memory → chat_memory.add_message("usuario", texto)
chat_memory = get_chat_memory()

__all__ = ["ChatMemory", "get_chat_memory", "chat_memory"]
