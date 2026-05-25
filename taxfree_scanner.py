
import re
import sys

# Token Type Constants

T_START  = "T_START"
T_FINISH = "T_FINISH"
T_VAR    =  "T_VAR"
T_IF     = "T_IF"
T_THEN   = "T_THEN"
T_ELSE   = "T_ELSE"
T_WHILE  = "T_WHILE"
T_DO     = "T_DO"
T_REPEAT = "T_REPEAT"
T_UNTIL  = "T_UNTIL"
T_FUNC   = "T_FUNC"
T_RETURN = "T_RETURN"
T_VOID   = "T_VOID"

T_INT     = "T_INT"
T_FLOAT_T = "T_FLOAT_T"
T_STRING_T= "T_STRING_T"
T_BOOL_T  = "T_BOOL_T"


T_READ  = "T_READ"
T_PRINT = "T_PRINT"

T_AND = "T_AND"
T_OR  = "T_OR"
T_NOT = "T_NOT"

T_ZAKAT = "T_ZAKAT"
T_TAX   = "T_TAX"
T_LOAN  = "T_LOAN"

INTEGER  = "INTEGER"
FLOAT    = "FLOAT"
STRING   = "STRING"
BOOL_LIT = "BOOL_LIT"

IDENTIFIER = "IDENTIFIER"

T_OP_ASSIGN = "T_OP_ASSIGN"
T_OP_ARITH  = "T_OP_ARITH"
T_OP_REL    = "T_OP_REL"

T_DELIM = "T_DELIM"
EOF = "EOF"

#   Keywords Table

KEYWORDS = {
    "start"  : T_START,
    "finish" : T_FINISH,
    "var"    : T_VAR,
    "if"     : T_IF,
    "then"   : T_THEN,
    "else"   : T_ELSE,
    "while"  : T_WHILE,
    "do"     : T_DO,
    "repeat" : T_REPEAT,
    "until"  : T_UNTIL,
    "func"   : T_FUNC,
    "return" : T_RETURN,
    "void"   : T_VOID,
    "int":    T_INT,
    "float":  T_FLOAT_T,
    "string": T_STRING_T,
    "bool":   T_BOOL_T,
    "read"   : T_READ,
    "print"  : T_PRINT,
    "and"    : T_AND,
    "or"     : T_OR,
    "not"    : T_NOT,
    "zakat"  : T_ZAKAT,
    "tax"    : T_TAX,
    "loan"   : T_LOAN,
    "true"   : BOOL_LIT,
    "false"  : BOOL_LIT,
}

#  Regular Expressions

RE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,7}$")

RE_INTEGER = re.compile(r"^[-+]?[0-9]{1,8}$")

RE_FLOAT = re.compile(r"^[-+]?[0-9]{1,8}\.[0-9]{1,8}$")

#   Token Class
class Token:
    def __init__(self, token_type, line, value):
        self.token_type = token_type
        self.line = line
        self.value = value

    def __repr__(self):
        return f"<{self.token_type}, {self.line}, {self.value}>"

# Error Class 

class ScannerError:
    def __init__(self, line, message):
        self.line = line
        self.message = message

    def __repr__(self):
        return f"Line {self.line}: {self.message}"

# Scanner Class 

class Scanner:

    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens = []
        self.symbol_table = {}
        self.errors = []

    def _current(self):
        if self.pos < len(self.source):
            return self.source[self.pos]
        return ""

    def _peek(self):
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return ""

    def _advance(self):
        ch = self._current()
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def _add_token(self, token_type, value, line=None):
        if line is None:
            line = self.line
        self.tokens.append(Token(token_type, line, value))

    def _add_error(self, message, line=None):
        if line is None:
            line = self.line
        self.errors.append(ScannerError(line, message))

    def _skip_line_comment(self):
        while self._current() != "" and self._current() != "\n":
            self._advance()

    def _skip_block_comment(self):
        start_line = self.line
        self._advance()
        self._advance()

        while self._current() != "":
            if self._current() == "*" and self._peek() == "/":
                self._advance()
                self._advance()
                return
            self._advance()

        self._add_error("unterminated block comment", start_line)

    def _read_string(self):
        start_line = self.line
        value = ""
        self._advance()

        while self._current() != "":
            ch = self._current()

            if ch == '"':
                self._advance()
                self._add_token(STRING, '"' + value + '"', start_line)
                return

            if ch == "\n":
                self._add_error("unterminated string literal", start_line)
                return

            value += ch
            self._advance()

        self._add_error("unterminated string literal", start_line)

    def _read_identifier_or_keyword(self):
        start_line = self.line
        lexeme = ""

        while self._current().isascii() and self._current().isalnum():
            lexeme += self._advance()

        lower_lexeme = lexeme.lower()

        if lower_lexeme in KEYWORDS:
            self._add_token(KEYWORDS[lower_lexeme], lower_lexeme, start_line)
            return

        if RE_IDENTIFIER.match(lexeme):
            self._add_token(IDENTIFIER, lower_lexeme, start_line)
            if lower_lexeme not in self.symbol_table:
                self.symbol_table[lower_lexeme] = start_line
        else:
            self._add_error(f"invalid identifier '{lexeme}' (exceeds 8 chars)", start_line)
            self._add_token("IDENTIFIER_TOO_LONG", lower_lexeme, start_line)

    def _read_number(self):
        start_line = self.line
        lexeme = ""
        dot_count = 0

        while self._current().isdigit() or self._current() == ".":
            if self._current() == ".":
                 dot_count += 1
            lexeme += self._advance()

        if dot_count == 0:
            if RE_INTEGER.match(lexeme):
                self._add_token(INTEGER, lexeme, start_line)
            else:
                self._add_error(f"number '{lexeme}' exceeds 8 digits", start_line)

        elif dot_count == 1:
            if RE_FLOAT.match(lexeme):
                self._add_token(FLOAT, lexeme, start_line)
            else:
                self._add_error(f"malformed float '{lexeme}'", start_line)

        else:
            self._add_error(f"malformed number '{lexeme}'", start_line)


    def _read_signed_number(self):
      start_line = self.line
      lexeme = self._advance() 
      while self._current().isdigit() or self._current() == ".":
        lexeme += self._advance()
      dot_count = lexeme.count(".")
      if dot_count == 0:
        if RE_INTEGER.match(lexeme):
            self._add_token(INTEGER, lexeme, start_line)
        else:
            self._add_error(f"number '{lexeme}' exceeds 8 digits", start_line)
      elif dot_count == 1:
        if RE_FLOAT.match(lexeme):
            self._add_token(FLOAT, lexeme, start_line)
        else:
            self._add_error(f"malformed float '{lexeme}'", start_line)
      else:
        self._add_error(f"malformed number '{lexeme}'", start_line)    

    def scan(self):
        while self.pos < len(self.source):
            ch = self._current()

            if ch in " \t\r\n":
                self._advance()
                continue

            if ch == "/" and self._peek() == "/":
                self._skip_line_comment()
                continue

            if ch == "/" and self._peek() == "*":
                self._skip_block_comment()
                continue

            if ch == '"':
                self._read_string()
                continue

            if ch.isalpha():
                self._read_identifier_or_keyword()
                continue

            if ch.isdigit():
                self._read_number()
                continue

            two = ch + self._peek()

            if two in ["==", "!=", "<=", ">="]:
                line = self.line
                self._advance()
                self._advance()
                self._add_token(T_OP_REL, two, line)
                continue

            if ch in ["<", ">"]:
                line = self.line
                self._advance()
                self._add_token(T_OP_REL, ch, line)
                continue
            if (ch == "-" or ch == "+" ) and self._peek().isdigit():
             last = self.tokens[-1].token_type if self.tokens else None
             last_val = self.tokens[-1].value if self.tokens else None
             if last is None or last in [T_OP_ASSIGN, T_OP_ARITH, T_OP_REL] or (last == T_DELIM and last_val == "("):
                self._read_signed_number()
                continue

            if ch == "=":
                line = self.line
                self._advance()
                self._add_token(T_OP_ASSIGN, ch, line)
                continue

            if ch in ["+", "-", "*", "/", "%", "^"]:
                line = self.line
                self._advance()
                self._add_token(T_OP_ARITH, ch, line)
                continue

            if ch in [".", ",", "(", ")", "{", "}", ";", ":"]:
                line = self.line
                self._advance()
                self._add_token(T_DELIM, ch, line)
                continue

            self._add_error(f"invalid symbol '{ch}'", self.line)
            self._advance()

        self.tokens.append(Token( EOF, self.line, "-"))

    def print_output(self):
        print(f"Total number of lexemes found: {len(self.tokens) - 1}")

        print("\nToken List:")
        for token in self.tokens:
            print(f"  <{token.token_type}, {token.line}, {token.value}>")

        print("\nSymbol Table:")
        if len(self.symbol_table) == 0:
            print("  No identifiers found.")
        else:
            for name, line in self.symbol_table.items():
                print(f"  {name:<12} first seen at line {line}")

        print("\nErrors:")
        if len(self.errors) == 0:
            print("  No lexical errors found.")
        else:
            for error in self.errors:
                print(f"  Line {error.line}: {error.message}")


# Main 

def main():
    if len(sys.argv) < 2:
        print("Usage: python scanner.py <filename.tf>")
        return

    file_name = sys.argv[1]

    try:
        with open(file_name, "r") as f:
            source_code = f.read()

        scanner = Scanner(source_code)
        scanner.scan()
        scanner.print_output()

    except FileNotFoundError:
        print(f"Error: file '{file_name}' not found.")


if __name__ == "__main__":
    main()


from nodes import Token as ParserToken


def tokenize(source):
    scanner = Scanner(source)
    scanner.scan()

    for err in scanner.errors:
        print(f"  [Lexical error at line {err.line}]: {err.message}")

    result = []
    for t in scanner.tokens:
        if t.token_type == EOF:
            continue
        result.append(ParserToken(type=t.token_type, value=t.value, line=t.line))
    return result