
import streamlit as st

# Guarded imports
try:
    import pandas as pd
    import numpy as np
except Exception as e:
    st.error("Please install pandas and numpy: pip install -r requirements.txt")
    st.stop()

from optimizer import solve_schedule

st.set_page_config(page_title="Avenida Shift Scheduler (12-24)", layout="wide")
st.title("Avenida Shift Scheduler (12:00–24:00)")

# Sets
D = list(range(1,8))
T = list(range(1,14))  # 13 slots
SLOT_LABELS = ["12-13","13-14","14-15","15-16","16-17","17-18","18-19","19-20","20-21","21-22","22-23","23-24","24-01?"]

# Default staff
DEFAULT_STAFF = [
    {"name":"Cristina_Mata",    "min_week_hours":25.0, "max_week_hours":32.5},
    {"name":"Gabriela_Velasco", "min_week_hours":20.0, "max_week_hours":26.0},
    {"name":"Javi",             "min_week_hours":27.5},
    {"name":"Lorena",           "min_week_hours":25.0, "max_week_hours":32.5},
    {"name":"Aurora",           "min_week_hours":25.0, "max_week_hours":32.5},
    {"name":"Clara_Nogales",    "min_week_hours":25.0, "max_week_hours":32.5},
]

with st.sidebar:
    st.header("Configuration")
    max_dev = st.number_input("Max deviation per slot", min_value=0.0, value=2.5, step=0.1)
    ensure_min_staff = st.checkbox("Require at least 1 staff per slot", value=True)

    st.subheader("Staff table")
    if "staff_df" not in st.session_state:
        st.session_state["staff_df"] = pd.DataFrame(DEFAULT_STAFF)
    staff_upload = st.file_uploader("Upload staff CSV (optional)", type=["csv"])
    if staff_upload is not None:
        st.session_state["staff_df"] = pd.read_csv(staff_upload)
    if st.button("Load default staff"):
        st.session_state["staff_df"] = pd.DataFrame(DEFAULT_STAFF)
    staff_df = st.data_editor(
        st.session_state["staff_df"],
        num_rows="dynamic",
        use_container_width=True
    )

    st.subheader("Demand CSV (7x13, no header)")
    st.caption("Rows: Mon..Sun; Cols: 13 hourly slots (12..24). If omitted, built-in default is used.")
    demand_file = st.file_uploader("Upload sales_demand_template.csv", type=["csv"])

# Default demand (first 13 columns of your AMPL table)
default_demand = {
    1: [0.23,0.25,0.70,1.39,0.80,1.16,1.27,0.28,0.89,1.18,0.91,0.08,0.26],
    2: [0.76,0.77,0.56,0.79,0.45,0.29,0.45,1.43,1.42,0.05,0.73,0.75,0.99],
    3: [0.31,0.38,0.29,0.53,0.49,1.63,0.53,0.35,0.01,0.26,0.29,0.88,0.35],
    4: [0.86,0.65,0.37,1.71,1.33,2.14,0.69,0.17,0.29,0.72,0.80,1.59,0.72],
    5: [0.30,0.75,1.05,1.28,0.56,1.09,0.55,0.80,1.20,0.43,0.97,0.50,0.74],
    6: [2.23,1.25,0.21,0.23,0.59,1.10,1.74,1.60,1.09,0.92,1.17,0.24,1.13],
    7: [0.37,0.59,1.10,1.74,1.60,1.09,0.92,1.17,0.24,1.13,1.89,0.80,0.00],
}

if demand_file is not None:
    demand_df = pd.read_csv(demand_file, header=None)
    if demand_df.shape != (7,13):
        st.error(f"Demand CSV must be 7 rows x 13 columns. Got {demand_df.shape}.")
        st.stop()
else:
    demand_df = pd.DataFrame([default_demand[d] for d in D])

# Build Min/Max dicts
def to_hours_dict(df, col):
    out = {}
    for _, r in df.iterrows():
        out[str(r["name"])] = float(r[col])
    return out

MinHw = to_hours_dict(staff_df, "min_week_hours")
MaxHw = to_hours_dict(staff_df, "max_week_hours")
W = [str(w) for w in staff_df["name"].tolist()]

if st.button("Solve", type="primary"):
    with st.spinner("Solving..."):
        Demand = {d: list(map(float, demand_df.iloc[d-1].tolist())) for d in D}
        status, obj, schedule, metrics = solve_schedule(
            W=W, D=D, T=T,
            MinHw=MinHw, MaxHw=MaxHw,
            Demand=Demand,
            Max_Deviation=max_dev,
            require_min_staff=ensure_min_staff,
        )

    st.success(f"Status: {status}; Total deviation: {obj:.4f}")
    # Schedule table
    import pandas as pd
    sched_df = pd.DataFrame(schedule, columns=["worker","day","slot"]).sort_values(["day","slot","worker"])
    st.dataframe(sched_df, use_container_width=True)

    # Coverage table
    rows = []
    for (d,t),(u,o,staffed,dem) in metrics.items():
        rows.append({"day":d,"slot":t,"staffed":staffed,"demand":dem,"under":u,"over":o})
    cov_df = pd.DataFrame(rows).sort_values(["day","slot"])
    st.dataframe(cov_df, use_container_width=True)

    # Downloads
    st.download_button("Download schedule CSV", sched_df.to_csv(index=False).encode("utf-8"),
                       file_name="avenida_schedule.csv", mime="text/csv")
    st.download_button("Download coverage CSV", cov_df.to_csv(index=False).encode("utf-8"),
                       file_name="avenida_coverage.csv", mime="text/csv")

# Template download (7x13, no header)
templ = pd.DataFrame([default_demand[d] for d in D])
st.download_button("Download demand template (7x13 CSV, no header)",
                   templ.to_csv(index=False, header=False).encode("utf-8"),
                   file_name="sales_demand_template.csv",
                   mime="text/csv")
