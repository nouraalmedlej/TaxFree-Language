"""
parser.py — Stack-based LL(1) predictive parser for the TaxFree language.

This parser uses an explicit stack with push/pop (the classical LL(1)
predictive parser algorithm from class). It builds the same parse tree
the recursive-descent version produced, so all downstream code
(semantic_analyzer, tac_generator) keeps working without any change.

How it works (in plain words):
  - We start with the stack containing the end marker '$' and the start
    symbol 'program' on top.
  - At each step we pop the top of the stack:
      * if it is a terminal, we try to match it against the current input
        token. On match we advance the input.
      * if it is a non-terminal, we look up M[non-terminal, lookahead] in
        the LL(1) parsing table; the table gives a production A -> X1 ... Xn,
        and we push X1..Xn on the stack in reverse order so that X1 ends up
        on top.
  - Parse-tree nodes are kept on a parallel "tree stack". When a
    non-terminal is expanded, we attach the new child nodes to the parent
    node that produced them.

The grammar is the LL(1) grammar from Phase 2 (after left-recursion
elimination and left factoring). Terminals are taken from the Phase 1
scanner. For T_DELIM and T_OP_ARITH the value matters (e.g. '(' vs '{'),
so for those tokens we look the table up by (type, value).
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Union
from nodes import Token, Node, ParseError
from taxfree_scanner import tokenize


# Internal markers
EPS = "ε"
END = "T_EOF"

# A grammar symbol on the stack is either:
#   - a string (the non-terminal name, like "stmt_list")
#   - a string (a plain terminal type, like "IDENTIFIER" or "T_IF")
#   - a tuple ("T_DELIM", "(")  or  ("T_OP_ARITH", "+")
#       to mean "the terminal of that type AND that exact value"
Symbol = Union[str, Tuple[str, str]]


class Parser:
    """Stack-based LL(1) predictive parser. Produces a parse tree."""

    # The set of non-terminal names. Anything not in here is a terminal.
    NON_TERMINALS = {
        "program", "func_list", "param_list", "param_list_p", "param",
        "type_name", "block",
        "stmt_list", "statement", "stmt_p", "var_init", "if_p", "return_p",
        "arg_list", "arg_list_p",
        "expr",
        "or_expr", "or_expr_p",
        "and_expr", "and_expr_p",
        "rel_expr", "rel_expr_p",
        "add_expr", "add_expr_p",
        "mul_expr", "mul_expr_p",
        "pow_expr", "pow_expr_p",
        "unary_expr",
        "primary", "primary_p",
    }

    # Display label for each non-terminal in the parse tree. For prime
    # non-terminals (like add_expr_p) we keep the apostrophe form so the
    # tree matches what the rest of the project expects.
    LABEL = {
        "param_list_p": "param_list'",
        "stmt_p":       "stmt'",
        "if_p":         "if'",
        "return_p":     "return'",
        "arg_list_p":   "arg_list'",
        "or_expr_p":    "or_expr'",
        "and_expr_p":   "and_expr'",
        "rel_expr_p":   "rel_expr'",
        "add_expr_p":   "add_expr'",
        "mul_expr_p":   "mul_expr'",
        "pow_expr_p":   "pow_expr'",
        "primary_p":    "primary'",
    }

    def __init__(self, tokens: List[Token]):
        # Drop any whitespace/comment tokens just in case (the scanner does
        # not emit them, but we are defensive).
        self.tokens = [t for t in tokens if t.type not in ("T_COMMENT", "T_WHITESPACE")]

        # Append an explicit EOF token so the parser has a real lookahead at
        # the end of input.
        last_line = self.tokens[-1].line if self.tokens else 1
        self.tokens.append(Token(END, "$", last_line))

        self.pos = 0
        self.errors: List[str] = []
        self.table = self._build_table()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def parse(self) -> Node:
        """Run the LL(1) algorithm and return the root of the parse tree."""
        # The root parse-tree node for the start symbol.
        root = Node("program")

        # Symbol stack and a parallel "node stack". Every non-terminal on
        # the symbol stack has a matching node on the node stack — that is
        # the node we will attach its children to when it gets expanded.
        # Terminals push None on the node stack because they only need to
        # add a leaf to whatever parent is currently active when matched.
        #
        # We push a special end marker (END, None), then the start symbol.
        symbol_stack: List[Symbol] = [END, "program"]
        node_stack:   List = [None, root]

        # Each entry of the parent stack is the parse-tree node we should
        # attach matched terminals to. We track parents using sentinel
        # markers: when we expand a non-terminal A, we push the markers for
        # each RHS symbol so they know whose parent they are.
        # See _expand() below for details.

        while symbol_stack:
            top_symbol = symbol_stack.pop()
            top_node = node_stack.pop()
            lookahead = self._lookahead_key()

            # End of input.
            if top_symbol == END:
                if self._current().type == END:
                    return root
                tok = self._current()
                raise ParseError(
                    f"Syntax error at line {tok.line}: "
                    f"unexpected token '{tok.value}' after program end."
                )

            # Terminal on top: match against input.
            if top_symbol not in self.NON_TERMINALS:
                self._match(top_symbol, top_node)
                continue

            # Non-terminal on top: look up M[A, a].
            production = self.table.get((top_symbol, lookahead))
            if production is None and isinstance(lookahead, tuple):
                # Fallback: try the bare type only (helps T_OP_REL which is
                # grouped, not split by value).
                production = self.table.get((top_symbol, lookahead[0]))

            if production is None:
                tok = self._current()
                found = tok.value if tok.value else tok.type
                raise ParseError(
                    f"Syntax error at line {tok.line}: "
                    f"unexpected '{found}' while parsing {self._display_nt(top_symbol)}."
                )

            self._expand(top_symbol, top_node, production,
                         symbol_stack, node_stack)

        # Stack emptied without seeing $ — shouldn't normally happen.
        return root

    # ------------------------------------------------------------------
    # Stack operations
    # ------------------------------------------------------------------
    def _match(self, terminal: Symbol, parent_info):
        """Match a terminal against the current input token.

        parent_info is a tuple (parent_node, placeholder_node). The matched
        terminal replaces the placeholder's contents so the leaf appears in
        the correct position among its siblings.
        """
        tok = self._current()
        if not self._token_matches(terminal, tok):
            expected = self._display_terminal(terminal)
            found = f"'{tok.value}'" if tok.value else tok.type
            raise ParseError(
                f"Syntax error at line {tok.line}: expected {expected}, found {found}."
            )
        # Replace the placeholder's label and attach the token.
        if parent_info is not None:
            placeholder = parent_info
            leaf_label = (f"{tok.type}('{tok.value}')"
                          if isinstance(terminal, tuple)
                          else tok.type)
            placeholder.label = leaf_label
            placeholder.token = tok
        self.pos += 1

    def _expand(self, nt: str, nt_node: Node, production: List[Symbol],
                symbol_stack: List[Symbol], node_stack: List):
        """
        Apply A -> X1 X2 ... Xn. Push the RHS on the stack in reverse so
        X1 ends up on top. Each RHS symbol — whether terminal or non-
        terminal — gets a placeholder child node attached to nt_node in
        left-to-right order. Non-terminals will be expanded into that
        placeholder; terminals will be matched and overwrite the
        placeholder's label/token.
        """
        # ε production: add a single "ε" child and don't push anything.
        if not production or production == [EPS]:
            nt_node.add(Node(EPS))
            return

        # Create placeholders in source order and attach them now, so the
        # final children list is in correct grammar order.
        child_nodes = []
        for sym in production:
            if sym in self.NON_TERMINALS:
                child = Node(self._display_nt(sym))
            else:
                # Terminal placeholder: will be filled in when matched.
                child = Node("__pending__")
            nt_node.add(child)
            child_nodes.append(child)

        # Push RHS symbols on the stack in reverse so X1 ends up on top.
        for sym, child in zip(reversed(production), reversed(child_nodes)):
            symbol_stack.append(sym)
            node_stack.append(child)

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _lookahead_key(self) -> Symbol:
        """The terminal key used to index the parsing table."""
        tok = self._current()
        if tok.type in ("T_DELIM", "T_OP_ARITH"):
            return (tok.type, tok.value)
        return tok.type

    def _token_matches(self, terminal: Symbol, tok: Token) -> bool:
        if isinstance(terminal, tuple):
            return tok.type == terminal[0] and tok.value == terminal[1]
        return tok.type == terminal

    def _display_terminal(self, terminal: Symbol) -> str:
        if isinstance(terminal, tuple):
            return f"{terminal[0]}('{terminal[1]}')"
        return terminal

    def _display_nt(self, nt: str) -> str:
        return self.LABEL.get(nt, nt)

    # ------------------------------------------------------------------
    # Build the LL(1) parsing table M[A, a] = production
    # ------------------------------------------------------------------
    def _build_table(self) -> Dict[Tuple[str, Symbol], List[Symbol]]:
        T: Dict[Tuple[str, Symbol], List[Symbol]] = {}

        def add(nt: str, lookaheads: List[Symbol], prod: List[Symbol]):
            for la in lookaheads:
                T[(nt, la)] = prod

        # FIRST-style sets used for several alternatives — defining them
        # once keeps the rest of the table short and readable.
        expr_start: List[Symbol] = [
            "INTEGER", "FLOAT", "STRING", "BOOL_LIT", "IDENTIFIER",
            "T_ZAKAT", "T_TAX", "T_LOAN", "T_NOT",
            ("T_DELIM", "("),
            ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
        ]
        stmt_start: List[Symbol] = [
            "T_VAR", "IDENTIFIER", "T_IF", "T_WHILE",
            "T_REPEAT", "T_PRINT", "T_READ", "T_RETURN",
        ]
        expr_follow: List[Symbol] = [
            ("T_DELIM", ")"), ("T_DELIM", ","), ("T_DELIM", ";"),
            ("T_DELIM", "}"),
            "T_THEN", "T_DO", "T_UNTIL", "T_ELSE", "T_FINISH", END,
        ]

        # program -> func_list T_START stmt_list T_FINISH
        add("program", ["T_FUNC", "T_START"],
            ["func_list", "T_START", "stmt_list", "T_FINISH"])

        # func_list -> T_FUNC IDENTIFIER ( param_list ) : type_name block func_list | ε
        add("func_list", ["T_FUNC"],
            ["T_FUNC", "IDENTIFIER", ("T_DELIM", "("), "param_list",
             ("T_DELIM", ")"), ("T_DELIM", ":"), "type_name", "block",
             "func_list"])
        add("func_list", ["T_START"], [EPS])

        # param_list -> param param_list' | ε
        add("param_list", ["IDENTIFIER"], ["param", "param_list_p"])
        add("param_list", [("T_DELIM", ")")], [EPS])

        # param_list' -> , param param_list' | ε
        add("param_list_p", [("T_DELIM", ",")],
            [("T_DELIM", ","), "param", "param_list_p"])
        add("param_list_p", [("T_DELIM", ")")], [EPS])

        # param -> IDENTIFIER : type_name
        add("param", ["IDENTIFIER"],
            ["IDENTIFIER", ("T_DELIM", ":"), "type_name"])

        # type_name -> T_INT | T_FLOAT_T | T_STRING_T | T_BOOL_T | T_VOID
        add("type_name", ["T_INT"],      ["T_INT"])
        add("type_name", ["T_FLOAT_T"],  ["T_FLOAT_T"])
        add("type_name", ["T_STRING_T"], ["T_STRING_T"])
        add("type_name", ["T_BOOL_T"],   ["T_BOOL_T"])
        add("type_name", ["T_VOID"],     ["T_VOID"])

        # block -> { stmt_list }
        add("block", [("T_DELIM", "{")],
            [("T_DELIM", "{"), "stmt_list", ("T_DELIM", "}")])

        # stmt_list -> statement stmt_list | ε
        add("stmt_list", stmt_start, ["statement", "stmt_list"])
        add("stmt_list",
            [("T_DELIM", "}"), "T_FINISH", "T_ELSE", "T_UNTIL", END],
            [EPS])

        # statement -> ...
        add("statement", ["T_VAR"],
            ["T_VAR", "IDENTIFIER", ("T_DELIM", ":"), "type_name",
             "var_init", ("T_DELIM", ";")])
        add("statement", ["IDENTIFIER"],
            ["IDENTIFIER", "stmt_p"])
        add("statement", ["T_IF"],
            ["T_IF", ("T_DELIM", "("), "expr", ("T_DELIM", ")"),
             "T_THEN", "block", "if_p"])
        add("statement", ["T_WHILE"],
            ["T_WHILE", ("T_DELIM", "("), "expr", ("T_DELIM", ")"),
             "T_DO", "block"])
        add("statement", ["T_REPEAT"],
            ["T_REPEAT", "block", "T_UNTIL",
             ("T_DELIM", "("), "expr", ("T_DELIM", ")"),
             ("T_DELIM", ";")])
        add("statement", ["T_PRINT"],
            ["T_PRINT", ("T_DELIM", "("), "arg_list",
             ("T_DELIM", ")"), ("T_DELIM", ";")])
        add("statement", ["T_READ"],
            ["T_READ", ("T_DELIM", "("), "IDENTIFIER",
             ("T_DELIM", ")"), ("T_DELIM", ";")])
        add("statement", ["T_RETURN"],
            ["T_RETURN", "return_p", ("T_DELIM", ";")])

        # stmt' -> = expr ; | ( arg_list ) ;
        add("stmt_p", ["T_OP_ASSIGN"],
            ["T_OP_ASSIGN", "expr", ("T_DELIM", ";")])
        add("stmt_p", [("T_DELIM", "(")],
            [("T_DELIM", "("), "arg_list", ("T_DELIM", ")"),
             ("T_DELIM", ";")])

        # var_init -> = expr | ε
        add("var_init", ["T_OP_ASSIGN"], ["T_OP_ASSIGN", "expr"])
        add("var_init", [("T_DELIM", ";")], [EPS])

        # if' -> T_ELSE block | ε
        add("if_p", ["T_ELSE"], ["T_ELSE", "block"])
        add("if_p",
            stmt_start + [("T_DELIM", "}"), "T_FINISH", "T_UNTIL", END],
            [EPS])

        # return' -> expr | ε
        add("return_p", expr_start, ["expr"])
        add("return_p", [("T_DELIM", ";")], [EPS])

        # arg_list -> expr arg_list' | ε
        add("arg_list", expr_start, ["expr", "arg_list_p"])
        add("arg_list", [("T_DELIM", ")")], [EPS])

        # arg_list' -> , expr arg_list' | ε
        add("arg_list_p", [("T_DELIM", ",")],
            [("T_DELIM", ","), "expr", "arg_list_p"])
        add("arg_list_p", [("T_DELIM", ")")], [EPS])

        # ------------------------------------------------------------------
        # Expressions
        # ------------------------------------------------------------------
        add("expr", expr_start, ["or_expr"])

        add("or_expr", expr_start, ["and_expr", "or_expr_p"])
        add("or_expr_p", ["T_OR"], ["T_OR", "and_expr", "or_expr_p"])
        add("or_expr_p", expr_follow, [EPS])

        add("and_expr", expr_start, ["rel_expr", "and_expr_p"])
        add("and_expr_p", ["T_AND"], ["T_AND", "rel_expr", "and_expr_p"])
        add("and_expr_p", ["T_OR"] + expr_follow, [EPS])

        add("rel_expr", expr_start, ["add_expr", "rel_expr_p"])
        add("rel_expr_p", ["T_OP_REL"],
            ["T_OP_REL", "add_expr", "rel_expr_p"])
        add("rel_expr_p", ["T_AND", "T_OR"] + expr_follow, [EPS])

        add("add_expr", expr_start, ["mul_expr", "add_expr_p"])
        add("add_expr_p", [("T_OP_ARITH", "+")],
            [("T_OP_ARITH", "+"), "mul_expr", "add_expr_p"])
        add("add_expr_p", [("T_OP_ARITH", "-")],
            [("T_OP_ARITH", "-"), "mul_expr", "add_expr_p"])
        add("add_expr_p",
            ["T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        add("mul_expr", expr_start, ["pow_expr", "mul_expr_p"])
        add("mul_expr_p", [("T_OP_ARITH", "*")],
            [("T_OP_ARITH", "*"), "pow_expr", "mul_expr_p"])
        add("mul_expr_p", [("T_OP_ARITH", "/")],
            [("T_OP_ARITH", "/"), "pow_expr", "mul_expr_p"])
        add("mul_expr_p", [("T_OP_ARITH", "%")],
            [("T_OP_ARITH", "%"), "pow_expr", "mul_expr_p"])
        add("mul_expr_p",
            [("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
             "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        # pow is right-associative: pow' -> ^ pow_expr | ε  (recurses to pow_expr)
        add("pow_expr", expr_start, ["unary_expr", "pow_expr_p"])
        add("pow_expr_p", [("T_OP_ARITH", "^")],
            [("T_OP_ARITH", "^"), "pow_expr"])
        add("pow_expr_p",
            [("T_OP_ARITH", "*"), ("T_OP_ARITH", "/"), ("T_OP_ARITH", "%"),
             ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
             "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        # unary_expr -> + unary | - unary | not unary | primary
        add("unary_expr", [("T_OP_ARITH", "+")],
            [("T_OP_ARITH", "+"), "unary_expr"])
        add("unary_expr", [("T_OP_ARITH", "-")],
            [("T_OP_ARITH", "-"), "unary_expr"])
        add("unary_expr", ["T_NOT"], ["T_NOT", "unary_expr"])
        add("unary_expr",
            ["INTEGER", "FLOAT", "STRING", "BOOL_LIT", "IDENTIFIER",
             "T_ZAKAT", "T_TAX", "T_LOAN", ("T_DELIM", "(")],
            ["primary"])

        # primary
        add("primary", ["INTEGER"],  ["INTEGER"])
        add("primary", ["FLOAT"],    ["FLOAT"])
        add("primary", ["STRING"],   ["STRING"])
        add("primary", ["BOOL_LIT"], ["BOOL_LIT"])
        add("primary", ["IDENTIFIER"], ["IDENTIFIER", "primary_p"])
        add("primary", [("T_DELIM", "(")],
            [("T_DELIM", "("), "expr", ("T_DELIM", ")")])
        add("primary", ["T_ZAKAT"],
            ["T_ZAKAT", ("T_DELIM", "("), "expr", ("T_DELIM", ")")])
        add("primary", ["T_TAX"],
            ["T_TAX", ("T_DELIM", "("), "expr", ("T_DELIM", ","),
             "expr", ("T_DELIM", ")")])
        add("primary", ["T_LOAN"],
            ["T_LOAN", ("T_DELIM", "("), "expr", ("T_DELIM", ","),
             "expr", ("T_DELIM", ","), "expr", ("T_DELIM", ")")])

        # primary' -> ( arg_list ) | ε
        add("primary_p", [("T_DELIM", "(")],
            [("T_DELIM", "("), "arg_list", ("T_DELIM", ")")])
        add("primary_p",
            [("T_OP_ARITH", "^"), ("T_OP_ARITH", "*"), ("T_OP_ARITH", "/"),
             ("T_OP_ARITH", "%"),
             ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
             "T_OP_REL", "T_AND", "T_OR"] + expr_follow, [EPS])

        return T


# ----------------------------------------------------------------------
# Convenience entry point that scanners/test files use
# ----------------------------------------------------------------------
def run_test(source: str, label: str = ""):
    """Tokenize + parse a source string. Returns (ok, parse_tree_or_error)."""
    if label:
        print("=" * 60)
        print(" ", label)
        print("=" * 60)
        for i, line in enumerate(source.splitlines(), 1):
            print(f"  {i:3d}  {line}")
        print()

    try:
        tokens = tokenize(source)
        parser = Parser(tokens)
        tree = parser.parse()
        print("✔  Parsing successful.")
        print()
        print(tree.pretty(last=True))
        print()
        return True, tree
    except ParseError as e:
        print(f"✘  {e}")
        print()
        return False, str(e)
