#!/usr/bin/env python3
"""Offline-only format/integrity triage of one known E115 stock FW ZIP.
Does not execute Windows EXE, access USB or HID, or modify firmware.
NOT a signature, exact hardware match, erase-range or recovery proof.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ZIP_SHA = "20ed1e118745c25df8b3c4dda036a2cc0f1c45a0a3bae6955a41178517fb9ed9"
MEMBERS = {
    "eVic_VTwo_mini_V5.04.bin": (70904, "c2dfa3034828b06081567eb384d90d8b5e2c9e8be8917a116cc8c2e1954f7274"),
    "UpdateFirmware.exe": (9972224, "9d1016e88791f9cb80f625a01c01970704e334a02039d52c76f5aea52c9b241f"),
    "Logo.bmp": (382, "4c86e48f209f192b7eb306f837214622a8a722d38231732db4e43b43dbce1fb4"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def aprom_xor(data):
    """Symmetric APROM format conversion from fixed ClockSelect/python-evic."""
    size = len(data)
    return bytes(b ^ ((size + 408376 + idx - size // 408376) & 0xFF)
                 for idx, b in enumerate(data))


def firmware_fields(cleartext):
    if len(cleartext) < 8 or b"Joyetech APROM" not in cleartext:
        raise ValueError("APROM marker missing")
    i = cleartext.find(b"E115")
    if i < 0 or i + 7 > len(cleartext):
        raise ValueError("E115 marker missing")
    sp, pc = struct.unpack_from("<II", cleartext)
    if not 0x20000000 <= sp <= 0x20008000 or not (pc & 1) or (pc & ~1) >= len(cleartext):
        raise ValueError("implausible vector table")
    # The legacy parser's lax value must NOT be called an exact HW version match.
    legacy_hw_value = struct.unpack("<I", b"\x00" + cleartext[i + 4:i + 7])[0]
    return {
        "e115_offset": i, "following_bytes": cleartext[i + 4:i + 8].hex(),
        "legacy_hw_check_value": legacy_hw_value,
        "sp": sp, "reset_vector": pc,
    }


def pe_fields(exe):
    if len(exe) < 512 or exe[:2] != b"MZ":
        raise ValueError("invalid MZ")
    p = struct.unpack_from("<I", exe, 0x3C)[0]
    if p + 24 + 128 > len(exe) or exe[p:p+4] != b"PE\x00\x00":
        raise ValueError("invalid PE signature")
    optional = p + 24
    if struct.unpack_from("<H", exe, optional)[0] != 0x10B:
        raise ValueError("not PE32")
    # IMAGE_OPTIONAL_HEADER32: DataDirectory starts at +96, SECURITY index 4.
    cert_offset, cert_size = struct.unpack_from("<II", exe, optional + 96 + 4 * 8)
    return {
        "has_authenticode_cert_entry": bool(cert_offset and cert_size),
        "references_hid_dll": b"HID.DLL" in exe,
        "references_setupapi": b"SETUPAPI.dll" in exe,
    }


def audit(path):
    raw = Path(path).read_bytes()
    if sha(raw) != ZIP_SHA:
        raise ValueError("ZIP SHA-256 differs from pinned specimen")
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC invalid")
        if set(z.namelist()) != set(MEMBERS):
            raise ValueError("unexpected member inventory")
        files = {}
        for name, (length, expected_hash) in MEMBERS.items():
            b = z.read(name)
            if len(b) != length or sha(b) != expected_hash:
                raise ValueError("member integrity mismatch: " + name)
            files[name] = b
    encrypted = files["eVic_VTwo_mini_V5.04.bin"]
    decoded = aprom_xor(encrypted)
    if aprom_xor(decoded) != encrypted:
        raise ValueError("APROM XOR round-trip failed")
    return {
        "zip_sha256": sha(raw),
        "members": {k: {"length": len(v), "sha256": sha(v)} for k, v in files.items()},
        "decrypted_sha256": sha(decoded),
        "firmware": firmware_fields(decoded),
        "updater": pe_fields(files["UpdateFirmware.exe"]),
        "status": "OFFLINE_FORMAT_PASS_ONLY",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="unmodified UpdateFirmware.zip")
    args = parser.parse_args()
    print(json.dumps(audit(args.archive), indent=2))
