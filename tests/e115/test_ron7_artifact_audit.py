"""Synthetic ELF fault vectors; no firmware or device operations."""
import struct
import unittest

from ron7_artifact_audit import inspect


def fixture():
    names = b"\0.text\0.data\0.sram\0.raminit\0.shstrtab\0"
    image = bytearray(0x600)
    image[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHIIIIIHHHHHH", image, 16,
                     2, 40, 1, 1, 52, 0x400, 0, 52, 32, 4, 40, 6, 5)
    # .sram's conservative load interval overlaps .raminit, as in Ron7.
    segments = [(0x100, 0, 0, 4), (0x200, 0x20000000, 4, 4),
                (0x300, 8, 8, 24), (0x320, 0x20000008, 16, 32)]
    for i, (offset, vma, lma, size) in enumerate(segments):
        struct.pack_into("<IIIIIIII", image, 52 + 32*i,
                         1, offset, vma, lma, size, size, 6, 4)
    image[0x100:0x104] = b"TEXT"
    image[0x200:0x204] = b"DATA"
    table = struct.pack("<IIIIII", 4, 0x20000000, 4,
                        0x20000008, 0x20000008, 32)
    image[0x300:0x318] = table
    image[0x380:0x380+len(names)] = names
    specs = [(".text", 1, 6, 0, 0x100, 4),
             (".data", 1, 3, 0x20000000, 0x200, 4),
             (".sram", 1, 3, 0x20000008, 0x320, 32),
             (".raminit", 1, 3, 8, 0x300, 24),
             (".shstrtab", 3, 0, 0, 0x380, len(names))]
    for i, (name, kind, flags, vma, offset, size) in enumerate(specs, 1):
        struct.pack_into("<IIIIIIIIII", image, 0x400+40*i,
                         names.index(name.encode()), kind, flags,
                         vma, offset, size, 0, 0, 4, 0)
    return image, b"TEXTDATA" + table


class ArtifactVectors(unittest.TestCase):
    def test_selected_bin_and_initialization_table(self):
        elf, raw = fixture()
        result = inspect(elf, raw)
        self.assertTrue(result["raw_matches_selected_sections"])
        self.assertTrue(result["initialization_matches_sections"])
        self.assertEqual(result["raw_bytes"], 32)

    def test_conservative_overlap_stays_separate_from_bin(self):
        elf, raw = fixture()
        result = inspect(elf, raw)
        self.assertEqual(result["load_lma_overlaps"], [[2, 3, 16, 32]])
        self.assertGreater(result["load_lma_conflicts"][0]["different_bytes"], 0)
        self.assertTrue(result["raw_matches_selected_sections"])

    def test_missing_raminit_bytes_rejected(self):
        elf, raw = fixture()
        self.assertFalse(inspect(elf, raw[:8])["raw_matches_selected_sections"])

    def test_wrong_copy_source_detected(self):
        elf, raw = fixture()
        struct.pack_into("<I", elf, 0x300, 12)
        self.assertFalse(inspect(elf, raw)["initialization_matches_sections"])

    def test_selected_section_collision_rejected(self):
        elf, raw = fixture()
        struct.pack_into("<I", elf, 52 + 32*2 + 12, 4)
        with self.assertRaisesRegex(ValueError, "selected LMA overlap"):
            inspect(elf, raw)

    def test_truncated_elf_rejected(self):
        elf, raw = fixture()
        with self.assertRaises(ValueError):
            inspect(elf[:0x420], raw)

    def test_big_endian_rejected(self):
        elf, raw = fixture()
        elf[5] = 2
        with self.assertRaises(ValueError):
            inspect(elf, raw)
