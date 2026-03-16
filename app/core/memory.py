from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from typing import List

from app.core.database_client import database


class DatabaseChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> List[BaseMessage]:
        history = database.get_chat_history(self.session_id)
        return messages_from_dict(history)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        updated = messages_to_dict(self.messages + messages)
        database.save_chat_history(self.session_id, updated)

    def clear(self) -> None:
        database.delete_chat_history(self.session_id)

