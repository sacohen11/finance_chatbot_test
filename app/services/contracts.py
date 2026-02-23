from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ContractEntry:
    contractor_name: str
    contract_value: str
    notes: str


class ContractService:
    def __init__(self) -> None:
        self._entries: List[ContractEntry] = []

    def add_contract(self, contractor_name: str, contract_value: str, notes: str) -> None:
        self._entries.append(
            ContractEntry(
                contractor_name=contractor_name.strip(),
                contract_value=contract_value.strip(),
                notes=notes.strip(),
            )
        )

    def list_contracts(self) -> List[ContractEntry]:
        return list(self._entries)
