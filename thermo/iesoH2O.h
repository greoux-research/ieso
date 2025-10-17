#ifndef iesoH2O_H
#define iesoH2O_H

#include <iostream>
#include <fstream>
#include <math.h>

using namespace std;

/*! \class iesoH2OFluidRegion1 \author Gréoux Research - www.greoux.re */
class iesoH2OFluidRegion1 {

public:
	/*! Constructor */
	iesoH2OFluidRegion1();

	/*! Constructor */
	iesoH2OFluidRegion1(double arg_T, double arg_P);

	/*! Volume (m3.kg-1) */
	double V;

	/*! Enthalpy (J.kg-1) */
	double H;

	/*! Entropy (J.kg-1.K-1) */
	double S;

	/*! Calculate region for a given temperature (K) and a given pressure (Pa) */
	void Calculate(double arg_T, double arg_P);

	/*! Quick mode? (backward equations) */
	bool QUICK;

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double T_HP_i(double arg_H, double arg_P);

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double T_HP(double arg_H, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double T_SP_i(double arg_S, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double T_SP(double arg_S, double arg_P);
};

/*! \class iesoH2OFluidRegion2 \author Gréoux Research - www.greoux.re */
class iesoH2OFluidRegion2 {

public:
	/*! Constructor */
	iesoH2OFluidRegion2();

	/*! Constructor */
	iesoH2OFluidRegion2(double arg_T, double arg_P);

	/*! Volume (m3.kg-1) */
	double V;

	/*! Enthalpy (J.kg-1) */
	double H;

	/*! Entropy (J.kg-1.K-1) */
	double S;

	/*! Calculate region for a given temperature (K) and a given pressure (Pa) */
	void Calculate(double arg_T, double arg_P);

	/*! Quick mode? (backward equations) */
	bool QUICK;

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double T_HP_i(double arg_H, double arg_P);

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double T_HP(double arg_H, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double T_SP_i(double arg_S, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double T_SP(double arg_S, double arg_P);

protected:
	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double _T_HP_A_(double arg_H, double arg_P);

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double _T_HP_B_(double arg_H, double arg_P);

	/*! Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
	double _T_HP_C_(double arg_H, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double _T_SP_A_(double arg_S, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double _T_SP_B_(double arg_S, double arg_P);

	/*! Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
	double _T_SP_C_(double arg_S, double arg_P);
};

/*! \class iesoH2OFluidRegion4 \author Gréoux Research - www.greoux.re */
class iesoH2OFluidRegion4 {

public:
	/*! Constructor */
	iesoH2OFluidRegion4();

	// === === inputs: temperature (K) and steam quality (kg.kg-1) === === */

	/*! Saturation pressure (Pa), function of temperature (K) and steam quality (kg.kg-1) */
	double P_TX(double arg_T, double arg_X);

	/*! Volume (m3.kg-1), function of temperature (K) and steam quality (kg.kg-1) */
	double V_TX(double arg_T, double arg_X);

	/*! Enthalpy (J.kg-1), function of temperature (K) and steam quality (kg.kg-1) */
	double H_TX(double arg_T, double arg_X);

	/*! Entropy (J.kg-1.K-1), function of temperature (K) and steam quality (kg.kg-1) */
	double S_TX(double arg_T, double arg_X);

	// === === inputs: pressure (Pa) and steam quality (kg.kg-1) === === */

	/*! Saturation temperature (K), function of pressure (Pa) and steam quality (kg.kg-1) */
	double T_PX(double arg_P, double arg_X);

	/*! Volume (m3.kg-1), function of pressure (Pa) and steam quality (kg.kg-1) */
	double V_PX(double arg_P, double arg_X);

	/*! Enthalpy (J.kg-1), function of pressure (Pa) and steam quality (kg.kg-1) */
	double H_PX(double arg_P, double arg_X);

	/*! Entropy (J.kg-1.K-1), function of pressure (Pa) and steam quality (kg.kg-1) */
	double S_PX(double arg_P, double arg_X);
};

/*! \class iesoH2OFluidRegionIndex \author Gréoux Research - www.greoux.re */
class iesoH2OFluidRegionIndex {

public:
	/*! Constructor */
	iesoH2OFluidRegionIndex();

	/*! Region index, function of temperature (K) and pressure (Pa) */
	unsigned int R_TP(double arg_T, double arg_P);

	/*! Region index, function of enthalpy (J.kg-1) and pressure (Pa) */
	unsigned int R_HP(double arg_H, double arg_P);

	/*! Region index, function of entropy (J.kg-1.K-1) and pressure (Pa) */
	unsigned int R_SP(double arg_S, double arg_P);
};

/*! \class iesoH2OPt \author Gréoux Research - www.greoux.re */
class iesoH2OPt {

public:
	/*! Constructor */
	iesoH2OPt();

	/*! Temperature (K) */
	double T;

	/*! Pressure (Pa) */
	double P;

	/*! Fraction of steam (kg.kg-1) */
	double X;

	/*! Volume (m3.kg-1) */
	double V;

	/*! Enthalpy (J.kg-1) */
	double H;

	/*! Entropy (J.kg-1.K-1) */
	double S;

	/*! Exergy (J.kg-1) */
	double E;

	/*! Mass flow rate (kg.s-1) */
	double F;

	/*! Calculate */
	bool Calculate(string arg_O);

	/*! Calculate */
	bool Calculate(unsigned int arg_O);

	/*! Copy */
	void Copy(iesoH2OPt arg_Pt);

	/*! Snap */
	void Snap();

protected:
	/*! Environment temperature (K) */
	double _T0_;

	/*! Set T, P */
	bool _TP_(double arg_T, double arg_P);

	/*! Set H, P */
	bool _HP_(double arg_H, double arg_P);

	/*! Set S, P */
	bool _SP_(double arg_S, double arg_P);

	/*! Set T, X */
	bool _TX_(double arg_T, double arg_X);

	/*! Set P, X */
	bool _PX_(double arg_P, double arg_X);
};

/*! \class iesoH2OComex \author Gréoux Research - www.greoux.re */
class iesoH2OComex {

public:
	/*! Constructor */
	iesoH2OComex();

	/*! Constructor. arg_R: compression ratio (%). arg_I: isentropic efficiency (%). */
	iesoH2OComex(double arg_R, double arg_I);

	/*! Compression ratio (%) */
	double R;

	/*! Isentropic efficiency (%) */
	double I;

	/*! Inlet */
	iesoH2OPt Inlet;

	/*! Outlet */
	iesoH2OPt Outlet;

	/*! Calculate */
	bool Calculate();
};

#endif
