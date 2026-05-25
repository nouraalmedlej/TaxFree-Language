class TACInterpreter:

    def __init__(self, instructions):
        if isinstance(instructions, str):
            self.instructions = [ln.strip() for ln in instructions.split("\n") if ln.strip()]
        else:
            self.instructions = list(instructions)

        self.env = {}
        self.output_lines = []
        self.labels = {}
        self.params_queue = []
        self.pc = 0
        self.runtime_errors = []
        self.max_steps = 100000
        self._scan_labels()

    def _scan_labels(self):
        for i, line in enumerate(self.instructions):
            parts = line.split()
            if len(parts) == 2 and parts[0] == "label":
                self.labels[parts[1]] = i

    def run(self, input_values=None):
        self._input_buffer = list(input_values) if input_values else []
        self._input_pos = 0
        self.pc = 0
        steps = 0

        while self.pc < len(self.instructions):
            steps += 1
            if steps > self.max_steps:
                self.runtime_errors.append("Runtime error: too many steps (possible infinite loop).")
                break

            line = self.instructions[self.pc].strip()
            if not line:
                self.pc += 1
                continue

            try:
                jumped = self._exec_line(line)
            except Exception as e:
                self.runtime_errors.append(f"Runtime error at instruction {self.pc}: {e}")
                break

            if not jumped:
                self.pc += 1

        return self.get_output()

    def _exec_line(self, line):
        if line.startswith("label "):
            return False

        if line.startswith("goto "):
            target = line.split()[1]
            return self._jump_to(target)

        if line.startswith("ifFalse "):
            parts = line.split()
            cond_val = self._lookup(parts[1])
            target = parts[3]
            if not self._truthy(cond_val):
                return self._jump_to(target)
            return False

        if line.startswith("print "):
            val = self._lookup(line[6:].strip())
            self.output_lines.append(self._fmt(val))
            return False

        if line.startswith("read "):
            var = line[5:].strip()
            if self._input_pos < len(self._input_buffer):
                self.env[var] = self._input_buffer[self._input_pos]
                self._input_pos += 1
            else:
                self.env[var] = 0
            return False

        if line.startswith("param "):
            val = self._lookup(line[6:].strip())
            self.params_queue.append(val)
            return False

        if line.startswith("return"):
            self.pc = len(self.instructions)
            return True

        if "=" in line:
            return self._exec_assignment(line)

        return False

    def _exec_assignment(self, line):
        lhs, rhs = line.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()

        if rhs.startswith("call "):
            func_name = rhs.split()[1]
            args = list(self.params_queue)
            self.params_queue = []
            self.env[lhs] = self._builtin_or_default(func_name, args)
            return False

        tokens = rhs.split()

        if len(tokens) == 3:
            left = self._lookup(tokens[0])
            op = tokens[1]
            right = self._lookup(tokens[2])
            self.env[lhs] = self._apply_binary(left, op, right)
            return False

        if len(tokens) == 2:
            op, operand = tokens
            val = self._lookup(operand)
            self.env[lhs] = self._apply_unary(op, val)
            return False

        if len(tokens) == 1:
            tok = tokens[0]
            if tok.startswith("not") and len(tok) > 3 and not self._is_known_literal(tok):
                inner = self._lookup(tok[3:])
                self.env[lhs] = self._apply_unary("not", inner)
            elif tok.startswith("-") and len(tok) > 1 and not self._looks_like_number(tok):
                inner = self._lookup(tok[1:])
                self.env[lhs] = self._apply_unary("-", inner)
            elif tok.startswith("+") and len(tok) > 1 and not self._looks_like_number(tok):
                self.env[lhs] = self._lookup(tok[1:])
            else:
                self.env[lhs] = self._lookup(tok)
            return False

        return False

    def _builtin_or_default(self, name, args):
        if name == "zakat" and len(args) >= 1:
            return float(args[0]) * 0.025
        if name == "tax" and len(args) >= 2:
            return float(args[0]) * float(args[1])
        if name == "loan" and len(args) >= 3:
            principal, rate, months = float(args[0]), float(args[1]), float(args[2])
            if months == 0:
                return 0
            return (principal * (1 + rate)) / months
        return 0

    def _apply_binary(self, left, op, right):
        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == "-": return left - right
        if op == "*": return left * right
        if op == "/":
            if right == 0:
                self.runtime_errors.append("Runtime error: division by zero.")
                return 0
            if isinstance(left, int) and isinstance(right, int):
                return left // right if right != 0 else 0
            return left / right
        if op == "%":
            if right == 0:
                self.runtime_errors.append("Runtime error: modulo by zero.")
                return 0
            return left % right
        if op == "^": return left ** right
        if op == "<":  return left < right
        if op == ">":  return left > right
        if op == "<=": return left <= right
        if op == ">=": return left >= right
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == "and": return bool(left) and bool(right)
        if op == "or":  return bool(left) or bool(right)
        return 0

    def _apply_unary(self, op, val):
        if op == "-":   return -val
        if op == "+":   return +val
        if op == "not": return not bool(val)
        return val

    def _lookup(self, token):
        if token in self.env:
            return self.env[token]
        if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
            return token[1:-1]
        if token == "true":  return True
        if token == "false": return False
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return 0

    def _looks_like_number(self, tok):
        body = tok[1:] if tok and tok[0] in "+-" else tok
        try:
            float(body)
            return True
        except ValueError:
            return False

    def _is_known_literal(self, tok):
        if tok in ("true", "false"):
            return True
        if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
            return True
        return False

    def _truthy(self, v):
        if isinstance(v, bool):  return v
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str):   return len(v) > 0
        return bool(v)

    def _fmt(self, v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, float):
            if v == int(v):
                return f"{v:.1f}"
            return str(v)
        return str(v)

    def _jump_to(self, label):
        if label in self.labels:
            self.pc = self.labels[label]
            return True
        self.runtime_errors.append(f"Runtime error: unknown label '{label}'.")
        self.pc = len(self.instructions)
        return True

    def get_output(self):
        out = "\n".join(self.output_lines)
        if self.runtime_errors:
            out += "\n" + "\n".join(self.runtime_errors)
        return out

    def get_final_env(self):
        return dict(self.env)
