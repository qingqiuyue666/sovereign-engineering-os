import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.xlsx_adapter_contract import (
    XlsxReadonlyLimits,
    build_xlsx_readonly_capability_request,
)


class XlsxAdapterContractTests(unittest.TestCase):
    def test_builds_readonly_capability_request(self):
        request = build_xlsx_readonly_capability_request()

        self.assertEqual(request.adapter_id, "xlsx_readonly_runtime")
        self.assertEqual(request.capability, "inspect_local_xlsx_metadata")
        self.assertEqual(request.mode, AdapterMode.READONLY)
        self.assertEqual(request.risk_class, AdapterRiskClass.LOCAL_READONLY)
        self.assertTrue(request.boundary.is_runtime_safe_for_current_branch())

    def test_limits_validate_positive_values(self):
        XlsxReadonlyLimits().validate()

        with self.assertRaises(ValueError):
            XlsxReadonlyLimits(max_header_rows=0).validate()
        with self.assertRaises(ValueError):
            XlsxReadonlyLimits(max_header_columns=0).validate()
        with self.assertRaises(ValueError):
            XlsxReadonlyLimits(max_formula_scan_cells=0).validate()


if __name__ == "__main__":
    unittest.main()
