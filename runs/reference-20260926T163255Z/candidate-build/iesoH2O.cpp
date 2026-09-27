// Gréoux Research - www.greoux.re

#include "iesoH2O.h"

/* Constructor */
iesoH2OFluidRegion1::iesoH2OFluidRegion1() {

	/* Volume (m3.kg-1) */
	V = 0.0;

	/* Enthalpy (J.kg-1) */
	H = 0.0;

	/* Entropy (J.kg-1.K-1) */
	S = 0.0;

	/* Quick mode? (backward equations) */
	QUICK = false;
}

/* Constructor */
iesoH2OFluidRegion1::iesoH2OFluidRegion1(double arg_T, double arg_P) {

	/* Volume (m3.kg-1) */
	V = 0.0;

	/* Enthalpy (J.kg-1) */
	H = 0.0;

	/* Entropy (J.kg-1.K-1) */
	S = 0.0;

	/* Calculate region for a given temperature (K) and a given pressure (Pa) */
	Calculate(arg_T, arg_P);
}

/* Calculate region for a given temperature (K) and a given pressure (Pa) */
void iesoH2OFluidRegion1::Calculate(double arg_T, double arg_P) {

	const double R = 0.461526;

	const double n[34] = { 0.14632971213167, -0.84548187169114,
			-0.37563603672040e1, 0.33855169168385e1, -0.95791963387872,
			0.15772038513228, -0.16616417199501e-1, 0.81214629983568e-3,
			0.28319080123804e-3, -0.60706301565874e-3, -0.18990068218419e-1,
			-0.32529748770505e-1, -0.21841717175414e-1, -0.52838357969930e-4,
			-0.47184321073267e-3, -0.30001780793026e-3, 0.47661393906987e-4,
			-0.44141845330846e-5, -0.72694996297594e-15, -0.31679644845054e-4,
			-0.28270797985312e-5, -0.85205128120103e-9, -0.22425281908000e-5,
			-0.65171222895601e-6, -0.14341729937924e-12, -0.40516996860117e-6,
			-0.12734301741641e-8, -0.17424871230634e-9, -0.68762131295531e-18,
			0.14478307828521e-19, 0.26335781662795e-22, -0.11947622640071e-22,
			0.18228094581404e-23, -0.93537087292458e-25 };

	const double I[34] = { 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2,
			2, 3, 3, 3, 4, 4, 4, 5, 8, 8, 21, 23, 29, 30, 31, 32 };

	const double J[34] = { -2, -1, 0, 1, 2, 3, 4, 5, -9, -7, -1, 0, 1, 3, -3, 0,
			1, 3, 17, -4, 0, 6, -5, -2, 10, -8, -11, -6, -29, -31, -38, -39,
			-40, -41 };

	double T = arg_T;
	double P = arg_P / 1e6; /* Pa to MPa */

	double Tr = 1386 / T;
	double Pr = P / 16.53;
	double g = 0.0;
	double gp = 0.0;
	double gpp = 0.0;
	double gt = 0.0;
	double gtt = 0.0;
	double gpt = 0.0;

	for (unsigned int i = 0; i < 34; i++) {

		g += n[i] * pow(7.1 - Pr, I[i]) * pow(Tr - 1.222, J[i]);

		gp -= n[i] * I[i] * pow(7.1 - Pr, I[i] - 1) * pow(Tr - 1.222, J[i]);

		gpp += n[i] * I[i] * (I[i] - 1) * pow(7.1 - Pr, I[i] - 2)
				* pow(Tr - 1.222, J[i]);

		gt += n[i] * pow(7.1 - Pr, I[i]) * J[i] * pow(Tr - 1.222, J[i] - 1);

		gtt += n[i] * pow(7.1 - Pr, I[i]) * J[i] * (J[i] - 1)
				* pow(Tr - 1.222, J[i] - 2);

		gpt -= n[i] * I[i] * pow(7.1 - Pr, I[i] - 1) * J[i]
				* pow(Tr - 1.222, J[i] - 1);
	}

	V = Pr * gp * R * T / P / 1000;

	H = Tr * gt * R * T;
	H *= 1000; /* kJ.kg-1 to J.kg-1 */

	S = R * (Tr * gt - g);
	S *= 1000; /* kJ.kg-1.K-1 to J.kg-1.K-1 */
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion1::T_HP_i(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double H = arg_H / 1e3; /* J.kg-1 to kJ.kg-1 */

	const double I[20] = { 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4,
			5, 6 };

	const double J[20] = { 0, 1, 2, 6, 22, 32, 0, 1, 2, 3, 4, 10, 32, 10, 32,
			10, 32, 32, 32, 32 };

	const double n[20] = { -0.23872489924521e3, 0.40421188637945e3,
			0.11349746881718e3, -0.58457616048039e1, -0.15285482413140e-3,
			-0.10866707695377e-5, -0.13391744872602e2, 0.43211039183559e2,
			-0.54010067170506e2, 0.30535892203916e2, -0.65964749423638e1,
			0.93965400878363e-2, 0.11573647505340e-6, -0.25858641282073e-4,
			-0.40644363084799e-8, 0.66456186191635e-7, 0.80670734103027e-10,
			-0.93477771213947e-12, 0.58265442020601e-14, -0.15020185953503e-16 };

	double Pr = P / 1.0;
	double nu = H / 2500;

	double T = 0;
	for (unsigned int i = 0; i < 20; i++)
		T += n[i] * pow(Pr, I[i]) * pow(nu + 1, J[i]);

	return T;
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion1::T_HP(double arg_H, double arg_P) {

	if (QUICK) {

		return T_HP_i(arg_H, arg_P);
	} else {

		bool zero_was_found = false;

		const unsigned long MAXITER = 1e+9;
		const double PRECISION = 1e-9;

		double mini = T_HP_i(arg_H, arg_P) - 5.0;
		double maxi = mini + 10.0;
		double mean = 0.5 * (maxi + mini);

		double zero = 0.0;

		double x, y;
		double y_mini, y_maxi, y_mean;
		double y_mini_X_y_mean;
		double y_maxi_X_y_mean;

		unsigned long i;

		for (i = 0; i < MAXITER; i++) {

			x = mini;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_mini = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = mean;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_mean = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = maxi;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_maxi = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			y_mini_X_y_mean = y_mini * y_mean;
			y_maxi_X_y_mean = y_maxi * y_mean;

			/* --- */

			if (y_mini_X_y_mean < 0)
				maxi = mean;
			else if (y_maxi_X_y_mean < 0)
				mini = mean;
			else
				break;

			/* --- */

			mean = 0.5 * (maxi + mini);
		}

		if (zero_was_found) {

			if (false)
				cout << "T_HP, iterations (#) = " << i << endl;

			return zero;
		} else {

			return T_HP_i(arg_H, arg_P);
		}
	}
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion1::T_SP_i(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double S = arg_S / 1e3; /* J.kg-1.K-1 to kJ.kg-1.K-1 */

	const double I[20] = { 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3,
			3, 4 };

	const double J[20] = { 0, 1, 2, 3, 11, 31, 0, 1, 2, 3, 12, 31, 0, 1, 2, 9,
			31, 10, 32, 32 };

	const double n[20] = { 0.17478268058307e3, 0.34806930892873e2,
			0.65292584978455e1, 0.33039981775489, -0.19281382923196e-6,
			-0.24909197244573e-22, -0.26107636489332, 0.22592965981586,
			-0.64256463395226e-1, 0.78876289270526e-2, 0.35672110607366e-9,
			0.17332496994895e-23, 0.56608900654837e-3, -0.32635483139717e-3,
			0.44778286690632e-4, -0.51322156908507e-9, -0.42522657042207e-25,
			0.26400441360689e-12, 0.78124600459723e-28, -0.30732199903668e-30 };

	double Pr = P / 1.0;
	double sigma = S;

	double T = 0;
	for (unsigned int i = 0; i < 20; i++)
		T += n[i] * pow(Pr, I[i]) * pow(sigma + 2, J[i]);

	return T;
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion1::T_SP(double arg_S, double arg_P) {

	if (QUICK) {

		return T_SP_i(arg_S, arg_P);
	} else {

		bool zero_was_found = false;

		const unsigned long MAXITER = 1e+9;
		const double PRECISION = 1e-9;

		double mini = T_SP_i(arg_S, arg_P) - 5.0;
		double maxi = mini + 10.0;
		double mean = 0.5 * (maxi + mini);

		double zero = 0.0;

		double x, y;
		double y_mini, y_maxi, y_mean;
		double y_mini_X_y_mean;
		double y_maxi_X_y_mean;

		unsigned long i;

		for (i = 0; i < MAXITER; i++) {

			x = mini;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_mini = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = mean;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_mean = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = maxi;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_maxi = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			y_mini_X_y_mean = y_mini * y_mean;
			y_maxi_X_y_mean = y_maxi * y_mean;

			/* --- */

			if (y_mini_X_y_mean < 0)
				maxi = mean;
			else if (y_maxi_X_y_mean < 0)
				mini = mean;
			else
				break;

			/* --- */

			mean = 0.5 * (maxi + mini);
		}

		if (zero_was_found) {

			if (false)
				cout << "T_SP, iterations (#) = " << i << endl;

			return zero;
		} else {

			return T_SP_i(arg_S, arg_P);
		}
	}
}

/* Constructor */
iesoH2OFluidRegion2::iesoH2OFluidRegion2() {

	/* Volume (m3.kg-1) */
	V = 0.0;

	/* Enthalpy (J.kg-1) */
	H = 0.0;

	/* Entropy (J.kg-1.K-1) */
	S = 0.0;

	/* Quick mode? (backward equations) */
	QUICK = false;
}

/* Constructor */
iesoH2OFluidRegion2::iesoH2OFluidRegion2(double arg_T, double arg_P) {

	/* Volume (m3.kg-1) */
	V = 0.0;

	/* Enthalpy (J.kg-1) */
	H = 0.0;

	/* Entropy (J.kg-1.K-1) */
	S = 0.0;

	/* Calculate region for a given temperature (K) and a given pressure (Pa) */
	Calculate(arg_T, arg_P);
}

/* Calculate region for a given temperature (K) and a given pressure (Pa) */
void iesoH2OFluidRegion2::Calculate(double arg_T, double arg_P) {

	const double R = 0.461526;

	const double Ir[43] = { 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4,
			4, 5, 6, 6, 6, 7, 7, 7, 8, 8, 9, 10, 10, 10, 16, 16, 18, 20, 20, 20,
			21, 22, 23, 24, 24, 24 };

	const double Jr[43] = { 0, 1, 2, 3, 6, 1, 2, 4, 7, 36, 0, 1, 3, 6, 35, 1, 2,
			3, 7, 3, 16, 35, 0, 11, 25, 8, 36, 13, 4, 10, 14, 29, 50, 57, 20,
			35, 48, 21, 53, 39, 26, 40, 58 };

	const double nr[43] = { -0.0017731742473212999, -0.017834862292357999,
			-0.045996013696365003, -0.057581259083432, -0.050325278727930002,
			-3.3032641670203e-05, -0.00018948987516315, -0.0039392777243355001,
			-0.043797295650572998, -2.6674547914087001e-05,
			2.0481737692308999e-08, 4.3870667284435001e-07,
			-3.2277677238570002e-05, -0.0015033924542148, -0.040668253562648998,
			-7.8847309559367001e-10, 1.2790717852285001e-08,
			4.8225372718507002e-07, 2.2922076337661001e-06,
			-1.6714766451061001e-11, -0.0021171472321354998,
			-23.895741934103999, -5.9059564324270004e-18, -1.2621808899101e-06,
			-0.038946842435739003, 1.1256211360459e-11, -8.2311340897998004,
			1.9809712802088e-08, 1.0406965210174e-19, -1.0234747095929e-13,
			-1.0018179379511e-09, -8.0882908646984998e-11, 0.10693031879409,
			-0.33662250574170999, 8.9185845355420999e-25,
			3.0629316876231997e-13, -4.2002467698208001e-06,
			-5.9056029685639003e-26, 3.7826947613457002e-06,
			-1.2768608934681e-15, 7.3087610595061e-29, 5.5414715350778001e-17,
			-9.4369707241209998e-07 };

	double T = arg_T;
	double P = arg_P / 1e6; /* Pa to MPa */

	double Tr = 540 / T;
	double Pr = P / 1;

	double gr = 0.0;
	double grp = 0.0;
	double grpp = 0.0;
	double grt = 0.0;
	double grtt = 0.0;
	double grpt = 0.0;

	unsigned int i;

	for (i = 0; i < 43; i++) {

		gr += nr[i] * pow(Pr, Ir[i]) * pow(Tr - 0.5, Jr[i]);

		grp += nr[i] * Ir[i] * pow(Pr, Ir[i] - 1) * pow(Tr - 0.5, Jr[i]);

		grpp += nr[i] * Ir[i] * (Ir[i] - 1) * pow(Pr, Ir[i] - 2)
				* pow(Tr - 0.5, Jr[i]);

		grt += nr[i] * pow(Pr, Ir[i]) * Jr[i] * pow(Tr - 0.5, Jr[i] - 1);

		grtt += nr[i] * pow(Pr, Ir[i]) * Jr[i] * (Jr[i] - 1)
				* pow(Tr - 0.5, Jr[i] - 2);

		grpt += nr[i] * Ir[i] * pow(Pr, Ir[i] - 1) * Jr[i]
				* pow(Tr - 0.5, Jr[i] - 1);
	}

	const double Jo[9] = { 0, 1, -5, -4, -3, -2, -1, 2, 3 };

	const double no[9] = { -0.96927686500217E+01, 0.10086655968018E+02,
			-0.56087911283020E-02, 0.71452738081455E-01, -0.40710498223928E+00,
			0.14240819171444E+01, -0.43839511319450E+01, -0.28408632460772E+00,
			0.21268463753307E-01 };

	double go = 0.0;
	double gop = 0.0;
	// double gopp = 0.0;
	double got = 0.0;
	double gott = 0.0;
	// double gopt = 0.0;

	go = log(Pr);
	gop = pow(Pr, -1);
	// gopp = -1 * pow(Pr, -2);

	for (i = 0; i < 9; i++) {

		go += no[i] * pow(Tr, Jo[i]);

		got += no[i] * Jo[i] * pow(Tr, Jo[i] - 1);

		gott += no[i] * Jo[i] * (Jo[i] - 1) * pow(Tr, Jo[i] - 2);
	}

	V = Pr * (gop + grp) * R * T / P / 1000;

	H = Tr * (got + grt) * R * T;
	H *= 1000; /* kJ.kg-1 to J.kg-1 */

	S = R * (Tr * (got + grt) - (go + gr));
	S *= 1000; /* kJ.kg-1.K-1 to J.kg-1.K-1 */
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_HP_A_(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double H = arg_H / 1e3; /* J.kg-1 to kJ.kg-1 */

	const double I[34] = { 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2,
			2, 2, 2, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 7 };

	const double J[34] =
			{ 0, 1, 2, 3, 7, 20, 0, 1, 2, 3, 7, 9, 11, 18, 44, 0, 2, 7, 36, 38,
					40, 42, 44, 24, 44, 12, 32, 44, 32, 36, 42, 34, 44, 28 };
	const double n[34] = { 0.10898952318288e4, 0.84951654495535e3,
			-0.10781748091826e3, 0.33153654801263e2, -0.74232016790248e1,
			0.11765048724356e2, 0.18445749355790e1, -0.41792700549624e1,
			0.62478196935812e1, -0.17344563108114e2, -0.20058176862096e3,
			0.27196065473796e3, -0.45511318285818e3, 0.30919688604755e4,
			0.25226640357872e6, -0.61707422868339e-2, -0.31078046629583,
			0.11670873077107e2, 0.12812798404046e9, -0.98554909623276e9,
			0.28224546973002e10, -0.35948971410703e10, 0.17227349913197e10,
			-0.13551334240775e5, 0.12848734664650e8, 0.13865724283226e1,
			0.23598832556514e6, -0.13105236545054e8, 0.73999835474766e4,
			-0.55196697030060e6, 0.37154085996233e7, 0.19127729239660e5,
			-0.41535164835634e6, -0.62459855192507e2 };

	double Pr = P / 1;
	double nu = H / 2000;

	double T = 0;
	for (unsigned int i = 0; i < 34; i++)
		T += n[i] * pow(Pr, I[i]) * pow(nu - 2.1, J[i]);

	return T;
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_HP_B_(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double H = arg_H / 1e3; /* J.kg-1 to kJ.kg-1 */

	const double I[38] = { 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2,
			2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 6, 7, 7, 9, 9 };

	const double J[38] = { 0, 1, 2, 12, 18, 24, 28, 40, 0, 2, 6, 12, 18, 24, 28,
			40, 2, 8, 18, 40, 1, 2, 12, 24, 2, 12, 18, 24, 28, 40, 18, 24, 40,
			28, 2, 28, 1, 40 };

	const double n[38] = { 0.14895041079516e4, 0.74307798314034e3,
			-0.97708318797837e2, 0.24742464705674e1, -0.63281320016026,
			0.11385952129658e1, -0.47811863648625, 0.85208123431544e-2,
			0.93747147377932, 0.33593118604916e1, 0.33809355601454e1,
			0.16844539671904, 0.73875745236695, -0.47128737436186,
			0.15020273139707, -0.21764114219750e-2, -0.21810755324761e-1,
			-0.10829784403677, -0.46333324635812e-1, 0.71280351959551e-4,
			0.11032831789999e-3, 0.18955248387902e-3, 0.30891541160537e-2,
			0.13555504554949e-2, 0.28640237477456e-6, -0.10779857357512e-4,
			-0.76462712454814e-4, 0.14052392818316e-4, -0.31083814331434e-4,
			-0.10302738212103e-5, 0.28217281635040e-6, 0.12704902271945e-5,
			0.73803353468292e-7, -0.11030139238909e-7, -0.81456365207833e-13,
			-0.25180545682962e-10, -0.17565233969407e-17, 0.86934156344163e-14 };

	double Pr = P / 1;
	double nu = H / 2000;

	double T = 0;
	for (unsigned int i = 0; i < 38; i++)
		T += n[i] * pow(Pr - 2, I[i]) * pow(nu - 2.6, J[i]);

	return T;
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_HP_C_(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double H = arg_H / 1e3; /* J.kg-1 to kJ.kg-1 */

	const double I[23] = { -7, -7, -6, -6, -5, -5, -2, -2, -1, -1, 0, 0, 1, 1,
			2, 6, 6, 6, 6, 6, 6, 6, 6 };

	const double J[23] = { 0, 4, 0, 2, 0, 2, 0, 1, 0, 2, 0, 1, 4, 8, 4, 0, 1, 4,
			10, 12, 16, 20, 22 };

	const double n[23] = { -0.32368398555242e13, 0.73263350902181e13,
			0.35825089945447e12, -0.58340131851590e12, -0.10783068217470e11,
			0.20825544563171e11, 0.61074783564516e6, 0.85977722535580e6,
			-0.25745723604170e5, 0.31081088422714e5, 0.12082315865936e4,
			0.48219755109255e3, 0.37966001272486e1, -0.10842984880077e2,
			-0.45364172676660e-1, 0.14559115658698e-12, 0.11261597407230e-11,
			-0.17804982240686e-10, 0.12324579690832e-6, -0.11606921130984e-5,
			0.27846367088554e-4, -0.59270038474176e-3, 0.12918582991878e-2 };

	double Pr = P / 1;
	double nu = H / 2000;

	double T = 0;
	for (unsigned int i = 0; i < 23; i++)
		T += n[i] * pow(Pr + 25, I[i]) * pow(nu - 1.8, J[i]);

	return T;
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion2::T_HP_i(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double H = arg_H / 1e3; /* J.kg-1 to kJ.kg-1 */

	double Tsat;

	iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();
	Tsat = (*r4).T_PX(arg_P, 0.0);
	delete r4;

	double T;

	if (P <= 4) {

		T = _T_HP_A_(arg_H, arg_P);
	} else if ((P > 4) && (P <= 6.546699678)) {

		T = _T_HP_B_(arg_H, arg_P);
	} else {

		double hf = 0.26526571908428e4
				+ pow((P - 0.45257578905948e1) / 1.2809002730136e-4, 0.5);

		if (H >= hf) {

			T = _T_HP_B_(arg_H, arg_P);
		} else {

			T = _T_HP_C_(arg_H, arg_P);
		}
	}

	if (T < Tsat) {

		T = Tsat;
	}

	return T;
}

/* Temperature (K), function of enthalpy (J.kg-1) and pressure (Pa) */
double iesoH2OFluidRegion2::T_HP(double arg_H, double arg_P) {

	if (QUICK) {

		return T_HP_i(arg_H, arg_P);
	} else {

		bool zero_was_found = false;

		const unsigned long MAXITER = 1e+9;
		const double PRECISION = 1e-9;

		double mini = T_HP_i(arg_H, arg_P) - 5.0;
		double maxi = mini + 10.0;
		double mean = 0.5 * (maxi + mini);

		double zero = 0.0;

		double x, y;
		double y_mini, y_maxi, y_mean;
		double y_mini_X_y_mean;
		double y_maxi_X_y_mean;

		unsigned long i;

		for (i = 0; i < MAXITER; i++) {

			x = mini;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_mini = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = mean;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_mean = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = maxi;

			Calculate(x, arg_P);
			y = arg_H - H;

			y_maxi = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			y_mini_X_y_mean = y_mini * y_mean;
			y_maxi_X_y_mean = y_maxi * y_mean;

			/* --- */

			if (y_mini_X_y_mean < 0)
				maxi = mean;
			else if (y_maxi_X_y_mean < 0)
				mini = mean;
			else
				break;

			/* --- */

			mean = 0.5 * (maxi + mini);
		}

		if (zero_was_found) {

			if (false)
				cout << "T_HP, iterations (#) = " << i << endl;

			return zero;
		} else {

			return T_HP_i(arg_H, arg_P);
		}
	}
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_SP_A_(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double S = arg_S / 1e3; /* J.kg-1.K-1 to kJ.kg-1.K-1 */

	const double I[46] = { -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.25, -1.25,
			-1.25, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -0.75, -0.75, -0.5, -0.5,
			-0.5, -0.5, -0.25, -0.25, -0.25, -0.25, 0.25, 0.25, 0.25, 0.25, 0.5,
			0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.75, 0.75, 0.75, 0.75, 1.0, 1.0,
			1.25, 1.25, 1.5, 1.5 };

	const double J[46] = { -24, -23, -19, -13, -11, -10, -19, -15, -6, -26, -21,
			-17, -16, -9, -8, -15, -14, -26, -13, -9, -7, -27, -25, -11, -6, 1,
			4, 8, 11, 0, 1, 5, 6, 10, 14, 16, 0, 4, 9, 17, 7, 18, 3, 15, 5, 18 };

	const double n[46] = { -0.39235983861984e6, 0.51526573827270e6,
			0.40482443161048e5, -0.32193790923902e3, 0.96961424218694e2,
			-0.22867846371773e2, -0.44942914124357e6, -0.50118336020166e4,
			0.35684463560015, 0.44235335848190e5, -0.13673388811708e5,
			0.42163260207864e6, 0.22516925837475e5, 0.47442144865646e3,
			-0.14931130797647e3, -0.19781126320452e6, -0.23554399470760e5,
			-0.19070616302076e5, 0.55375669883164e5, 0.38293691437363e4,
			-0.60391860580567e3, 0.19363102620331e4, 0.42660643698610e4,
			-0.59780638872718e4, -0.70401463926862e3, 0.33836784107553e3,
			0.20862786635187e2, 0.33834172656196e-1, -0.43124428414893e-4,
			0.16653791356412e3, -0.13986292055898e3, -0.78849547999872,
			0.72132411753872e-1, -0.59754839398283e-2, -0.12141358953904e-4,
			0.23227096733871e-6, -0.10538463566194e2, 0.20718925496502e1,
			-0.72193155260427e-1, 0.20749887081120e-6, -0.18340657911379e-1,
			0.29036272348696e-6, 0.21037527893619, 0.25681239729999e-3,
			-0.12799002933781e-1, -0.82198102652018e-5 };

	double Pr = P / 1;
	double sigma = S / 2;

	double T = 0;
	for (unsigned int i = 0; i < 46; i++)
		T += n[i] * pow(Pr, I[i]) * pow(sigma - 2, J[i]);

	return T;
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_SP_B_(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double S = arg_S / 1e3; /* J.kg-1.K-1 to kJ.kg-1.K-1 */

	const double I[44] = { -6, -6, -5, -5, -4, -4, -4, -3, -3, -3, -3, -2, -2,
			-2, -2, -1, -1, -1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1,
			2, 2, 2, 3, 3, 3, 4, 4, 5, 5, 5 };

	const double J[44] = { 0, 11, 0, 11, 0, 1, 11, 0, 1, 11, 12, 0, 1, 6, 10, 0,
			1, 5, 8, 9, 0, 1, 2, 4, 5, 6, 9, 0, 1, 2, 3, 7, 8, 0, 1, 5, 0, 1, 3,
			0, 1, 0, 1, 2 };

	const double n[44] = { 0.31687665083497e6, 0.20864175881858e2,
			-0.39859399803599e6, -0.21816058518877e2, 0.22369785194242e6,
			-0.27841703445817e4, 0.99207436071480e1, -0.75197512299157e5,
			0.29708605951158e4, -0.34406878548526e1, 0.38815564249115,
			0.17511295085750e5, -0.14237112854449e4, 0.10943803364167e1,
			0.89971619308495, -0.33759740098958e4, 0.47162885818355e3,
			-0.19188241993679e1, 0.41078580492196, -0.33465378172097,
			0.13870034777505e4, -0.40663326195838e3, 0.41727347159610e2,
			0.21932549434532e1, -0.10320050009077e1, 0.35882943516703,
			0.52511453726066e-2, 0.12838916450705e2, -0.28642437219381e1,
			0.56912683664855, -0.99962954584931e-1, -0.32632037778459e-2,
			0.23320922576723e-3, -0.15334809857450, 0.29072288239902e-1,
			0.37534702741167e-3, 0.17296691702411e-2, -0.38556050844504e-3,
			-0.35017712292608e-4, -0.14566393631492e-4, 0.56420857267269e-5,
			0.41286150074605e-7, -0.20684671118824e-7, 0.16409393674725e-8 };

	double Pr = P / 1;
	double sigma = S / 0.7853;
	double T = 0;
	for (unsigned int i = 0; i < 44; i++)
		T += n[i] * pow(Pr, I[i]) * pow(10 - sigma, J[i]);

	return T;
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion2::_T_SP_C_(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double S = arg_S / 1e3; /* J.kg-1.K-1 to kJ.kg-1.K-1 */

	const double I[30] = { -2, -2, -1, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3,
			4, 4, 4, 5, 5, 5, 6, 6, 7, 7, 7, 7, 7 };

	const double J[30] = { 0, 1, 0, 0, 1, 2, 3, 0, 1, 3, 4, 0, 1, 2, 0, 1, 5, 0,
			1, 4, 0, 1, 2, 0, 1, 0, 1, 3, 4, 5 };

	const double n[30] = { 0.90968501005365e3, 0.24045667088420e4,
			-0.59162326387130e3, 0.54145404128074e3, -0.27098308411192e3,
			0.97976525097926e3, -0.46966772959435e3, 0.14399274604723e2,
			-0.19104204230429e2, 0.53299167111971e1, -0.21252975375934e2,
			-0.31147334413760, 0.60334840894623, -0.42764839702509e-1,
			0.58185597255259e-2, -0.14597008284753e-1, 0.56631175631027e-2,
			-0.76155864584577e-4, 0.22440342919332e-3, -0.12561095013413e-4,
			0.63323132660934e-6, -0.20541989675375e-5, 0.36405370390082e-7,
			-0.29759897789215e-8, 0.10136618529763e-7, 0.59925719692351e-11,
			-0.20677870105164e-10, -0.20874278181886e-10, 0.10162166825089e-9,
			-0.16429828281347e-9 };

	double Pr = P / 1;
	double sigma = S / 2.9251;

	double T = 0;
	for (unsigned int i = 0; i < 30; i++)
		T += n[i] * pow(Pr, I[i]) * pow(2 - sigma, J[i]);

	return T;
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion2::T_SP_i(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double S = arg_S / 1e3; /* J.kg-1.K-1 to kJ.kg-1.K-1 */

	double Tsat;

	iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();
	Tsat = (*r4).T_PX(arg_P, 0.0);
	delete r4;

	double T;

	if (P <= 4) {

		T = _T_SP_A_(arg_S, arg_P);
	} else if (S >= 5.85) {

		T = _T_SP_B_(arg_S, arg_P);
	} else {

		T = _T_SP_C_(arg_S, arg_P);
	}

	if (T < Tsat) {

		T = Tsat;
	}

	return T;
}

/* Temperature (K), function of entropy (J.kg-1.K-1) and pressure (Pa) */
double iesoH2OFluidRegion2::T_SP(double arg_S, double arg_P) {

	if (QUICK) {

		return T_SP_i(arg_S, arg_P);
	} else {

		bool zero_was_found = false;

		const unsigned long MAXITER = 1e+9;
		const double PRECISION = 1e-9;

		double mini = T_SP_i(arg_S, arg_P) - 5.0;
		double maxi = mini + 10.0;
		double mean = 0.5 * (maxi + mini);

		double zero = 0.0;

		double x, y;
		double y_mini, y_maxi, y_mean;
		double y_mini_X_y_mean;
		double y_maxi_X_y_mean;

		unsigned long i;

		for (i = 0; i < MAXITER; i++) {

			x = mini;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_mini = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = mean;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_mean = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			x = maxi;

			Calculate(x, arg_P);
			y = arg_S - S;

			y_maxi = y;

			if (pow(pow(y, 2.0), 0.5) < PRECISION) {
				zero = x;
				zero_was_found = true;
				break;
			}

			/* --- */

			y_mini_X_y_mean = y_mini * y_mean;
			y_maxi_X_y_mean = y_maxi * y_mean;

			/* --- */

			if (y_mini_X_y_mean < 0)
				maxi = mean;
			else if (y_maxi_X_y_mean < 0)
				mini = mean;
			else
				break;

			/* --- */

			mean = 0.5 * (maxi + mini);
		}

		if (zero_was_found) {

			if (false)
				cout << "T_SP, iterations (#) = " << i << endl;

			return zero;
		} else {

			return T_SP_i(arg_S, arg_P);
		}
	}
}

/* Constructor */
iesoH2OFluidRegion4::iesoH2OFluidRegion4() {
}

// === === inputs: temperature (K) and steam quality (kg.kg-1) === === */

/* Saturation pressure (Pa), function of temperature (K) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::P_TX(double arg_T, double arg_X) {

	double P = 0;
	double T = arg_T;
	const double Tc = 647.096;

	if (T < 273.15)
		T = 273.15;
	else if (T > Tc)
		T = Tc;

	const double n[11] = { 0, 0.11670521452767E+04, -0.72421316703206E+06,
			-0.17073846940092E+02, 0.12020824702470E+05, -0.32325550322333E+07,
			0.14915108613530E+02, -0.48232657361591E+04, 0.40511340542057E+06,
			-0.23855557567849E+00, 0.65017534844798E+03 };

	double tita = T + n[9] / (T - n[10]);
	double A = pow(tita, 2) + n[1] * tita + n[2];
	double B = n[3] * pow(tita, 2) + n[4] * tita + n[5];
	double C = n[6] * pow(tita, 2) + n[7] * tita + n[8];
	P = pow(2 * C / (-B + pow(pow(B, 2) - 4 * A * C, 0.5)), 4);

	P *= 1e6; /* MPa to Pa */

	return P;
}

/* Volume (m3.kg-1), function of temperature (K) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::V_TX(double arg_T, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(arg_T, P_TX(arg_T, arg_X));
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(arg_T, P_TX(arg_T, arg_X));

	double V = (*r1).V + arg_X * ((*r2).V - (*r1).V);

	delete r1;
	delete r2;

	return V;
}

/* Enthalpy (J.kg-1), function of temperature (K) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::H_TX(double arg_T, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(arg_T, P_TX(arg_T, arg_X));
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(arg_T, P_TX(arg_T, arg_X));

	double H = (*r1).H + arg_X * ((*r2).H - (*r1).H);

	delete r1;
	delete r2;

	return H;
}

/* Entropy (J.kg-1.K-1), function of temperature (K) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::S_TX(double arg_T, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(arg_T, P_TX(arg_T, arg_X));
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(arg_T, P_TX(arg_T, arg_X));

	double S = (*r1).S + arg_X * ((*r2).S - (*r1).S);

	delete r1;
	delete r2;

	return S;
}

// === === inputs: pressure (Pa) and steam quality (kg.kg-1) === === */

/* Saturation temperature (K), function of pressure (Pa) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::T_PX(double arg_P, double arg_X) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double T = 0;

	if (P < 611.212677 / 1e6)
		P = 611.212677 / 1e6;
	else if (P > 22.064)
		P = 22.064;

	const double n[11] = { 0, 0.11670521452767E+04, -0.72421316703206E+06,
			-0.17073846940092E+02, 0.12020824702470E+05, -0.32325550322333E+07,
			0.14915108613530E+02, -0.48232657361591E+04, 0.40511340542057E+06,
			-0.23855557567849E+00, 0.65017534844798E+03 };

	double beta = pow(P, 0.25);
	double E = pow(beta, 2) + n[3] * beta + n[6];
	double F = n[1] * pow(beta, 2) + n[4] * beta + n[7];
	double G = n[2] * pow(beta, 2) + n[5] * beta + n[8];
	double D = 2 * G / (-F - pow(pow(F, 2) - 4 * E * G, 0.5));

	T = (n[10] + D - pow(pow(n[10] + D, 2) - 4 * (n[9] + n[10] * D), 0.5)) / 2;

	return T;
}

/* Volume (m3.kg-1), function of pressure (Pa) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::V_PX(double arg_P, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(T_PX(arg_P, arg_X), arg_P);
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(T_PX(arg_P, arg_X), arg_P);

	double V = (*r1).V + arg_X * ((*r2).V - (*r1).V);

	delete r1;
	delete r2;

	return V;
}

/* Enthalpy (J.kg-1), function of pressure (Pa) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::H_PX(double arg_P, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(T_PX(arg_P, arg_X), arg_P);
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(T_PX(arg_P, arg_X), arg_P);

	double H = (*r1).H + arg_X * ((*r2).H - (*r1).H);

	delete r1;
	delete r2;

	return H;
}

/* Entropy (J.kg-1.K-1), function of pressure (Pa) and steam quality (kg.kg-1) */
double iesoH2OFluidRegion4::S_PX(double arg_P, double arg_X) {

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(T_PX(arg_P, arg_X), arg_P);
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(T_PX(arg_P, arg_X), arg_P);

	double S = (*r1).S + arg_X * ((*r2).S - (*r1).S);

	delete r1;
	delete r2;

	return S;
}

/* Constructor */
iesoH2OFluidRegionIndex::iesoH2OFluidRegionIndex() {
}

/* Region index, function of temperature (K) and pressure (Pa) */
unsigned int iesoH2OFluidRegionIndex::R_TP(double arg_T, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */
	double T = arg_T; /* K to K */

	double Psat, P273, P623;
	unsigned int region = 0;

	if ((T >= 273.15) && (T <= 1073.15)) {

		iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();

		Psat = (*r4).P_TX(arg_T, 0.0);
		P273 = (*r4).P_TX(273.15, 0.0);
		P623 = (*r4).P_TX(623.15, 0.0);

		delete r4;

		Psat /= 1e6; /* Pa to MPa */
		P273 /= 1e6; /* Pa to MPa */
		P623 /= 1e6; /* Pa to MPa */

		if ((P >= P273) && (P <= 100.0)) {

			if (T <= 623.15) {

				if (P >= Psat)
					region = 1;
				else
					region = 2;
			} else {

				if (P <= P623) {

					region = 2;
				} else {

					const double n[6] = { 0, 0.34805185628969e3,
							-0.11671859879975e1, 0.10192970039326e-2,
							0.57254459862746e3, 0.1391883977870e2 };

					double T_Boundary23 = n[4] + pow((P - n[5]) / n[3], 0.5);

					if (T >= T_Boundary23)
						region = 2;
					else
						region = 3;
				}
			}
		}
	}

	return region;
}

/* Region index, function of enthalpy (J.kg-1) and pressure (Pa) */
unsigned int iesoH2OFluidRegionIndex::R_HP(double arg_H, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1();
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2();

	double H273_1, H623_1, H623_2, H1073_2, HLIQ, HVAP;

	double P273, P623;
	unsigned int region = 0;

	iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();

	P273 = (*r4).P_TX(273.15, 0.0);
	P623 = (*r4).P_TX(623.15, 0.0);

	P273 /= 1e6; /* Pa to MPa */
	P623 /= 1e6; /* Pa to MPa */

	if ((P >= P273) && (P <= 100.0)) {

		(*r1).Calculate(273.15, arg_P);
		H273_1 = (*r1).H;

		(*r1).Calculate(623.15, arg_P);
		H623_1 = (*r1).H;

		(*r2).Calculate(623.15, arg_P);
		H623_2 = (*r2).H;

		(*r2).Calculate(1073.15, arg_P);
		H1073_2 = (*r2).H;

		if (P <= P623) {

			if ((arg_H >= H273_1) && (arg_H <= H623_2)) {

				HLIQ = (*r4).H_PX(arg_P, 0.0);
				HVAP = (*r4).H_PX(arg_P, 1.0);

				if (arg_H < HLIQ)
					region = 1;
				else if (arg_H > HVAP)
					region = 2;
				else
					region = 4;
			} else if ((arg_H >= H623_2) && (arg_H <= H1073_2)) {

				region = 2;
			}
		} else {

			const double n[6] = { 0, 0.34805185628969e3, -0.11671859879975e1,
					0.10192970039326e-2, 0.57254459862746e3, 0.1391883977870e2 };

			double T_Boundary23 = n[4] + pow((P - n[5]) / n[3], 0.5);

			(*r2).Calculate(T_Boundary23, arg_P);
			double H_Boundary23_2 = (*r2).H;

			if ((arg_H >= H273_1) && (arg_H <= H1073_2)) {

				if (arg_H <= H623_1)
					region = 1;
				else if (arg_H >= H_Boundary23_2)
					region = 2;
				else
					region = 3;
			}
		}
	}

	delete r1;
	delete r2;
	delete r4;

	return region;
}

/* Region index, function of entropy (J.kg-1.K-1) and pressure (Pa) */
unsigned int iesoH2OFluidRegionIndex::R_SP(double arg_S, double arg_P) {

	double P = arg_P / 1e6; /* Pa to MPa */

	iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1();
	iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2();

	double S273_1, S623_1, S623_2, S1073_2, SLIQ, SVAP;

	double P273, P623;
	unsigned int region = 0;

	iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();

	P273 = (*r4).P_TX(273.15, 0.0);
	P623 = (*r4).P_TX(623.15, 0.0);

	P273 /= 1e6; /* Pa to MPa */
	P623 /= 1e6; /* Pa to MPa */

	if ((P >= P273) && (P <= 100.0)) {

		(*r1).Calculate(273.15, arg_P);
		S273_1 = (*r1).S;

		(*r1).Calculate(623.15, arg_P);
		S623_1 = (*r1).S;

		(*r2).Calculate(623.15, arg_P);
		S623_2 = (*r2).S;

		(*r2).Calculate(1073.15, arg_P);
		S1073_2 = (*r2).S;

		if (P <= P623) {

			if ((arg_S >= S273_1) && (arg_S <= S623_2)) {

				SLIQ = (*r4).S_PX(arg_P, 0.0);
				SVAP = (*r4).S_PX(arg_P, 1.0);

				if (arg_S < SLIQ)
					region = 1;
				else if (arg_S > SVAP)
					region = 2;
				else
					region = 4;
			} else if ((arg_S >= S623_2) && (arg_S <= S1073_2)) {

				region = 2;
			}
		} else {

			const double n[6] = { 0, 0.34805185628969e3, -0.11671859879975e1,
					0.10192970039326e-2, 0.57254459862746e3, 0.1391883977870e2 };

			double T_Boundary23 = n[4] + pow((P - n[5]) / n[3], 0.5);

			(*r2).Calculate(T_Boundary23, arg_P);
			double H_Boundary23_2 = (*r2).S;

			if ((arg_S >= S273_1) && (arg_S <= S1073_2)) {

				if (arg_S <= S623_1)
					region = 1;
				else if (arg_S >= H_Boundary23_2)
					region = 2;
				else
					region = 3;
			}
		}
	}

	delete r1;
	delete r2;
	delete r4;

	return region;
}

/* Constructor */
iesoH2OPt::iesoH2OPt() {

	/* Temperature (K) */
	T = 25.0 + 273.15;

	/* Pressure (Pa) */
	P = 1.0 * 1e+5;

	/* Fraction of steam (kg.kg-1) */
	X = -1.0;

	/* Volume (m3.kg-1) */
	V = 1.0;

	/* Enthalpy (J.kg-1) */
	H = 0.0;

	/* Entropy (J.kg-1.K-1) */
	S = 0.0;

	/* Exergy (J.kg-1) */
	E = 0.0;

	/* Mass flow rate (kg.s-1) */
	F = 1.0;

	/* Environment temperature (K) */
	_T0_ = 25.0 + 273.15;
}

/* Calculate */
bool iesoH2OPt::Calculate(string arg_O) {

	if (arg_O == "T, P") {

		return Calculate(0);
	} else if (arg_O == "H, P") {

		return Calculate(1);
	} else if (arg_O == "S, P") {

		return Calculate(2);
	} else if (arg_O == "T, X") {

		return Calculate(3);
	} else if (arg_O == "P, X") {

		return Calculate(4);
	} else {

		return false;
	}
}

/* Calculate */
bool iesoH2OPt::Calculate(unsigned int arg_O) {

	switch (arg_O) {

	case 0:
		/* Set T and P */
		return _TP_(T, P);
		break;
	case 1:
		/* Set H and P */
		return _HP_(H, P);
		break;
	case 2:
		/* Set S and P */
		return _SP_(S, P);
		break;
	case 3:
		/* Set T and X */
		return _TX_(T, X);
		break;
	case 4:
		/* Set P and X */
		return _PX_(P, X);
		break;
	default:
		/* Error */
		return false;
		break;
	}
}

/* Set T and P */
bool iesoH2OPt::_TP_(double arg_T, double arg_P) {

	bool output = false;

	/* === === === */

	/* Temperature (K) */
	T = arg_T;

	/* Pressure (Pa) */
	P = arg_P;

	/* === === === */

	iesoH2OFluidRegionIndex *r = new iesoH2OFluidRegionIndex();

	unsigned int region = (*r).R_TP(T, P);

	if (region == 1) {

		/* Fraction of steam (kg.kg-1) */
		X = -1.0;

		iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1(T, P);

		/* Volume (m3.kg-1) */
		V = (*r1).V;

		/* Enthalpy (J.kg-1) */
		H = (*r1).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r1).S;

		delete r1;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	} else if (region == 2) {

		/* Fraction of steam (kg.kg-1) */
		X = +2.0;

		iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2(T, P);

		/* Volume (m3.kg-1) */
		V = (*r2).V;

		/* Enthalpy (J.kg-1) */
		H = (*r2).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r2).S;

		delete r2;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	}

	delete r;

	/* === === === */

	return output;
}

/* Set H and P */
bool iesoH2OPt::_HP_(double arg_H, double arg_P) {

	bool output = false;

	/* === === === */

	/* Enthalpy (J.kg-1) */
	H = arg_H;

	/* Pressure (Pa) */
	P = arg_P;

	/* === === === */

	iesoH2OFluidRegionIndex *r = new iesoH2OFluidRegionIndex();

	unsigned int region = (*r).R_HP(H, P);

	if (region == 1) {

		/* Fraction of steam (kg.kg-1) */
		X = -1.0;

		iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1();

		/* Temperature (K) */
		T = (*r1).T_HP(H, P);

		/* Calculate region */
		(*r1).Calculate(T, P);

		/* Volume (m3.kg-1) */
		V = (*r1).V;

		/* Enthalpy (J.kg-1) */
		H = (*r1).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r1).S;

		delete r1;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	} else if (region == 2) {

		/* Fraction of steam (kg.kg-1) */
		X = +2.0;

		iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2();

		/* Temperature (K) */
		T = (*r2).T_HP(H, P);

		/* Calculate region */
		(*r2).Calculate(T, P);

		/* Volume (m3.kg-1) */
		V = (*r2).V;

		/* Enthalpy (J.kg-1) */
		H = (*r2).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r2).S;

		delete r2;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	} else if (region == 4) {

		iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();
		iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1((*r4).T_PX(P, 0), P);
		iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2((*r4).T_PX(P, 0), P);

		/* Fraction of steam (kg.kg-1) */
		X = (H - (*r1).H) / ((*r2).H - (*r1).H);

		/* other properties */
		output = _PX_(P, X);

		delete r4;
		delete r1;
		delete r2;
	}

	delete r;

	/* === === === */

	return output;
}

/* Set S and P */
bool iesoH2OPt::_SP_(double arg_S, double arg_P) {

	bool output = false;

	/* === === === */

	/* Entropy (J.kg-1.K-1) */
	S = arg_S;

	/* Pressure (Pa) */
	P = arg_P;

	/* === === === */

	iesoH2OFluidRegionIndex *r = new iesoH2OFluidRegionIndex();

	unsigned int region = (*r).R_SP(S, P);

	if (region == 1) {

		/* Fraction of steam (kg.kg-1) */
		X = -1.0;

		iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1();

		/* Temperature (K) */
		T = (*r1).T_SP(S, P);

		/* Calculate region */
		(*r1).Calculate(T, P);

		/* Volume (m3.kg-1) */
		V = (*r1).V;

		/* Enthalpy (J.kg-1) */
		H = (*r1).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r1).S;

		delete r1;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	} else if (region == 2) {

		/* Fraction of steam (kg.kg-1) */
		X = +2.0;

		iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2();

		/* Temperature (K) */
		T = (*r2).T_SP(S, P);

		/* Calculate region */
		(*r2).Calculate(T, P);

		/* Volume (m3.kg-1) */
		V = (*r2).V;

		/* Enthalpy (J.kg-1) */
		H = (*r2).H;

		/* Entropy (J.kg-1.K-1) */
		S = (*r2).S;

		delete r2;

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		output = true;
	} else if (region == 4) {

		iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();
		iesoH2OFluidRegion1 *r1 = new iesoH2OFluidRegion1((*r4).T_PX(P, 0), P);
		iesoH2OFluidRegion2 *r2 = new iesoH2OFluidRegion2((*r4).T_PX(P, 0), P);

		/* Fraction of steam (kg.kg-1) */
		X = (S - (*r1).S) / ((*r2).S - (*r1).S);

		/* other properties */
		output = _PX_(P, X);

		delete r4;
		delete r1;
		delete r2;
	}

	delete r;

	/* === === === */

	return output;
}

/* Set T and X */
bool iesoH2OPt::_TX_(double arg_T, double arg_X) {

	bool output = false;

	/* === === === */

	/* Temperature (K) */
	T = arg_T;

	/* Fraction of steam (kg.kg-1) */
	X = arg_X;

	/* === === === */

	if (((T >= 273.15) && (T <= 623.15)) && ((X >= 0.0) && (X <= 1.0))) {

		iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();

		/* Pressure (Pa) */
		P = (*r4).P_TX(T, X);

		/* Volume (m3.kg-1) */
		V = (*r4).V_TX(T, X);

		/* Enthalpy (J.kg-1) */
		H = (*r4).H_TX(T, X);

		/* Entropy (J.kg-1.K-1) */
		S = (*r4).S_TX(T, X);

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		delete r4;

		output = true;
	}

	/* === === === */

	return output;
}

/* Set P and X */
bool iesoH2OPt::_PX_(double arg_P, double arg_X) {

	bool output = false;

	/* === === === */

	/* Pressure (Pa) */
	P = arg_P;

	/* Fraction of steam (kg.kg-1) */
	X = arg_X;

	/* === === === */

	if (((P >= 611.213) && (P <= 1.65292 * 1.0e+7))
			&& ((X >= 0.0) && (X <= 1.0))) {

		iesoH2OFluidRegion4 *r4 = new iesoH2OFluidRegion4();

		/* Temperature (K) */
		T = (*r4).T_PX(P, X);

		/* Volume (m3.kg-1) */
		V = (*r4).V_PX(P, X);

		/* Enthalpy (J.kg-1) */
		H = (*r4).H_PX(P, X);

		/* Entropy (J.kg-1.K-1) */
		S = (*r4).S_PX(P, X);

		/* Exergy (J.kg-1) */
		E = H - _T0_ * S;

		delete r4;

		output = true;
	}

	/* === === === */

	return output;
}

/* Copy */
void iesoH2OPt::Copy(iesoH2OPt arg_Pt) {

	/* Temperature (K) */
	T = arg_Pt.T;

	/* Pressure (Pa) */
	P = arg_Pt.P;

	/* Fraction of steam (kg.kg-1) */
	X = arg_Pt.X;

	/* Volume (m3.kg-1) */
	V = arg_Pt.V;

	/* Enthalpy (J.kg-1) */
	H = arg_Pt.H;

	/* Entropy (J.kg-1.K-1) */
	S = arg_Pt.S;

	/* Exergy (J.kg-1) */
	E = arg_Pt.E;

	/* Mass flow rate (kg.s-1) */
	F = arg_Pt.F;
}

/* Snap */
void iesoH2OPt::Snap() {

	cout << endl;

	/* Temperature */
	cout << "T (Temperature, C) = " << T - 273.15 << endl;

	/* Pressure */
	cout << "P (Pressure, bar) = " << P * 1.0e-5 << endl;

	/* Fraction of steam */
	cout << "X (Fraction of steam, %) = " << X * 1.0e+2 << endl;

	/* Volume */
	cout << "V (Volume, m3.kg-1) = " << V << endl;

	/* Enthalpy */
	cout << "H (Enthalpy, kJ.kg-1) = " << H * 1.0e-3 << endl;

	/* Entropy */
	cout << "S (Entropy, kJ.kg-1.K-1) = " << S * 1.0e-3 << endl;

	/* Exergy */
	cout << "E (Exergy, kJ.kg-1) = " << E * 1.0e-3 << endl;

	/* Mass flow rate */
	cout << "F (Mass flow rate, kg.s-1) = " << F << endl;
}

/* Constructor */
iesoH2OComex::iesoH2OComex() {

	/* Compression ratio (%) */
	R = 1.0;

	/* Isentropic efficiency (%) */
	I = 1.0;
}

/* Constructor. arg_R: compression ratio (%). arg_I: isentropic efficiency (%). */
iesoH2OComex::iesoH2OComex(double arg_R, double arg_I) {

	/* Compression ratio (%) */
	R = arg_R;

	/* Isentropic efficiency (%) */
	I = arg_I;
}

/* Calculate */
bool iesoH2OComex::Calculate() {

	bool output = false;

	/* --- */

	Outlet.Copy(Inlet);

	/* --- */

	Outlet.P *= R;
	if (Outlet.Calculate(2)) { // = Calculate("S, P")
		if (R <= 1.0) {
			Outlet.H = Inlet.H + (1.0 * I) * (Outlet.H - Inlet.H);
		} else {
			Outlet.H = Inlet.H + (1.0 / I) * (Outlet.H - Inlet.H);
		}
		if (Outlet.Calculate(1)) { // = Calculate("H, P")
			output = true;
		}
	}

	/* --- */

	return output;
}
