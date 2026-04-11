from .base import BaseRecallClient, RecallRecord
from .cpsc_client import CPSCClient

ALL_CLIENTS: list[BaseRecallClient] = [
    CPSCClient(),
]

__all__ = [
    "BaseRecallClient",
    "RecallRecord",
    "CPSCClient",
    "ALL_CLIENTS",
]
