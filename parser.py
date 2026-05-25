from __future__ import annotations
from typing import List
from nodes import Token, Node, ParseError
from taxfree_scanner import tokenize

class Parser:
    # Terminals that count as expression starters
    EXPR_FIRST = {
        "INTEGER", "FLOAT", "STRING", "BOOL_LIT", "IDENTIFIER",
        "T_ZAKAT", "T_TAX", "T_LOAN", "T_NOT",
        ("T_DELIM", "("),
        ("T_OP_ARITH", "+"), ("T_OP_ARITH", "-"),
    }

    def __init__(self, tokens: List[Token]):
        # Filter out whitespace/comment tokens if any
        self.tokens = [t for t in tokens if t.type not in ("T_COMMENT", "T_WHITESPACE")]
        self.pos   = 0
        self.errors: List[str] = []

    # token access 
    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        # synthetic EOF
        last_line = self.tokens[-1].line if self.tokens else 1
        return Token("T_EOF", "$", last_line)

    def advance(self) -> Token:
        tok = self.peek()
        self.pos += 1
        return tok

    def expect(self, ttype: str, tvalue: str = None) -> Token:
        """Consume a token, raise ParseError if it doesn't match."""
        tok = self.peek()
        if tok.type != ttype or (tvalue is not None and tok.value != tvalue):
            expected = f"'{tvalue}'" if tvalue else ttype
            found    = f"'{tok.value}'" if tok.value else tok.type
            raise ParseError(
                f"Syntax error at line {tok.line}: expected {expected}, found {found}."
            )
        return self.advance()

    def match(self, ttype: str, tvalue: str = None) -> bool:
        """True if the current token matches without consuming."""
        tok = self.peek()
        if tok.type != ttype:
            return False
        if tvalue is not None and tok.value != tvalue:
            return False
        return True

    def at_expr_start(self) -> bool:
        tok = self.peek()
        if (tok.type, tok.value) in self.EXPR_FIRST:
            return True
        if tok.type in self.EXPR_FIRST:
            return True
        return False

    # ── helpers that build leaf nodes ─────────
    def leaf(self, ttype: str, tvalue: str = None) -> Node:
        tok = self.expect(ttype, tvalue)
        return Node(tok.type if not tvalue else f"{tok.type}('{tok.value}')", token=tok)

    # ═══════════════════════════════════════════
    #  ENTRY POINT
    def parse(self) -> Node:
        root = self.parse_program()
        if not self.match("T_EOF"):
            tok = self.peek()
            raise ParseError(
                f"Syntax error at line {tok.line}: unexpected token '{tok.value}' after program end."
            )
        return root
    
    #  PROGRAM =
    # func_list T_START stmt_list T_FINISH
    def parse_program(self) -> Node:
        n = Node("program")
        n.add(self.parse_func_list())
        n.add(self.leaf("T_START"))
        n.add(self.parse_stmt_list())
        n.add(self.leaf("T_FINISH"))
        return n
    
    #  func_list=
    #  T_FUNC IDENTIFIER ( param_list ) : type_name block func_list |  ε
    def parse_func_list(self) -> Node:
        n = Node("func_list")
        if self.match("T_FUNC"):
            n.add(self.leaf("T_FUNC"))
            n.add(self.leaf("IDENTIFIER"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_param_list())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DELIM", ":"))
            n.add(self.parse_type_name())
            n.add(self.parse_block())
            n.add(self.parse_func_list())
        else:
            n.add(Node("ε"))
        return n

    #  param_list  =
    #   param param_list'  |  ε
    def parse_param_list(self) -> Node:
        n = Node("param_list")
        if self.match("IDENTIFIER"):
            n.add(self.parse_param())
            n.add(self.parse_param_list_p())
        else:
            n.add(Node("ε"))
        return n

    def parse_param_list_p(self) -> Node:
        n = Node("param_list'")
        if self.match("T_DELIM", ","):
            n.add(self.leaf("T_DELIM", ","))
            n.add(self.parse_param())
            n.add(self.parse_param_list_p())
        else:
            n.add(Node("ε"))
        return n

    # param  =
    #   IDENTIFIER : type_name
    def parse_param(self) -> Node:
        n = Node("param")
        n.add(self.leaf("IDENTIFIER"))
        n.add(self.leaf("T_DELIM", ":"))
        n.add(self.parse_type_name())
        return n

    # type_name  = 
    #  T_INT | T_FLOAT_T | T_STRING_T | T_BOOL_T | T_VOID
    def parse_type_name(self) -> Node:
        n = Node("type_name")
        tok = self.peek()
        if tok.type in ("T_INT", "T_FLOAT_T", "T_STRING_T", "T_BOOL_T", "T_VOID"):
            n.add(self.leaf(tok.type))
        else:
            raise ParseError(
                f"Syntax error at line {tok.line}: expected a type name "
                f"(int/float/string/bool/void), found '{tok.value}'."
            )
        return n

    # block  =
    #   { stmt_list }
    def parse_block(self) -> Node:
        n = Node("block")
        n.add(self.leaf("T_DELIM", "{"))
        n.add(self.parse_stmt_list())
        n.add(self.leaf("T_DELIM", "}"))
        return n

    #  stmt_list  =
    #   statement stmt_list  |  ε
    STMT_FIRST = {
        "T_VAR", "IDENTIFIER", "T_IF", "T_WHILE",
        "T_REPEAT", "T_PRINT", "T_READ", "T_RETURN",
    }

    def parse_stmt_list(self) -> Node:
        n = Node("stmt_list")
        if self.peek().type in self.STMT_FIRST:
            n.add(self.parse_statement())
            n.add(self.parse_stmt_list())
        else:
            n.add(Node("ε"))
        return n

    #  statement  (8 alternatives)
    def parse_statement(self) -> Node:
        n   = Node("statement")
        tok = self.peek()

        if tok.type == "T_VAR":
            # T_VAR IDENTIFIER : type_name var_init ;
            n.add(self.leaf("T_VAR"))
            n.add(self.leaf("IDENTIFIER"))
            n.add(self.leaf("T_DELIM", ":"))
            n.add(self.parse_type_name())
            n.add(self.parse_var_init())
            n.add(self.leaf("T_DELIM", ";"))

        elif tok.type == "IDENTIFIER":
            # IDENTIFIER stmt'
            n.add(self.leaf("IDENTIFIER"))
            n.add(self.parse_stmt_prime())

        elif tok.type == "T_IF":
            # T_IF ( expr ) T_THEN block if'
            n.add(self.leaf("T_IF"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_THEN"))
            n.add(self.parse_block())
            n.add(self.parse_if_prime())

        elif tok.type == "T_WHILE":
            # T_WHILE ( expr ) T_DO block
            n.add(self.leaf("T_WHILE"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DO"))
            n.add(self.parse_block())

        elif tok.type == "T_REPEAT":
            # T_REPEAT block T_UNTIL ( expr ) ;
            n.add(self.leaf("T_REPEAT"))
            n.add(self.parse_block())
            n.add(self.leaf("T_UNTIL"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DELIM", ";"))

        elif tok.type == "T_PRINT":
            # T_PRINT ( arg_list ) ;
            n.add(self.leaf("T_PRINT"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_arg_list())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DELIM", ";"))

        elif tok.type == "T_READ":
            # T_READ ( IDENTIFIER ) ;
            n.add(self.leaf("T_READ"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.leaf("IDENTIFIER"))
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DELIM", ";"))

        elif tok.type == "T_RETURN":
            # T_RETURN return' ;
            n.add(self.leaf("T_RETURN"))
            n.add(self.parse_return_prime())
            n.add(self.leaf("T_DELIM", ";"))

        else:
            raise ParseError(
                f"Syntax error at line {tok.line}: unexpected token '{tok.value}' "
                f"at start of statement."
            )
        return n

    # stmt'  = 
    #  T_OP_ASSIGN expr ;  |  ( arg_list ) ;
    def parse_stmt_prime(self) -> Node:
        n   = Node("stmt'")
        tok = self.peek()
        if tok.type == "T_OP_ASSIGN":
            n.add(self.leaf("T_OP_ASSIGN"))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ";"))
        elif tok.type == "T_DELIM" and tok.value == "(":
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_arg_list())
            n.add(self.leaf("T_DELIM", ")"))
            n.add(self.leaf("T_DELIM", ";"))
        else:
            raise ParseError(
                f"Syntax error at line {tok.line}: expected '=' or '(' after identifier, "
                f"found '{tok.value}'."
            )
        return n

    # var_init  =
    #   T_OP_ASSIGN expr  |  ε
    def parse_var_init(self) -> Node:
        n = Node("var_init")
        if self.match("T_OP_ASSIGN"):
            n.add(self.leaf("T_OP_ASSIGN"))
            n.add(self.parse_expr())
        else:
            n.add(Node("ε"))
        return n

    # if'  =  T_ELSE block  |  ε
    def parse_if_prime(self) -> Node:
        n = Node("if'")
        if self.match("T_ELSE"):
            n.add(self.leaf("T_ELSE"))
            n.add(self.parse_block())
        else:
            n.add(Node("ε"))
        return n

    # return'  =
    #   expr  |  ε
    def parse_return_prime(self) -> Node:
        n = Node("return'")
        if self.at_expr_start():
            n.add(self.parse_expr())
        else:
            n.add(Node("ε"))
        return n

    # arg_list  =  expr arg_list'  |  ε
    def parse_arg_list(self) -> Node:
        n = Node("arg_list")
        if self.at_expr_start():
            n.add(self.parse_expr())
            n.add(self.parse_arg_list_p())
        else:
            n.add(Node("ε"))
        return n

    def parse_arg_list_p(self) -> Node:
        n = Node("arg_list'")
        if self.match("T_DELIM", ","):
            n.add(self.leaf("T_DELIM", ","))
            n.add(self.parse_expr())
            n.add(self.parse_arg_list_p())
        else:
            n.add(Node("ε"))
        return n

    #  EXPRESSIONS  (precedence chain)
    
    # expr = or_expr
    def parse_expr(self) -> Node:
        n = Node("expr")
        n.add(self.parse_or_expr())
        return n
 
    # or_expr = and_expr or_expr'
    def parse_or_expr(self) -> Node:
        n = Node("or_expr")
        n.add(self.parse_and_expr())
        n.add(self.parse_or_expr_p())
        return n
 
    def parse_or_expr_p(self) -> Node:
        n = Node("or_expr'")
        if self.match("T_OR"):
            n.add(self.leaf("T_OR"))
            n.add(self.parse_and_expr())
            n.add(self.parse_or_expr_p())
        else:
            n.add(Node("ε"))
        return n
 
    # and_expr = rel_expr and_expr'
    def parse_and_expr(self) -> Node:
        n = Node("and_expr")
        n.add(self.parse_rel_expr())
        n.add(self.parse_and_expr_p())
        return n
 
    def parse_and_expr_p(self) -> Node:
        n = Node("and_expr'")
        if self.match("T_AND"):
            n.add(self.leaf("T_AND"))
            n.add(self.parse_rel_expr())
            n.add(self.parse_and_expr_p())
        else:
            n.add(Node("ε"))
        return n
 
    # rel_expr = add_expr rel_expr'
    def parse_rel_expr(self) -> Node:
        n = Node("rel_expr")
        n.add(self.parse_add_expr())
        n.add(self.parse_rel_expr_p())
        return n
 
    def parse_rel_expr_p(self) -> Node:
        n = Node("rel_expr'")
        if self.match("T_OP_REL"):
            n.add(self.leaf("T_OP_REL"))
            n.add(self.parse_add_expr())
            n.add(self.parse_rel_expr_p())
        else:
            n.add(Node("ε"))
        return n
 
    # add_expr = mul_expr add_expr'
    def parse_add_expr(self) -> Node:
        n = Node("add_expr")
        n.add(self.parse_mul_expr())
        n.add(self.parse_add_expr_p())
        return n
 
    def parse_add_expr_p(self) -> Node:
        n = Node("add_expr'")
        tok = self.peek()
        if tok.type == "T_OP_ARITH" and tok.value in ("+", "-"):
            n.add(self.leaf("T_OP_ARITH"))
            n.add(self.parse_mul_expr())
            n.add(self.parse_add_expr_p())
        else:
            n.add(Node("ε"))
        return n
 
    # mul_expr = pow_expr mul_expr'
    def parse_mul_expr(self) -> Node:
        n = Node("mul_expr")
        n.add(self.parse_pow_expr())
        n.add(self.parse_mul_expr_p())
        return n
 
    def parse_mul_expr_p(self) -> Node:
        n = Node("mul_expr'")
        tok = self.peek()
        if tok.type == "T_OP_ARITH" and tok.value in ("*", "/", "%"):
            n.add(self.leaf("T_OP_ARITH"))
            n.add(self.parse_pow_expr())
            n.add(self.parse_mul_expr_p())
        else:
            n.add(Node("ε"))
        return n
 
    # pow_expr = unary_expr pow_expr'
    def parse_pow_expr(self) -> Node:
        n = Node("pow_expr")
        n.add(self.parse_unary_expr())
        n.add(self.parse_pow_expr_p())
        return n
 
    def parse_pow_expr_p(self) -> Node:
        n = Node("pow_expr'")
        tok = self.peek()
        if tok.type == "T_OP_ARITH" and tok.value == "^":
            n.add(self.leaf("T_OP_ARITH"))
            n.add(self.parse_pow_expr())    # right-associative: recurse to pow_expr
        else:
            n.add(Node("ε"))
        return n
 
    # unary_expr  =  + unary | - unary | not unary | primary
    def parse_unary_expr(self) -> Node:
        n   = Node("unary_expr")
        tok = self.peek()
        if tok.type == "T_OP_ARITH" and tok.value in ("+", "-"):
            n.add(self.leaf("T_OP_ARITH"))
            n.add(self.parse_unary_expr())
        elif tok.type == "T_NOT":
            n.add(self.leaf("T_NOT"))
            n.add(self.parse_unary_expr())
        else:
            n.add(self.parse_primary())
        return n
    
    #  primary
    def parse_primary(self) -> Node:
        n   = Node("primary")
        tok = self.peek()

        if tok.type == "INTEGER":
            n.add(self.leaf("INTEGER"))

        elif tok.type == "FLOAT":
            n.add(self.leaf("FLOAT"))

        elif tok.type == "STRING":
            n.add(self.leaf("STRING"))

        elif tok.type == "BOOL_LIT":
            n.add(self.leaf("BOOL_LIT"))

        elif tok.type == "T_ZAKAT":
            n.add(self.leaf("T_ZAKAT"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))

        elif tok.type == "T_TAX":
            n.add(self.leaf("T_TAX"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ","))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))

        elif tok.type == "T_LOAN":
            n.add(self.leaf("T_LOAN"))
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ","))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ","))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))

        elif tok.type == "IDENTIFIER":
            n.add(self.leaf("IDENTIFIER"))
            n.add(self.parse_primary_prime())

        elif tok.type == "T_DELIM" and tok.value == "(":
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_expr())
            n.add(self.leaf("T_DELIM", ")"))

        else:
            raise ParseError(
                f"Syntax error at line {tok.line}: unexpected token '{tok.value}' "
                f"in expression."
            )
        return n

    # primary'  =  ( arg_list )  |  ε
    def parse_primary_prime(self) -> Node:
        n = Node("primary'")
        if self.match("T_DELIM", "("):
            n.add(self.leaf("T_DELIM", "("))
            n.add(self.parse_arg_list())
            n.add(self.leaf("T_DELIM", ")"))
        else:
            n.add(Node("ε"))
        return n
    
    
# 
#  run_test  — helper used by test_cases.py

def run_test(source: str, test_name: str = ""):
    """Parse source, print result + tree. Returns (success, tree_or_None)."""
    print("=" * 60)
    if test_name:
        print(f"  {test_name}")
        print("=" * 60)
    print("SOURCE:")
    for i, line in enumerate(source.strip().splitlines(), 1):
        print(f"  {i:>3}  {line}")
    print()
 
    tokens = tokenize(source)
    parser = Parser(tokens)
    try:
        tree = parser.parse()
        print("✔  Parsing successful.\n")
        print("PARSE TREE:")
        print(tree.pretty(last=True))
        print()
        return True, tree
    except ParseError as e:
        print(f"✘  {e}\n")
        return False, None
 
 
# 
#  MAIN  — run all 5 test cases when executed directly
# 
if __name__ == "__main__":
    import test_cases
    test_cases.run_all()
