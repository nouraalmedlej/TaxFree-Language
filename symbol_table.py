"""
TaxFree Compiler - Phase 3 (Semantic Analysis)
Part 1: Symbol Table and Scope Management

This module extends the simple symbol table from Phase 1 (which only stored
an identifier name and its first-occurrence line) into a full semantic
symbol table that supports:

  - identifier name
  - type        (int / float / string / bool / function)
  - scope level (global, or the name of the function the symbol lives in)
  - declaration line
  - for functions: parameter count, parameter types, and return type

It also supports nested scopes (global vs. each function body) and detects
the two scope errors required in this phase:
  - using a variable before it is declared
  - declaring the same name twice in the same scope

Token type names match the Phase 1 scanner (T_INT, T_FLOAT_T, ...).

Author: Symbol Table & Scope (team member 1)
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. The data we store for each identifier
# ---------------------------------------------------------------------------

@dataclass
class Symbol:
    """One row in the symbol table."""
    name: str                       # identifier name, e.g. "wealth"
    kind: str                       # "variable" or "function"
    type: str                       # "int" | "float" | "string" | "bool"
                                    #   for a function this is its RETURN type,
                                    #   or "void"
    scope: str                      # "global" or the function name
    decl_line: int                  # line where it was declared

    # The next three are only meaningful when kind == "function"
    param_count: int = 0
    param_types: list = field(default_factory=list)   # e.g. ["float", "float"]
    return_type: Optional[str] = None                 # e.g. "float" or "void"

    def __str__(self):
        if self.kind == "function":
            params = ", ".join(self.param_types) if self.param_types else "(none)"
            return (f"{self.name:<14} | function | returns {self.return_type:<7} "
                    f"| scope: {self.scope:<10} | line {self.decl_line} "
                    f"| {self.param_count} param(s): {params}")
        else:
            return (f"{self.name:<14} | variable | type: {self.type:<7} "
                    f"| scope: {self.scope:<10} | line {self.decl_line}")


# ---------------------------------------------------------------------------
# 2. A single scope (one dictionary of names)
# ---------------------------------------------------------------------------

class Scope:
    """
    A scope is just a named dictionary of symbols.
    TaxFree has exactly two scope levels, so we never nest deeper than:
        global  ->  one function body
    but the design below would still work if more levels were added later.
    """
    def __init__(self, name: str, parent: "Scope" = None):
        self.name = name                # "global" or a function name
        self.parent = parent            # the enclosing scope (None for global)
        self.symbols: dict[str, Symbol] = {}

    def declare(self, symbol: Symbol) -> Optional[str]:
        """
        Add a new symbol to THIS scope.
        Returns None on success, or an error message string if the name is
        already declared in this same scope (duplicate declaration).
        """
        if symbol.name in self.symbols:
            existing = self.symbols[symbol.name]
            return (f"Semantic Error at line {symbol.decl_line}: "
                    f"'{symbol.name}' is already declared in scope "
                    f"'{self.name}' (first declared at line {existing.decl_line}).")
        self.symbols[symbol.name] = symbol
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look for a name in THIS scope only (no parent search)."""
        return self.symbols.get(name)


# ---------------------------------------------------------------------------
# 3. The symbol table - manages all scopes together
# ---------------------------------------------------------------------------

class SymbolTable:
    """
    Manages the global scope plus the function scope that is currently open.
    The semantic analyzer (team member 3's integration code) calls these
    methods as it walks the parse tree.
    """

    def __init__(self):
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        # We keep every scope we ever created so the final report can print
        # the complete table, even after a function scope is closed.
        self.all_scopes: list[Scope] = [self.global_scope]
        self.errors: list[str] = []

    # --- opening and closing scopes ---------------------------------------

    def enter_function_scope(self, function_name: str):
        """Called when the parser starts reading a function body."""
        new_scope = Scope(function_name, parent=self.global_scope)
        self.all_scopes.append(new_scope)
        self.current_scope = new_scope

    def exit_function_scope(self):
        """Called when the function body ends - go back to global."""
        self.current_scope = self.global_scope

    # --- declaring things --------------------------------------------------

    def declare_variable(self, name: str, var_type: str, line: int):
        """
        Declare a variable in the current scope.
        var_type is the plain type name: 'int', 'float', 'string', 'bool'.
        Records an error if the name is a duplicate in this scope.
        """
        symbol = Symbol(
            name=name,
            kind="variable",
            type=var_type,
            scope=self.current_scope.name,
            decl_line=line,
        )
        error = self.current_scope.declare(symbol)
        if error:
            self.errors.append(error)
        return symbol

    def declare_function(self, name: str, return_type: str,
                         param_types: list, line: int):
        """
        Declare a function. Functions always live in the GLOBAL scope in
        TaxFree (there are no nested functions), so we always declare them
        there even if called while another scope is somehow open.
        """
        symbol = Symbol(
            name=name,
            kind="function",
            type=return_type,           # for a function, type == return type
            scope="global",
            decl_line=line,
            param_count=len(param_types),
            param_types=list(param_types),
            return_type=return_type,
        )
        error = self.global_scope.declare(symbol)
        if error:
            self.errors.append(error)
        return symbol

    def declare_parameter(self, name: str, param_type: str, line: int):
        """
        A function parameter behaves like a local variable inside the
        function body, so it is declared in the current (function) scope.
        """
        return self.declare_variable(name, param_type, line)

    # --- using things ------------------------------------------------------

    def use_variable(self, name: str, line: int) -> Optional[Symbol]:
        """
        Called when an identifier is USED (in an expression, assignment,
        read, etc). Implements the scope lookup rule:
          1. look in the current scope
          2. if not found and we are inside a function, look in global
          3. if still not found -> 'used before declaration' error
        Returns the Symbol if found, or None (and records an error) if not.
        """
        # step 1: current scope
        found = self.current_scope.lookup_local(name)
        if found:
            return found

        # step 2: fall back to global (only matters inside a function)
        if self.current_scope is not self.global_scope:
            found = self.global_scope.lookup_local(name)
            if found:
                return found

        # step 3: not declared anywhere visible
        self.errors.append(
            f"Semantic Error at line {line}: "
            f"'{name}' is used but was not declared in scope "
            f"'{self.current_scope.name}'."
        )
        return None

    def use_function(self, name: str, line: int) -> Optional[Symbol]:
        """
        Called when a function is CALLED. Functions are always global, so
        we look there directly. (Argument-count / type checking is team
        member 2's job - this only checks the name exists and is a function.)
        """
        found = self.global_scope.lookup_local(name)
        if found is None:
            self.errors.append(
                f"Semantic Error at line {line}: "
                f"function '{name}' is called but was never declared."
            )
            return None
        if found.kind != "function":
            self.errors.append(
                f"Semantic Error at line {line}: "
                f"'{name}' is not a function but is being called like one."
            )
            return None
        return found

    # --- reporting ---------------------------------------------------------

    def print_table(self):
        """Print the full symbol table, one scope at a time."""
        print("=" * 78)
        print("SYMBOL TABLE")
        print("=" * 78)
        for scope in self.all_scopes:
            label = ("GLOBAL SCOPE" if scope.name == "global"
                     else f"FUNCTION SCOPE: {scope.name}")
            print(f"\n[{label}]")
            if not scope.symbols:
                print("   (empty)")
            else:
                for sym in scope.symbols.values():
                    print("   " + str(sym))
        print()

    def print_errors(self):
        """Print all scope-related semantic errors found so far."""
        print("=" * 78)
        print("SCOPE / DECLARATION ERRORS")
        print("=" * 78)
        if not self.errors:
            print("No scope or declaration errors found.")
        else:
            for e in self.errors:
                print("   " + e)
        print()
