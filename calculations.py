"""
calculations.py

Core structural engineering module for calculating the Total Wall Horizontal 
Bending Capacity (Mh) of unreinforced masonry walls in kNm.

Methods Implemented:
1. AS 3700:2011 (Australian Masonry Structures Standard)
2. Griffith & Vaculik (Proportional Line vs. Stepped Failure Analysis)
3. Willis et al. (Combined Bed Joint Torque and Unit Moment Capacity)

Units Convention:
- Dimensional inputs: millimeters (mm)
- Stress inputs: Megapascals (MPa or N/mm^2)
- Intermediate moment calculations: N-mm (or N-mm/m)
- Returned final capacities: kilonewton-meters (kNm)
"""

import math
from typing import Dict, Union, Any, Optional

# Constant for converting N-mm to kNm (divide by 1,000,000)
NMM_TO_KNM: float = 1e-6

# Geometrical correction factor for bed joint torsion (Kb)
KB_FACTOR: float = 0.214


def compute_section_modulus_per_m(tu: float) -> float:
    """
    Calculates the elastic section modulus per meter of wall height/length (Zd).

    Args:
        tu: Thickness of masonry unit / wall thickness (mm).

    Returns:
        Zd in mm^3 per meter.
    """
    return (1000.0 * (tu ** 2)) / 6.0


def compute_bed_joint_shear(Ftn: float, fd: float) -> float:
    """
    Calculates the ultimate shear stress capacity of the bed joint (Taub).

    Args:
        Ftn: Flexural tensile strength perpendicular to bed joint (MPa).
        fd: Design vertical compressive stress (MPa).

    Returns:
        Taub in MPa (N/mm^2).
    """
    return (1.6 * Ftn) + (0.9 * fd)


def calculate_as3700(
    Hwall: float,
    Sp: float,
    tu: float,
    hu: float,
    Fbtm: float,
    Ftn: float,
    fd: float,
    Zd: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculates Total Wall Horizontal Bending Capacity per AS 3700:2011.

    Args:
        Hwall: Total wall height (mm).
        Sp: Minimum overlap of masonry units in successive courses (mm).
        tu: Thickness of masonry unit (mm).
        hu: Height of masonry unit (mm).
        Fbtm: Tensile strength / modulus of rupture of masonry unit (MPa).
        Ftn: Flexural tensile strength perpendicular to bed joint (MPa).
        fd: Vertical compressive stress (MPa).
        Zd: Optional pre-calculated section modulus per meter (mm^3/m).

    Returns:
        Dictionary containing total capacity in kNm, per-meter capacity in kNm/m,
        the perpend spacing factor (Kp), and individual equation results in kNm/m.
    """
    if Zd is None:
        Zd = compute_section_modulus_per_m(tu)

    # Perpend spacing factor (Kp)
    Kp = min(Sp / tu, Sp / hu, 1.0)

    # Guard against division by zero if Ftn is set to 0.0
    if Ftn <= 0.0:
        Mh1_per_m = 0.0
        Mh2_per_m = 0.0
    else:
        sqrt_Ftn = math.sqrt(Ftn)
        Mh1_per_m = 2.0 * Kp * sqrt_Ftn * (1.0 + (fd / Ftn)) * Zd
        Mh2_per_m = 4.0 * Kp * sqrt_Ftn * Zd

    Mh3_per_m = (0.44 * Fbtm * Zd) + (0.56 * Ftn * Zd)

    # Governing capacity per meter (N-mm/m)
    Mh_per_m_nmm = min(Mh1_per_m, Mh2_per_m, Mh3_per_m)

    # Scale to total wall height (N-mm) and convert to kNm
    wall_height_m = Hwall / 1000.0
    Mh_total_knm = (Mh_per_m_nmm * wall_height_m) * NMM_TO_KNM

    return {
        "Mh_AS3700_total_kNm": Mh_total_knm,
        "Mh_AS3700_per_m_kNm": Mh_per_m_nmm * NMM_TO_KNM,
        "Kp": Kp,
        "Mh1_per_m_kNm": Mh1_per_m * NMM_TO_KNM,
        "Mh2_per_m_kNm": Mh2_per_m * NMM_TO_KNM,
        "Mh3_per_m_kNm": Mh3_per_m * NMM_TO_KNM,
    }


def calculate_griffith_vaculik(
    Hwall: float,
    tu: float,
    hu: float,
    lu: float,
    tj: float,
    Fbtm: float,
    Ftn: float,
    fd: float,
    nu_poisson: float,
    Taub: Optional[float] = None,
    Kb: float = KB_FACTOR,
) -> Dict[str, Union[float, str]]:
    """
    Calculates Total Wall Horizontal Bending Capacity per Griffith & Vaculik.

    Evaluates both Line Failure (cracking through units and perpend joints) 
    and Stepped Failure (cracking along bed and perpend joints) and identifies
    the governing failure mode.

    Args:
        Hwall: Total wall height (mm).
        tu: Thickness of masonry unit (mm).
        hu: Height of masonry unit (mm).
        lu: Length of masonry unit (mm).
        tj: Thickness of mortar joint (mm).
        Fbtm: Tensile strength / modulus of rupture of masonry unit (MPa).
        Ftn: Flexural tensile strength perpendicular to bed joint (MPa).
        fd: Vertical compressive stress (MPa).
        nu_poisson: Poisson's ratio of the masonry unit (unitless).
        Taub: Optional pre-calculated ultimate bed joint shear stress (MPa).
        Kb: Geometrical correction factor (default = 0.214).

    Returns:
        Dictionary containing total capacity in kNm, governing failure mode 
        ("Line" or "Stepped"), and line/stepped capacities.
    """
    if Taub is None:
        Taub = compute_bed_joint_shear(Ftn, fd)

    course_height = hu + tj
    unit_moment_modulus = (hu * (tu ** 2)) / 6.0

    # Line Failure per meter (N-mm/m)
    Mh_line_per_m_nmm = (
        (1.0 / (2.0 * course_height))
        * ((Fbtm - (nu_poisson * fd)) * unit_moment_modulus)
        * 1000.0
    )

    # Stepped Failure per meter (N-mm/m)
    Mh_stepped_per_m_nmm = (
        (1.0 / course_height)
        * (Taub * Kb * 0.5 * (lu + tj) * (tu ** 2))
        * 1000.0
    )

    # Determine governing failure mode
    if Mh_line_per_m_nmm <= Mh_stepped_per_m_nmm:
        Mh_governing_per_m_nmm = Mh_line_per_m_nmm
        governing_mode = "Line"
    else:
        Mh_governing_per_m_nmm = Mh_stepped_per_m_nmm
        governing_mode = "Stepped"

    # Scale to total wall height (N-mm) and convert to kNm
    wall_height_m = Hwall / 1000.0
    Mh_total_knm = (Mh_governing_per_m_nmm * wall_height_m) * NMM_TO_KNM

    return {
        "Mh_Griffith_total_kNm": Mh_total_knm,
        "Griffith_governing_mode": governing_mode,
        "Mh_line_per_m_kNm": Mh_line_per_m_nmm * NMM_TO_KNM,
        "Mh_stepped_per_m_kNm": Mh_stepped_per_m_nmm * NMM_TO_KNM,
        "Mh_line_total_kNm": (Mh_line_per_m_nmm * wall_height_m) * NMM_TO_KNM,
        "Mh_stepped_total_kNm": (Mh_stepped_per_m_nmm * wall_height_m) * NMM_TO_KNM,
    }


def calculate_willis(
    Hwall: float,
    tu: float,
    hu: float,
    lu: float,
    tj: float,
    Fbtm: float,
    Ftn: float,
    fd: float,
    nu_poisson: float,
    Taub: Optional[float] = None,
    Kb: float = KB_FACTOR,
) -> Dict[str, float]:
    """
    Calculates Total Wall Horizontal Bending Capacity per Willis et al.

    Directly computes the total capacity across the full wall height by summing
    the torsional resistance of bed joints and flexural resistance of brick units.

    Args:
        Hwall: Total wall height (mm).
        tu: Thickness of masonry unit (mm).
        hu: Height of masonry unit (mm).
        lu: Length of masonry unit (mm).
        tj: Thickness of mortar joint (mm).
        Fbtm: Tensile strength / modulus of rupture of masonry unit (MPa).
        Ftn: Flexural tensile strength perpendicular to bed joint (MPa).
        fd: Vertical compressive stress (MPa).
        nu_poisson: Poisson's ratio of the masonry unit (unitless).
        Taub: Optional pre-calculated ultimate bed joint shear stress (MPa).
        Kb: Geometrical correction factor (default = 0.214).

    Returns:
        Dictionary containing total capacity in kNm and intermediate parameters.
    """
    if Taub is None:
        Taub = compute_bed_joint_shear(Ftn, fd)

    course_height = hu + tj

    # Number of bed joints (nb) and masonry units (nu) in the failure plane
    nb = Hwall / course_height
    nu = Hwall / (2.0 * course_height)

    # Torque developed by a single bed joint (N-mm)
    Tb = Taub * Kb * 0.5 * (lu + tj) * (tu ** 2)

    # Moment capacity of a single masonry unit (N-mm)
    Mu = (Fbtm - (nu_poisson * fd)) * ((hu * (tu ** 2)) / 6.0)

    # Total Wall Capacity (N-mm) converted to kNm
    Mh_total_nmm = (nb * Tb) + (nu * Mu)
    Mh_total_knm = Mh_total_nmm * NMM_TO_KNM

    return {
        "Mh_Willis_total_kNm": Mh_total_knm,
        "nb": nb,
        "nu": nu,
        "Tb_kNm": Tb * NMM_TO_KNM,
        "Mu_kNm": Mu * NMM_TO_KNM,
    }


def calculate_all_methods(
    inputs: Optional[Dict[str, float]] = None,
    *,
    Hwall: Optional[float] = None,
    Sp: Optional[float] = None,
    tu: Optional[float] = None,
    hu: Optional[float] = None,
    lu: Optional[float] = None,
    tj: Optional[float] = None,
    Fbtm: Optional[float] = None,
    Ftn: Optional[float] = None,
    fd: Optional[float] = None,
    nu_poisson: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Master calculation function that evaluates Total Wall Horizontal Bending 
    Capacity (Mh) in kNm across all three methods (AS 3700:2011, Griffith & Vaculik, 
    and Willis et al.).

    Supports passing parameters either as a single dictionary (`inputs`) OR as 
    explicit keyword arguments.

    Args:
        inputs: Optional dictionary containing the 10 engineering parameters.
        Hwall: Total Wall Height (mm).
        Sp: Min overlap of masonry unit in successive courses (mm).
        tu: Thickness of masonry unit / wall thickness (mm).
        hu: Height of masonry unit (mm).
        lu: Length of masonry unit (mm).
        tj: Thickness of mortar joint (mm).
        Fbtm: Tensile strength / modulus of rupture of masonry unit (MPa).
        Ftn: Flexural tensile strength perpendicular to bed joint (MPa).
        fd: Vertical compressive stress (MPa).
        nu_poisson: Poisson's ratio of the masonry unit (unitless).

    Returns:
        Dictionary containing the total capacities (in kNm) for all 3 methods,
        the governing failure mode for Griffith & Vaculik, and detailed breakdowns.
    """
    # Consolidate inputs from dictionary or explicit arguments
    params: Dict[str, Optional[float]] = {
        "Hwall": Hwall,
        "Sp": Sp,
        "tu": tu,
        "hu": hu,
        "lu": lu,
        "tj": tj,
        "Fbtm": Fbtm,
        "Ftn": Ftn,
        "fd": fd,
        "nu_poisson": nu_poisson,
    }

    if inputs is not None:
        for key in params:
            if key in inputs and inputs[key] is not None:
                params[key] = float(inputs[key])

    # Validate that all required parameters are present
    missing_keys = [k for k, v in params.items() if v is None]
    if missing_keys:
        raise ValueError(f"Missing required engineering parameters: {', '.join(missing_keys)}")

    # Unpack validated float values
    p_Hwall = float(params["Hwall"])  # type: ignore
    p_Sp = float(params["Sp"])        # type: ignore
    p_tu = float(params["tu"])        # type: ignore
    p_hu = float(params["hu"])        # type: ignore
    p_lu = float(params["lu"])        # type: ignore
    p_tj = float(params["tj"])        # type: ignore
    p_Fbtm = float(params["Fbtm"])    # type: ignore
    p_Ftn = float(params["Ftn"])      # type: ignore
    p_fd = float(params["fd"])        # type: ignore
    p_nu = float(params["nu_poisson"])  # type: ignore

    # Basic dimensional sanity checks
    if any(val <= 0 for val in (p_Hwall, p_tu, p_hu, p_lu)):
        raise ValueError("Wall and masonry unit dimensions (Hwall, tu, hu, lu) must be strictly positive.")
    if p_tj < 0 or p_Sp < 0:
        raise ValueError("Mortar joint thickness (tj) and overlap (Sp) cannot be negative.")

    # Compute shared helper properties
    Zd = compute_section_modulus_per_m(p_tu)
    Taub = compute_bed_joint_shear(p_Ftn, p_fd)

    # Execute the three methods
    as3700_res = calculate_as3700(
        Hwall=p_Hwall, Sp=p_Sp, tu=p_tu, hu=p_hu, Fbtm=p_Fbtm, Ftn=p_Ftn, fd=p_fd, Zd=Zd
    )

    griffith_res = calculate_griffith_vaculik(
        Hwall=p_Hwall,
        tu=p_tu,
        hu=p_hu,
        lu=p_lu,
        tj=p_tj,
        Fbtm=p_Fbtm,
        Ftn=p_Ftn,
        fd=p_fd,
        nu_poisson=p_nu,
        Taub=Taub,
        Kb=KB_FACTOR,
    )

    willis_res = calculate_willis(
        Hwall=p_Hwall,
        tu=p_tu,
        hu=p_hu,
        lu=p_lu,
        tj=p_tj,
        Fbtm=p_Fbtm,
        Ftn=p_Ftn,
        fd=p_fd,
        nu_poisson=p_nu,
        Taub=Taub,
        Kb=KB_FACTOR,
    )

    return {
        # Primary summary outputs (in kNm)
        "Mh_AS3700_total": as3700_res["Mh_AS3700_total_kNm"],
        "Mh_Griffith_total": griffith_res["Mh_Griffith_total_kNm"],
        "Griffith_governing_mode": griffith_res["Griffith_governing_mode"],
        "Mh_Willis_total": willis_res["Mh_Willis_total_kNm"],
        # Shared helper parameters
        "helpers": {
            "Zd_mm3_per_m": Zd,
            "Taub_MPa": Taub,
            "Kb": KB_FACTOR,
        },
        # Detailed method breakdowns
        "details": {
            "AS3700": as3700_res,
            "Griffith_Vaculik": griffith_res,
            "Willis": willis_res,
        },
    }

# --- QUICK TEST BLOCK ---
if __name__ == "__main__":
    test_inputs = {
        "Hwall": 3000,      # 3m wall height
        "Sp": 115,          # overlap
        "tu": 110,          # brick thickness
        "hu": 76,           # brick height
        "lu": 230,          # brick length
        "tj": 10,           # mortar thickness
        "Fbtm": 1.5,        # brick tensile strength
        "Ftn": 0.2,         # bed joint tensile strength
        "fd": 0.5,          # vertical compression
        "nu_poisson": 0.2   # Poisson's ratio
    }
    
    try:
        results = calculate_all_methods(test_inputs)
        print("✅ Backend Engine is Working!")
        print(f"AS 3700:      {results['Mh_AS3700_total']:.2f} kNm")
        print(f"Willis:       {results['Mh_Willis_total']:.2f} kNm")
        print(f"Griffith:     {results['Mh_Griffith_total']:.2f} kNm")
        print(f"Failure Mode: {results['Griffith_governing_mode']}")
    except Exception as e:
        print(f"❌ Error: {e}")