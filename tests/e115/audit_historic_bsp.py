#!/usr/bin/env python3
"""Device-free forensic comparison of historic official M451 BSP and pinned 2018 BSP.

Only downloads a manufacturer's ZIP of source files and the public driver source
already checked out at the pinned BSP commit. Does not build firmware, execute
any archive content, write devices, or publish binary artifacts.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import difflib
import io
import os
import ssl
import sys
import urllib.request
import zipfile

URL = "https://www.nuvoton.com/opencms/resource-download.jsp?tp_GUID=SW0120140916095112"
MAX_DOWNLOAD = 90 * 1024 * 1024
FILES = ("clk.c", "fmc.c", "sys.c", "usbd.c")
PINNED = Path(os.environ.get("BSP_CHECKOUT", "/missing")) / "Library" / "StdDriver" / "src"


def controlled_fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; historical SDK file audit/1.0)",
        "Accept": "application/zip,application/octet-stream,*/*",
    })
    with urllib.request.urlopen(req, timeout=45, context=ssl.create_default_context()) as response:
        result = bytearray()
        while chunk := response.read(1024 * 1024):
            result.extend(chunk)
            if len(result) > MAX_DOWNLOAD:
                raise ValueError("vendor archive exceeds 90 MiB controlled limit")
        return bytes(result)


def main():
    print("Official original package URL:", URL)
    try:
        raw = controlled_fetch()
    except Exception as exc:
        print("HISTORIC_ARCHIVE_NOT_RETRIEVED:", type(exc).__name__, str(exc)[:250])
        return 0  # investigation inconclusive, NOT a successful source comparison
    print("Archive bytes:", len(raw), "SHA256:", sha256(raw).hexdigest())
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        print("HISTORIC_ARCHIVE_INVALID_OR_VENDOR_ERROR_PAGE")
        return 0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        selected = {}
        for name in FILES:
            candidates = [item for item in z.infolist()
                          if item.filename.replace("\\", "/").lower().endswith(
                              "/library/stddriver/src/" + name)]
            # The vendor can return either one top-level folder or plain Library/.
            if len(candidates) != 1:
                print("MISSING_OR_MULTIPLE_VENDOR_SOURCE", name, len(candidates))
                return 0
            info = candidates[0]
            if info.file_size > 2 * 1024 * 1024:
                print("UNEXPECTEDLY_LARGE_VENDOR_SOURCE", name)
                return 0
            selected[name] = z.read(info)
        total_delta = 0
        for name in FILES:
            old = selected[name]
            modern_path = PINN / name
            if not modern_path.is_file():
                print("PINNED_2018_BSP_MISSING", str(modern_path))
                return 1
            new = modern_path.read_bytes()
            old_lines = old.decode("utf-8", errors="replace").splitlines()
            new_lines = new.decode("utf-8", errors="replace").splitlines()
            sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
            ops = sm.get_opcodes()
            stat = Counter(tag for tag, *_ in ops)
            hunks = len(sm.get_grouped_opcodes(n=3))
            changed_lines = sum((ae-as_) + (be-bs)
                                for op,as_,ae,bs,be in ops if op != "equal")
            total_delta += changed_lines
            print("DRIVER", name,
                  "v3.01.001_sha256", sha256(old).hexdigest(),
                  "v3.01.003_sha256", sha256(new).hexdigest(),
                  "old_lines", len(old_lines), "new_lines", len(new_lines),
                  "changed_lines", changed_lines, "diff_hunks", hunks,
                  "equal", old == new)
            for part in sm.get_grouped_opcodes(n=2)[:6]:
                patch = list(difflib.unified_diff(old_lines, new_lines,
                     fromfile=f"v3.01.001/{name}",tofile=f"v3.01.003/{name}",
                     n=2, lineterm=""))
                # Bound the disclosure/CI logs to a representative preview.
                print("CHANGE_PREVIEW",name,"\n".join(patch[:36])[:2500])
                break
        print("HISTORIC_BSP_DIFF_FINISHED; changed_source_lines", total_delta)
    return 0

if __name__ == "__main__":
    sys.exit(main())
