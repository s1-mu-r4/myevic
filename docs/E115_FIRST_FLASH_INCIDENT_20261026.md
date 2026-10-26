# E115 first CFW flash — immutable evidence summary

**Report:** 2026-10-26 JST · **Device:** owner Joyetech eVic VTwo Mini E115 / HW 1.00
**Disposition:** **CFW BOOT FAIL** / **STOCK RESTORE PASS (once, on this device)**.
**No device-specific ID, serial, full memory dump, private Windows path or screenshots published.**

## Direct owner evidence, in sequence

1. A local `ron7-pufflimit-e115-EXPERIMENTAL.bin` was downloaded from the then-available [CI #7](https://github.com/s1-mu-r4/myevic/actions/runs/40239433860) one-day artifact. File size: **100,500 bytes**. Windows `Get-FileHash -Algorithm SHA256` showed **`DB6C67B897DA841119F868E7B745CAC70D010ADDAC5438172DF3987EF74D4046`**, an exact match to the CI conversion output. The on-device APROM has **not** been independently read back, and a local file match does not prove the downloader programmed every byte.
2. The **Joyetech Update Firmware 1.20** program showed **"Firmware update completed."** and a full progress bar after choosing CFW. Its background `Firmware Version 5.04` may have been read/cached before the update; it is **not** evidence that the CFW executed.
3. Windows subsequently showed **USB device not recognized**. The device also failed to boot with a battery inserted. No runtime trace confirms that it ever reached `Reset_Handler`, `InitUSB`, or the main loop. A Windows USB warning alone cannot diagnose which stage failed.
4. Holding **+** during USB reconnection made the Joyetech updater recognize **eVic VTwo mini, Firmware Version 0.00, Hardware Version 1.00**. This is consistent with recovery/LDROM mode (zero FW version does not prove APROM erasure).
5. The owner then **successfully reinstalled stock firmware** over this recovery entry. It establishes one real recovery success after this CFW failure, not guaranteed protection against every future failure mode.

The local manufacturer E115 V5.04 stock package was checked offline with SHA256
`20ed1e118745c25df8b3c4dda036a2cc0f1c45a0a3bae6955a41178517fb9ed9`.
The stock ZIP itself is not distributed in this repository.

## Controlled offline evidence (never a hardware pass)

| Evidence | Verified claim | Limitation |
|---|---|---|
| [Actions #7](https://github.com/s1-mu-r4/myevic/actions/runs/40239433860) | Two reproducible CFW builds; 100,500B image (1,900B below 100KiB limit), selected USB stack-frame and ELF LOAD invariants | No real startup, output regulation or APROM verification |
| [Actions #13](https://github.com/s1-mu-r4/myevic/actions/runs/40241452939) | Ron7 original source and amended fork compiled with same toolchain; matched initial SP `0x20003778`, reset PC `0x000015CD`, 420B data-copy and 13,776B SRAM zero-span | Static image metadata does not prove actual reset execution |
| [Actions #19](https://github.com/s1-mu-r4/myevic/actions/runs/40243396498) | All three compared images contain the full E115/HW1.00 product record; shipped 2019 image 99,700B, Ron7 2026 rebuild 100,456B, amended candidate 100,500B | The shipped image predates the 2026 limiter; not a verified working limiter baseline |
| [Actions #21](https://github.com/s1-mu-r4/myevic/actions/runs/40245001030) | 2019 source with 2026 GCC compatibility fixes exceeded ROM budget by 144B under the current runner | Historical control **did not build**, despite job's overall success |
| [Actions #25](https://github.com/s1-mu-r4/myevic/actions/runs/40246297907) | Attempted manufacturer M451 BSP v3.01.001 archive fetch | Received 29B non-ZIP error response; **no driver differential was performed** |
| [Actions #28](https://github.com/s1-mu-r4/myevic/actions/runs/40247058812) | 20 Python tests including seven source-bound mock CONFIG/LDROM branch cases; main ARM build passes | Models code logic only. Physical CONFIG, LDROM bytes and branches remain unknown |
| [Actions #29](https://github.com/s1-mu-r4/myevic/actions/runs/40247164752) | Latest frozen-source offline CI passed | Hardware remains CFW BOOT FAIL |

## What an updater success message does NOT prove

`Firmware update completed` is **host-interface evidence**, not verified APROM readback. The user's specific transaction may have (a) stored the image but failed at boot; (b) reported host transfer completion without verifiable target storage; or (c) experienced a device-specific boot/configuration branch. No available log separates these at present.

Do not re-interpret the unchanged `Firmware Version 5.04` on the host as successful CFW execution or imply that the restart via + means CFW itself reached its own LDROM reset path.

## Firmware changes and safety handling

The experimental research fork touched source in only `src/meusbd.c`, `src/myevic.s`, and `linker.ld`:
- Separate large USB profile buffers on the stack; reject malformed FMCREAD length/alignment/overflow.
- Preserve proper SRAM NOLOAD mapping and include the RAM-init table in a virtual firmware-file size.

These are **offline fixes only**, not evidence that the experimental CFW is suitable for any physical device. **Never reuse or reflash** `ron7-pufflimit-e115-EXPERIMENTAL.bin`. The CI's temporary image publication has been disabled; the older one-day historical artifact must not be reused or treated as a release.

## Preserved history, without duplicate live reports

The earlier verbose technical reports remain recoverable through Git history at
[research tip before consolidation](https://github.com/s1-mu-r4/myevic/tree/5266feea7f2521170e1ea91271df40f8b13a0e35/docs):
`E115_RECOVERY_PREFLIGHT.md`, `E115_ROOT_CAUSE_TRIAGE_20261026.md`,
`E115_HISTORIC_BSP_AND_BOOT_GATES_20261026.md`, and previous revisions of this incident file. No history is force-rewritten.

**Conclusion: The experimental CFW failed to boot; stock USB recovery succeeded once. The root cause remains unknown.**
