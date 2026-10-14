import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import agent
import actions
from main import load_workflows
from registry import WORKFLOW_IDS, run_workflow


class WorkflowTests(unittest.TestCase):
    def test_excel_loads_all_ten_workflows(self):
        flows = load_workflows()
        self.assertEqual(len(flows), 10)

    def test_selector_uses_gemini(self):
        flows = load_workflows()
        call = SimpleNamespace(type="function_call", name="select_workflow",
            arguments={"workflow_id": "WF001"})
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), \
                patch("google.genai.Client") as client_cls:
            client = client_cls.return_value
            client.interactions.create.return_value.steps = [call]
            self.assertEqual(agent.select_workflow(
                "Which products need restocking?", flows), "WF001")
            client.interactions.create.assert_called_once()

    def test_selector_reports_gemini_errors(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), \
                patch("google.genai.Client", side_effect=RuntimeError("API error")):
            with self.assertRaisesRegex(RuntimeError, "API error"):
                agent.select_workflow("Which products need restocking?", load_workflows())

    def test_all_ten_workflows_are_registered(self):
        self.assertEqual(len(WORKFLOW_IDS), 10)
        self.assertNotIn("error", run_workflow("WF010"))

    def test_inventory_flags_stock_below_minimum(self):
        with patch("actions.read_rows", return_value=[
            {"name": "Mug", "stock": "5", "minimum": "10"},
            {"name": "Bag", "stock": "12", "minimum": "10"},
        ]):
            result = actions.check_inventory()
        self.assertEqual([row["product"] for row in result], ["Mug"])
        self.assertEqual(result[0]["reorder_quantity"], 15)

    def test_prices_match_sku_and_flag_large_difference(self):
        def rows(filename):
            return {
                "prices.csv": [{"sku": "A", "price": "100"},
                               {"sku": "B", "price": "50"}],
                "vendor_prices.csv": [{"sku": "A", "vendor_price": "120"},
                                      {"sku": "C", "vendor_price": "30"}],
            }[filename]
        with patch("actions.read_rows", side_effect=rows):
            result = actions.validate_prices()
        self.assertTrue(result["validated_products"][0]["flagged"])
        self.assertEqual(len(result["exceptions"]), 1)
        self.assertEqual(len(result["unmatched_skus"]), 2)

    def test_vendor_file_splits_valid_and_invalid_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "vendor.csv"
            source.write_text("SKU,Product Name\nA,Mug\n,Missing SKU\n",
                              encoding="utf-8")
            with patch.object(actions, "OUTPUT_DIR", root / "outputs"):
                result = actions.process_vendor_file(str(source))
        self.assertEqual(result["valid_rows"], 1)
        self.assertEqual(result["invalid_rows"], 1)

    def test_description_reports_missing_optional_details(self):
        copy = {"product_name": "Mug", "long_description": "Steel Mug",
            "short_description": "Mug", "seo_title": "Mug",
            "meta_description": "Steel Mug"}
        with patch("agent.generate_product_copy", return_value=copy):
            result = actions.product_description(name="Mug", material="steel")
        self.assertIn("category", result["missing_attributes"])
        self.assertIn("steel", result["long_description"].lower())

    def test_order_lookup_accepts_email_and_handles_missing(self):
        with patch("actions.read_rows", return_value=[{
            "order_id": "A-1", "email": "person@example.com",
            "status": "Shipped", "items": "Mug|Bag",
            "shipment": "In transit", "tracking": "T-1",
        }]):
            found = actions.order_status("PERSON@example.com")
            missing = actions.order_status("unknown@example.com")
        self.assertEqual(found["items"], ["Mug", "Bag"])
        self.assertIn("error", missing)

    def test_duplicate_detection_finds_exact_and_similar_products(self):
        products = [
            {"sku": "X", "name": "Steel Mug"},
            {"sku": "X", "name": "Steel Mug"},
            {"sku": "Y", "name": "Blue Shirt"},
            {"sku": "Z", "name": "Blue Shirts"},
        ]
        with patch("actions.read_rows", return_value=products):
            result = actions.find_duplicates()
        self.assertEqual(len(result["exact_duplicates"]), 1)
        self.assertEqual(len(result["possible_duplicates"]), 1)

    def test_campaign_requires_core_fields(self):
        self.assertIn("error", actions.campaign_brief())
        result = actions.campaign_brief("Shoes", "Runners", "Launch sale", "May")
        self.assertIn("Launch sale", result["message"])

    def test_keyword_classifier_removes_duplicates(self):
        result = actions.classify_keywords("buy shoes, buy shoes, best shirts")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["intent"], "Transactional")

    def test_employee_assignment_uses_skill_and_load(self):
        people = [
            {"name": "A", "skills": "python", "tasks": "2", "available": "true", "max_tasks": "4"},
            {"name": "B", "skills": "python", "tasks": "1", "available": "false", "max_tasks": "4"},
        ]
        with patch("actions.read_rows", return_value=people):
            result = actions.assign_employee("python", "Build report")
        self.assertEqual(result["assigned_employee"], "A")

    def test_performance_report_counts_failures(self):
        logs = [
            {"seconds": "2", "error": "false", "message": ""},
            {"seconds": "8", "error": "true", "message": "Timeout"},
        ]
        with patch("actions.read_rows", return_value=logs):
            result = actions.performance_report()
        self.assertEqual(result["failed_runs"], 1)
        self.assertEqual(result["average_seconds"], 5)


if __name__ == "__main__":
    unittest.main()
