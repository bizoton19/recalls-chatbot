from .base import BaseRecallClient, RecallRecord
from .cpsc_client import CPSCClient
from .nhtsa_client import NHTSAClient
from .fda_client import FDAClient
from .usda_client import USDAClient

ALL_CLIENTS: list[BaseRecallClient] = [
    CPSCClient(),
    NHTSAClient(),
    FDAClient(),
    USDAClient(),
]

__all__ = [
    "BaseRecallClient",
    "RecallRecord",
    "CPSCClient",
    "NHTSAClient",
    "FDAClient",
    "USDAClient",
    "ALL_CLIENTS",
]
