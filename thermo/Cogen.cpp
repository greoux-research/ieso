// Gréoux Research - www.greoux.re

#include "Cogen.h"

#include <cmath>
#include <iomanip>
#include <sstream>

/* Constructor */

Cogen::Cogen() {

	STX_T_LLIM_C = 0.0;
	STX_T_ULIM_C = 0.0;
}

/* Limits
 *
 * The supported extraction domain is the open interval between the saturation
 * temperature at the condenser pressure and the saturation temperature at the
 * turbine inlet pressure. Outside it the extraction pressure does not lie
 * between the two: below, extraction would be at or under condenser pressure
 * (the heat is free, a <= 0); above, it would be at or over inlet pressure,
 * and the expansion helper -- which also computes compressions -- returns
 * plausible-looking coefficients for a plant that cannot exist. The
 * boundaries themselves are excluded. The inlet steam must be superheated.
 */

bool Cogen::Limits() {

	std::ostringstream why;

	Reason = "";

	if (!(std::isfinite(TUR_T) && std::isfinite(TUR_P) && std::isfinite(CDR_P))) {
		Reason = "turbine and condenser conditions must be finite";
		return false;
	}

	if (!(CDR_P > 0.0 && CDR_P < TUR_P)) {
		why << "condenser pressure " << CDR_P << " bar must be positive and below the turbine inlet pressure " << TUR_P << " bar";
		Reason = why.str();
		return false;
	}

	Pt.P = CDR_P * 1.0e+5;
	Pt.X = 1.0;
	if (!Pt.Calculate("P, X")) {
		why << "condenser pressure " << CDR_P << " bar is outside the supported range of the steam tables";
		Reason = why.str();
		return false;
	}

	STX_T_LLIM = Pt.T;
	STX_T_LLIM_C = Pt.T - 273.15;

	Pt.P = TUR_P * 1.0e+5;
	Pt.X = 1.0;
	if (!Pt.Calculate("P, X")) {
		why << "turbine inlet pressure " << TUR_P << " bar is outside the supported range of the steam tables";
		Reason = why.str();
		return false;
	}

	STX_T_ULIM = Pt.T;
	STX_T_ULIM_C = Pt.T - 273.15;

	if (!(TUR_T > STX_T_ULIM_C)) {
		why << "turbine inlet steam must be superheated: " << TUR_T << " C is not above the saturation temperature "
		    << STX_T_ULIM_C << " C at " << TUR_P << " bar";
		Reason = why.str();
		return false;
	}

	return true;
}

/* Calculate */

bool Cogen::Calculate() {

	std::ostringstream why;

	if (!std::isfinite(STX_T)) {
		Reason = "extraction temperature must be finite";
		return false;
	}

	if (!Limits())
		return false;

	if (!(STX_T > STX_T_LLIM_C && STX_T < STX_T_ULIM_C)) {
		why << std::setprecision(10) << "extraction temperature " << STX_T << " C is outside the supported range ("
		    << STX_T_LLIM_C << ", " << STX_T_ULIM_C << ") C, boundaries excluded: the saturation temperatures at the condenser ("
		    << CDR_P << " bar) and turbine inlet (" << TUR_P << " bar) pressures";
		Reason = why.str();
		return false;
	}

	double tur_t = TUR_T + 273.15; // C to K
	double tur_p = TUR_P * 1.0e+5; // bar to Pa
	double cdr_p = CDR_P * 1.0e+5; // bar to Pa
	double stx_t = STX_T + 273.15; // C to K

	/* --- */

	Pt.T = stx_t;
	Pt.X = 1.0;
	if (!Pt.Calculate("T, X")) {
		Reason = "saturated steam at the extraction temperature could not be evaluated";
		return false;
	}

	STX_P = Pt.P;

	if (!(STX_P > cdr_p && STX_P < tur_p)) {
		why << "extraction pressure " << STX_P / 1.0e+5 << " bar does not lie between the condenser and inlet pressures";
		Reason = why.str();
		return false;
	}

	/* --- */

	Pt.T = tur_t;
	Pt.P = tur_p;
	if (!Pt.Calculate("T, P")) {
		Reason = "turbine inlet state could not be evaluated";
		return false;
	}

	TUR_H = Pt.H;

	/* --- */

	Expansion.R = STX_P / tur_p;
	Expansion.I = 0.88;
	Expansion.Inlet.Copy(Pt);
	if (!Expansion.Calculate()) {
		Reason = "expansion from inlet to extraction pressure could not be evaluated";
		return false;
	}
	Pt.Copy(Expansion.Outlet);

	STX_H_I = Pt.H;

	/* --- */

	Expansion.R = cdr_p / STX_P;
	Expansion.I = 0.88;
	Expansion.Inlet.Copy(Pt);
	if (!Expansion.Calculate()) {
		Reason = "expansion from extraction to condenser pressure could not be evaluated";
		return false;
	}
	Pt.Copy(Expansion.Outlet);

	CDR_H_I = Pt.H;

	/* --- */

	Pt.P = STX_P;
	Pt.X = 0.0;
	if (!Pt.Calculate("P, X")) {
		Reason = "saturated liquid at the extraction pressure could not be evaluated";
		return false;
	}

	STX_H_O = Pt.H;

	/* --- */

	Pt.P = cdr_p;
	Pt.X = 0.0;
	if (!Pt.Calculate("P, X")) {
		Reason = "saturated liquid at the condenser pressure could not be evaluated";
		return false;
	}

	CDR_H_O = Pt.H;

	/* --- */

	a = (STX_H_I - CDR_H_I) / (STX_H_I - STX_H_O);

	b = (STX_H_I - STX_H_O) / (TUR_H - CDR_H_I);

	/* --- admissibility: heat costs electricity, but less than its own energy;
	 *     at full extraction the plant still produces electricity (a * b < 1) */

	if (!(std::isfinite(a) && std::isfinite(b) && a > 0.0 && a < 1.0 && b > 0.0 && a * b < 1.0)) {
		why << "coefficients a = " << a << ", b = " << b << " are not admissible (need 0 < a < 1, b > 0, a*b < 1)";
		Reason = why.str();
		return false;
	}

	return true;
}

/* Snap */

void Cogen::Snap() {

	cout << a << " " << b << endl;
}
