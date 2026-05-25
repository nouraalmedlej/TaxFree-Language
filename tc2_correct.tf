// Test Case 2: Progressive Income Tax
// mix of cases in keywords and identifiers

func calcTax(amount : float) : float {
    var rate : float = 0.15 ;
    return amount * rate ;
}

func showInfo() : void {
    print("Using tax, zakat, and loan rules") ;
}

start
var income : float = 1000.0 ;
var note : string = "Tax calculation" ;
tax
zakat
loan
print("Tax: ", calcTax(income)) ;
finish