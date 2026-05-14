import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.xlsx_output_writer_contract import (
    XlsxOutputWriterPaths,
    build_xlsx_output_writer_capability_request,
)


class XlsxOutputWriterContractTests(unittest.TestCase):
    def test_builds_approved_writer_capability_request(self):
        request = build_xlsx_output_writer_capability_request()

        self.assertEqual(request.adapter_id, "xlsx_output_writer")
        self.assertEqual(request.capability, "create_metadata_summary_workbook")
        self.assertEqual(request.mode, AdapterMode.APPROVED_WRITE)
        self.assertEqual(request.risk_class, AdapterRiskClass.APPROVED_OUTPUT_WRITE)
        self.assertTrue(request.boundary.output_write_allowed)
        self.assertTrue(request.boundary.is_runtime_safe_for_current_branch())

    def test_output_writer_paths_are_fixed(self):
        paths = XlsxOutputWriterPaths()

        self.assertEqual(paths.plan_file, "xlsx_output_plan.json")
        self.assertEqual(paths.manifest_file, "xlsx_output_manifest.json")
        self.assertEqual(paths.validation_report_file, "xlsx_output_validation.json")


if __name__ == "__main__":
    unittest.main()
