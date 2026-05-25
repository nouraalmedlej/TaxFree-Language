from parser import Node

class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0
        # Track user-defined function names and their parameter lists.
        # Maps name -> list of parameter names (in order).
        self.functions = {}
        # The function we are currently generating code inside, if any.
        self._current_func = None

    # -------------------------
    # helpers
    # -------------------------
    def new_temp(self):
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self):
        l = f"L{self.label_counter}"
        self.label_counter += 1
        return l

    def emit(self, code):
        self.instructions.append(code)

    # -------------------------
    # MAIN
    # -------------------------
    def generate(self, node: Node):
        if node is None or node.label == "ε":
            return None

        # PROGRAM: jump over functions to the main body, emit main body,
        # then halt, then emit each function as a labeled block.
        if node.label == "program":
            func_list_node = None
            stmt_list_node = None
            for c in node.children:
                if c.label == "func_list":
                    func_list_node = c
                elif c.label == "stmt_list":
                    stmt_list_node = c

            # First pass: collect function info (names + parameter names) so
            # we know them before we generate any call.
            self._collect_functions(func_list_node)

            if self.functions:
                self.emit("goto __MAIN__")

            # Emit each function body, each prefixed by its own label.
            self._emit_functions(func_list_node)

            # Main body.
            if self.functions:
                self.emit("label __MAIN__")
            if stmt_list_node is not None:
                self.generate(stmt_list_node)
            self.emit("halt")
            return

        if node.label in ("T_START", "T_FINISH"):
            return

        # BLOCKS (but not func_list — that is handled in 'program')
        if node.label in ("block", "stmt_list"):
            for c in node.children:
                self.generate(c)
            return

        # -------------------------
        # STATEMENTS
        # -------------------------
        if node.label == "statement":
            first = node.children[0]

            # VAR DECL
            if first.token and first.token.type == "T_VAR":
                var_name = node.children[1].token.value
                init = next((c for c in node.children if c.label == "var_init"), None)

                if init and len(init.children) > 1:
                    val = self.generate(init.children[1])
                    self.emit(f"{var_name} = {val}")
                return

            # IDENTIFIER
            if first.token and first.token.type == "IDENTIFIER":
                name = first.token.value
                stmt_p = node.children[1]

                # assignment
                if stmt_p.children and stmt_p.children[0].token and stmt_p.children[0].token.type == "T_OP_ASSIGN":
                    val = self.generate(stmt_p.children[1])
                    self.emit(f"{name} = {val}")
                    return

                # function call
                if stmt_p.children and stmt_p.children[0].label == "(":
                    args = self._collect_args(stmt_p)
                    for a in args:
                        self.emit(f"param {a}")

                    t = self.new_temp()
                    self.emit(f"{t} = call {name}")
                    return

            # PRINT
            if first.token and first.token.type == "T_PRINT":
                args = self._collect_args(node)
                for a in args:
                    self.emit(f"print {a}")
                return

            # READ
            if first.token and first.token.type == "T_READ":
                var = node.children[2].token.value
                self.emit(f"read {var}")
                return

            # RETURN
            if first.token and first.token.type == "T_RETURN":
                ret = node.children[1] if len(node.children) > 1 else None
                if ret and ret.children and ret.children[0].label != "ε":
                    val = self.generate(ret.children[0])
                    self.emit(f"return {val}")
                else:
                    self.emit("return")
                return

            # -------------------------
            # IF
            # -------------------------
            if first.token and first.token.type == "T_IF":
                condition = self.generate(node.children[2])

                else_label = self.new_label()
                end_label = self.new_label()

                self.emit(f"ifFalse {condition} goto {else_label}")

                # then block
                self.generate(node.children[5])

                self.emit(f"goto {end_label}")
                self.emit(f"label {else_label}")

                # else is wrapped inside an if' node at children[6].
                # if' has either [T_ELSE, block] or [ε].
                if len(node.children) > 6:
                    if_p = node.children[6]
                    has_else = (if_p.children and
                                if_p.children[0].token is not None and
                                if_p.children[0].token.type == "T_ELSE")
                    if has_else:
                        # children[1] of if' is the else block
                        self.generate(if_p.children[1])

                self.emit(f"label {end_label}")
                return

            # -------------------------
            # WHILE
            # -------------------------
            if first.token and first.token.type == "T_WHILE":
                start_label = self.new_label()
                end_label = self.new_label()

                self.emit(f"label {start_label}")

                condition = self.generate(node.children[2])
                self.emit(f"ifFalse {condition} goto {end_label}")

                self.generate(node.children[5])

                self.emit(f"goto {start_label}")
                self.emit(f"label {end_label}")
                return

        # -------------------------
        # EXPRESSIONS
        # -------------------------
        if node.label in ("expr", "or_expr", "and_expr", "rel_expr", "add_expr", "mul_expr", "pow_expr"):
            left = self.generate(node.children[0])

            if len(node.children) > 1:
                return self._binary(left, node.children[1])

            return left

        # unary
        if node.label == "unary_expr":
            if len(node.children) == 2:
                op = node.children[0].token.value
                val = self.generate(node.children[1])

                t = self.new_temp()
                self.emit(f"{t} = {op}{val}")
                return t

            return self.generate(node.children[0])

        # primary
        if node.label == "primary":
            first = node.children[0]

            if first.token:
                tok = first.token

                # parenthesized expression: ( expr )
                if tok.type == "T_DELIM" and tok.value == "(":
                    # children[1] is the expr
                    return self.generate(node.children[1])

                # built-in calls: zakat(...), tax(...), loan(...)
                if tok.type in ("T_ZAKAT", "T_TAX", "T_LOAN"):
                    # collect the expr arguments under this primary node
                    args = []
                    for c in node.children[1:]:
                        if c.label == "expr":
                            args.append(self.generate(c))
                    for a in args:
                        self.emit(f"param {a}")
                    t = self.new_temp()
                    self.emit(f"{t} = call {tok.value}")
                    return t

                # user-defined function call: IDENTIFIER ( arg_list )
                if tok.type == "IDENTIFIER":
                    if len(node.children) > 1:
                        primary_tail = node.children[1]
                        is_call = (primary_tail.children and
                                   primary_tail.children[0].token is not None and
                                   primary_tail.children[0].token.type == "T_DELIM" and
                                   primary_tail.children[0].token.value == "(")
                        if is_call:
                            # arg_list is primary_tail.children[1]
                            args = self._collect_args(primary_tail)
                            for a in args:
                                self.emit(f"param {a}")
                            t = self.new_temp()
                            self.emit(f"{t} = call {tok.value}")
                            return t
                    # plain variable reference
                    return tok.value

                # literal token (INTEGER, FLOAT, STRING, BOOL_LIT)
                return tok.value

            return self.generate(first)

        return None

    # -------------------------
    # binary
    # -------------------------
    def _binary(self, left, tail):
        if not tail.children or tail.children[0].label == "ε":
            return left

        op = tail.children[0].token.value
        right = self.generate(tail.children[1])

        t = self.new_temp()
        self.emit(f"{t} = {left} {op} {right}")

        if len(tail.children) > 2:
            return self._binary(t, tail.children[2])

        return t

    # -------------------------
    # args
    # -------------------------
    def _collect_args(self, node):
        args = []

        def walk(n):
            for c in n.children:
                if c.label == "expr":
                    args.append(self.generate(c))
                elif c.label in ("arg_list", "arg_list'"):
                    walk(c)

        walk(node)
        return args

    # -------------------------
    # function collection and emission
    # -------------------------
    def _collect_functions(self, func_list_node):
        """Walk func_list nodes and record each function's name + parameter names."""
        if func_list_node is None:
            return
        node = func_list_node
        while node and node.children and node.children[0].label != "ε":
            # node is a func_list whose children start with: T_FUNC IDENTIFIER ( param_list ) : type block func_list
            name_tok = None
            param_list_node = None
            for c in node.children:
                if c.token and c.token.type == "IDENTIFIER" and name_tok is None:
                    name_tok = c.token
                elif c.label == "param_list":
                    param_list_node = c
            if name_tok is None:
                break
            param_names = self._collect_param_names(param_list_node)
            self.functions[name_tok.value] = param_names
            # Move to the trailing func_list (the recursive part)
            next_fl = None
            for c in reversed(node.children):
                if c.label == "func_list":
                    next_fl = c
                    break
            node = next_fl

    def _collect_param_names(self, param_list_node):
        """Pull parameter names in order from a param_list subtree."""
        names = []
        if param_list_node is None:
            return names

        def walk(n):
            if n.label == "param":
                # first child is the IDENTIFIER
                for c in n.children:
                    if c.token and c.token.type == "IDENTIFIER":
                        names.append(c.token.value)
                        break
                return
            for c in n.children:
                walk(c)

        walk(param_list_node)
        return names

    def _emit_functions(self, func_list_node):
        """Emit each function body as a labeled block."""
        if func_list_node is None:
            return
        node = func_list_node
        while node and node.children and node.children[0].label != "ε":
            name_tok = None
            block_node = None
            for c in node.children:
                if c.token and c.token.type == "IDENTIFIER" and name_tok is None:
                    name_tok = c.token
                elif c.label == "block":
                    block_node = c
            if name_tok is None or block_node is None:
                break

            # Label the function entry. We use a __func__name pattern.
            func_label = f"__func_{name_tok.value}"
            self.emit(f"label {func_label}")

            # Bind parameters: pop them from the param queue in order.
            param_names = self.functions.get(name_tok.value, [])
            for p in param_names:
                self.emit(f"{p} = pop_param")

            self._current_func = name_tok.value
            self.generate(block_node)
            # If the function does not end in an explicit return, fall through
            # to a safety return so control still goes back to the caller.
            self.emit("return")
            self._current_func = None

            next_fl = None
            for c in reversed(node.children):
                if c.label == "func_list":
                    next_fl = c
                    break
            node = next_fl

    # -------------------------
    # output
    # -------------------------
    def get_tac(self):
        return "\n".join(self.instructions)