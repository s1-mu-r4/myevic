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
- The upstream [Ron7 `pufflimit` README](https://github.com/wighawag/myevic/tree/pufflimit) explicitly says **"It has NOT yet run on a device."** In a prior E-Cigarette Forum exchange on 2026-10-24, Ron7 also said **he had not obtained an eVic**, and asked the owner to test an E115. Thus his lack of an earlier hardware run is **already answered**, and he should not be asked the same question again. No other confirmed working limiter baseline has been provided. This makes an E115-specific diagnosis premature.
- Eight cold-start C function bodies, including `InitDevices`, `InitDataFlash`, `FMCCheckConfig`, `SetProductID`, `InitHardware`, `InitUSB` and `Main`, matched the 2019 upstream source. Yet compiled machine code, initial settings, BSP driver behavior and physical device state may differ.
- **CONFIG/LDROM are competing unconfirmed paths:** `FMCCheckConfig` can erase/rewrite CONFIG and reboot if DFEN/DFBA differ; `SetProductID` scans **actual physical LDROM** and calls `ResetToLDROM` if it finds no supported model ID. The E115 string in the **APROM file** does not prove the LDROM scan succeeded.
- The official archived Nuvoton **BSP v3.01.001** was **not obtained** (29B error response); the runner uses pinned **v3.01.003**. Do not call the older BSP differential a PASS. Further repetitive archive polling is suspended.


## Bounded Ron7 GCC6 comparison (2026-10-26)

Ron7 replied to the owner's first E115 FAIL report and published [`pufflimit-gcc6` commit `3405ec82`](https://github.com/wighawag/myevic/commit/3405ec82dfbf61a190740ee0cc4f6be9e6552ba1) (2026-10-26). He confirmed **no other limiter test device had booted**, and suspects toolchain modernization. This branch starts anew from the 2019 upstream source; it is **not a patch stacked atop the existing current-GCC `pufflimit` branch**.

**Direct GitHub file blob audit:** `src/pufflimit.c`, `inc/pufflimit.h`, `src/dataflash.c`, and `src/main.c` are byte-identical between the GCC6 branch, the existing `pufflimit` branch and this E115 experiment. The GCC6 branch instead uses the **unchanged original** `linker.ld`, `src/myevic.s` and `src/meusbd.c`; it does **not** carry this fork's USB scratch-stack separation, FMCREAD validation or SRAM LOAD/no-overlap patches. An older build is not intrinsically safer for hardware.

[One-off CI #34](https://github.com/s1-mu-r4/myevic/actions/runs/40315356577) executed Ron7's `build-gcc6.sh` at that immutable source commit, with the script's verified ARM GCC **6.3.1 (2017-q2)**, the **same pinned M451 BSP v3.01.003**, and the pinned `python-evic` converter. Both paths built, with no BIN artifact published or physical operation:

| GCC6 path | image size | free under 102400B | initial SP | Thumb PC | SHA256 of converter BIN |
|---|---:|---:|---|---|---|
| `--upstream` old myevic | **99,696B** | 2,704B | `0x20003788` | `0x15F9` | `9781129af956933c38b042eb2c1ff76b8cff3bfd39362ae2208032d43ed2bd27` |
| `pufflimit-gcc6` | **97,536B** | 4,864B | `0x20003760` | `0x15F9` | `c1e5a8484bcb05e9c18b8f036cf67efc87e7a3e6cd6d1ae8047f762665256bf2` |

**Interpretation:** Both 2017-GCC images stay within the explicit 100KiB ROM budget and have plausible Cortex-M4 vectors. This is a **working offline A/B control**, but neither BIN has been shown to boot on the owner's E115, and matching reset-vector addresses do not prove matching startup instructions, loader behavior or runtime safety.

**Narrow source caveat:** Ron7's statement that all limiter code runs *only* on FIRE is not literally true: `DFCheckValuesValidity()` calls `PLValidate()` during `InitDataFlash()`, and `ResetDataFlash()` invokes `PLResetDefaults()` before a settings write, **before** `InitUSB()`. The actual FIRE gate is indeed called at firing time. There is **no evidence** these startup validation/default routines caused this boot failure, but they should not be excluded categorically from a first-boot review.

**Decision:** Do **not** flash either GCC6 image now. The next useful discriminator is a source/ELF audit of the *old* GCC6 startup, CONFIG and USB/stack constraints and a discussion with Ron7 about the **pre-USB PLValidate/PLResetDefaults** paths. If an expendable device or explicit new risk-approved physical trial is considered later, apply a separately reviewed safety gate. No multi-step physical flashing without separate authorization.

The one-off GCC6 CI job was removed after its result was logged so it will not run on every future documentation change. The mandatory offline research job remains.

## Fixed work plan: two questions, then a stop/go decision

**Question A — Is there any actual known-good hardware run of this exact Ron7 limiter branch?**

Ron7 already confirmed in the October 24 E-Cigarette Forum exchange that his own implementation was untested and he did not have an eVic. **Do not repeat that question.** Report this first owner E115 result to Ron7 via the existing forum thread, with host completion, no boot, +/USB stock recovery, and local SHA256 match. Ask whether **another tester** has since obtained a working result or whether he sees a specific first-boot mechanism to prioritize. Require model/HW, exact source/BIN and build toolchain for any asserted success. Without such evidence, classify the feature as **generally unqualified on hardware**, not an E115-specific incompatibility.

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
