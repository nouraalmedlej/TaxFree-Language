# TaxFree — A Small Language for Financial Calculations

A statically-typed programming language designed for accountants, tax auditors,
zakat officers, and bank employees who write the same financial formulas every
day in spreadsheets. TaxFree gives them a clean syntax with `zakat`, `tax`, and
`loan` as built-in functions, so a rule can be written once and read again
without effort.

This repository contains the full front-end and a small back-end built as a
team project for the Compilers course.

---

## Team

| Name | Student ID | 
|------|------------|
| Noura Fahad Almedlej | 
| Reemas Mohammed Almoajel | 
| Rama Abdullah Alarbeed | 

Course: **Compilers** — Dr. Amal Alsaif

---

## What's implemented

The project covers all three phases of a compiler front-end plus a bonus
back-end:

- **Phase 1 — Lexical analysis.** A hand-written scanner with 35 token
  types (one per reserved word), error recovery, and a symbol table that
  records the first occurrence of every identifier.
- **Phase 2 — Syntax analysis.** A context-free grammar of 73 productions,
  fully transformed to LL(1) (left recursion eliminated, left factoring
  applied). Two parser implementations are provided: a recursive-descent
  parser (`parser.py`) and a table-driven LL(1) parser (`ll1_table_parser.py`).
  Both produce a parse tree.
- **Phase 3 — Semantic analysis.** An extended symbol table that supports
  global and per-function scopes, ten type-inference rules, and checks for
  `start` block existence, missing returns, division by literal zero, and
  duplicate declarations.
- **Bonus — Code generation.** A three-address-code generator and a TAC
  interpreter that actually runs the program from inside the GUI.

A Tkinter GUI (`GUI3.py`) wraps the whole pipeline with four buttons:
**Run Scanner**, **Run Parser**, **Run Semantic**, and **Run & Execute**.

---

## Repository layout

```
TaxFree-Compiler/
├── docs/                   Phase reports and the language specification
├── src/                    All compiler source code
│   ├── taxfree_scanner.py    Phase 1
│   ├── parser.py             Phase 2 (recursive descent)
│   ├── ll1_table_parser.py   Phase 2 (table-driven LL(1))
│   ├── nodes.py              Parse-tree node definitions
│   ├── symbol_table.py       Phase 3 part 1
│   ├── type_checker_updated.py  Phase 3 part 2
│   ├── semantic_checks.py    Phase 3 part 3
│   ├── semantic_analyzer.py  Phase 3 integration
│   ├── tac_generator.py      Bonus: TAC generation
│   ├── tac_interpreter.py    Bonus: TAC execution
│   └── GUI3.py               Tkinter front-end
├── tests/                  Test drivers and sample TaxFree programs
└── screenshots/            Output screenshots used in the report
```

---

## How to run

Requires Python 3.10 or newer (no external libraries needed).

```bash
# From the project root
python src/GUI3.py
```

Type or paste a TaxFree program in the upper text box and press one of the
four buttons.

### Running individual phases from the command line

```bash
# Scanner only, on a file:
python src/taxfree_scanner.py tests/examples/zakat.tf

# Full parser tests (3 correct + 2 with deliberate errors):
python tests/test_cases.py

# Symbol table tests (5 cases):
python tests/test_symbol_table.py
```

---

## Sample program

```
// zakat.tf
start
  var wealth : float ;
  var nisab  : float = 20000.00 ;
  var due    : float = 0.00 ;
  read(wealth) ;
  if (wealth >= nisab) then {
    due = wealth * 0.025 ;
    print("Zakat due: ", due) ;
  } else {
    print("Below nisab.") ;
  }
finish
```

---

## License

Course project — for academic use only.
