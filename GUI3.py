import tkinter as tk
from tkinter import scrolledtext
from taxfree_scanner import Scanner, tokenize
from parser import Parser
from parser import ParseError
from semantic_analyzer import SemanticAnalyzer
from tac_generator import TACGenerator
from tac_interpreter import TACInterpreter


def run_scanner():
    code = input_box.get("1.0", tk.END)
    scanner = Scanner(code)
    scanner.scan()

    output_box.delete("1.0", tk.END)

    output_box.insert(tk.END, "=== TOKENS ===\n")
    for t in scanner.tokens:
        output_box.insert(tk.END, f"{t.token_type} | Line {t.line} | {t.value}\n")

    output_box.insert(tk.END, "\n=== SYMBOL TABLE ===\n")
    if len(scanner.symbol_table) == 0:
        output_box.insert(tk.END, "(empty)\n")
    else:
        for name, line in scanner.symbol_table.items():
            output_box.insert(tk.END, f"{name} → line {line}\n")

    output_box.insert(tk.END, "\n=== ERRORS ===\n")
    if scanner.errors:
        for e in scanner.errors:
            output_box.insert(tk.END, f"Line {e.line}: {e.message}\n")
    else:
        output_box.insert(tk.END, "No errors ✅\n")


def run_parser():
    code = input_box.get("1.0", tk.END)
    output_box.delete("1.0", tk.END)

    tokens = tokenize(code)
    parser = Parser(tokens)

    try:
        tree = parser.parse()
        output_box.insert(tk.END, "=== PARSER RESULT ===\n")
        output_box.insert(tk.END, "✔ Parsing successful\n\n")
        output_box.insert(tk.END, "=== PARSE TREE ===\n")
        output_box.insert(tk.END, tree.pretty(last=True) + "\n")
    except ParseError as e:
        output_box.insert(tk.END, "=== PARSER RESULT ===\n")
        output_box.insert(tk.END, f"✘ {e}\n")


def run_semantic():
    code = input_box.get("1.0", tk.END)
    output_box.delete("1.0", tk.END)

    tokens = tokenize(code)
    parser = Parser(tokens)

    try:
        tree = parser.parse()

        sa = SemanticAnalyzer()
        sa.analyze(tree)

        output_box.insert(tk.END, "=== SEMANTIC ANALYSIS ===\n")

        errors = sa.st.errors + sa.tc.errors + sa.sc.errors

        if errors:
            for e in errors:
                output_box.insert(tk.END, f"{e}\n")
        else:
            output_box.insert(tk.END, "No semantic errors ✅\n\n")
            output_box.insert(tk.END, "=== GENERATED THREE-ADDRESS CODE (TAC) ===\n")
            tac_gen = TACGenerator()
            tac_gen.generate(tree)
            output_box.insert(tk.END, tac_gen.get_tac() + "\n")

    except ParseError as e:
        output_box.insert(tk.END, f"Parse Error: {e}\n")


def run_execute():
    code = input_box.get("1.0", tk.END)
    output_box.delete("1.0", tk.END)

    tokens = tokenize(code)
    parser = Parser(tokens)

    try:
        tree = parser.parse()
    except ParseError as e:
        output_box.insert(tk.END, f"✘ Parse Error: {e}\n")
        return

    sa = SemanticAnalyzer()
    sa.analyze(tree)
    errors = sa.st.errors + sa.tc.errors + sa.sc.errors

    if errors:
        output_box.insert(tk.END, "=== SEMANTIC ERRORS ===\n")
        for e in errors:
            output_box.insert(tk.END, f"{e}\n")
        output_box.insert(tk.END, "\n✘ Cannot execute: fix semantic errors first.\n")
        return

    tac_gen = TACGenerator()
    tac_gen.generate(tree)
    tac_text = tac_gen.get_tac()

    output_box.insert(tk.END, "=== GENERATED TAC ===\n")
    output_box.insert(tk.END, tac_text + "\n\n")

    interp = TACInterpreter(tac_gen.instructions)
    out = interp.run()

    output_box.insert(tk.END, "=== EXECUTION OUTPUT ===\n")
    if out.strip():
        output_box.insert(tk.END, out + "\n")
    else:
        output_box.insert(tk.END, "(no output)\n")

    if interp.runtime_errors:
        output_box.insert(tk.END, "\n=== RUNTIME ERRORS ===\n")
        for e in interp.runtime_errors:
            output_box.insert(tk.END, f"{e}\n")
    else:
        output_box.insert(tk.END, "\n✔ Program executed successfully.\n")


window = tk.Tk()
window.title("TaxFree Compiler")

tk.Label(window, text="Enter Code:").pack()
input_box = scrolledtext.ScrolledText(window, width=80, height=15)
input_box.pack()

btn_frame = tk.Frame(window)
btn_frame.pack()
tk.Button(btn_frame, text="Run Scanner",   command=run_scanner,   width=15, bg="#2196F3").pack(side=tk.LEFT, padx=5, pady=5)
tk.Button(btn_frame, text="Run Parser",    command=run_parser,    width=15, bg="#4CAF50").pack(side=tk.LEFT, padx=5, pady=5)
tk.Button(btn_frame, text="Run Semantic",  command=run_semantic,  width=15, bg="#FF9800").pack(side=tk.LEFT, padx=5, pady=5)
tk.Button(btn_frame, text="Run & Execute", command=run_execute,   width=15, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5, pady=5)

tk.Label(window, text="Output:").pack()
output_box = scrolledtext.ScrolledText(window, width=125, height=30)
output_box.pack()

window.mainloop()
