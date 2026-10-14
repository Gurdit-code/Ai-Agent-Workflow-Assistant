from actions import (
    assign_employee,
    campaign_brief,
    classify_keywords,
    check_inventory,
    find_duplicates,
    order_status,
    performance_report,
    process_vendor_file,
    product_description,
    validate_prices,
)

WORKFLOWS = {
    "WF001": check_inventory,
    "WF002": validate_prices,
    "WF003": process_vendor_file,
    "WF004": product_description,
    "WF005": order_status,
    "WF006": find_duplicates,
    "WF007": campaign_brief,
    "WF008": classify_keywords,
    "WF009": assign_employee,
    "WF010": performance_report,
}

WORKFLOW_IDS = tuple(WORKFLOWS)


def run_workflow(wf_id, **inputs):
    action = WORKFLOWS.get(str(wf_id))
    if action is None:
        return {"error": f"Workflow {wf_id} is not implemented."}
    return action(**inputs)
