
# Avenida Shift Scheduler (Streamlit)

This app solves the weekly shift-scheduling MILP for the **Avenida** store.

## Quick start

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Upload an optional **Demand CSV** (`day,slot,value`). If omitted, the built-in Avenida demand is used.
- Adjust weekly min/max hours in the sidebar.
- Click **Solve** to run the optimizer.
- Download the resulting **schedule** and **slot metrics** as CSV.

## Files
- `streamlit_app.py` — Streamlit UI.
- `optimizer.py` — MILP model in PuLP/CBC.
- `requirements.txt` — Python dependencies.
- `sales_demand_template.csv` — CSV template with default Avenida demand (7×15).
- `README.md` — This guide.
