# E115 first-boot forensic follow-up — historical BSP and pre-USB source comparison

**Research date: 2026-10-26 (JST). Status: no demonstrated root cause, physical flash halted.**

## Source comparison results: unchanged boot decision functions

Compared the source function bodies in the 2019 upstream base [`546394bcf1`](https://github.com/wighawag/myevic/commit/546394bcf1ac9ab63381fa2fb484a0dfa11d443f) against current [E115 research fork](https://github.com/s1-mu-r4/myevic/pull/1) without relying on approximate diff locations:

| Function | Identical source across versions? | Role before USB |
|---|---|---|
| `InitDevices()` | **Yes** | HIRC/HXT/PLL, USB clock and watchdog |
| `InitHardware()` | **Yes** | LXT attempt, GPIO, peripheral setup, then `InitUSB()` |
| `InitDataFlash()` | **Yes** | Reads CONFIG, parameters, counter pages, discovers model |
| `FMCCheckConfig()` | **Yes** | May erase/write CONFIG and reset if DFEN or DFBA differs |
| `SetProductID()` | **Yes** | Reads actual LDROM ID; if not found, calls `ResetToLDROM()` |
| `ResetToLDROM()` | **Yes** | Set boot selection and reset |
| `InitUSB()` | **Yes** | Configure and start USB subsystem |
| `Main()` | **Yes** | Cold-start call order |

**Interpretation:** The 2026 limiter feature and the current minimal-fix branch did not directly rewrite these particular boot-time C bodies. This makes a newly edited conditional in one of them a weaker hypothesis. It does **not** show that their compiled instructions, linked addresses, peripheral-driver callees, initial data state or the actual physical boot behavior are identical.

**Key first-boot safety finding:** `FMCCheckConfig()` is a **destructive conditional path inherited from upstream**. When `cfg[0] & 1` (DFEN disabled) or `cfg[1] != DATAFLASH_PARAMS_BASE`, it calls `FMC_EnableConfigUpdate()`, `FMC_Erase(FMC_CONFIG_BASE)`, `FMC_WriteConfig(cfg,2)`, reads the CONFIG back, and calls `SYS_ResetChip()`. Whether this path ran on the user's E115 is unknown; no CONFIG dump or trace is available. In `SetProductID()`, an unsuccessful scan of the actual LDROM calls `ResetToLDROM()`. The file's embedded E115 record is separate from that physical LDROM read.

## Historical BSP provenance and actual acquisition attempt

Original [myevic 2017-era build instructions](https://github.com/ClockSelect/myevic/blob/master/git_doc_en/howtobuild_en.md) cite **M451 Series BSP CMSIS V3.01.001**, while the currently pinned firmware runner uses the official [M451BSP source at `61f8103b`](https://github.com/OpenNuvoton/M451BSP/commit/61f8103bfe58ae8853affdba8a01dcc26e41079e) (V3.01.003, 2018-02-23). The pinned source commit is the **initial commit** of that repository, without earlier commits to compare by Git history.

Official [Nuvoton 2017 forum listing](https://forum.nuvoton.com/en/numicro-cortex-m4-mcu/general-discussion/129) still links to **M451 Series_BSP_CMSIS_V3.01.001.zip** at the legacy URL:
`https://www.nuvoton.com/opencms/resource-download.jsp?tp_GUID=SW0120140916095112`.

Implemented a **separate, device-free CI job** comparing four driver sources (`clk.c`, `fmc.c`, `sys.c`, `usbd.c`) and outputting byte hashes/diff summaries **if and only if** the original ZIP is actually acquired. [Actions #25, historical-bsp job](https://github.com/s1-mu-r4/myevic/actions/runs/40246297907) reached the old official URL but received a **29-byte non-ZIP response**, SHA256 `902abf38e682c5d0d5b2e8dcdd46acb9797df2222c90bf420328d02ea5dfdfd3`. Thus **HISTORIC_ARCHIVE_INVALID_OR_VENDOR_ERROR_PAGE**, **NO V3.01.001 CODE WAS RECOVERED** and **NO DRIVER DIFF HAS BEEN PERFORMED**. A green CI conclusion here means the attempt was recorded gracefully, **not** that an old-source comparison passed.

The [source-only comparison tool](../tests/e115/audit_historic_bsp.py) also accepts a locally acquired manufacturer package with `--zip /path/to/M451_Series_BSP_CMSIS_V3.01.001.zip`. It checks the archive and SHA256, reads only the four relevant source files with per-entry size limits, and compares them with the pinned source. It does **not** execute binaries or run the firmware updater. Any local ZIP may be inspected privately without committing its bytes to GitHub.

## Other build facts, not a cause conclusion

- `a73cd679` (2026 modern toolchain compatibility fix) changes the linker layout, assembly Thumb annotation, library search and `-fcommon`; these affect the actual ELF and warrant review. It predates the Ron7 limiter.
- The tracked 99,700B BIN was built/last changed in **2019** before the new limiter. It cannot establish that a 2026 limiter build should match it.
- Intermediate pre-limiter modernized build reaches `.raminit` at `0x19090`, **144B over the 100KiB ROM budget**, under the current runner. This test did not produce a runnable control BIN.
- The E115 candidate's downloaded file SHA matched CI, the updater showed "Firmware update completed", CFW failed to boot, and the owner **successfully restored stock via +/USB**. The program's actual APROM bytes and reason for failed boot are still not measured.

## Decision and next actions

**No reflash of any image, no published installable test artifacts, no merge.** Do not bypass `SetProductID` or skip CONFIG/clock protection to force a boot. The evidence does not justify a change to boot policy yet.

1. Find a verifiable original V3.01.001 source package or earlier matching SDK (retain source URL and SHA256). Compare exact `clk/fmc/sys/usbd` implementations and startup constants.
2. If that remains unavailable, inspect the known V3.01.003 code with a source-based contract review (reset/CONFIG read/write behavior, HXT-to-PLL fallback, LDROM read failure modes) and identify discriminating evidence; preserve separate root-cause hypotheses.
3. Any proposed patch must be supported by evidence in the actual cold-start call chain, use a **new candidate identity**, and remain unflashed until specifically reviewed for power/output safety and recoverability.

**Status: HISTORIC_BSP_SOURCE_UNAVAILABLE; PRE_USB_C_BODIES_UNCHANGED; ROOT_CAUSE_UNKNOWN; CURRENT_CFW_NO-GO.**
