# semantic_checks.py
# Phase 3 - additional semantic checks for TaxFree

from symbol_table import SymbolTable
from type_checker_updated import TypeChecker


class SemanticChecker:

    def __init__(self, symbol_table, type_checker):
        self.st = symbol_table
        self.tc = type_checker
        self.errors = []
        self._func_has_return = {}

    def _err(self, msg):
        self.errors.append(msg)

    # program must have a start block
    def check_start_exists(self, found):
        if not found:
            self._err("Semantic Error: program has no 'start' block.")

    # called when we see a return inside a function
    def register_return(self, func_name):
        self._func_has_return[func_name] = True

    # every non-void function must have a return
    def check_all_functions_return(self):
        for scope in self.st.all_scopes:
            sym = self.st.global_scope.lookup_local(scope.name)
            if sym and sym.kind == "function" and sym.return_type != "void":
                if not self._func_has_return.get(scope.name, False):
                    self._err(
                        f"Semantic Error: '{scope.name}' must return "
                        f"'{sym.return_type}' but has no return statement."
                    )

    # division by zero with a literal 0
    def check_division(self, right_value, line):
        try:
            if float(right_value) == 0.0:
                self._err(f"Semantic Error at line {line}: division by zero.")
        except (ValueError, TypeError):
            pass

    def all_errors(self):
        return self.errors

    def print_errors(self):
        print("=" * 60)
        print("ADDITIONAL SEMANTIC ERRORS")
        print("=" * 60)
        if not self.errors:
            print("  no additional semantic errors found")
        else:
            for e in self.errors:
                print("  " + e)
        print()
