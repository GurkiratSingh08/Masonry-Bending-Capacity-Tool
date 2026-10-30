import numpy as np
import pandas as pd

"""
app.py - Streamlit UI/UX Application for Unreinforced Masonry (URM) Horizontal
Bending Capacity (Mh) Evaluation (AS 3700:2011, Griffith & Vaculik, Willis et al.)
"""

from typing import Dict, Any
import streamlit as st
import plotly.graph_objects as go
from calculations import calculate_all_methods

# ==============================================================================
# 1. PAGE CONFIGURATION & BENCHMARK DEFAULTS
# ==============================================================================
st.set_page_config(
    page_title="URM Horizontal Bending Capacity (Mh)",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULTS: Dict[str, float] = {
    "Hwall": 3000.0, "lu": 230.0, "hu": 76.0, "tu": 110.0, "tj": 10.0,
    "Sp": 115.0, "Fbtm": 1.5, "Ftn": 0.20, "fd": 0.50, "nu_poisson": 0.20,
}


def init_session_state() -> None:
    """Initializes default engineering parameters in Streamlit session state."""
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_to_defaults() -> None:
    """Callback to reset all sidebar input widgets to benchmark defaults."""
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


# ==============================================================================
# 2. CUSTOM CSS STYLING
# ==============================================================================
def inject_custom_css() -> None:
    """Injects custom CSS for executive KPI cards, badges, and typography."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #ffffff, #f8fafc);
            border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px;
            box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05);
        }
        @media (prefers-color-scheme: dark) {
            div[data-testid="stMetric"] {
                background: linear-gradient(145deg, #1e293b, #0f172a);
                border: 1px solid #334155;
            }
        }
        .mode-card {
            border-radius: 12px; padding: 14px 18px; border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05); height: 100%;
        }
        .mode-card-line {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(249, 115, 22, 0.04));
            border-left: 5px solid #ef4444;
        }
        .mode-card-stepped {
            background: linear-gradient(135deg, rgba(13, 148, 136, 0.08), rgba(59, 130, 246, 0.04));
            border-left: 5px solid #0d9488;
        }
        .badge {
            display: inline-block; padding: 4px 12px; border-radius: 9999px;
            font-size: 0.80rem; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;
        }
        .badge-line { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-stepped { background-color: #ccfbf1; color: #0f766e; border: 1px solid #5eead4; }
        .helper-box {
            background-color: rgba(148, 163, 184, 0.1);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 8px; padding: 10px 14px; text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 3. SIDEBAR INPUT CONTROLS
# ==============================================================================
def render_sidebar() -> Dict[str, float]:
    """Renders grouped sidebar inputs and returns the 10-key float dictionary."""
    with st.sidebar:
        st.title("🧱 URM Parameters")
        st.caption("Configure geometric and mechanical properties for $M_h$ analysis.")
        st.button("🔄 Reset to Default Benchmark", on_click=reset_to_defaults, use_container_width=True)

        with st.expander("📐 Wall & Unit Geometry (mm)", expanded=True):
            Hwall = st.number_input("Total Wall Height (Hwall)", min_value=500.0, max_value=10000.0, step=100.0, key="Hwall")
            lu = st.number_input("Unit Length (lu)", min_value=50.0, max_value=600.0, step=5.0, key="lu")
            hu = st.number_input("Unit Height (hu)", min_value=30.0, max_value=400.0, step=2.0, key="hu")
            tu = st.number_input("Unit / Wall Thickness (tu)", min_value=50.0, max_value=500.0, step=5.0, key="tu")
            tj = st.number_input("Mortar Joint Thickness (tj)", min_value=2.0, max_value=30.0, step=1.0, key="tj")
            Sp = st.number_input("Perpend Overlap (Sp)", min_value=10.0, max_value=300.0, step=5.0, key="Sp")

        with st.expander("🧪 Material & Stress Parameters", expanded=True):
            Fbtm = st.number_input("Brick Modulus of Rupture (Fbtm, MPa)", min_value=0.1, max_value=10.0, step=0.1, format="%.2f", key="Fbtm")
            Ftn = st.number_input("Flexural Tensile Strength of Bed Joint (Ftn, MPa)", min_value=0.05, max_value=3.0, step=0.05, format="%.2f", key="Ftn")
            fd = st.number_input("Vertical Compressive Stress (fd, MPa)", min_value=0.0, max_value=5.0, step=0.05, format="%.2f", key="fd")
            nu_poisson = st.number_input("Brick Poisson's Ratio (ν)", min_value=0.05, max_value=0.45, step=0.01, format="%.2f", key="nu_poisson")

    return {
        "Hwall": float(Hwall), "Sp": float(Sp), "tu": float(tu), "hu": float(hu), "lu": float(lu),
        "tj": float(tj), "Fbtm": float(Fbtm), "Ftn": float(Ftn), "fd": float(fd), "nu_poisson": float(nu_poisson),
    }


# ==============================================================================
# 4. PLOTLY VISUALIZATION BUILDERS
# ==============================================================================
def build_primary_comparison_chart(res: Dict[str, Any]) -> go.Figure:
    """Creates a bar chart comparing Total Wall Capacity across the 3 methods."""
    methods = ["AS 3700:2011", "Griffith & Vaculik", "Willis et al."]
    values = [res["Mh_AS3700_total"], res["Mh_Griffith_total"], res["Mh_Willis_total"]]
    colors = ["#3b82f6", "#0d9488", "#6366f1"]

    fig = go.Figure(
        go.Bar(
            x=methods, y=values, text=[f"{v:.2f} kNm" for v in values], textposition="outside",
            marker=dict(color=colors, line=dict(width=1.5, color="#1e293b")), width=0.45,
        )
    )
    max_val = max(values) if max(values) > 0 else 1.0
    fig.update_layout(
        title="Total Wall Horizontal Bending Capacity (Mh)",
        yaxis_title="Total Capacity Mh (kNm)", yaxis=dict(range=[0, max_val * 1.22]),
        template="plotly_white", height=400, margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def build_submechanism_chart(res: Dict[str, Any], h_wall_m: float) -> go.Figure:
    """Creates a horizontal bar chart comparing sub-mechanisms and governing modes."""
    as_det = res["details"]["AS3700"]
    gv_det = res["details"]["Griffith_Vaculik"]

    mh1_tot = as_det["Mh1_per_m_kNm"] * h_wall_m
    mh2_tot = as_det["Mh2_per_m_kNm"] * h_wall_m
    mh3_tot = as_det["Mh3_per_m_kNm"] * h_wall_m
    as_gov = res["Mh_AS3700_total"]

    line_tot = gv_det["Mh_line_total_kNm"]
    step_tot = gv_det["Mh_stepped_total_kNm"]
    gv_mode = res["Griffith_governing_mode"]

    labels = ["AS 3700: Mh1", "AS 3700: Mh2", "AS 3700: Mh3", "Griffith: Line", "Griffith: Stepped"]
    vals = [mh1_tot, mh2_tot, mh3_tot, line_tot, step_tot]
    is_gov = [
        abs(mh1_tot - as_gov) < 1e-6, abs(mh2_tot - as_gov) < 1e-6, abs(mh3_tot - as_gov) < 1e-6,
        gv_mode == "Line", gv_mode == "Stepped",
    ]
    colors = ["#ef4444" if g else "#94a3b8" for g in is_gov]
    tags = [f"{v:.2f} kNm (Governing)" if g else f"{v:.2f} kNm" for v, g in zip(vals, is_gov)]

    fig = go.Figure(
        go.Bar(
            x=vals, y=labels, orientation="h", text=tags, textposition="outside",
            marker=dict(color=colors, line=dict(width=1.2, color="#1e293b")),
        )
    )
    max_v = max(vals) if max(vals) > 0 else 1.0
    fig.update_layout(
        title="Sub-Mechanism Breakdown (AS 3700 vs. Griffith & Vaculik)",
        xaxis_title="Scaled Total Wall Capacity (kNm)", xaxis=dict(range=[0, max_v * 1.32]),
        yaxis=dict(autorange="reversed"), template="plotly_white", height=400,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig

# ==============================================================================
# 4B. PHASE 4: FAILURE MODE SWITCH & EXPORT
# ==============================================================================
SWEEP_CONFIG: Dict[str, Dict[str, Any]] = {
    "Fbtm": {
        "label": "Brick Modulus of Rupture (Fbtm)", "unit": "MPa", "min": 0.1, "max": 10.0,
        "reason": (
            "Increasing Fbtm directly elevates the flexural tensile resistance of the brick units (Line Failure) "
            "while leaving mortar bed joint torsional-shear resistance (Stepped Failure) unchanged. Once brick "
            "strength exceeds the bed joint torsional capacity, cracking bypasses the units and steps through the mortar."
        ),
    },
    "fd": {
        "label": "Vertical Compressive Stress (fd)", "unit": "MPa", "min": 0.0, "max": 5.0,
        "reason": (
            "Higher vertical precompression increases mortar bed joint frictional shear resistance (τb = 1.6·Ftn + 0.9·fd), "
            "rapidly strengthening Stepped Failure capacity. Simultaneously, Poisson lateral tension (−ν·fd) slightly reduces "
            "net brick flexural capacity, shifting the governing mechanism from Stepped Failure to Line Failure."
        ),
    },
    "Ftn": {
        "label": "Bed Joint Flexural Tensile Strength (Ftn)", "unit": "MPa", "min": 0.05, "max": 3.0,
        "reason": (
            "Increasing Ftn boosts the cohesive bond component of bed joint shear strength (τb), directly increasing "
            "torsional resistance against Stepped Failure. Because Line Failure depends solely on brick strength and "
            "vertical stress, higher Ftn forces the governing crack path to shift into the brick units (Line Failure)."
        ),
    },
    "lu": {
        "label": "Masonry Unit Length (lu)", "unit": "mm", "min": 50.0, "max": 600.0,
        "reason": (
            "Longer masonry units expand the bed joint overlap lever arm (lu + tj), proportionally increasing mortar joint "
            "torsional resistance (Stepped Failure). Because unit length does not alter individual brick flexural modulus "
            "(Line Failure), longer units drive the governing failure mode toward Line Failure."
        ),
    },
    "hu": {
        "label": "Masonry Unit Height (hu)", "unit": "mm", "min": 30.0, "max": 400.0,
        "reason": (
            "Taller units increase the brick section modulus ratio hu/(hu + tj), slightly raising Line Failure capacity. "
            "Conversely, taller units reduce the number of horizontal bed joints per meter of wall height, lowering "
            "cumulative bed joint torsional resistance and shifting the governing mechanism toward Stepped Failure."
        ),
    },
    "tj": {
        "label": "Mortar Joint Thickness (tj)", "unit": "mm", "min": 2.0, "max": 30.0,
        "reason": (
            "Increasing mortar joint thickness widens the torsional bed joint lever arm (lu + tj) in Stepped Failure "
            "while scaling course frequency 1/(hu + tj) equally for both modes. Consequently, thicker mortar joints "
            "marginally increase Stepped Failure capacity relative to Line Failure."
        ),
    },
}


def find_failure_mode_switch(inputs: Dict[str, float], param_key: str) -> Dict[str, Any]:
    """Sweeps param_key across 150 points and interpolates the exact Line/Stepped switch."""
    cfg = SWEEP_CONFIG[param_key]
    x_vals = np.linspace(cfg["min"], cfg["max"], 150)
    line_l, step_l, gv_l, as_l, wi_l = [], [], [], [], []

    for val in x_vals:
        res = calculate_all_methods({**inputs, param_key: float(val)})
        gv_d = res["details"]["Griffith_Vaculik"]
        line_l.append(gv_d["Mh_line_total_kNm"])
        step_l.append(gv_d["Mh_stepped_total_kNm"])
        gv_l.append(res["Mh_Griffith_total"])
        as_l.append(res["Mh_AS3700_total"])
        wi_l.append(res["Mh_Willis_total"])

    line_arr, step_arr = np.array(line_l), np.array(step_l)
    diff = line_arr - step_arr
    crossings = np.where(np.diff(np.sign(diff)) != 0)[0]

    sw_val, sw_mh = None, None
    if len(crossings) > 0:
        i = int(crossings[0])
        x0, x1, y0, y1 = x_vals[i], x_vals[i + 1], diff[i], diff[i + 1]
        sw_val = float(x0 - y0 * (x1 - x0) / (y1 - y0))
        sw_mh = float(line_arr[i] + (sw_val - x0) / (x1 - x0) * (line_arr[i + 1] - line_arr[i]))

    return {
        "x": x_vals, "Mh_line_total_kNm": line_arr, "Mh_stepped_total_kNm": step_arr,
        "Mh_Griffith_total": np.array(gv_l), "Mh_AS3700_total": np.array(as_l),
        "Mh_Willis_total": np.array(wi_l), "switch_value": sw_val, "switch_Mh_kNm": sw_mh,
    }


def render_phase4_tab(inputs: Dict[str, float], results: Dict[str, Any]) -> None:
    """Renders Tab 3: Failure mode switch analysis, transition plot, and CSV exports."""
    param_key = st.selectbox(
        "🔎 Select Design Parameter to Sweep for Failure Mode Transition:",
        options=list(SWEEP_CONFIG.keys()),
        format_func=lambda k: f"{SWEEP_CONFIG[k]['label']} [{SWEEP_CONFIG[k]['unit']}]",
    )
    cfg = SWEEP_CONFIG[param_key]
    unit = cfg["unit"]
    sweep = find_failure_mode_switch(inputs, param_key)

    cur_val = inputs[param_key]
    cur_mode = results["Griffith_governing_mode"]
    cur_mh = results["Mh_Griffith_total"]
    sw_val, sw_mh = sweep["switch_value"], sweep["switch_Mh_kNm"]
    target_mode = "Stepped" if cur_mode == "Line" else "Line"

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Current {param_key} & Mode", f"{cur_val:.2f} {unit}", f"Governing: {cur_mode} Failure", delta_color="off")
    if sw_val is not None and sw_mh is not None:
        m2.metric("Exact Switch Threshold", f"{sw_val:.3f} {unit}", f"Transition Mh: {sw_mh:.2f} kNm", delta_color="off")
        m3.metric(f"Required Change (Δ{param_key})", f"{sw_val - cur_val:+.3f} {unit}", f"Flips to {target_mode} Failure")
    else:
        m2.metric("Exact Switch Threshold", "No Switch in Range", f"Tested {cfg['min']}–{cfg['max']} {unit}", delta_color="off")
        m3.metric(f"Required Change (Δ{param_key})", "N/A", f"{cur_mode} governs across full range", delta_color="off")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sweep["x"], y=sweep["Mh_line_total_kNm"], name="Line Failure (Mh,line)", line=dict(color="#ef4444", width=2.5, dash="dash")))
    fig.add_trace(go.Scatter(x=sweep["x"], y=sweep["Mh_stepped_total_kNm"], name="Stepped Failure (Mh,step)", line=dict(color="#0d9488", width=2.5, dash="dash")))
    fig.add_trace(go.Scatter(x=sweep["x"], y=sweep["Mh_Griffith_total"], name="Governing Griffith Mh", line=dict(color="#1e293b", width=4)))
    fig.add_trace(go.Scatter(x=[cur_val], y=[cur_mh], mode="markers", name="Current Operating Point", marker=dict(size=12, color="#f59e0b", symbol="diamond", line=dict(width=2, color="#1e293b"))))

    if sw_val is not None and sw_mh is not None:
        fig.add_vline(x=sw_val, line_dash="dot", line_color="#7c3aed", line_width=2, annotation_text=f"Switch: {sw_val:.2f} {unit} ({sw_mh:.2f} kNm)", annotation_position="top left")

    fig.update_layout(title=f"Failure Mode Transition Curve vs. {cfg['label']}", xaxis_title=f"{cfg['label']} ({unit})", yaxis_title="Total Wall Capacity Mh (kNm)", template="plotly_white", height=420, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"<div class='mode-card mode-card-stepped'><b>🔬 Physical Engineering Reason ({cfg['label']}):</b><br>{cfg['reason']}</div>", unsafe_allow_html=True)
    st.caption("Governing Analytical Equilibrium Condition ($M_{h,\\text{line}} = M_{h,\\text{step}}$):")
    st.latex(r"\frac{1}{12}(F_{btm} - \nu f_d) h_u = 0.5 \tau_b K_b (l_u + t_j)")

    summary_df = pd.DataFrame([{**inputs, "Mh_AS3700_kNm": results["Mh_AS3700_total"], "Mh_Griffith_kNm": cur_mh, "Griffith_Mode": cur_mode, "Mh_Willis_kNm": results["Mh_Willis_total"], "Switch_Param": param_key, "Switch_Threshold": sw_val}])
    sweep_df = pd.DataFrame({param_key: sweep["x"], "Mh_line_kNm": sweep["Mh_line_total_kNm"], "Mh_stepped_kNm": sweep["Mh_stepped_total_kNm"], "Mh_Griffith_kNm": sweep["Mh_Griffith_total"], "Mh_AS3700_kNm": sweep["Mh_AS3700_total"], "Mh_Willis_kNm": sweep["Mh_Willis_total"]})

    d1, d2 = st.columns(2)
    d1.download_button("📥 Download Current Wall Summary (CSV)", data=summary_df.to_csv(index=False).encode("utf-8"), file_name="urm_mh_summary.csv", mime="text/csv", use_container_width=True)
    d2.download_button(f"📈 Download {param_key} Sensitivity Sweep (CSV)", data=sweep_df.to_csv(index=False).encode("utf-8"), file_name=f"urm_sweep_{param_key}.csv", mime="text/csv", use_container_width=True)

# ==============================================================================
# 5. MAIN APPLICATION WORKSPACE
# ==============================================================================
def main() -> None:
    init_session_state()
    inject_custom_css()
    inputs = render_sidebar()
    results = calculate_all_methods(inputs)

    st.title("🧱 Unreinforced Masonry Horizontal Bending Capacity ($M_h$)")
    st.markdown(
        "Comparative structural evaluation across **AS 3700:2011**, **Griffith & Vaculik**, "
        "and **Willis et al.** formulations."
    )

    # --- Top Executive KPI Row (4 Columns) ---
    as_tot = results["Mh_AS3700_total"]
    as_per_m = results["details"]["AS3700"]["Mh_AS3700_per_m_kNm"]
    gv_tot = results["Mh_Griffith_total"]
    wi_tot = results["Mh_Willis_total"]
    gv_mode = results["Griffith_governing_mode"]
    gv_det = results["details"]["Griffith_Vaculik"]
    margin = abs(gv_det["Mh_line_total_kNm"] - gv_det["Mh_stepped_total_kNm"])

    k1, k2, k3, k4 = st.columns([1, 1, 1, 1.25])
    with k1:
        st.metric("AS 3700:2011 Total Mh", f"{as_tot:.2f} kNm", f"{as_per_m:.2f} kNm/m (Per Meter)", delta_color="off")
    with k2:
        st.metric("Griffith & Vaculik Total Mh", f"{gv_tot:.2f} kNm", f"{gv_tot - as_tot:+.2f} kNm vs AS 3700")
    with k3:
        st.metric("Willis et al. Total Mh", f"{wi_tot:.2f} kNm", f"{wi_tot - as_tot:+.2f} kNm vs AS 3700")
    with k4:
        is_line = gv_mode == "Line"
        card_cls = "mode-card-line" if is_line else "mode-card-stepped"
        badge_cls = "badge-line" if is_line else "badge-stepped"
        mech_desc = (
            "Flexural cracking directly through brick units & perpend joints."
            if is_line
            else "Torsional-shear stepping along mortar bed & perpend joints."
        )
        st.markdown(
            f"""
            <div class="mode-card {card_cls}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.85rem; font-weight:600; opacity:0.85;">Governing Mode (G&V)</span>
                    <span class="badge {badge_cls}">{gv_mode} Failure</span>
                </div>
                <div style="font-size:1.35rem; font-weight:700; margin-top:6px;">Margin: {margin:.2f} kNm</div>
                <div style="font-size:0.78rem; opacity:0.8; margin-top:4px;">{mech_desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    tab1, tab2, tab3 = st.tabs(["📊 Comparative Capacity Visuals", "🧮 Detailed Engineering Breakdown", "🔄 Failure Mode Switch & Export"])

    with tab1:
        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(build_primary_comparison_chart(results), use_container_width=True)
        with c_right:
            st.plotly_chart(build_submechanism_chart(results, inputs["Hwall"] / 1000.0), use_container_width=True)

    with tab2:
        hlp = results["helpers"]
        as_d = results["details"]["AS3700"]
        wi_d = results["details"]["Willis"]

        st.subheader("Shared Section & Interface Parameters")
        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f"<div class='helper-box'><b>Section Modulus (Zd)</b><br>{hlp['Zd_mm3_per_m']:,.0f} mm³/m</div>", unsafe_allow_html=True)
        s2.markdown(f"<div class='helper-box'><b>Bed Joint Shear (τb)</b><br>{hlp['Taub_MPa']:.3f} MPa</div>", unsafe_allow_html=True)
        s3.markdown(f"<div class='helper-box'><b>Torsion Factor (Kb)</b><br>{hlp['Kb']:.3f}</div>", unsafe_allow_html=True)
        s4.markdown(f"<div class='helper-box'><b>Perpend Factor (Kp)</b><br>{as_d['Kp']:.3f}</div>", unsafe_allow_html=True)

        st.divider()
        b1, b2, b3 = st.columns(3)
        with b1:
            st.markdown("#### 1. AS 3700:2011")
            st.latex(r"M_{h1} = 2 K_p \sqrt{F_{tn}} \left(1 + \frac{f_d}{F_{tn}}\right) Z_d")
            st.latex(r"M_{h2} = 4 K_p \sqrt{F_{tn}} Z_d")
            st.latex(r"M_{h3} = (0.44 F_{btm} + 0.56 F_{tn}) Z_d")
            st.markdown(
                f"- **$M_{{h1}}$ (per m):** `{as_d['Mh1_per_m_kNm']:.3f} kNm/m`\n"
                f"- **$M_{{h2}}$ (per m):** `{as_d['Mh2_per_m_kNm']:.3f} kNm/m`\n"
                f"- **$M_{{h3}}$ (per m):** `{as_d['Mh3_per_m_kNm']:.3f} kNm/m`\n"
                f"- **Governing (per m):** `{as_d['Mh_AS3700_per_m_kNm']:.3f} kNm/m`\n"
                f"- **Total Wall $M_h$:** **`{as_d['Mh_AS3700_total_kNm']:.3f} kNm`**"
            )
        with b2:
            st.markdown("#### 2. Griffith & Vaculik")
            st.latex(r"M_{h,\text{line}} = \frac{10^3}{2(h_u + t_j)} (F_{btm} - \nu f_d) \frac{h_u t_u^2}{6}")
            st.latex(r"M_{h,\text{step}} = \frac{10^3}{h_u + t_j} \left(0.5 \tau_b K_b (l_u + t_j) t_u^2\right)")
            st.markdown(
                f"- **Line (per m):** `{gv_det['Mh_line_per_m_kNm']:.3f} kNm/m`\n"
                f"- **Stepped (per m):** `{gv_det['Mh_stepped_per_m_kNm']:.3f} kNm/m`\n"
                f"- **Line Total:** `{gv_det['Mh_line_total_kNm']:.3f} kNm`\n"
                f"- **Stepped Total:** `{gv_det['Mh_stepped_total_kNm']:.3f} kNm`\n"
                f"- **Governing ($M_h$):** **`{gv_det['Mh_Griffith_total_kNm']:.3f} kNm ({gv_mode})`**"
            )
        with b3:
            st.markdown("#### 3. Willis et al.")
            st.latex(r"M_{h,\text{total}} = (n_b \cdot T_b) + (n_u \cdot M_u)")
            st.latex(r"T_b = 0.5 \tau_b K_b (l_u + t_j) t_u^2")
            st.latex(r"M_u = (F_{btm} - \nu f_d) \frac{h_u t_u^2}{6}")
            st.markdown(
                f"- **Bed Joints ($n_b$):** `{wi_d['nb']:.2f}`\n"
                f"- **Brick Units ($n_u$):** `{wi_d['nu']:.2f}`\n"
                f"- **Joint Torque ($T_b$):** `{wi_d['Tb_kNm']:.4f} kNm`\n"
                f"- **Unit Moment ($M_u$):** `{wi_d['Mu_kNm']:.4f} kNm`\n"
                f"- **Total Wall $M_h$:** **`{wi_d['Mh_Willis_total_kNm']:.3f} kNm`**"
            )
    with tab3:
        render_phase4_tab(inputs, results)        


if __name__ == "__main__":
    main()

