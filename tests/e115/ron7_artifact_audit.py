"""Offline Ron7 ELF32/objcopy contract, not an update or Flash validator."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def inspect(elf: bytes, raw: bytes) -> dict:
    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(elf):
            raise ValueError("truncated ELF")
        return struct.unpack_from(fmt, elf, offset)

    if elf[:6] != b"\x7fELF\x01\x01":
        raise ValueError("ELF32 little-endian required")
    h = unpack("<HHIIIIIHHHHHH", 16)
    if h[1] != 40 or h[8] != 32 or h[10] != 40:
        raise ValueError("ARM ELF32 tables required")
    phoff, shoff, phnum, shnum, strindex = h[4], h[5], h[9], h[11], h[12]
    if strindex >= shnum:
        raise ValueError("invalid section names")
    headers = [unpack("<IIIIIIIIII", shoff+40*i) for i in range(shnum)]
    nh = headers[strindex]
    names = elf[nh[4]:nh[4]+nh[5]]
    loads = []
    for i in range(phnum):
        p = unpack("<IIIIIIII", phoff+32*i)
        if p[0] == 1:
            if p[1]+p[4] > len(elf) or p[4] > p[5]:
                raise ValueError("invalid LOAD extent")
            loads.append(dict(offset=p[1], vma=p[2], lma=p[3],
                              filesz=p[4], memsz=p[5]))
    sections = {}
    for s in headers[1:]:
        if s[0] >= len(names):
            raise ValueError("invalid section name")
        name = names[s[0]:].split(b"\0", 1)[0].decode("ascii")
        if not s[2] & 2:
            continue
        matches = [p for p in loads if p["vma"] <= s[3]
                   and s[3]+s[5] <= p["vma"]+p["memsz"]
                   and (s[1] == 8 or
                        (s[4]-p["offset"] == s[3]-p["vma"]
                         and s[4]+s[5] <= p["offset"]+p["filesz"]))]
        if len(matches) != 1 or (s[1] != 8 and s[4]+s[5] > len(elf)):
            raise ValueError("ambiguous/unmapped allocated section: " + name)
        sections[name] = dict(type=s[1], vma=s[3], size=s[5], offset=s[4],
                              lma=matches[0]["lma"]+s[3]-matches[0]["vma"])
    selected = [".text", ".data", ".raminit"]
    if any(n not in sections for n in selected+[".sram"]):
        raise ValueError("missing Ron7 section")
    ranges = sorted((sections[n]["lma"], sections[n]["lma"]+sections[n]["size"])
                    for n in selected)
    if any(b > c for (_, b), (c, _) in zip(ranges, ranges[1:])):
        raise ValueError("selected LMA overlap")
    if ranges[0][0] != 0 or ranges[-1][1] > 0x20000:
        raise ValueError("unexpected APROM extent")
    reconstructed = bytearray(ranges[-1][1])
    for name in selected:
        s = sections[name]
        if s["type"] != 1:
            raise ValueError("selected section must be PROGBITS")
        reconstructed[s["lma"]:s["lma"]+s["size"]] = elf[s["offset"]:s["offset"]+s["size"]]
    table = sections[".raminit"]
    if table["size"] != 24:
        raise ValueError("unexpected RAMInitTable size")
    actual = unpack("<IIIIII", table["offset"])
    data, zero = sections[".data"], sections[".sram"]
    expected = (data["lma"], data["vma"], data["size"],
                zero["vma"], zero["vma"], zero["size"])
    overlaps, conflicts = [], []
    for i, a in enumerate(loads):
        for j, b in enumerate(loads[i+1:], i+1):
            start, end = max(a["lma"], b["lma"]), min(a["lma"]+a["filesz"], b["lma"]+b["filesz"])
            if start < end:
                overlaps.append([i, j, start, end])
                left = a["offset"]+start-a["lma"]
                right = b["offset"]+start-b["lma"]
                different = sum(x != y for x, y in zip(
                    elf[left:left+end-start], elf[right:right+end-start]))
                if different:
                    conflicts.append(dict(loads=[i, j], start=start,
                                          end=end, different_bytes=different))
    return dict(sections=sections, loads=loads, load_lma_overlaps=overlaps,
                load_lma_conflicts=conflicts,
                raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
                elf_sha256=hashlib.sha256(elf).hexdigest(),
                raw_matches_selected_sections=raw == reconstructed,
                initialization_table=list(actual), initialization_matches_sections=actual == expected,
                excluded_alloc_sections=[n for n in sections if n not in selected],
                conservative_load_end=max(p["lma"]+p["filesz"] for p in loads),
                note="OFFLINE_INSPECTED: no LDROM erase/CONFIG/Flash guarantee")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("raw", type=Path)
    args = parser.parse_args()
    result = inspect(args.elf.read_bytes(), args.raw.read_bytes())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["raw_matches_selected_sections"] and
                     result["initialization_matches_sections"] else 1)
