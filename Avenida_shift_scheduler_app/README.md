
# Avenida Shift Scheduler (Streamlit)

This app mirrors the sidebar and outputs of your original package:
- Sidebar shows a full **staff table editor** and **Demand CSV upload**.
- No random seed and **no solver time limit** controls.
- If no CSV is uploaded, the built‑in Avenida demand is used.

## Run
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Files
- `streamlit_app.py` — Streamlit UI (staff editor + demand + outputs).
- `optimizer.py` — MILP model (PuLP/CBC).
- `requirements.txt` — dependencies.
- `sales_demand_template.csv` — example/template demand.
- `README.md` — this guide.
