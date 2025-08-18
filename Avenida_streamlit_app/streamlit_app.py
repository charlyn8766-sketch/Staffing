
import io
import json
import pandas as pd
import streamlit as st
from optimizer import solve_schedule

st.set_page_config(page_title="Avenida Shift Scheduler", page_icon="🧮", layout="wide")
st.title("Avenida Shift Scheduler")

st.markdown("Upload optional **Demand CSV** (long format: columns = day, slot, value). "
            "If you don't upload, default data for Avenida will be used.")

# Default Avenida data
default_W = [
    "Cristina_Mata",
    "Gabriela_Velasco",
    "Javi",
    "Lorena",
    "Aurora",
    "Clara_Nogales",
]
D = list(range(1,8))
T = list(range(1,16))

default_MinHw = {
    "Cristina_Mata":    25,
    "Gabriela_Velasco": 20,
    "Javi":             27.5,
    "Lorena":           25,
    "Aurora":           25,
    "Clara_Nogales":    25,
}
default_MaxHw = {
    "Cristina_Mata":    32.5,
    "Gabriela_Velasco": 26,
    "Javi":             27.5,
    "Lorena":           32.5,
    "Aurora":           32.5,
    "Clara_Nogales":    32.5,
}
default_Demand = {
    1: [0.23, 0.25, 0.70, 1.39, 0.80, 1.16, 1.27, 0.28, 0.89, 1.18, 0.91, 0.08, 0.26, 0.22, 0.44],
    2: [0.76, 0.77, 0.56, 0.79, 0.45, 0.29, 0.45, 1.43, 1.42, 0.05, 0.73, 0.75, 0.99, 0.41, 0.36],
    3: [0.31, 0.38, 0.29, 0.53, 0.49, 1.63, 0.53, 0.35, 0.01, 0.26, 0.29, 0.88, 0.35, 0.54, 0.67],
    4: [0.86, 0.65, 0.37, 1.71, 1.33, 2.14, 0.69, 0.17, 0.29, 0.72, 0.80, 1.59, 0.72, 0.91, 0.28],
    5: [0.30, 0.75, 1.05, 1.28, 0.56, 1.09, 0.55, 0.80, 1.20, 0.43, 0.97, 0.50, 0.74, 1.04, 1.45],
    6: [2.23, 1.25, 0.21, 0.23, 0.59, 1.10, 1.74, 1.60, 1.09, 0.92, 1.17, 0.24, 1.13, 1.89, 0.80],
    7: [0.37, 0.59, 1.10, 1.74, 1.60, 1.09, 0.92, 1.17, 0.24, 1.13, 1.89, 0.80, 0.00, 0.00, 0.00],
}

with st.sidebar:
    st.header("Parameters")
    max_dev = st.number_input("Max deviation per slot", min_value=0.0, value=2.5, step=0.1)
    ensure_min_staff = st.checkbox("Require at least 1 staff per slot", value=True)
    weekend_15_only = st.checkbox("15h contracts weekend-only", value=True)
    st.caption("Note: No employee has a 15h contract here; this toggle will have no effect.")

    st.subheader("Weekly hours (min/max)")
    min_cols, max_cols = st.columns(2)
    MinHw = {}
    MaxHw = {}
    with min_cols:
        for w in default_W:
            MinHw[w] = st.number_input(f"MinHw - {w}", value=float(default_MinHw[w]), step=0.5)
    with max_cols:
        for w in default_W:
            MaxHw[w] = st.number_input(f"MaxHw - {w}", value=float(default_MaxHw[w]), step=0.5)

uploaded = st.file_uploader("Upload demand CSV (columns: day,slot,value)", type=["csv"])

def read_demand_csv(file) -> dict:
    df = pd.read_csv(file)
    expected_cols = {"day","slot","value"}
    if set(df.columns.str.lower()) == expected_cols:
        df.columns = [c.lower() for c in df.columns]
    else:
        # try to coerce common variants
        rename = {}
        for c in df.columns:
            lc = c.lower().strip()
            if lc in ("d","day"): rename[c] = "day"
            elif lc in ("t","slot","timeslot"): rename[c] = "slot"
            elif lc in ("val","value","demand"): rename[c] = "value"
        df = df.rename(columns=rename)
        if set(df.columns) < {"day","slot","value"}:
            raise ValueError("CSV must have columns: day, slot, value")
    dem = {d: [0.0]*len(T) for d in D}
    for _, r in df.iterrows():
        d = int(r["day"]); t = int(r["slot"]); v = float(r["value"])
        if d not in dem: continue
        if t < 1 or t > len(T): continue
        dem[d][t-1] = v
    return dem

if uploaded is not None:
    try:
        Demand = read_demand_csv(uploaded)
        st.success("Custom demand loaded.")
    except Exception as e:
        st.error(f"Failed to parse uploaded CSV: {e}")
        Demand = default_Demand
else:
    Demand = default_Demand

run = st.button("Solve")

if run:
    with st.spinner("Solving..."):
        status, obj, schedule, metrics = solve_schedule(
            W=default_W, D=D, T=T,
            MinHw=MinHw, MaxHw=MaxHw,
            Demand=Demand,
            Max_Deviation=max_dev,
            weekend_15h_only=weekend_15_only,
            require_min_staff=ensure_min_staff,
            solver_time_limit=None
        )

    st.subheader("Result")
    st.write(f"**Status:** {status}")
    st.write(f"**Total deviation:** {obj:.4f}")

    # Schedule table
    sched_df = pd.DataFrame(schedule, columns=["worker","day","slot"]).sort_values(["day","slot","worker"])
    st.dataframe(sched_df, use_container_width=True)

    # Slot metrics
    rows = []
    for (d,t), (u,o,staffed,dem) in metrics.items():
        rows.append({"day": d, "slot": t, "staffed": staffed, "demand": dem, "under": u, "over": o})
    met_df = pd.DataFrame(rows).sort_values(["day","slot"])
    st.dataframe(met_df, use_container_width=True)

    # Download buttons
    st.download_button("Download schedule CSV",
        data=sched_df.to_csv(index=False).encode("utf-8"),
        file_name="avenida_schedule.csv",
        mime="text/csv"
    )
    st.download_button("Download slot metrics CSV",
        data=met_df.to_csv(index=False).encode("utf-8"),
        file_name="avenida_slot_metrics.csv",
        mime="text/csv"
    )

st.divider()
st.markdown("### Demand CSV template")
templ = pd.DataFrame([{"day": d, "slot": t, "value": default_Demand[d][t-1]} for d in D for t in T])
st.dataframe(templ.head(15), use_container_width=True)
st.download_button("Download template CSV",
    data=templ.to_csv(index=False).encode("utf-8"),
    file_name="sales_demand_template.csv",
    mime="text/csv"
)
