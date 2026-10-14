import json
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def _client():
    from google import genai

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is missing from .env")
    return genai.Client(api_key=key)


def select_workflow(request, flows):
    client = _client()
    ids = flows["Workflow_ID"].astype(str).tolist()
    defs = flows.fillna("").to_dict("records")
    tool = {
        "type": "function",
        "name": "select_workflow",
        "description": "Choose the best workflow ID for the user's request.",
        "parameters": {
            "type": "object",
            "properties": {"workflow_id": {"type": "string", "enum": ids}},
            "required": ["workflow_id"],
        },
    }
    res = client.interactions.create(
        model=GEMINI_MODEL,
        input=(f"Choose the best workflow for this request: {request}\n"
            f"Workflow definitions from Excel: {json.dumps(defs)}\n"
            "Use each workflow's trigger, inputs, steps, decision logic, tools, "
            "and expected output to decide. Call select_workflow with the "
            "matching workflow ID. Do not execute the workflow."),
        tools=[tool],
        generation_config={"tool_choice": "any"},
    )

    for step in res.steps:
        if step.type == "function_call" and step.name == "select_workflow":
            workflow_id = str(step.arguments["workflow_id"])
            if workflow_id in ids:
                return workflow_id
    raise ValueError("Gemini did not select a workflow.")


def generate_product_copy(attributes):
    client = _client()
    fields = ["product_name", "long_description", "short_description",
        "seo_title", "meta_description"]
    schema = {
        "type": "object",
        "properties": {field: {"type": "string"} for field in fields},
        "required": fields,
    }
    res = client.interactions.create(
        model=GEMINI_MODEL,
        input=("Create product copy using only the supplied attributes. "
            "Do not add claims or details that are not supplied. Return JSON "
            "with product_name, long_description, short_description, "
            "seo_title, and meta_description. Attributes: "
            f"{json.dumps(attributes, ensure_ascii=False)}"),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
    )
    result = json.loads(res.output_text or "{}")
    if not set(fields).issubset(result):
        raise ValueError("Gemini returned incomplete product copy.")
    return result


