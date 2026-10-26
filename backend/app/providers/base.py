from abc import ABC, abstractmethod


class ProviderError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class DataProvider(ABC):
    @abstractmethod
    async def page(self, spec, city, category, page): ...
    @abstractmethod
    async def diagnose(self): ...
