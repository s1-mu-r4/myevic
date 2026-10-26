# E115 first-boot research — current decision and bounded plan

**State:** **STOP / NO-GO for experimental CFW reflash** · **Last reviewed:** 2026-10-26 (JST).
**Scope:** Evaluate **Ron7's existing `pufflimit`**, not develop new limiter features. This Draft PR is a **research record, not a merge candidate**.

## One-screen status

| Subject | State |
|---|---|
| Device | eVic VTwo Mini, E115/HW 1.00 |
| Exact downloaded test image | SHA256 independently matched CI output; 100,500B |
| Desktop update | Reported `Firmware update completed` |
| Experimental firmware | **FAILED** to boot; USB not recognized |
| Manufacturer stock restore | **SUCCEEDED** after +/USB recovery entry |
| First-stage CPU execution and APROM readback | **UNKNOWN** |
| Root cause | **UNKNOWN** |
| CI | Offline/static checks **PASS**; **never a device qualification** |
| Branches | Keep `pufflimit` and `master` unmodified |
| Executable firmware artifacts | No new publishing or user-device writes |

Full, source-linked evidence: [`E115_FIRST_FLASH_INCIDENT_20261026.md`](E115_FIRST_FLASH_INCIDENT_20261026.md).

### Important correction to earlier hypotheses

- The tracked **99,700B `bin/myevic.bin` is a 2019 upstream build**, predating the limiter introduced on **2026-10-25**. It is **not** a previously working Ron7 limiter binary, and different vectors/size are not proof of a defect.
- The upstream [Ron7 `pufflimit` README](https://github.com/wighawag/myevic/tree/pufflimit) explicitly says **"It has NOT yet run on a device."** There is currently **no confirmed working limiter baseline** in the public branch. This makes a device-specific E115 diagnosis premature.
- Eight cold-start C function bodies, including `InitDevices`, `InitDataFlash`, `FMCCheckConfig`, `SetProductID`, `InitHardware`, `InitUSB` and `Main`, matched the 2019 upstream source. Yet compiled machine code, initial settings, BSP driver behavior and physical device state may differ.
- **CONFIG/LDROM are competing unconfirmed paths:** `FMCCheckConfig` can erase/rewrite CONFIG and reboot if DFEN/DFBA differ; `SetProductID` scans **actual physical LDROM** and calls `ResetToLDROM` if it finds no supported model ID. The E115 string in the **APROM file** does not prove the LDROM scan succeeded.
- The official archived Nuvoton **BSP v3.01.001** was **not obtained** (29B error response); the runner uses pinned **v3.01.003**. Do not call the older BSP differential a PASS. Further repetitive archive polling is suspended.

## Fixed work plan: two questions, then a stop/go decision

**Question A — Is there any actual known-good hardware run of this exact Ron7 limiter branch?**

Check evidence from Ron7 (or another tester) for: hardware model + HW revision; the exact firmware source commit and SHA of the BIN flashed; build toolchain/BSP; whether the device reached its menu and USB; any boot failures or fixes. The public README currently states **untested**. If there are **no controlled successful reports**, classify the feature as **generally unqualified on hardware**, not an E115-only failure. Do not manufacture a “known good” control from the 2019 old binary.

**Question B — What does the updater's "Firmware update completed" acknowledge, and where could APROM stop before USB enumeration?**

Use **source/offline analysis only** to determine whether the host received a transport ACK, final-write ACK, readback verification or something else. Then review just the pre-USB `Reset_Handler → InitDevices → InitDataFlash (CONFIG, LDROM ID) → InitHardware → InitUSB` boundary. Seek *one discriminating signature* that separates host-success/actual-image failure from first-boot reset/diversion; do not proliferate test matrices or papers.

**Gate:** After A and B, provide a compact choice:
1. **GO for offline patch review only** if a concrete, reproducible cause is supported and the patch has an identifiable acceptance test; **still no physical reflashing** without separately accepting device risk and reviewing the exact new candidate.
2. **STOP/ARCHIVE** if evidence cannot separate causes without another hardware readback or a known-good device. Consider a separate expendable verified-compatible unit, or change approach. Do not continue generic v3.01.001 hunting or incrementally author new reports.

## Repository discipline

- **Two live documents only:** this decision file + the linked incident evidence. Historical details are preserved in earlier [Git tree](https://github.com/s1-mu-r4/myevic/tree/5266feea7f2521170e1ea91271df40f8b13a0e35/docs) and CI logs.
- No new Markdown reports, variants of build scripts, fresh hypotheses or test cases unless one of the two questions demonstrably needs it to change the decision.
- Disable the repeated failing `historical-bsp` CI job and the optional 2019 modernized control build (known to exceed ROM by 144B). Preserve mandatory reproducible ARM build, static consistency tests and original-vs-patched comparison.
- Do not merge or force-push, send USB/HID commands, disassemble hardware, use SWD/Nu-Link, or publish installable BINs.
- Progress = a hypothesis eliminated by **new discriminating evidence**, a supported and reviewed minimal patch, or an independently observed hardware outcome. **Green test counts are not root-cause progress.**

**Current decision remains: STOP / preserve the owner's restored stock firmware.**
