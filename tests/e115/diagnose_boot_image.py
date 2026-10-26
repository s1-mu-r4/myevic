#!/usr/bin/env python3
"""Offline Cortex-M4 startup/layout invariants. Never reads or writes the device.
Produces useful PASS/FAIL evidence but DOES NOT prove on-device startup safety.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess

FLASH_END = 0x19000
SRAM_BEGIN = 0x20000000
SRAM_END = 0x20008000
NEEDED = (
    "Reset_Handler", "Stack_Top", "RAMInitTable", "RAMInitEnd",
    "Data_Start_ROM", "Data_Start_RAM", "Data_Size",
    "SRAMZ_Start", "SRAMZ_End", "SRAMZ_Size",
)

def symbols(elf: Path):
    result = subprocess.check_output(
        ["arm-none-eabi-nm", "--defined-only", str(elf)], text=True)
    found = {}
    for line in result.splitlines():
        m = re.match(r"^([0-9A-Fa-f]+)\s+([A-Za-z])\s+(\S+)$", line)
        if m:
            found[m.group(3)] = int(m.group(1), 16)
    missing = set(NEEDED) - set(found)
    if missing:
        raise ValueError(f"Required startup symbols missing: {sorted(missing)}")
    return found

def audit(elf: Path, image: Path):
    sym = symbols(elf)
    fw = image.read_bytes()
    assert 0 < len(fw) <= FLASH_END, "Image beyond 100 KiB user firmware limit"
    initial_sp, initial_pc = struct.unpack_from("<II", fw)
    assert initial_sp == sym["Stack_Top"], "vector SP not linker Stack_Top"
    assert SRAM_BEGIN < initial_sp <= SRAM_END and initial_sp % 8 == 0, "bad stack address"
    assert initial_pc & 1, "reset vector not Thumb"
    assert (initial_pc & ~1) == (sym["Reset_Handler"] & ~1), "reset entry mismatch"
    assert (initial_pc & ~1) < len(fw), "reset PC outside image"
    ptr = sym["RAMInitTable"]
    end = sym["RAMInitEnd"]
    assert end == ptr + 24, "exactly two 12-byte startup init records required"
    assert end <= len(fw), "RAM initialization table not in ROM image"
    table = struct.unpack_from("<6I", fw, ptr)
    expected = (
        sym["Data_Start_ROM"], sym["Data_Start_RAM"], sym["Data_Size"],
        sym["SRAMZ_Start"], sym["SRAMZ_Start"], sym["SRAMZ_Size"])
    assert table == expected, f"RAM init triples wrong: {table} != {expected}"
    assert table[0] + table[2] == ptr, "initialized data overlaps/misses init table"
    assert SRAM_BEGIN <= table[1] <= SRAM_END, "initialized data not in SRAM"
    assert table[1]+table[2] <= table[3], "initialized data overlaps BSS/stack"
    assert table[3]+table[5] == sym["SRAMZ_End"], "BSS zeroing span inconsistent"
    assert sym["SRAMZ_End"] <= SRAM_END, "BSS/stack exceeds SRAM"
    assert sym["SRAMZ_Start"] <= sym["Stack_Top"] <= sym["SRAMZ_End"], "stack not within reserved section"
    return {
        "size": len(fw),
        "initial_sp": f"0x{initial_sp:08X}",
        "initial_pc": f"0x{initial_pc:08X}",
        "reset_handler": f"0x{sym['Reset_Handler']:08X}",
        "ram_init_offset": f"0x{ptr:X}",
        "ram_init_triples": [f"0x{x:08X}" for x in table],
        "stack_top": f"0x{sym['Stack_Top']:08X}",
        "sram_zerofill_bytes": sym["SRAMZ_Size"],
        "data_init_bytes": sym["Data_Size"],
        "result": "PASS_STARTUP_LAYOUT_STATIC_ONLY",
    }

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("elf",type=Path)
    p.add_argument("bin",type=Path)
    args=p.parse_args()
    print(json.dumps(audit(args.elf,args.bin), indent=2))
