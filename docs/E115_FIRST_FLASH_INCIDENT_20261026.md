# E115: first experimental CFW boot failure and successful stock restoration

**Reported:** 2026-10-26 JST. **Owner-reported evidence:** CFW_BOOT_FAIL; STOCK_RECOVERY_PASS.  
**Scope:** Ron7 `pufflimit` firmware, eVic VTwo Mini E115 HW 1.00. No device actions were performed by this repository or its CI.

## Observed sequence

1. Immediately following the owner's first CFW update, Windows displayed a **USB device not recognized** warning. The provided screenshot reports that the latest connected USB device malfunctioned and Windows cannot recognize it.
2. The device did not boot even when the battery was inserted.
3. The owner then held **+** while connecting USB and **successfully recovered the device by installing the manufacturer's stock FW**.

**Outcome:** Failed to start the experimental CFW. The stock LDROM-mediated recovery path succeeded once after this failure. Neither observation establishes the USB enumeration failure's internal cause or guarantees every future restoration scenario.

The screenshot, serial numbers, USB device-unique identifiers and physical firmware dumps are not copied into this public repository.

## Candidate fingerprint and evidence boundary

The test artifact published for this experiment by [CI #7](https://github.com/s1-mu-r4/myevic/actions/runs/40239433860) was named `ron7-pufflimit-e115-EXPERIMENTAL.bin`, length **100,500 bytes**, SHA256 `db6c67b897da841119f868e7b745cac70d010addac5438172df3987ef74d4046`.

The owner reported failure immediately after preparing for that test, but has not supplied a freshly computed hash of the **file actually selected in the desktop updater**. Accordingly, the candidate's exact bytes on the device are not yet independently confirmed. It is also unknown whether the downloader reported a complete write, whether any CONFIG changes occurred, and what errors—if any—appeared inside the updater.

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
| Exact firmware/update transaction | Current CI confirms output hash, not bytes actually stored in APROM | If safely available, owner file SHA and updater completion details; no hardware access needed |
| Hardware compatibility and protection | Product marker E115 matches, but may not capture every electrical/hardware variant | Board-specific startup assumptions and firmware map; no power test |

**Important:** Windows USB-unrecognized message is a symptom, not proof the USB descriptors or driver are defective. If firmware fails before USB starts, the same message is possible.

**Next test:** Reproduce fixed Ron7 original vs corrected source offline, then add reset/startup and memory-initialization invariants before proposing any new experimental firmware.

**Current decision: HARDWARE CFW BOOT FAIL / STOCK RESTORE PASS / NEXT FLASH NO-GO.**
