# E115: first experimental CFW boot failure and successful stock restoration

**Reported:** 2026-10-26 JST. **Owner-reported evidence:** CFW_BOOT_FAIL; STOCK_RECOVERY_PASS.  
**Scope:** Ron7 `pufflimit` firmware, eVic VTwo Mini E115 HW 1.00. No device actions were performed by this repository or its CI.

## Observed sequence

1. Immediately following the owner's first CFW update, Windows displayed a **USB device not recognized** warning. The provided screenshot reports that the latest connected USB device malfunctioned and Windows cannot recognize it.
2. The device did not boot even when the battery was inserted.
3. The owner then held **+** while connecting USB and **successfully recovered the device by installing the manufacturer's stock FW**.

**Outcome:** Failed to start the experimental CFW. The stock LDROM-mediated recovery path succeeded once after this failure. Neither observation establishes the USB enumeration failure's internal cause or guarantees every future restoration scenario.

The screenshot, serial numbers, USB device-unique identifiers and physical firmware dumps are not copied into this public repository.

### Desktop updater screenshots clarified by owner (2026-10-26)

The owner supplied two additional screenshots from the same first-flash/recovery sequence. **Only the reported UI text is transcribed here; original screenshots, device-unique information, and Windows paths are not published.**

1. **After experimental CFW upload:** Joyetech `Update Firmware 1.20` displayed a modal **"Firmware update completed."** with a full progress bar. In the background, the device was labelled **"eVic VTwo mini"** and `Firmware Version: 5.04`. The latter may be a cached pre-update firmware version; it is **not** evidence that the new CFW ever executed or that stock FW remained active.
2. **After reconnecting with '+' held:** The same updater recognized **"eVic VTwo mini"**, `Firmware Version: 0.00`, `Hardware Version: 1.00`. This is consistent with the observed LDROM/recovery-mode response and with the later successful stock-firmware restoration. The zero firmware version does **not** prove APROM is empty or identify exactly how boot failed.

**Revised diagnosis boundary:** The host updater did **not** present an in-process error in the supplied completion screenshot. The failure occurred **despite host-reported successful transfer**, followed by Windows USB non-recognition and no battery-powered startup. This prioritizes a post-transfer boot failure (or a mismatch between host completion and stored APROM bytes) over an obvious interrupted host update. Host success is not verified target Flash readback. Exact execution stop point remains unknown.


## Candidate fingerprint and evidence boundary

The test artifact published for this experiment by [CI #7](https://github.com/s1-mu-r4/myevic/actions/runs/40239433860) was named `ron7-pufflimit-e115-EXPERIMENTAL.bin`, length **100,500 bytes**, SHA256 `db6c67b897da841119f868e7b745cac70d010addac5438172df3987ef74d4046`.

**Owner-provided Windows PowerShell check (2026-10-26):** `Get-FileHash` of the locally retained `ron7-pufflimit-e115-EXPERIMENTAL.bin` returned SHA-256 `DB6C67B897DA841119F868E7B745CAC70D010ADDAC5438172DF3987EF74D4046`, **exactly matching the CI #7 artifact**. This rules out an altered or misidentified *local file*. The user's absolute Windows account path is intentionally omitted. The updater transaction log and independent readback of APROM have not been provided, so the exact bytes accepted/programmed by the device are still not independently proven. A subsequent screenshot confirms that the updater **reported firmware update completion without displaying an error**; see the UI-evidence section below. Actual CONFIG changes remain unknown.

A passing build, ROM-size audit, ELF LOAD consistency and synthetic USB stack frame test do **not** establish ARM reset execution or hardware safety.

## Action and risk gate

- **NO-GO: do not use or reflash the test candidate.** Do not attempt trial-and-error modifications on the recovered owner device.
- After this incident, source control [disabled future executable BIN uploads](https://github.com/s1-mu-r4/myevic/commit/ba2c4eb9d8bb30e650a8e1d81ebe5fae709b1357) in the CI workflow. The previously uploaded CI #7 artifact remains in historical GitHub Actions until its expiry/manual deletion. This repository's connected automation cannot delete that existing artifact.
- Keep the experiment Draft, do not merge to `pufflimit`/`master`, do not modify upstream Ron7.
- Record successful stock recovery, but do not equate successful *reinstallation of stock* with complete restoration of original flash settings or CONFIG values.
- Perform all next root-cause work **offline only**.

## Offline diagnostic priorities, none yet proven

| Area | Reason to investigate | Evidence needed |
|---|---|---|
| Startup/vector/ROM layout | Display and battery startup failed, so failure may precede USB initialization | Decoded initial SP/PC, Reset_Handler branch, RAMInitTable triplets, section LMA, BSS and stack bounds |
| DataFlash and CONFIG first boot | `InitDataFlash()` can call `FMCCheckConfig()`, which may change CONFIG and reset on mismatch | Source trace and target-state distinctions; **no new real CONFIG writes/read commands** |
| Clock and USB setup | USB enumeration failed after the update | Determine whether CPU got as far as descriptor setup, or failed earlier |
| Exact firmware/update transaction | Local BIN hash matches CI; host updater displayed 'Firmware update completed'; APROM write/readback was not independently verified | Inspect host updater success/verification semantics offline; no device writes |
| Hardware compatibility and protection | Product marker E115 matches, but may not capture every electrical/hardware variant | Board-specific startup assumptions and firmware map; no power test |

**Important:** Windows USB-unrecognized message is a symptom, not proof the USB descriptors or driver are defective. If firmware fails before USB starts, the same message is possible.

**Next test:** Reproduce fixed Ron7 original vs corrected source offline, then add reset/startup and memory-initialization invariants before proposing any new experimental firmware.

**Current decision: HARDWARE CFW BOOT FAIL / STOCK RESTORE PASS / NEXT FLASH NO-GO.**

## Offline forensic follow-up (2026-10-26, GitHub Actions #13)

[GitHub Actions #13](https://github.com/s1-mu-r4/myevic/actions/runs/40241452939) compiled **both** the pinned original Ron7 `pufflimit` and current amended firmware in the same isolated ARM toolchain, without firmware upload or hardware access. A new source/ELF/raw-BIN audit checked the initial Cortex-M4 SP and reset vector against linker symbols and both startup RAM-init records against the exact embedded values.

| Invariant | Original `pufflimit` | Current revised build |
|---|---|---|
| Decoded BIN | 100,456 B | 100,500 B |
| Initial SP | `0x20003778` | `0x20003778` |
| Initial PC (Thumb) | `0x000015CD` | `0x000015CD` |
| Reset_Handler | `0x000015CC` | `0x000015CC` |
| RAM copy size | `0x1A4` = 420 B | same |
| SRAM zero-init size | `0x35D0` = 13,776 B | same |
| RAMInitTable LMA | `0x18850` | `0x1887C` |
| Startup static symbol/table checks | PASS | PASS |

Both images have self-consistent symbols and RAM initialization table. This **rules out an obvious static reset-vector mismatch and a simple missing/wrong RAM init table** as an explanation. It does **not** demonstrate runtime execution, correctness of the clock tree, flash CONFIG settings, or any USB code path.

### Earliest code paths before USB enumeration

The source-level cold-start ordering in this fork is:

1. `Reset_Handler` → `Startup` copies and clears RAM → `Main`.
2. `Main` → `InitDevices` enables/awaits high-frequency crystal and sets clocks.
3. `Main` → `InitVariables` → `InitDataFlash` → `FMCCheckConfig`. If CONFIG0/1 do not match, `FMCCheckConfig` can erase/write CONFIG and issue `SYS_ResetChip()`. The owner's starting CONFIG contents are unknown.
4. `Main` → `InitHardware`. When the saved `x32off` flag is not set, this routine starts the low-frequency 32.768 kHz crystal and **waits for ready**.
5. Only later does `InitHardware` call `InitUSB`; display setup and the ordinary main loop follow.

Thus a reset loop or stalled clock readiness **before** `InitUSB` can yield a non-enumerating USB device even when the USB descriptor code is correct. This is a candidate mechanism **not a diagnosis**; there is no trace from this hardware proving how far the CPU reached.

**Next priority:** source-only checks of boot-time CONFIG behavior, clock readiness/timeouts, and target hardware assumptions. Do not change the image or repeat flashing until a candidate fault is supported by evidence.
