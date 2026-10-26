#!/usr/bin/env python3
"""Compile/test the guard copied verbatim from patched Ron7 C. No USB/device IO."""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

def check(path: Path):
    src = path.read_text()
    marker = "__myevic__ uint32_t hidFMCReadCmd( CMD_T *pCmd )"
    assert marker in src
    body = src.split(marker, 1)[1].split("//-------------------------------------------------------------------------", 1)[0]
    match = re.search(r"\bif\s*\((.*?)\)\s*\{\s*return -1;\s*\}", body, re.S)
    assert match, "missing FMCREAD rejection branch"
    cond = match.group(1)
    checks = ("u32ParamLen == 0", "% EP2_MAX_PKT_SIZE", "u32StartAddr & 3U", "0xFFFFFFFFU - u32ParamLen")
    assert all(part in cond for part in checks), "missing required FMCREAD guard"
    code = """#include <stdint.h>
#define EP2_MAX_PKT_SIZE 64
int gate(uint32_t u32StartAddr, uint32_t u32ParamLen) {
if (""" + cond + """) return -1;
return 0;
}
int main() {
  struct { uint32_t addr, length; int ok; } v[] = {
    {0,0,0},{0,1,0},{0,63,0},{0,64,1},{0,128,1},
    {0,2048,1},{0,4096,1},{1,64,0},{4,64,1},
    {0xffffffc0U,64,0},{0xffffff80U,64,1}
  };
  for (unsigned i=0; i<sizeof(v)/sizeof(*v); i++) {
    if ((gate(v[i].addr,v[i].length)==0) != v[i].ok) return i+1;
  }
  return 0;
}
"""
    with tempfile.TemporaryDirectory(prefix="ron7-fmc-guard-") as d:
        codepath = Path(d)/"test.c"
        prog = Path(d)/"test"
        codepath.write_text(code)
        subprocess.run(["cc","-std=c99","-Wall","-Wextra","-Werror",str(codepath),"-o",str(prog)],check=True)
        subprocess.run([str(prog)],check=True)
    print("PASS FMCREAD guard: 11 C-native vectors; length alignment, zero, addr alignment and overflow")
    print("NOTE command read-address whitelist and real USB receive state are NOT VERIFIED")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    args=parser.parse_args()
    check(args.source)
