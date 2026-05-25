from parser import run_test
 
# ────────────────────────────────────────────────
#  Test 1 — Zakat with if/else  (CORRECT)
# ────────────────────────────────────────────────
TEST1 = """\
// Test 1
start
  var wealth : float ;
  var nisab : float = 20000.00 ;
  var due : float = 0.00 ;
  read(wealth) ;
  if (wealth >= nisab) then {
    due = wealth * 0.025 ;
    print("Zakat due: ", due) ;
  } else {
    print("Below nisab.") ;
  }
finish
"""
 
# ────────────────────────────────────────────────
#  Test 2 — Function + while loop  (CORRECT)
# ────────────────────────────────────────────────
TEST2 = """\
// Test 2
func calcTax(amount : float, rate : float) : float {
  var result : float = 0.0 ;
  result = amount * rate ;
  return result ;
}
 
start
  var total : float = 0.0 ;
  var i : int = 0 ;
  while (i < 5) do {
    total = total + calcTax(1000.00, 0.15) ;
    i = i + 1 ;
  }
  print("Total: ", total) ;
finish
"""
 
# ────────────────────────────────────────────────
#  Test 3 — Repeat-until with boolean  (CORRECT)
# ────────────────────────────────────────────────
TEST3 = """\
// Test 3
start
  var n : int = 1 ;
  var done : bool = false ;
  repeat {
    n = n * 2 ;
    if (n > 1000) then {
      done = true ;
    }
  } until (done) ;
  print("final n = ", n) ;
finish
"""
 
# ────────────────────────────────────────────────
#  Test 4 — Missing semicolon  (SYNTAX ERROR)
# ────────────────────────────────────────────────
TEST4 = """\
// Test 4
start
  var x : int = 5 ;
  var y : int = 10
  print(x + y) ;
finish
"""
 
# ────────────────────────────────────────────────
#  Test 5 — Missing closing parenthesis  (SYNTAX ERROR)
# ────────────────────────────────────────────────
TEST5 = """\
// Test 5
start
  var a : int = 1 ;
  if (a > 0 then {
    print("positive") ;
  }
finish
"""
 
def run_all():
    results = []
    results.append(run_test(TEST1, "Test 1 — Zakat with if/else  [expected: PASS]"))
    results.append(run_test(TEST2, "Test 2 — Function and while loop  [expected: PASS]"))
    results.append(run_test(TEST3, "Test 3 — Repeat-until with boolean  [expected: PASS]"))
    results.append(run_test(TEST4, "Test 4 — Missing semicolon  [expected: SYNTAX ERROR]"))
    results.append(run_test(TEST5, "Test 5 — Missing closing parenthesis  [expected: SYNTAX ERROR]"))
 
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    labels = [
        "Test 1 — if/else",
        "Test 2 — function + while",
        "Test 3 — repeat-until",
        "Test 4 — missing ';' (error)",
        "Test 5 — missing ')' (error)",
    ]
    for (ok, _), label in zip(results, labels):
        status = "✔ PASS" if ok else "✘ FAIL/ERROR"
        print(f"  {status}   {label}")
    print()
 
if __name__ == "__main__":
    run_all()
