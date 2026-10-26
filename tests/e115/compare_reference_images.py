#!/usr/bin/env python3
"""Offline-only APROM comparison, NEVER an installation or device utility."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

def decode(blob: bytes):
    size = len(blob)
    return bytes(b ^ ((size + 408376 + i - size // 408376) & 255) for i, b in enumerate(blob))

def describe(path: Path):
    blob = path.read_bytes()
    raw = decode(blob)
    sp, pc = struct.unpack_from("<II", raw)
    # A plain "E115" substring can occur in a UI list of products,
    # e.g. "E115E196"; it is NOT a verified target product record.
    specific_marker = b"E115\x01\x00\x01\x00"
    e115 = raw.find(specific_marker)
    ordinary_E115_offsets = [i for i in range(len(raw)-3) if raw[i:i+4] == b"E115"]
    joy = raw.find(b"Joyetech APROM")
    expected = (
        e115 >= 0 and 0x20000000 < sp <= 0x20008000
        and bool(pc & 1) and (pc & ~1) < len(raw)
    )
    return {
        "file": path.name, "bytes": len(blob),
        "encrypted_sha256": hashlib.sha256(blob).hexdigest(),
        "decoded_sha256": hashlib.sha256(raw).hexdigest(),
        "vector_sp": f"0x{sp:08X}", "vector_pc": f"0x{pc:08X}",
        "joyetech_aprom_offset": joy, "E115_hw100_record_offset": e115,
        "raw_E115_substring_offsets": ordinary_E115_offsets,
        "product_marker_following_bytes": raw[e115+4:e115+8].hex() if e115 >= 0 else None,
        "has_pufflimit_text": b"pufflimit" in raw.lower() or b"puff limit" in raw.lower(),
        "E115_vector_plausible_not_verified_hardware": expected,
    }, raw

def compare(paths):
    results = [describe(p) for p in paths]
    meta = [m for m, _ in results]
    comparison = []
    for i in range(1, len(results)):
        prior = results[0][1]
        other = results[i][1]
        min_len = min(len(prior), len(other))
        mismatch = sum(a != b for a, b in zip(prior[:min_len], other[:min_len]))
        first = next((j for j, (a,b) in enumerate(zip(prior, other)) if a != b), None)
        comparison.append({
            "base": meta[0]["file"], "other": meta[i]["file"],
            "equal": prior == other, "first_decoded_mismatch": first,
            "raw_decoded_byte_mismatches_in_common_span": mismatch,
            "length_difference": len(other) - len(prior),
            "warning": "Byte positions after an insertion/section-layout change do not imply matching symbol offsets.",
        })
    return {"images":meta,"relative_to_first":comparison,
            "evidence_note":"No APROM readback/device verification. A tracked shipped BIN may be older than the currently committed source."}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", type=Path, nargs="+")
    args = ap.parse_args()
    if len(args.images) < 2: ap.error("provide at least two images")
    print(json.dumps(compare(args.images), indent=2))
