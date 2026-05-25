from parser import tokenize, Parser, Node
from symbol_table import SymbolTable
from type_checker_updated import TypeChecker
from semantic_checks import SemanticChecker


class SemanticAnalyzer:

    def __init__(self):
        self.st = SymbolTable()
        self.tc = TypeChecker(self.st)
        self.sc = SemanticChecker(self.st, self.tc)
        self.current_function = None

    # ===============================
    # ENTRY
    # ===============================
    def analyze(self, tree: Node):
        self._visit_program(tree)
        self.sc.check_all_functions_return()

    # ===============================
    # PROGRAM
    # ===============================
    def _visit_program(self, node: Node):
        has_start = any(c.token and c.token.type == "T_START" for c in node.children)
        self.sc.check_start_exists(has_start)

        for c in node.children:
            if c.label == "func_list":
                self._visit_func_list(c)
            elif c.label == "stmt_list":
                self._visit_stmt_list(c)

    # ===============================
    # FUNCTIONS
    # ===============================
    def _visit_func_list(self, node: Node):
        if not node.children or node.children[0].label == "Îµ":
            return

        func_tok = None
        for c in node.children:
            if c.token and c.token.type == "IDENTIFIER":
                func_tok = c.token
                break

        if not func_tok:
            return

        self.current_function = func_tok.value
        ret_type = self._get_type(node)
        param_types = self._get_param_types(node)

        self.st.declare_function(func_tok.value, ret_type, param_types, func_tok.line)
        self.st.enter_function_scope(func_tok.value)

        # parameters are local variables inside the function body
        for name, p_type, line in self._get_params(node):
            self.st.declare_parameter(name, p_type, line)

        block_node = next((c for c in node.children if c.label == "block"), None)
        if block_node:
            self._visit_block(block_node)

        self.st.exit_function_scope()
        self.current_function = None

        next_func_list = node.children[-1]
        if next_func_list.label == "func_list":
            self._visit_func_list(next_func_list)

    # ===============================
    # BLOCK
    # ===============================
    def _visit_block(self, node: Node):
        for c in node.children:
            if c.label == "stmt_list":
                self._visit_stmt_list(c)

    # ===============================
    # STATEMENTS
    # ===============================
    def _visit_stmt_list(self, node: Node):
        for c in node.children:
            if c.label == "statement":
                self._visit_stmt(c)
            elif c.label == "stmt_list":
                self._visit_stmt_list(c)

    def _visit_stmt(self, node: Node):
        if not node.children:
            return

        first = node.children[0]
        if not first.token:
            return

        t = first.token.type

        if t == "T_VAR":
            self._handle_var(node)

        elif t == "IDENTIFIER":
            self._handle_assignment_or_call(node)

        elif t == "T_RETURN":
            self._handle_return(node)

        elif t == "T_PRINT":
            args = self._collect_args(node)
            self.tc.check_print_args(args, first.token.line)

        elif t == "T_READ":
            # read(x) requires x to be declared
            for c in node.children:
                if c.token and c.token.type == "IDENTIFIER":
                    self.st.use_variable(c.token.value, c.token.line)
                    break

        elif t == "T_IF":
            expr_node = next((c for c in node.children if c.label == "expr"), None)
            cond_type = self._eval_expr(expr_node)
            if cond_type not in (None, "bool"):
                self.tc.errors.append(
                    f"Type Error at line {first.token.line}: if condition must be bool, got '{cond_type}'."
                )
            for c in node.children:
                if c.label in ("block", "if'"):
                    self._visit_block_or_if_tail(c)

        elif t == "T_WHILE":
            expr_node = next((c for c in node.children if c.label == "expr"), None)
            cond_type = self._eval_expr(expr_node)
            if cond_type not in (None, "bool"):
                self.tc.errors.append(
                    f"Type Error at line {first.token.line}: while condition must be bool, got '{cond_type}'."
                )
            for c in node.children:
                if c.label == "block":
                    self._visit_block(c)

        elif t == "T_REPEAT":
            for c in node.children:
                if c.label == "block":
                    self._visit_block(c)
                elif c.label == "expr":
                    cond_type = self._eval_expr(c)
                    if cond_type not in (None, "bool"):
                        self.tc.errors.append(
                            f"Type Error at line {first.token.line}: repeat-until condition must be bool, got '{cond_type}'."
                        )

    def _visit_block_or_if_tail(self, node: Node):
        if node.label == "block":
            self._visit_block(node)
            return
        for c in node.children:
            if c.label == "block":
                self._visit_block(c)

    # ===============================
    # VARIABLE DECLARATION
    # ===============================
    def _handle_var(self, node: Node):
        id_tok = next(
            c.token for c in node.children
            if c.token and c.token.type == "IDENTIFIER"
        )

        var_type = self._get_type(node)
        self.st.declare_variable(id_tok.value, var_type, id_tok.line)

        init = next((c for c in node.children if c.label == "var_init"), None)
        if init and init.children and init.children[0].label != "Îµ":
            expr_node = next((c for c in init.children if c.label == "expr"), None)
            expr_type = self._eval_expr(expr_node)
            self.tc.check_assignment(id_tok.value, expr_type, id_tok.line)

    # ===============================
    # ASSIGNMENT / CALL
    # ===============================
    def _handle_assignment_or_call(self, node: Node):
        id_tok = node.children[0].token
        stmt_p = node.children[1]

        # function call statement: name(...);
        if stmt_p.children and stmt_p.children[0].token and stmt_p.children[0].token.value == "(":
            args = self._collect_args(stmt_p)
            self.tc.check_function_call(id_tok.value, args, id_tok.line)
            return

        # assignment: name = expr;
        expr_node = next((c for c in stmt_p.children if c.label == "expr"), None)
        expr_type = self._eval_expr(expr_node)
        self.tc.check_assignment(id_tok.value, expr_type, id_tok.line)

    # ===============================
    # RETURN
    # ===============================
    def _handle_return(self, node: Node):
        return_tail = next((c for c in node.children if c.label == "return'"), None)
        expr_node = None
        if return_tail:
            expr_node = next((c for c in return_tail.children if c.label == "expr"), None)

        ret_type = self._eval_expr(expr_node) if expr_node else None
        line = node.children[0].token.line

        self.tc.check_return(self.current_function, ret_type, line)
        self.sc.register_return(self.current_function)

    # ===============================
    # EXPRESSIONS
    # ===============================
    def _eval_expr(self, node: Node):
        if node is None or node.label == "Îµ":
            return None

        # expr -> or_expr
        if node.label == "expr":
            return self._eval_expr(node.children[0]) if node.children else None

        # left-associative expression levels with prime/tail nodes
        if node.label in ("or_expr", "and_expr", "rel_expr", "add_expr", "mul_expr", "pow_expr"):
            if not node.children:
                return None
            left_type = self._eval_expr(node.children[0])
            if len(node.children) > 1:
                return self._eval_tail(node.children[1], left_type)
            return left_type

        # unary_expr -> (+|-|not) unary_expr | primary
        if node.label == "unary_expr":
            if not node.children:
                return None
            first = node.children[0]
            if first.token and first.token.type in ("T_OP_ARITH", "T_NOT"):
                op = first.token.value
                val_type = self._eval_expr(node.children[1])
                return self.tc.check_unary(op, val_type, first.token.line)
            return self._eval_expr(first)

        # primary literals, variables, calls, and parenthesized expressions
        if node.label == "primary":
            if not node.children:
                return None

            first = node.children[0]

            # (expr)
            if first.token and first.token.value == "(":
                expr_node = next((c for c in node.children if c.label == "expr"), None)
                return self._eval_expr(expr_node)

            if first.token:
                tok = first.token

                if tok.type == "INTEGER":
                    return "int"
                if tok.type == "FLOAT":
                    return "float"
                if tok.type == "STRING":
                    return "string"
                if tok.type == "BOOL_LIT":
                    return "bool"

                # built-in calls: zakat(...), tax(...), loan(...)
                if tok.type in ("T_ZAKAT", "T_TAX", "T_LOAN"):
                    args = self._collect_args(node)
                    return self.tc.check_builtin_call(tok.value, args, tok.line)

                # identifier or user-defined function call
                if tok.type == "IDENTIFIER":
                    primary_tail = node.children[1] if len(node.children) > 1 else None
                    if primary_tail and primary_tail.children and primary_tail.children[0].token and primary_tail.children[0].token.value == "(":
                        args = self._collect_args(primary_tail)
                        return self.tc.check_function_call(tok.value, args, tok.line)

                    sym = self.st.use_variable(tok.value, tok.line)
                    return sym.type if sym else None

            return None

        # generic wrapper: one real child
        if len(node.children) == 1:
            return self._eval_expr(node.children[0])

        return None

    def _eval_tail(self, tail: Node, left_type):
        if tail is None or not tail.children or tail.children[0].label == "Îµ":
            return left_type

        op_node = tail.children[0]
        if not op_node.token:
            return left_type

        op = op_node.token.value
        line = op_node.token.line
        right_node = tail.children[1] if len(tail.children) > 1 else None
        right_type = self._eval_expr(right_node)

        if op in ("+", "-", "*", "/", "%", "^"):
            result_type = self.tc.check_arithmetic(left_type, op, right_type, line)
        elif op in ("<", ">", "<=", ">=", "==", "!="):
            result_type = self.tc.check_relational(left_type, op, right_type, line)
        elif op in ("and", "or"):
            result_type = self.tc.check_logical(left_type, op, right_type, line)
        else:
            result_type = left_type

        next_tail = tail.children[2] if len(tail.children) > 2 else None
        return self._eval_tail(next_tail, result_type)

    # ===============================
    # HELPERS
    # ===============================
    def _get_type(self, node: Node):
        for c in node.children:
            if c.label == "type_name":
                t_node = c.children[0]
                return {
                    "T_INT": "int",
                    "T_FLOAT_T": "float",
                    "T_STRING_T": "string",
                    "T_BOOL_T": "bool",
                    "T_VOID": "void"
                }.get(t_node.label if not t_node.token else t_node.token.type)

            res = self._get_type(c)
            if res:
                return res

        return None

    def _get_param_types(self, node: Node):
        return [p_type for _, p_type, _ in self._get_params(node)]

    def _get_params(self, node: Node):
        params = []

        def walk(n):
            if n.label == "param":
                name_tok = next((c.token for c in n.children if c.token and c.token.type == "IDENTIFIER"), None)
                p_type = self._get_type(n)
                if name_tok and p_type:
                    params.append((name_tok.value, p_type, name_tok.line))
            for ch in n.children:
                walk(ch)

        walk(node)
        return params

    def _collect_args(self, node):
        args = []

        for c in node.children:
            if c.label == "expr":
                args.append(self._eval_expr(c))
            elif c.label in ("arg_list", "arg_list'"):
                args.extend(self._collect_args(c))
            else:
                # Needed for built-in calls, where expr nodes are direct children of primary.
                if c.children and c.label not in ("primary'",):
                    args.extend(self._collect_args(c))

        return args


# ===============================
# RUNNER
# ===============================
def run_semantic(source: str):
    tokens = tokenize(source)
    parser = Parser(tokens)
    tree = parser.parse()

    sa = SemanticAnalyzer()
    sa.analyze(tree)

    return sa
