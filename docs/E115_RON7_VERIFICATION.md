# E115 verification of Ron7 `pufflimit` (research only)

**Upstream:** [wighawag/myevic](https://github.com/wighawag/myevic), branch `pufflimit`, fixed starting commit `08202453b54c2284df27c9f188f66c2b2fb0f92e`. This is a derivative under the upstream GPL-3.0 license. The original code history is retained.

**Target:** Joyetech eVic VTwo Mini (E115, hardware 1.00). The objective is to determine whether Ron7's *existing* firmware and puff count limit can safely be tested on a physical E115. No new scheduling, usage-budget or logging features are introduced.

## Minimal changes under review

- `src/meusbd.c`: Isolate the USB SETPROFILE scratch page in a non-inlined helper, preventing it from coexisting in the same call stack with `SaveProfile()`'s separate 2 KiB scratch page.
- `linker.ld`: Mark the SRAM initialization area `NOLOAD`, eliminating a conflicting file-backed LOAD region.
- `src/myevic.s`: Include the complete RAM initialization table in the virtual firmware-file size.
- `src/meusbd.c`: Reject invalid FMCREAD lengths, unaligned addresses and arithmetic overflow.

## Prior controlled test result

The exact equivalent source changes were previously tested in a reproducible ARM GCC 12.2.1 offline build. Two clean builds gave identical ELF, raw BIN and converted BIN. The resulting image was **100,500 bytes** (1,900 bytes below the linker ROM limit); the identified USB function-stack pairs were 2,144 and 2,136 bytes, and there were no conflicting ELF LOAD bytes. The ROM size is **not** proof of firmware safety. The tests under `tests/e115` repeat the build and source/ELF checks inside this fork.

## Unverified and prohibited actions

Physical-device startup, protective shutoff, puff counter behavior, interrupt-stack peaks, and stock-LDROM recovery **have not been validated**. The presence of a responsive LDROM does not establish a successful flash/restore path. No firmware binaries are committed, uploaded as release artifacts, or offered for installation.

**NO-GO for flashing.** No USB/HID device access, firing, CONFIG changes, SWD, or merge to the upstream branch is part of this research PR. Proceed to physical testing only after a separate safety and recovery review.

## Recovery and stock-firmware readiness

See [`E115_RECOVERY_PREFLIGHT.md`](E115_RECOVERY_PREFLIGHT.md) for manufacturer-sourced USB recovery instructions, device-free stock V5.04 ZIP verification, and a precise accounting of what is still not known about proprietary LDROM writes. This document describes a **possible recovery path, not a guarantee**. Never connect the firmware updater merely to infer that its operations are read-only.

A device-free checker is available as `python3 tests/e115/e115_stock_zip_audit.py /path/to/UpdateFirmware.zip`. The genuine stock ZIP is **not** stored in GitHub and must be obtained from the manufacturer. This preflight does not change the no-flash ruling.
