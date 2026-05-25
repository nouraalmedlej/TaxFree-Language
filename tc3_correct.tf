/* Test Case 3: Full Program
   variables, loops, conditions and Boolean
   All keywords in mixed case to test case insensitivity
*/

start

var count : int = -3 ;
var eligible : bool = true ;
var blocked : bool = false ;

while (count > 0) do {
    print("Counting: ", count) ;
    count = count - 1 ;
}

repeat {
    print("Repeat test") ;
} until (count == 0) ;

if (eligible and not blocked) then {
    print("Allowed") ;
} else {
    print("Denied") ;
}

if (eligible or blocked) then {
    print("Boolean test") ;
}

finish