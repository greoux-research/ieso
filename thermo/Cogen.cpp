// Gréoux Research - www.greoux.re

#include "Cogen.h"

/* Constructor */

Cogen::Cogen() {

}

/* Calculate */

bool Cogen::Calculate() {

	bool output = true;

	/* --- */

	TUR_T += 273.15; // C to K
	TUR_P *= 1.0e+5; // bar to Pa
	CDR_P *= 1.0e+5; // bar to Pa
	STX_T += 273.15; // C to K

	/* --- */

	Pt.P = CDR_P;
	Pt.X = 1.0;
	if (!Pt.Calculate("P, X"))
		output = false;

	STX_T_LLIM = Pt.T;

	/* --- */

	Pt.P = TUR_P;
	Pt.X = 1.0;
	if (!Pt.Calculate("P, X"))
		output = false;

	STX_T_ULIM = Pt.T;

	/* --- */

	Pt.T = STX_T;
	Pt.X = 1.0;
	if (!Pt.Calculate("T, X"))
		output = false;

	STX_P = Pt.P;

	/* --- */

	Pt.T = TUR_T;
	Pt.P = TUR_P;
	if (!Pt.Calculate("T, P"))
		output = false;

	TUR_H = Pt.H;

	/* --- */

	Expansion.R = STX_P / TUR_P;
	Expansion.I = 0.88;
	Expansion.Inlet.Copy(Pt);
	if (!Expansion.Calculate())
		output = false;
	Pt.Copy(Expansion.Outlet);

	STX_H_I = Pt.H;

	/* --- */

	Expansion.R = CDR_P / STX_P;
	Expansion.I = 0.88;
	Expansion.Inlet.Copy(Pt);
	if (!Expansion.Calculate())
		output = false;
	Pt.Copy(Expansion.Outlet);

	CDR_H_I = Pt.H;

	/* --- */

	Pt.P = STX_P;
	Pt.X = 0.0;
	if (!Pt.Calculate("P, X"))
		output = false;

	STX_H_O = Pt.H;

	/* --- */

	Pt.P = CDR_P;
	Pt.X = 0.0;
	if (!Pt.Calculate("P, X"))
		output = false;

	CDR_H_O = Pt.H;

	/* --- */

	a = (STX_H_I - CDR_H_I) / (STX_H_I - STX_H_O);

	b = (STX_H_I - STX_H_O) / (TUR_H - CDR_H_I);

	/* --- */

	return output;

}

/* Snap */

void Cogen::Snap() {

	cout << a << " " << b << endl;

}
