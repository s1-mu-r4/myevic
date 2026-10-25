#!/usr/bin/env bash
# Local CI workspace only; never accesses or programs a connected device.
set -euo pipefail
ROOT="$(pwd)"
# GitHub checkout safe-directory entry is temporary and not inherited by this shell.
git config --global --add safe.directory "$ROOT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export SOURCE_DATE_EPOCH=1792902672
PINNED_RON7="08202453b54c2284df27c9f188f66c2b2fb0f92e"
PINNED_BSP="61f8103bfe58ae8853affdba8a01dcc26e41079e"
PINNED_EVIC="ef62fa601fd9b25d6261fdddf984cba462229b2b"
git merge-base --is-ancestor "$PINNED_RON7" HEAD

git clone --quiet https://github.com/OpenNuvoton/M451BSP.git "$TMP/bsp"
git clone --quiet https://github.com/ClockSelect/python-evic.git "$TMP/python-evic"
git -C "$TMP/bsp" checkout --quiet --detach "$PINNED_BSP"
git -C "$TMP/python-evic" checkout --quiet --detach "$PINNED_EVIC"
test "$(git -C "$TMP/bsp" rev-parse HEAD)" = "$PINNED_BSP"
test "$(git -C "$TMP/python-evic" rev-parse HEAD)" = "$PINNED_EVIC"

PYTHONPATH="$ROOT/tests/e115" python3 -m unittest discover -s tests/e115 -p "test_*.py" -v
python3 tests/e115/validate_fmcread_guard.py src/meusbd.c

python3 -m venv "$TMP/venv"
"$TMP/venv/bin/python" -m pip install --no-input \
  binstruct==1.0.1 bitarray==3.12.3 click==8.5.0 pillow==13.0.0
mkdir -p "$TMP/tools" "$TMP/sdk" "$TMP/build1" "$TMP/build2"
ln -s "$TMP/bsp" "$TMP/sdk/nuvoton-sdk"
cat > "$TMP/tools/evic" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec python3 -c 'from evic.cli import main; main()' "$@"
EOF
chmod +x "$TMP/tools/evic"
export PATH="$TMP/tools:$TMP/venv/bin:$PATH"
export PYTHONPATH="$TMP/python-evic"
export EVICSDK="$TMP/sdk" ARMGCC="/usr/lib"
printf 'LDFLAGS += -Map=bin/myevic.map\nCFLAGS += -fstack-usage\n' > "$TMP/map.mk"

for n in 1 2; do
  git archive HEAD | tar -x -C "$TMP/build$n"
  (
    cd "$TMP/build$n"
    make clean
    make -f Makefile -f "$TMP/map.mk" -j2 all
  )
done

for filename in myevic.elf myevic_dec.bin myevic.bin; do
  cmp "$TMP/build1/bin/$filename" "$TMP/build2/bin/$filename"
  sha256sum "$TMP/build1/bin/$filename"
done

python3 tests/e115/ron7_artifact_audit.py \
  "$TMP/build1/bin/myevic.elf" "$TMP/build1/bin/myevic_dec.bin" > "$TMP/elf.json"

python3 - "$TMP" <<'PY'
import json
from pathlib import Path
import re
import sys
root = Path(sys.argv[1])
report = json.loads((root/"elf.json").read_text())
assert report["raw_matches_selected_sections"], "selected sections differ from generated BIN"
assert report["initialization_matches_sections"], "startup RAMInitTable mismatch"
assert not report["load_lma_conflicts"], "overlapping ELF PT_LOAD bytes"
assert report["sections"][".sram"]["type"] == 8, ".sram is not NOBITS"
assert report["sections"][".raminit"]["size"] == 24, "RAM initialisation table size changed"
length = len((root/"build1/bin/myevic_dec.bin").read_bytes())
assert 0 < length <= 102400, "ROM limit exceeded"
assert length == report["sections"][".raminit"]["lma"] + 24, "virtual MSC FW length incomplete"
frames = {}
for su in (root/"build1").rglob("*.su"):
    for line in su.read_text(errors="replace").splitlines():
        m = re.search(r":([^:\t]+)\t(\d+)\t", line)
        if m:
            name, size = m.group(1), int(m.group(2))
            frames[name] = max(size, frames.get(name, 0))
            if name.startswith("hidWriteStoredProfile."):
                frames["hidWriteStoredProfile"] = max(size, frames.get("hidWriteStoredProfile",0))
for fn in ("hidGetOutReport", "SaveProfile", "hidWriteStoredProfile"):
    assert fn in frames, f"stack frame missing: {fn}"
assert frames["hidGetOutReport"]+frames["SaveProfile"] < 4096, "stack-frame pair with SaveProfile over limit"
assert frames["hidGetOutReport"]+frames["hidWriteStoredProfile"] < 4096, "stack-frame pair with stored profile over limit"
print("PASS: fixed-source fork offline build (NOT device qualified)")
print("ROM used:",length,"remaining:",102400-length)
print("USB stack frames:", {k:frames[k] for k in ("hidGetOutReport","SaveProfile","hidWriteStoredProfile")})
print("ELF LOAD conflicts:",report["load_lma_conflicts"])
print("NOTE: full call-chain ISR stack, USB behavior, recovery write remain NOT VERIFIED")
PY

echo "=== Patched source: Cortex-M startup consistency ==="
python3 tests/e115/diagnose_boot_image.py \
  "$TMP/build1/bin/myevic.elf" "$TMP/build1/bin/myevic_dec.bin"

echo "=== Original Ron7 source: same-toolchain forensic comparison ==="
mkdir -p "$TMP/upstream-original"
git archive "$PINNED_RON7" | tar -x -C "$TMP/upstream-original"
if (
  cd "$TMP/upstream-original"
  make clean
  make -f Makefile -f "$TMP/map.mk" -j2 all
) > "$TMP/upstream-build.log" 2>&1; then
  python3 "$ROOT/tests/e115/diagnose_boot_image.py" \
    "$TMP/upstream-original/bin/myevic.elf" \
    "$TMP/upstream-original/bin/myevic_dec.bin"
  sha256sum "$TMP/upstream-original/bin/myevic.bin"
  python3 - "$TMP" <<'PY'
from pathlib import Path
import struct
import sys
base=Path(sys.argv[1])
def vec(name):
  raw=(base/name/"bin/myevic_dec.bin").read_bytes()
  return {"bytes":len(raw),"initial_sp":hex(struct.unpack_from("<I",raw)[0]),
          "initial_pc":hex(struct.unpack_from("<I",raw,4)[0])}
print("Offline vector comparison:", {"upstream_original":vec("upstream-original"),
                                      "patched":vec("build1")})
print("Neither image is authorized for flashing")
PY
else
  echo "UPSTREAM ORIGINAL BUILD FAILED IN THIS TOOLCHAIN (diagnostic only)"
  tail -35 "$TMP/upstream-build.log"
fi
echo "OFFLINE ONLY — real E115 CFW boot FAIL; do not flash any candidate."

