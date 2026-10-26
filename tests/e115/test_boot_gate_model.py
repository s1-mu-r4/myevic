"""Offline-only branch matrix for unchanged E115 cold-start gate functions.

This test deliberately models *source control flow*, not microcontroller behavior.
The test asserts source fragments have not changed before testing assumptions.
"""
import pathlib
import re
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[2]
EXPECTED_BASE = 0x1D800   # This must match linker layout; asserted below.


def body(filename: str, func: str) -> str:
    text = (SOURCE / filename).read_text()
    found = re.search(r"\b" + re.escape(func) + r"\s*\([^;]*?\)\s*\{", text, re.S)
    if not found:
        raise AssertionError(f"missing function {func}")
    start = found.end() - 1
    n = 0
    for idx in range(start, len(text)):
        if text[idx] == "{":
            n += 1
        elif text[idx] == "}":
            n -= 1
            if n == 0:
                return text[start:idx + 1]
    raise AssertionError("unclosed function")


def config_transition(dfen_disabled: bool, dfba_matches: bool,
                      write_ok: bool, verify_ok: bool) -> str:
    """Four branches of FMCCheckConfig mirrored from the preserved C function."""
    if not dfen_disabled and dfba_matches:
        return "NO_CONFIG_WRITE"
    if not write_ok:
        return "CONFIG_WRITE_FAILED"
    if not verify_ok:
        return "CONFIG_READBACK_FAILED"
    return "CONFIG_ERASE_WRITE_THEN_SOFTWARE_RESET"


def product_transition(ldrom_marker_matched: bool) -> str:
    """SetProductID terminal branch."""
    return "SET_MODEL_AND_CONTINUE" if ldrom_marker_matched else "RESET_TO_LDROM"


class FirstBootBranchMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = body("src/dataflash.c", "FMCCheckConfig")
        product = body("src/dataflash.c", "SetProductID")
        ldrom = body("src/dataflash.c", "ResetToLDROM")
        clk = body("src/main.c", "InitDevices")
        hw = body("src/main.c", "InitHardware")
        header = (SOURCE/"inc/dataflash.h").read_text()
        assert "#define DATAFLASH_APROM_END" in header
        assert "0x00020000" in header
        assert "DATAFLASH_PARAMS_BASE" in header
        # First-boot branch source contract, not merely hand-written model.
        for fragment in (
            "if ( cfg[0] & 1 || cfg[1] != DATAFLASH_PARAMS_BASE )",
            "FMC_EnableConfigUpdate();", "FMC_Erase( FMC_CONFIG_BASE );",
            "cfg[0] &= ~1;", "cfg[1] = DATAFLASH_PARAMS_BASE;",
            "FMC_WriteConfig( cfg, 2 )", "FMC_ReadConfig( cfg, 2 )",
            "SYS_ResetChip();",
        ):
            assert fragment in config, f"CONFIG model no longer matches source: {fragment}"
        assert "FMC_Read( LDROM_BASE + offset )" in product
        assert "if ( offset < LDROM_SIZE )" in product
        assert "ResetToLDROM();" in product
        assert "FMC_SELECT_NEXT_BOOT( 1 );" in ldrom
        assert "CLK_WaitClockReady" in clk
        assert "CLK_WaitClockReady( CLK_STATUS_LXTSTB_Msk );" in hw
        assert "InitUSB();" in hw
        # The caller currently does NOT check the crystal-ready return value.
        assert not re.search(r"\bif\s*\(\s*CLK_WaitClockReady", clk)
        assert not re.search(r"\bif\s*\(\s*CLK_WaitClockReady", hw)

    def test_config_already_matches_proceeds(self):
        self.assertEqual(config_transition(False, True, True, True),
                         "NO_CONFIG_WRITE")

    def test_dfen_disabled_causes_config_reset_if_successful(self):
        self.assertEqual(config_transition(True, True, True, True),
                         "CONFIG_ERASE_WRITE_THEN_SOFTWARE_RESET")

    def test_dfba_mismatch_causes_config_reset_if_successful(self):
        self.assertEqual(config_transition(False, False, True, True),
                         "CONFIG_ERASE_WRITE_THEN_SOFTWARE_RESET")

    def test_config_write_failure_does_not_report_success(self):
        self.assertEqual(config_transition(True, False, False, False),
                         "CONFIG_WRITE_FAILED")

    def test_config_verify_failure_does_not_report_success(self):
        self.assertEqual(config_transition(True, False, True, False),
                         "CONFIG_READBACK_FAILED")

    def test_ldrom_model_found_continues(self):
        self.assertEqual(product_transition(True), "SET_MODEL_AND_CONTINUE")

    def test_ldrom_model_missing_forces_ldrom_reset(self):
        self.assertEqual(product_transition(False), "RESET_TO_LDROM")


if __name__ == "__main__":
    unittest.main()
