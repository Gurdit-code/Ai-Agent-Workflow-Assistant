import json
import time
import traceback
from pathlib import Path

import streamlit as st
from main import load_workflows
from agent import select_workflow
from data_io import DATA_DIR
from registry import run_workflow

st.set_page_config(page_title="AI Agent Workflow Assistant",layout="centered")

st.title("AI Agent Workflow Assistant")
st.write("Enter a task and run a workflow, or choose one manually.")

try:
    flows = load_workflows()
except Exception as error:
    st.error(f"Could not load workflow Excel: {error}")
    st.info("Ensure the workbook is inside the data folder and has a sheet "
    "named 'Workflows'.")
    st.stop()

task = st.text_area("What do you want to do?",
    placeholder="Example: Which products need restocking?",
    height=90)

manual = st.checkbox("Choose workflow manually")
if manual:
    names = dict(zip(flows["Workflow_ID"], flows["Workflow_Name"]))
    wf_id = st.selectbox("Workflow", list(names),
        format_func=lambda item: names[item])
    selected_task = task.strip() or names[wf_id]
else:
    wf_id = (st.session_state.get("wf_id")
        if task == st.session_state.get("selected_task") else None)
    selected_task = task.strip()

matches = flows[flows["Workflow_ID"] == str(wf_id)] if wf_id else flows.iloc[0:0]
selected = matches.iloc[0] if not matches.empty else None
if selected is not None:
    st.subheader(f"Selected workflow: {selected['Workflow_Name']}")

inputs = {}
if wf_id == "WF004":
    st.subheader("Product details")
    inputs["name"] = st.text_input("Product name")
    inputs["category"] = st.text_input("Category (optional)")
    inputs["material"] = st.text_input("Material (optional)")
    inputs["color"] = st.text_input("Color (optional)")
    inputs["audience"] = st.text_input("Target audience (optional)")

elif wf_id == "WF005":
    inputs["order_id"] = st.text_input("Order ID or customer email")
elif wf_id == "WF007":
    inputs["product"] = st.text_input("Product or collection")
    inputs["audience"] = st.text_input("Target audience")
    inputs["goal"] = st.text_input("Campaign goal")
    inputs["dates"] = st.text_input("Campaign dates")
elif wf_id == "WF008":
    inputs["words"] = st.text_input("Keywords, separated by commas")
elif wf_id == "WF009":
    inputs["task"] = st.text_input("Task description")
    inputs["skill"] = st.text_input("Required skill")
    inputs["priority"] = st.selectbox("Priority", ["Normal", "High", "Low"])
    inputs["deadline"] = st.text_input("Deadline (optional)")
upload = None
if wf_id == "WF003":
    upload = st.file_uploader("Upload vendor data", type=["csv", "xlsx"])

if st.button("Run Workflow", type="primary", use_container_width=True):
    if not manual and not selected_task:
        st.warning("Enter a task first.")
    else:
        try:
            if not manual and not wf_id:
                with st.spinner("Finding workflow..."):
                    wf_id = select_workflow(selected_task, flows)
                st.session_state["wf_id"] = wf_id
                st.session_state["selected_task"] = task
                needs_inputs = wf_id in {
                    "WF003", "WF004", "WF005", "WF007", "WF008", "WF009"}
                if needs_inputs:
                    st.info("Workflow selected. Fill in the details, then run it.")
                    st.rerun()
            matches = flows[flows["Workflow_ID"] == str(wf_id)]
            selected = matches.iloc[0]

            if wf_id == "WF003":
                if upload is None:
                    st.warning("Upload a CSV or XLSX vendor file first.")
                    st.stop()
                ext = Path(upload.name).suffix.lower()
                out_dir = DATA_DIR.parent / "outputs"
                out_dir.mkdir(exist_ok=True)
                upload_path = out_dir / f"uploaded_vendor{ext}"
                upload_path.write_bytes(upload.getvalue())
                inputs["file_path"] = str(upload_path)

            if wf_id == "WF004" and not inputs["name"].strip():
                st.warning("Enter a product name.")
                st.stop()
            if wf_id == "WF007" and not all(
                    inputs[key].strip() for key in ("product", "audience", "goal", "dates")):
                st.warning("Enter product, audience, campaign goal, and dates.")
                st.stop()
            if wf_id == "WF008" and not inputs["words"].strip():
                st.warning("Enter at least one keyword.")
                st.stop()
            if wf_id == "WF009" and not all(
                    inputs[key].strip() for key in ("task", "skill")):
                st.warning("Enter a task and required skill.")
                st.stop()
            start = time.perf_counter()
            with st.spinner("Running workflow..."):
                result = run_workflow(str(wf_id), **inputs)
            st.success(f"Workflow {wf_id} finished.")
            st.subheader("Steps executed")
            for i, step in enumerate(str(selected["Steps"]).split("→"), start=1):
                st.write(f"{i}. {step.strip()}")
            st.subheader("Result")
            if isinstance(result, (dict, list)):
                st.json(result)
            else:
                st.write(result)
            elapsed = time.perf_counter() - start
            st.caption(f"Execution time: {elapsed:.2f} seconds")
            st.download_button("Download result as JSON",
                data=json.dumps(result, indent=2, ensure_ascii=False, default=str),
                file_name=f"{wf_id.lower()}_result.json",
                mime="application/json")
        except Exception as err:
            st.error(f"{type(err).__name__}: {err}")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())

with st.expander("Available workflows"):
    st.dataframe(flows[["Workflow_ID", "Workflow_Name"]],
        use_container_width=True,
        hide_index=True)

st.divider()
st.caption("AI Agent | Python + Streamlit")

