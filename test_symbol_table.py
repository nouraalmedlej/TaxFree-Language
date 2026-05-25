"""
Test driver for the TaxFree Symbol Table.

This file does NOT contain a full semantic analyzer (that is team member 3's
integration work). Instead it SIMULATES the calls that the analyzer would
make while walking the parse tree, so we can prove the symbol table behaves
correctly on its own.

Each test corresponds to a small TaxFree program. The comment above each
test shows the source code, then we make the declare/use calls in the same
order a tree walk would.
"""

from symbol_table import SymbolTable


def banner(text):
    print("\n" + "#" * 78)
    print("#  " + text)
    print("#" * 78)


# ===========================================================================
# TEST 1 - a correct program: global vars + one function with locals
# ===========================================================================
# TaxFree source being simulated:
#
#   func calcTax(amount : float, rate : float) : float {
#       var result : float = 0.0 ;
#       result = amount * rate ;
#       return result ;
#   }
#   start
#       var total : float = 0.0 ;
#       var i : int = 0 ;
#       total = total + calcTax(1000.00, 0.15) ;
#       print("Total: ", total) ;
#   finish
#
banner("TEST 1 - correct program (function + global scope)")

st = SymbolTable()

# --- function calcTax is declared in global scope (line 1) ---
st.declare_function("calcTax", return_type="float",
                    param_types=["float", "float"], line=1)

# --- walk into the function body: open its scope ---
st.enter_function_scope("calcTax")
# parameters become locals of calcTax
st.declare_parameter("amount", "float", line=1)
st.declare_parameter("rate", "float", line=1)
# local variable
st.declare_variable("result", "float", line=2)
# uses inside the function body
st.use_variable("result", line=3)
st.use_variable("amount", line=3)
st.use_variable("rate", line=3)
st.use_variable("result", line=4)   # in 'return result ;'
# leave the function
st.exit_function_scope()

# --- main program (global scope) ---
st.declare_variable("total", "float", line=6)
st.declare_variable("i", "int", line=7)
st.use_variable("total", line=8)
st.use_function("calcTax", line=8)
st.use_variable("total", line=9)

st.print_table()
st.print_errors()


# ===========================================================================
# TEST 2 - variable used before declaration
# ===========================================================================
# TaxFree source being simulated:
#
#   start
#       due = wealth * 0.025 ;     <-- 'due' and 'wealth' not declared yet
#       var wealth : float ;
#       var due : float ;
#   finish
#
banner("TEST 2 - variable used before declaration")

st = SymbolTable()
# the assignment on line 2 uses 'due' and 'wealth' before they exist
st.use_variable("due", line=2)
st.use_variable("wealth", line=2)
# now they get declared on lines 3 and 4
st.declare_variable("wealth", "float", line=3)
st.declare_variable("due", "float", line=4)

st.print_table()
st.print_errors()


# ===========================================================================
# TEST 3 - duplicate declaration in the same scope
# ===========================================================================
# TaxFree source being simulated:
#
#   start
#       var rate : float = 0.025 ;
#       var rate : float = 0.15 ;   <-- duplicate in the SAME (global) scope
#   finish
#
banner("TEST 3 - duplicate declaration in the same scope")

st = SymbolTable()
st.declare_variable("rate", "float", line=2)
st.declare_variable("rate", "float", line=3)   # should be flagged

st.print_table()
st.print_errors()


# ===========================================================================
# TEST 4 - same name in different scopes is ALLOWED (shadowing)
# ===========================================================================
# TaxFree source being simulated:
#
#   func apply(x : float) : float {
#       var rate : float = 0.15 ;   <-- local 'rate', different scope
#       return x * rate ;
#   }
#   start
#       var rate : float = 0.025 ; <-- global 'rate', this is fine
#       print(rate) ;
#   finish
#
# The Phase 1 spec said a local variable is allowed to shadow a global one,
# so this program must produce NO errors.
banner("TEST 4 - shadowing: same name in global and local scope is allowed")

st = SymbolTable()
st.declare_function("apply", return_type="float",
                    param_types=["float"], line=1)
st.enter_function_scope("apply")
st.declare_parameter("x", "float", line=1)
st.declare_variable("rate", "float", line=2)   # local rate
st.use_variable("x", line=3)
st.use_variable("rate", line=3)                # finds the LOCAL rate
st.exit_function_scope()

st.declare_variable("rate", "float", line=5)   # global rate - different scope, OK
st.use_variable("rate", line=6)                # finds the GLOBAL rate

st.print_table()
st.print_errors()


# ===========================================================================
# TEST 5 - a variable that is local to one function is NOT visible elsewhere
# ===========================================================================
# TaxFree source being simulated:
#
#   func helper(n : int) : int {
#       var temp : int = n ;
#       return temp ;
#   }
#   start
#       var answer : int = 0 ;
#       answer = temp ;            <-- ERROR: 'temp' is local to helper
#   finish
#
banner("TEST 5 - using a function-local variable from global scope (error)")

st = SymbolTable()
st.declare_function("helper", return_type="int",
                    param_types=["int"], line=1)
st.enter_function_scope("helper")
st.declare_parameter("n", "int", line=1)
st.declare_variable("temp", "int", line=2)
st.use_variable("n", line=2)
st.use_variable("temp", line=3)
st.exit_function_scope()

st.declare_variable("answer", "int", line=5)
st.use_variable("answer", line=6)
st.use_variable("temp", line=6)   # 'temp' is not visible here -> error

st.print_table()
st.print_errors()


print("\n" + "=" * 78)
print("All five symbol-table tests finished.")
print("=" * 78)
