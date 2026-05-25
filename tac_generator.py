from parser import Node

class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

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

        # PROGRAM
        if node.label == "program":
            for c in node.children:
                self.generate(c)
            return

        if node.label in ("T_START", "T_FINISH"):
            return

        # BLOCKS
        if node.label in ("block", "stmt_list", "func_list"):
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

                # else (optional)
                if len(node.children) > 6:
                    self.generate(node.children[6])

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
                return first.token.value
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
    # output
    # -------------------------
    def get_tac(self):
        return "\n".join(self.instructions)