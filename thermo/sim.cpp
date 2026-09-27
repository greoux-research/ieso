// Gréoux Research - www.greoux.re

#include "Cogen.h"

#include <cmath>
#include <cstdlib>
#include <iomanip>

Cogen C;

// Exit status: 0 success (coefficients on stdout), 1 usage, 2 malformed
// argument, 3 inputs outside the supported domain or calculation failure (a
// reason on stderr, nothing on stdout).

static bool parse(const char *text, double &value) {

	char *end = nullptr;
	value = strtod(text, &end);
	return end != text && *end == '\0';
}

int main(int argc, char *argv[]) {

	bool limits = argc == 5 && string(argv[1]) == "--limits";

	if (argc != 5) {
		cerr << "usage: " << argv[0] << " TUR_T TUR_P CDR_P STX_T" << endl;
		cerr << "       " << argv[0] << " --limits TUR_T TUR_P CDR_P" << endl;
		return 1;
	}

	double v[4] = {0.0, 0.0, 0.0, 0.0};
	int first = limits ? 2 : 1;

	for (int i = first; i < argc; ++i) {
		if (!parse(argv[i], v[i - first])) {
			cerr << "error: argument '" << argv[i] << "' is not a number" << endl;
			return 2;
		}
	}

	C.TUR_T = v[0];
	C.TUR_P = v[1];
	C.CDR_P = v[2];
	C.STX_T = limits ? 0.0 : v[3];

	if (limits) {
		// The supported extraction range for this turbine: the open interval
		// between the saturation temperatures at condenser and inlet pressure.
		if (!C.Limits()) {
			cerr << "error: " << C.Reason << endl;
			return 3;
		}
		cout << setprecision(17) << C.STX_T_LLIM_C << " " << C.STX_T_ULIM_C << endl;
		return 0;
	}

	if (C.Calculate()) {
		C.Snap();
		return 0;
	}

	cerr << "error: " << C.Reason << endl;
	return 3;
}
