# E115 startup failure — evidence-led offline root-cause triage (2026-10-26)

**Scope:** Experimental Ron7 `pufflimit` update to owner eVic VTwo Mini E115/HW1.00. This document does not introduce product features and never authorizes another flash.

## Confirmed real-device facts (owner supplied)

- Local experimental `ron7-pufflimit-e115-EXPERIMENTAL.bin` SHA256 `db6c67b897da841119f868e7b745cac70d010addac5438172df3987ef74d4046` matches the CI-produced file; 100,500B.
- Joyetech Updater 1.20 displayed **"Firmware update completed."** after the transfer. This is a host-side completion indication, **not independently checked target-APROM readback**.
- Immediately after update, Windows displayed USB device not recognized, and the device did not boot with battery installed.
- **+** held at USB insertion reached a recovery presentation (`Firmware Version: 0.00; Hardware Version: 1.00`), after which the owner **successfully installed stock FW**. This proves one real LDROM recovery event, not resilience to arbitrary failures.

See [first-flash incident](E115_FIRST_FLASH_INCIDENT_20261026.md). The original screenshots and user-specific device information are not publicly committed.

## New differential: shipped image versus rebuilds

[GitHub Actions #19](https://github.com/s1-mu-r4/myevic/actions/runs/40243396498) compared the **pinned Ron7 repo's already tracked** `bin/myevic.bin` to original source rebuilt with the pinned current ARM toolchain and to the experimental patched build. Comparison decoded the APROM transport format before inspecting vectors.

| Property | Shipped in Ron7 Git | Rebuilt original Ron7 source | Experimental patched CFW |
|---|---|---|---|
| Byte count | **99,700** | **100,456** | **100,500** |
| Encrypted SHA-256 | `b2dd2d1f917ecf7a439b79acae97b4c25315dae0222c82e8d8442989b9bbf750` | `a8d8a7807784765e64fd00d2498a7ae9574f0dc5e613a9db5616de7207bab0b8` | `db6c67b897da841119f868e7b745cac70d010addac5438172df3987ef74d4046` |
| Vector SP | `0x20003788` | `0x20003778` | `0x20003778` |
| Vector PC | `0x000015F9` | `0x000015CD` | `0x000015CD` |
| **Exact E115/HW1.00 record offset** | 77,128 | 79,124 | 79,168 |
| E115 record bytes | `45 31 31 35 01 00 01 00` | same | same |

All three binaries have a plausible Thumb reset vector and an exact E115/HW1.00 identifier record. This **rejects the simplest hypothesis that the tested BIN lacks the E115 product record**; it does not prove compatibility or correct bootloader recognition.

**Material build discrepancy:** Ron7's *tracked shipped binary* is not identical to a current-toolchain recompilation of the same pinned commit; their stack top, reset-vector address, size, and overall bytes differ. This may reflect historical toolchain/BSP/build flags or an out-of-date checked-in BIN. It is a **lead, not a diagnosed flaw**, and the shipped binary has **not** been tested on this E115. Do not flash any of these images as a control on the recovered unit.

**Important test correction:** A naive `raw.find(b"E115")` also matches a product-name list `E115E196`, not the product record. The image audit now searches for the full eight-byte E115/HW1.00 sequence. Earlier reports of a generic E115 substring alone were insufficient.

## Firmware cold-start gates before USB descriptors

These are direct source paths, each of which could fail without Windows receiving a valid USB descriptor:

1. **ROM vector/RAM initialization.** `Reset_Handler` → `Startup` → `Main`. [Actions #13](https://github.com/s1-mu-r4/myevic/actions/runs/40241452939) checked SP, Thumb PC, zeroed SRAM region and two `RAMInitTable` triplets. Both rebuilt original and experimental patched builds passed the **static** invariants. That does not prove real execution.
2. **Clock tree.** [`src/main.c`](../src/main.c), `InitDevices()` enables HIRC and external 12 MHz HXT, calls `CLK_WaitClockReady`, sets PLL/HCLK, WDT. Pinned Nuvoton [M451BSP `clk.c`](https://github.com/OpenNuvoton/M451BSP/blob/61f8103bfe58ae8853affdba8a01dcc26e41079e/Library/StdDriver/src/clk.c) shows `CLK_WaitClockReady` has a **bounded timeout** (~300ms), *not* an infinite busy wait. But `InitDevices` ignores the readiness return value in its HXT path, allowing further initialization with an unstable/failed clock.
3. **CONFIG and data settings.** `Main → InitVariables → InitDataFlash → FMCCheckConfig`. [`src/dataflash.c`](../src/dataflash.c) can erase/rewrite CONFIG and software-reset when CONFIG0 DFEN or CONFIG1 DFBA does not match its expected location. Actual CONFIG0/1 before and after first CFW boot were **never measured**. Do not assume a valid USB transfer leaves CONFIG untouched.
4. **LDROM-based model discovery.** In `SetProductID()`, firmware scans *physical LDROM* with `FMC_Read(LDROM_BASE+offset)` for known model identifiers; if **no supported model ID is found**, it calls `ResetToLDROM()` (which sets the next boot mode and does not return normally). This is an **early pre-USB self-diversion path**. The known E115/HW1.00 marker in the *APROM file* is **not evidence that a readable matching code exists in this device's LDROM**. The owner's old GETINFO snapshot likewise does not disclose the entire LDROM.
5. **RTC crystal and USB.** `Main → InitHardware` may enable 32.768 kHz LXT depending on saved configuration, and only later invokes `InitUSB()`. The pinned SDK has bounded clock-ready timeout, but the caller may continue in an invalid condition. Actual USB descriptors and firmware stage reached are unknown.

### Ranking for further work (not statistical likelihoods)

| Priority | Candidate | Why | Safe resolution/evidence |
|---|---|---|---|
| P1 | **Built source ≠ shipped Ron7 BIN; toolchain, BSP and layout evolution** | Definitively different 99,700 vs 100,456/100,500B images and reset vectors, without any tested good control on owned unit | Reconstruct original historical compiler/BSP from upstream documentation; compare *semantic* call sites, startup code and instructions with shipped image. No firmware installation |
| P1 | **LDROM model-ID scan fallback** | Reaches `ResetToLDROM()` before `InitUSB()` when marker lookup fails | Analyze exact E115 loader identifier format/source and scanner. If no safe device read exists, label unresolved. Never infer it from APROM string |
| P1 | **First-start CONFIG/DFBA reset and retained device settings** | May change boot/data mapping and reset before any UI/USB | Prove CONFIG conditional paths symbolically, and compare expected stock settings from public documentation. No blind CONFIG repair or reset on owner device |
| P2 | **Clock readiness and MCU peripheral initialization** | Clock-ready result is ignored by part of `InitDevices`; USB cannot function with broken clocks | Host simulate timeout/error branches and check safe failure policy; no powered device testing until a supported alternative exists |
| P2 | **Updater reports success without APROM readback** | Device CFW did not boot despite GUI completion | Compare updater/LDROM implementation and response semantics. Do not send read commands or repeat write on E115 |

Historical precedent only: [myevic issue #2](https://github.com/ClockSelect/myevic/issues/2) described an older 2016 DF CRC/HW-version corruption bug and a later fix. The owner's recovery updater still showed HW1.00. **This is not evidence that the old bug recurred.** The original myevic [compatibility list](https://github.com/ClockSelect/myevic/blob/master/git_doc_en/usageandcompatibility_en.md) includes eVic VTwo Mini, but doesn't certify this 2026-built image.

## Proposed resolution sequence (offline only)

1. Use pinned original source, checked-in shipped binary and rebuilds to diff **compiler and startup semantics**, not just byte offsets. Prefer a historically documented old compiler/BSP build as baseline and compare assembly/ELF output. Keep all firmwares private as research data; **no Actions firmware artifact uploads**.
2. Add a **simulation of first-boot states** (CONFIG match/mismatch, LDROM product-ID found/missing, HXT/LXT ready/timeout) and record whether boot proceeds to `InitUSB`, resets or fails. The simulation is not a substitute for hardware observation.
3. Investigate the updater's claim of completion via offline disassembly/specs only. Hardware readback is not independently available and should not be asserted as completed.
4. Evaluate changes such as bounded error/fail-closed handling for clock timeout, an explicit model-identification error path, and non-destructive first-start CONFIG validation **as source proposals only**. Each changes safety-critical startup behavior and requires a new separate review; never “just bypass” model identity or disable protection.
5. **DO NOT issue another firmware write** on the recovered E115. Consider a separate sacrificial verified-compatible test device, or wait until a credible cause can be proven with non-invasive evidence. No automatic firmware release, flash instruction, or merge to the protected branch.

**Current state:** Original physical firmware recovered. Test CFW failed. None of the hypotheses have been confirmed as the direct root cause.
