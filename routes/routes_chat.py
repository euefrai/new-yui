"""Compat layer: preserva imports legados de `routes.routes_chat`."""

from web.routes.routes_chat import (
    chat_bp,
    api_get_chats,
    api_new_chat,
    api_messages,
    api_send,
    api_chat_job,
    api_chat_stream,
    api_chat_title,
    api_chat_delete,
    api_message_edit,
    api_message_delete,
)
