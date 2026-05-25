from __future__ import annotations
from typing import List, Tuple, Union, Dict
from nodes import Token, ParseError
from taxfree_scanner import tokenize

Terminal = Union[str, Tuple[str, str]]
Symbol = Union[str, Terminal]
EPS = "ε"
END = "T_EOF"


class LL1TableParser:
    """
    A table-driven LL(1) predictive parser for the TaxFree grammar.

    Important:
    - This file is added to satisfy/show the table-driven LL(1) requirement.
    - It does not replace parser.py used by the GUI semantic/TAC pipeline.
    - It validates syntax using a stack + LL(1) parsing table.
    """

    NON_TERMINALS = {
        "program", "func_list", "func_decl", "param_list", "param_list_tail", "param", "type_name",
        "block", "stmt_list", "statement", "stmt_tail", "var_init", "if_tail", "return_tail",
        "arg_list", "arg_list_tail",
        "expr", "or_expr", "or_tail", "and_expr", "and_tail", "rel_expr", "rel_tail",
        "add_expr", "add_tail", "mul_expr", "mul_tail", "pow_expr", "pow_tail",
        "unary_expr", "primary", "primary_tail"
    }

    def __init__(self, tokens: List[Token]):
        self.tokens = list(tokens)
        last_line = self.tokens[-1].line if self.tokens else 1
        self.tokens.append(Token(END, "$", last_line))
        self.pos = 0
        self.steps: List[str] = []
        self.table = self._build_table()

    # -----------------------------
    # Token helpers
    # -----------------------------
    def current(self) -> Token:
        return self.tokens[self.pos]

    def lookahead_key(self) -> Terminal:
        tok = self.current()
        if tok.type in ("T_DELIM", "T_OP_ARITH"):
            return (tok.type, tok.value)
        return tok.type

    def token_matches(self, terminal: Terminal, tok: Token) -> bool:
        if isinstance(terminal, tuple):
            return tok.type == terminal[0] and tok.value == terminal[1]
        return tok.type == terminal

    def terminal_name(self, terminal: Terminal) -> str:
        if isinstance(terminal, tuple):
            return f"{terminal[0]}('{terminal[1]}')"
        return terminal

    # -----------------------------
    # Main parse method
    # -----------------------------
    def parse(self) -> str:
        stack: List[Symbol] = [END, "program"]

        while stack:
            top = stack.pop()
            tok = self.current()
            la = self.lookahead_key()

            if top == EPS:
                continue

            if top not in self.NON_TERMINALS:
                if self.token_matches(top, tok):
                    self.steps.append(f"match {self.terminal_name(top)} -> {tok.value}")
                    self.pos += 1
                else:
                    expected = self.terminal_name(top)
                    found = tok.value if tok.value else tok.type
                    raise ParseError(
                        f"Syntax error at line {tok.line}: expected {expected}, found '{found}'."
                    )
                continue

            production = self.table.get((top, la))
            if production is None:
                # fallback for grouped relational operators
                if tok.type == "T_OP_REL":
                    production = self.table.get((top, "T_OP_REL"))

            if production is None:
                found = tok.value if tok.value else tok.type
                raise ParseError(
                    f"Syntax error at line {tok.line}: no LL(1) rule for {top} with lookahead '{found}'."
                )

            rhs_text = " ".join(self.terminal_name(s) if s not in self.NON_TERMINALS else s for s in production)
            self.steps.append(f"{top} -> {rhs_text if rhs_text else EPS}")

            for sym in reversed(production):
                if sym != EPS:
                    stack.append(sym)

        if self.pos != len(self.tokens):
            tok = self.current()
            raise ParseError(f"Syntax error at line {tok.line}: extra token '{tok.value}'.")

        return "Parsing successful using table-driven LL(1) parser."

    # -----------------------------
    # Parsing table
    # -----------------------------
    def _build_table(self) -> Dict[Tuple[str, Terminal], List[Symbol]]:
        T: Dict[Tuple[str, Terminal], List[Symbol]] = {}

        def add(nt: str, lookaheads: List[Terminal], prod: List[Symbol]):
            for la in lookaheads:
                T[(nt, la)] = prod

        expr_start: List[Terminal] = [
            "INTEGER", "FLOAT", "STRING", "BOOL_LIT", "IDENTIFIER",
            "T_ZAKAT", "T_TAX", "T_LOAN", "T_NOT",
            ("T_DELIM", "("), ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-")
        ]

        stmt_start: List[Terminal] = [
            "T_VAR", "IDENTIFIER", "T_IF", "T_WHILE", "T_REPEAT",
            "T_PRINT", "T_READ", "T_RETURN"
        ]

        expr_follow: List[Terminal] = [
            ("T_DELIM", ")"), ("T_DELIM", ","), ("T_DELIM", ";"),
            ("T_DELIM", "}"), "T_THEN", "T_DO", "T_UNTIL", "T_ELSE", "T_FINISH", END
        ]

        # program -> func_list T_START stmt_list T_FINISH
        add("program", ["T_FUNC", "T_START"], ["func_list", "T_START", "stmt_list", "T_FINISH"])

        # function list
        add("func_list", ["T_FUNC"], ["func_decl", "func_list"])
        add("func_list", ["T_START"], [EPS])

        # function declaration
        add("func_decl", ["T_FUNC"], [
            "T_FUNC", "IDENTIFIER", ("T_DELIM", "("), "param_list", ("T_DELIM", ")"),
            ("T_DELIM", ":"), "type_name", "block"
        ])

        # parameters
        add("param_list", ["IDENTIFIER"], ["param", "param_list_tail"])
        add("param_list", [("T_DELIM", ")")], [EPS])
        add("param_list_tail", [("T_DELIM", ",")], [("T_DELIM", ","), "param", "param_list_tail"])
        add("param_list_tail", [("T_DELIM", ")")], [EPS])
        add("param", ["IDENTIFIER"], ["IDENTIFIER", ("T_DELIM", ":"), "type_name"])

        # type_name
        add("type_name", ["T_INT"], ["T_INT"])
        add("type_name", ["T_FLOAT_T"], ["T_FLOAT_T"])
        add("type_name", ["T_STRING_T"], ["T_STRING_T"])
        add("type_name", ["T_BOOL_T"], ["T_BOOL_T"])
        add("type_name", ["T_VOID"], ["T_VOID"])

        # block -> { stmt_list }
        add("block", [("T_DELIM", "{")], [("T_DELIM", "{"), "stmt_list", ("T_DELIM", "}")])

        # stmt_list
        add("stmt_list", stmt_start, ["statement", "stmt_list"])
        add("stmt_list", [("T_DELIM", "}"), "T_FINISH", "T_ELSE", "T_UNTIL", END], [EPS])

        # statements
        add("statement", ["T_VAR"], ["T_VAR", "IDENTIFIER", ("T_DELIM", ":"), "type_name", "var_init", ("T_DELIM", ";")])
        add("statement", ["IDENTIFIER"], ["IDENTIFIER", "stmt_tail"])
        add("statement", ["T_IF"], ["T_IF", ("T_DELIM", "("), "expr", ("T_DELIM", ")"), "T_THEN", "block", "if_tail"])
        add("statement", ["T_WHILE"], ["T_WHILE", ("T_DELIM", "("), "expr", ("T_DELIM", ")"), "T_DO", "block"])
        add("statement", ["T_REPEAT"], ["T_REPEAT", "block", "T_UNTIL", ("T_DELIM", "("), "expr", ("T_DELIM", ")"), ("T_DELIM", ";")])
        add("statement", ["T_PRINT"], ["T_PRINT", ("T_DELIM", "("), "arg_list", ("T_DELIM", ")"), ("T_DELIM", ";")])
        add("statement", ["T_READ"], ["T_READ", ("T_DELIM", "("), "IDENTIFIER", ("T_DELIM", ")"), ("T_DELIM", ";")])
        add("statement", ["T_RETURN"], ["T_RETURN", "return_tail", ("T_DELIM", ";")])

        # statement continuations
        add("stmt_tail", ["T_OP_ASSIGN"], ["T_OP_ASSIGN", "expr", ("T_DELIM", ";")])
        add("stmt_tail", [("T_DELIM", "(")], [("T_DELIM", "("), "arg_list", ("T_DELIM", ")"), ("T_DELIM", ";")])

        # optional variable initialization
        add("var_init", ["T_OP_ASSIGN"], ["T_OP_ASSIGN", "expr"])
        add("var_init", [("T_DELIM", ";")], [EPS])

        # optional else
        add("if_tail", ["T_ELSE"], ["T_ELSE", "block"])
        add("if_tail", stmt_start + [("T_DELIM", "}"), "T_FINISH", "T_UNTIL", END], [EPS])

        # return_tail
        add("return_tail", expr_start, ["expr"])
        add("return_tail", [("T_DELIM", ";")], [EPS])

        # arg_list
        add("arg_list", expr_start, ["expr", "arg_list_tail"])
        add("arg_list", [("T_DELIM", ")")], [EPS])
        add("arg_list_tail", [("T_DELIM", ",")], [("T_DELIM", ","), "expr", "arg_list_tail"])
        add("arg_list_tail", [("T_DELIM", ")")], [EPS])

        # expressions
        add("expr", expr_start, ["or_expr"])
        add("or_expr", expr_start, ["and_expr", "or_tail"])
        add("or_tail", ["T_OR"], ["T_OR", "and_expr", "or_tail"])
        add("or_tail", expr_follow, [EPS])

        add("and_expr", expr_start, ["rel_expr", "and_tail"])
        add("and_tail", ["T_AND"], ["T_AND", "rel_expr", "and_tail"])
        add("and_tail", ["T_OR"] + expr_follow, [EPS])

        add("rel_expr", expr_start, ["add_expr", "rel_tail"])
        add("rel_tail", ["T_OP_REL"], ["T_OP_REL", "add_expr", "rel_tail"])
        add("rel_tail", ["T_AND", "T_OR"] + expr_follow, [EPS])

        add("add_expr", expr_start, ["mul_expr", "add_tail"])
        add("add_tail", [("T_OP_ARITH", "+")], [("T_OP_ARITH", "+"), "mul_expr", "add_tail"])
        add("add_tail", [("T_OP_ARITH", "-")], [("T_OP_ARITH", "-"), "mul_expr", "add_tail"])
        add("add_tail", ["T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        add("mul_expr", expr_start, ["pow_expr", "mul_tail"])
        add("mul_tail", [("T_OP_ARITH", "*")], [("T_OP_ARITH", "*"), "pow_expr", "mul_tail"])
        add("mul_tail", [("T_OP_ARITH", "/")], [("T_OP_ARITH", "/"), "pow_expr", "mul_tail"])
        add("mul_tail", [("T_OP_ARITH", "%")], [("T_OP_ARITH", "%"), "pow_expr", "mul_tail"])
        add("mul_tail", [("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"), "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        add("pow_expr", expr_start, ["unary_expr", "pow_tail"])
        add("pow_tail", [("T_OP_ARITH", "^")], [("T_OP_ARITH", "^"), "pow_expr"])
        add("pow_tail", [("T_OP_ARITH", "*"), ("T_OP_ARITH", "/"), ("T_OP_ARITH", "%"),
                         ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
                         "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        add("unary_expr", [("T_OP_ARITH", "+")], [("T_OP_ARITH", "+"), "unary_expr"])
        add("unary_expr", [("T_OP_ARITH", "-")], [("T_OP_ARITH", "-"), "unary_expr"])
        add("unary_expr", ["T_NOT"], ["T_NOT", "unary_expr"])
        add("unary_expr", ["INTEGER", "FLOAT", "STRING", "BOOL_LIT", "IDENTIFIER", "T_ZAKAT", "T_TAX", "T_LOAN", ("T_DELIM", "(")], ["primary"])

        add("primary", ["INTEGER"], ["INTEGER"])
        add("primary", ["FLOAT"], ["FLOAT"])
        add("primary", ["STRING"], ["STRING"])
        add("primary", ["BOOL_LIT"], ["BOOL_LIT"])
        add("primary", ["IDENTIFIER"], ["IDENTIFIER", "primary_tail"])
        add("primary", [("T_DELIM", "(")], [("T_DELIM", "("), "expr", ("T_DELIM", ")")])
        add("primary", ["T_ZAKAT"], ["T_ZAKAT", ("T_DELIM", "("), "expr", ("T_DELIM", ")")])
        add("primary", ["T_TAX"], ["T_TAX", ("T_DELIM", "("), "expr", ("T_DELIM", ","), "expr", ("T_DELIM", ")")])
        add("primary", ["T_LOAN"], ["T_LOAN", ("T_DELIM", "("), "expr", ("T_DELIM", ","), "expr", ("T_DELIM", ","), "expr", ("T_DELIM", ")")])

        add("primary_tail", [("T_DELIM", "(")], [("T_DELIM", "("), "arg_list", ("T_DELIM", ")")])
        add("primary_tail", [("T_OP_ARITH", "^"), ("T_OP_ARITH", "*"), ("T_OP_ARITH", "/"), ("T_OP_ARITH", "%"),
                             ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
                             "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        return T


def parse_source(source: str, show_steps: bool = False) -> str:
    tokens = tokenize(source)
    parser = LL1TableParser(tokens)
    message = parser.parse()
    if show_steps:
        return message + "\n\n=== LL(1) Steps ===\n" + "\n".join(parser.steps)
    return message


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ll1_table_parser.py <file.tf>")
        sys.exit(0)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        source = f.read()

    try:
        print(parse_source(source, show_steps=False))
    except ParseError as e:
        print("Parse Error:", e)