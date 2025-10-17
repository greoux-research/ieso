// Gréoux Research - www.greoux.re

#include "Cogen.h"

Cogen C;

int main(int argc, char *argv[]) {

	if (argc != 5) {
		cerr << "Usage: " << argv[0] << " TUR_T TUR_P CDR_P STX_T" << endl;
		return 1; // Indicates error
	}

	// Convert command-line arguments to double and assign to members

	C.TUR_T = strtod(argv[1], nullptr);
	C.TUR_P = strtod(argv[2], nullptr);
	C.CDR_P = strtod(argv[3], nullptr);
	C.STX_T = strtod(argv[4], nullptr);

	if (C.Calculate()) {
		C.Snap();
	} else {
		cerr << "-1 -1" << endl;
	}

	return 0;

}
