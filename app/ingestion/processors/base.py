from abc import ABC, abstractmethod

class BaseDocumentProcessor(ABC):

    @abstractmethod
    def extract_pages(self, source) -> list[str]:
        pass

    @abstractmethod
    def document_type(self) -> str:
        pass

    @abstractmethod
    def extension(self) -> str:
        pass

