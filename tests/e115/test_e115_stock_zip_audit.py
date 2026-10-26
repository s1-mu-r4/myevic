"""Stdlib-only offline tests; no physical device, firmware update or USB access."""
import struct
import unittest

from e115_stock_zip_audit import aprom_xor, firmware_fields, pe_fields, audit


class OfflineTests(unittest.TestCase):
    def test_xor_round_trip(self):
        data = bytes(range(256)) * 4
        self.assertEqual(data, aprom_xor(aprom_xor(data)))

    def test_e115_marker_not_exact_hw_proof(self):
        data = bytearray(64)
        struct.pack_into("<II", data, 0, 0x200022E8, 0x11)
        data[16:30] = b"Joyetech APROM"
        data[40:48] = b"E115\x01\x00\x01\x00"
        fields = firmware_fields(data)
        self.assertEqual(fields["following_bytes"], "01000100")
        self.assertGreater(fields["legacy_hw_check_value"], 100)

    def test_marker_missing(self):
        with self.assertRaises(ValueError):
            firmware_fields(bytes(128))

    def test_vector_invalid(self):
        data = bytearray(64)
        struct.pack_into("<II", data, 0, 0, 0x10)
        data[16:30] = b"Joyetech APROM"
        data[40:48] = b"E115\x01\x00\x01\x00"
        with self.assertRaises(ValueError):
            firmware_fields(data)

    def test_missing_zip(self):
        with self.assertRaises(FileNotFoundError):
            audit("/unused/there-is-no-such-file.zip")

    def test_invalid_pe(self):
        with self.assertRaises(ValueError):
            pe_fields(bytes(1024))


if __name__ == "__main__":
    unittest.main()
