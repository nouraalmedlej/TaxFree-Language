from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Token:
    type:  str          # T_VAR, IDENTIFIER, T_OP_ARITH, T_DELIM …
    value: str          # lexeme exactly as scanned
    line:  int          # 1-based source line

    def __repr__(self):
        return f"<{self.type}, {self.line}, {self.value!r}>"

#  PARSE-TREE NODE
@dataclass
class Node:
    label:    str
    token:    Optional[Token] = None      # set for leaf nodes
    children: List["Node"]   = field(default_factory=list)

    def add(self, child: "Node"):
        self.children.append(child)
        return child

    def pretty(self, prefix="", last=True) -> str:
        connector = "└── " if last else "├── "
        label = f"{self.label} [{self.token.value!r} @ line {self.token.line}]" if self.token else self.label
        lines = [prefix + connector + label]
        child_prefix = prefix + ("    " if last else "│   ")
        for i, child in enumerate(self.children):
            lines.append(child.pretty(child_prefix, i == len(self.children) - 1))
        return "\n".join(lines)

#  PARSE ERROR
class ParseError(Exception):
    pass