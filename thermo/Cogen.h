#ifndef COGEN_H
#define COGEN_H

#include "iesoH2O.h"

/*! \class Cogen \author Gréoux Research - www.greoux.re */

class Cogen {

public:

	/*! Constructor */

	Cogen();

	/*! Turbine Inlet Temperature (C), Pressure (bar) and Enthalpy */

	double TUR_T;

	double TUR_P;

	double TUR_H;

	/*! Condenser Pressure (bar) */

	double CDR_P;

	/*! Condenser Inlet & Outlet Enthalpies (kJ.kg-1) */

	double CDR_H_I;

	double CDR_H_O;

	/*! Steam Extraction Temperature (C) + Its Lower & Upper Limits */

	double STX_T;

	double STX_T_LLIM;

	double STX_T_ULIM;

	/*! Steam Extraction Pressure (bar) */

	double STX_P;

	/*! Steam Extraction Inlet & Outlet Enthalpies (kJ.kg-1) */

	double STX_H_I;

	double STX_H_O;

	/*! a */

	double a;

	/*! b */

	double b;

	/*! Calculate */

	bool Calculate();

	/*! Snap */

	void Snap();

private:

	/*! Point */

	iesoH2OPt Pt;

	/*! Expansion */

	iesoH2OComex Expansion;

};

#endif
