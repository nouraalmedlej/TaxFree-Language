# type_checker_updated.py
# Phase 3 part 2 - checks types in TaxFree programs
# uses the symbol table from part 1

from symbol_table import SymbolTable


class TypeChecker:

    def __init__(self, symbol_table):
        self.st = symbol_table
        self.errors = []

    # check if a type is int or float
    def _is_numeric(self, t):
        return t in ("int", "float")

    # int can go into float but not the other way
    def _ok_types(self, target, val):
        if target == val:
            return True
        if target == "float" and val == "int":
            return True
        return False

    def _add_err(self, msg):
        self.errors.append(msg)

    # R1: assignment - types must match
    def check_assignment(self, var_name, expr_type, line):
        sym = self.st.use_variable(var_name, line)
        if sym is None or expr_type is None:
            return False
        if not self._ok_types(sym.type, expr_type):
            self._add_err(
                f"Type Error at line {line}: "
                f"cannot assign '{expr_type}' to '{var_name}' which is '{sym.type}'."
            )
            return False
        return True

    # R2: arithmetic - both sides must be numbers
    def check_arithmetic(self, left, op, right, line):
        if not self._is_numeric(left) or not self._is_numeric(right):
            self._add_err(
                f"Type Error at line {line}: "
                f"'{op}' needs numeric operands, got '{left}' and '{right}'."
            )
            return None
        if left == "float" or right == "float":
            return "float"
        return "int"

    # R3 and R4: relational operators
    def check_relational(self, left, op, right, line):
        if op in ("<", ">", "<=", ">="):
            if not self._is_numeric(left) or not self._is_numeric(right):
                self._add_err(
                    f"Type Error at line {line}: "
                    f"'{op}' needs numeric operands, got '{left}' and '{right}'."
                )
                return None
            return "bool"
        if op in ("==", "!="):
            if left != right and not (self._is_numeric(left) and self._is_numeric(right)):
                self._add_err(
                    f"Type Error at line {line}: "
                    f"cannot compare '{left}' with '{right}'."
                )
                return None
            return "bool"
        self._add_err(f"Type Error at line {line}: unknown operator '{op}'.")
        return None

    # R5: logical operators - both sides must be bool
    def check_logical(self, left, op, right, line):
        if left != "bool" or right != "bool":
            self._add_err(
                f"Type Error at line {line}: "
                f"'{op}' needs bool operands, got '{left}' and '{right}'."
            )
            return None
        return "bool"

    # R6 and R7: unary operators
    def check_unary(self, op, val_type, line):
        if op in ("+", "-"):
            if not self._is_numeric(val_type):
                self._add_err(
                    f"Type Error at line {line}: "
                    f"unary '{op}' needs a number, got '{val_type}'."
                )
                return None
            return val_type
        if op == "not":
            if val_type != "bool":
                self._add_err(
                    f"Type Error at line {line}: "
                    f"'not' needs bool, got '{val_type}'."
                )
                return None
            return "bool"
        self._add_err(f"Type Error at line {line}: unknown unary operator '{op}'.")
        return None

    # R8: function calls - count and types must match declaration
    def check_function_call(self, name, arg_types, line):
        sym = self.st.use_function(name, line)
        if sym is None:
            return None
        if len(arg_types) != sym.param_count:
            self._add_err(
                f"Type Error at line {line}: "
                f"'{name}' expects {sym.param_count} argument(s), got {len(arg_types)}."
            )
            return sym.return_type
        for i, (actual, expected) in enumerate(zip(arg_types, sym.param_types), 1):
            if not self._ok_types(expected, actual):
                self._add_err(
                    f"Type Error at line {line}: "
                    f"argument {i} of '{name}' should be '{expected}', got '{actual}'."
                )
        return sym.return_type

    # R9: return type must match what the function declared
    def check_return(self, func_name, returned_type, line):
        sym = self.st.use_function(func_name, line)
        if sym is None:
            return False
        expected = sym.return_type
        if expected == "void":
            if returned_type is not None:
                self._add_err(
                    f"Type Error at line {line}: "
                    f"'{func_name}' is void, should not return a value."
                )
                return False
            return True
        if returned_type is None:
            self._add_err(
                f"Type Error at line {line}: "
                f"'{func_name}' must return '{expected}' but nothing was returned."
            )
            return False
        if not self._ok_types(expected, returned_type):
            self._add_err(
                f"Type Error at line {line}: "
                f"'{func_name}' should return '{expected}', got '{returned_type}'."
            )
            return False
        return True

    # R10: TaxFree built-ins zakat / tax / loan
    def check_builtin_call(self, name, arg_types, line):
        needed = {"zakat": 1, "tax": 2, "loan": 3}
        if name not in needed:
            self._add_err(f"Type Error at line {line}: '{name}' is not a TaxFree built-in.")
            return None
        if len(arg_types) != needed[name]:
            self._add_err(
                f"Type Error at line {line}: "
                f"'{name}' expects {needed[name]} argument(s), got {len(arg_types)}."
            )
            return "float"
        for i, t in enumerate(arg_types, 1):
            if not self._is_numeric(t):
                self._add_err(
                    f"Type Error at line {line}: "
                    f"argument {i} of '{name}' must be numeric, got '{t}'."
                )
        return "float"

    # print can take any normal TaxFree type
    def check_print_args(self, arg_types, line):
        ok = True
        for t in arg_types:
            if t not in ("int", "float", "string", "bool"):
                self._add_err(
                    f"Type Error at line {line}: print cannot output type '{t}'."
                )
                ok = False
        return ok

    def all_errors(self):
        return self.st.errors + self.errors

    def print_errors(self):
        print("=" * 60)
        print("TYPE ERRORS")
        print("=" * 60)
        if not self.errors:
            print("  no type errors found")
        else:
            for e in self.errors:
                print("  " + e)
        print()
