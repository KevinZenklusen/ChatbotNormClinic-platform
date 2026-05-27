from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    messages_from_dict,
    messages_to_dict,
    AIMessage,
    HumanMessage
)
from typing import List

from app.core.database_client import database


def _normalize_content(content):
    """
    Convierte contenido a string plano
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        textos = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                textos.append(item["text"])
        return " ".join(textos)

    return str(content)


def _normalize_message(msg: BaseMessage) -> BaseMessage:
    """
    Devuelve un mensaje con content SIEMPRE string
    """
    content = _normalize_content(msg.content)

    if isinstance(msg, HumanMessage):
        return HumanMessage(content=content)

    if isinstance(msg, AIMessage):
        return AIMessage(content=content)

    return msg


class DatabaseChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> List[BaseMessage]:
        history = database.get_chat_history(self.session_id) or []

        msgs = messages_from_dict(history)

        normalized = [_normalize_message(m) for m in msgs]

        print("HISTORIAL NORMALIZADO")
        print(normalized)

        return normalized

    def add_messages(self, messages: List[BaseMessage]) -> None:
        normalized = [_normalize_message(m) for m in messages]

        existing = database.get_chat_history(self.session_id) or []
        existing_msgs = messages_from_dict(existing)

        existing_ids = {m.id for m in existing_msgs if m.id}

        unique_messages = [
            m for m in normalized
            if not m.id or m.id not in existing_ids
        ]

        if not unique_messages:
            return

        new_messages = messages_to_dict(unique_messages)

        database.append_chat_history(self.session_id, new_messages)

    def clear(self) -> None:
        database.delete_chat_history(self.session_id)