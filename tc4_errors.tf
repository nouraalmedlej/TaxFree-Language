// Test Case 4: Lexical Errors
// Expected:
// - Detect invalid identifier (length > 8)
// - Detect invalid symbol '@'
// - Detect unterminated string
// - Continue scanning without stopping

start
    var incomeTotal : float = 5000.11111111111111111111 ;
    var rate @ float = 0.15 ;
    print("Tax is ) ;
finish