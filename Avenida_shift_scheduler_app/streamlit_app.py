
import pandas as pd
import streamlit as st
from optimizer import solve_schedule

st.set_page_config(page_title="Avenida Shift Scheduler", page_icon="🧊", layout="wide")
st.title("Avenida Shift Scheduler")

# Fixed sets (to mirror your previous app)
D = list(range(1,8))
T = list(range(1,16))

# Default staff table (full list, no truncation)
default_staff = pd.DataFrame([
    {"worker":"Cristina_Mata",    "MinHw":25.0, "MaxHw":32.5},
    {"worker":"Gabriela_Velasco", "MinHw":20.0, "MaxHw":26.0},
    {"worker":"Javi",             "MinHw":27.5, "MaxHw":27.5},
    {"worker":"Lorena",           "MinHw":25.0, "MaxHw":32.5},
    {"worker":"Aurora",           "MinHw":25.0, "MaxHw":32.5},
    {"worker":"Clara_Nogales",    "MinHw":25.0, "MaxHw":32.5},
])

# Default demand (used if no CSV is uploaded)
default_demand = {
    1: [0.23, 0.25, 0.70, 1.39, 0.80, 1.16, 1.27, 0.28, 0.89, 1.18, 0.91, 0.08, 0.26, 0.22, 0.44],
    2: [0.76, 0.77, 0.56, 0.79, 0.45, 0.29, 0.45, 1.43, 1.42, 0.05, 0.73, 0.75, 0.99, 0.41, 0.36],
    3: [0.31, 0.38, 0.29, 0.53, 0.49, 1.63, 0.53, 0.35, 0.01, 0.26, 0.29, 0.88, 0.35, 0.54, 0.67],
    4: [0.86, 0.65, 0.37, 1.71, 1.33, 2.14, 0.69, 0.17, 0.29, 0.72, 0.80, 1.59, 0.72, 0.91, 0.28],
    5: [0.30, 0.75, 1.05, 1.28, 0.56, 1.09, 0.55, 0.80, 1.20, 0.43, 0.97, 0.50, 0.74, 1.04, 1.45],
    6: [2.23, 1.25, 0.21, 0.23, 0.59, 1.10, 1.74, 1.60, 1.09, 0.92, 1.17, 0.24, 1.13, 1.89, 0.80],
    7: [0.37, 0.59, 1.10, 1.74, 1.60, 1.09, 0.92, 1.17, 0.24, 1.13, 1.89, 0.80, 0.00, 0.00, 0.00],
}

# ---- SIDEBAR (mirror previous app: staff table editor + demand upload + simple params) ----
with st.sidebar:
    st.header("Staff table")
    staff_df = st.data_editor(
        default_staff,
        num_rows="dynamic",
        key="staff_table",
        use_container_width=True
    )
    st.caption("Edit weekly min/max hours directly in the table.")

    st.header("Demand")
    st.write("Upload CSV (columns: day,slot,value). If not uploaded, built-in Avenida demand is used.")
    demand_file = st.file_uploader("Upload demand CSV", type=["csv"], key="demand_csv")

    st.header("Model options")
    max_dev = st.number_input("Max deviation per slot", min_value=0.0, value=2.5, step=0.1)
    need_min_staff = st.checkbox("Require at least 1 staff per slot", value=True)
    weekend_15 = st.checkbox("15h contracts weekend-only", value=True, help="No 15h contracts in this store; has no effect.")

def parse_demand_csv(file):
    import pandas as pd
    df = pd.read_csv(file)
    # Normalize columns
    ren = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc in ("day", "d"): ren[c] = "day"
        elif lc in ("slot", "t", "timeslot"): ren[c] = "slot"
        elif lc in ("value", "val", "demand"): ren[c] = "value"
    df = df.rename(columns=ren)
    if not {"day","slot","value"}.issubset(df.columns):
        raise ValueError("CSV must contain columns: day, slot, value")
    demand = {d: [0.0]*len(T) for d in D}
    for _, r in df.iterrows():
        d = int(r["day"]); t = int(r["slot"]); v = float(r["value"])
        if d in demand and 1 <= t <= len(T):
            demand[d][t-1] = v
    return demand

# Use uploaded demand or default
if demand_file is not None:
    try:
        Demand = parse_demand_csv(demand_file)
        st.success("Custom demand loaded from CSV.")
    except Exception as e:
        st.error(f"Failed to parse CSV. Using default. Error: {e}")
        Demand = default_demand
else:
    Demand = default_demand

# Build MinHw/MaxHw dicts from staff table
def to_hours_dict(df, col):
    out = {}
    for _, r in df.iterrows():
        out[str(r["worker"])] = float(r[col])
    return out

MinHw = to_hours_dict(staff_df, "MinHw")
MaxHw = to_hours_dict(staff_df, "MaxHw")
W = [str(w) for w in staff_df["worker"].tolist()]

# ---- RUN ----
if st.button("Solve"):
    with st.spinner("Solving..."):
        status, obj, schedule, metrics = solve_schedule(
            W=W, D=D, T=T,
            MinHw=MinHw, MaxHw=MaxHw,
            Demand=Demand,
            Max_Deviation=max_dev,
            weekend_15h_only=weekend_15,
            require_min_staff=need_min_staff,
            solver_time_limit=None
        )

    st.subheader("Result")
    st.write(f"**Status:** {status}")
    st.write(f"**Total deviation:** {obj:.4f}")

    # Output: schedule table (long format)
    sched_df = pd.DataFrame(schedule, columns=["worker","day","slot"]).sort_values(["day","slot","worker"])
    st.markdown("**Schedule (long format)**")
    st.dataframe(sched_df, use_container_width=True)

    # Output: coverage vs demand table
    rows = []
    for (d,t), (u,o,staffed,dem) in metrics.items():
        rows.append({"day": d, "slot": t, "staffed": staffed, "demand": dem, "under": u, "over": o})
    cov_df = pd.DataFrame(rows).sort_values(["day","slot"])
    st.markdown("**Coverage vs Demand**")
    st.dataframe(cov_df, use_container_width=True)

    # Downloads
    st.download_button(
        "Download schedule CSV",
        data=sched_df.to_csv(index=False).encode("utf-8"),
        file_name="avenida_schedule.csv",
        mime="text/csv"
    )
    st.download_button(
        "Download coverage CSV",
        data=cov_df.to_csv(index=False).encode("utf-8"),
        file_name="avenida_coverage.csv",
        mime="text/csv"
    )

st.divider()
st.markdown("### Demand template")
templ = [{"day": d, "slot": t, "value": default_demand[d][t-1]} for d in D for t in T]
templ_df = pd.DataFrame(templ)
st.dataframe(templ_df.head(15), use_container_width=True)
st.download_button(
    "Download template CSV",
    data=templ_df.to_csv(index=False).encode("utf-8"),
    file_name="sales_demand_template.csv",
    mime="text/csv"
)
