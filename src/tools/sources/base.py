from abc import ABC, abstractmethod
from datetime import date
import pandas as pd


class BaseSource(ABC):
    @abstractmethod
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class BaseStockListSource(ABC):
    @abstractmethod
    async def fetch(self, market: str) -> pd.DataFrame:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
