> **2026-10-26 REAL-DEVICE UPDATE:** First experimental CFW boot **FAILED** (unrecognized USB, no boot with battery); the owner **successfully restored stock firmware** using the + button with USB. [Incident details](E115_FIRST_FLASH_INCIDENT_20261026.md). **Do not flash the failed experimental BIN again.** Earlier planning-only recovery notes below refer to the pre-test evidence state.

# E115｜Official USB recovery readiness (offline evidence, 2026-10-26)

## Intended goal

Prepare for a **first physical verification of Ron7's existing `pufflimit` firmware** on a Joyetech eVic VTwo Mini, box code E115 / HW 1.00. This file concerns recovery options only. It does not implement new device features or establish that a modified firmware is safe.

## Independent evidence available

| Evidence | What it supports | What it **does not** prove |
|---|---|---|
| [Joyetech Windows VT update instructions](https://www.joyetech.com/steps-on-vt-software-win/) and [Mac instructions](https://www.joyetech.com/steps-on-vt-software-mac/) | Manufacturer describes removing the cell and atomizer and, when updater is stuck, reconnecting USB while holding **+** to initiate update | A successful write/erase/recovery of this particular E115 |
| [Official eVic VTwo Mini firmware page](https://www.joyetech.com/mvr-software/?sid=189) | Manufacturer distributes E115-compatible VT firmware V5.04 (do not confuse with E043 VTwo) | USB connection alone guarantees a restored device |
| Prior owner-supplied E115 read-only mode evidence | Box E115, HW 1.00, FW 5.04 normally; holding **+** while connecting USB yielded FW=0 and LDROM version=100 in GETINFO | Physical LDROM bytes, CONFIG0/1, a writable LDROM program path |
| [myevic compatibility/readme](https://github.com/ClockSelect/myevic/blob/master/git_doc_en/usageandcompatibility_en.md) | eVic VTwo Mini is listed; myevic documentation uses manufacturer's updater with its custom BIN | This particular experimental Ron7 build is safe on this unit |
| The pinned stock ZIP below | Correct known copy of the V5.04 E115 manufacturer's archive, checked byte-by-byte | Firmware signature, individual write success, successful rollback or power-fail safety |

### Why a second desktop updater test is not read-only

The stock Windows update program can transmit **SETPARAMS (0x53)** to request a boot-state change, followed by reset, before the APROM **0xC3** firmware transfer. A successful GETINFO display must **not** be treated as proof the application made no changes. Merely launching the stock updater in a connected state is **not authorized here**.

For this reason, do **not** execute the updater just to see whether the device is recognised as a harmless read-only experiment. A valid read-only GETINFO/LDROM observation has already been supplied; repeating it would not verify recovery writes.

### Stock archive integrity preflight (entirely device-free)

Use only your already downloaded **official E115 V5.04 Windows ZIP**, not a similar model's updater. From the repository root:

```sh
python3 tests/e115/e115_stock_zip_audit.py /path/to/UpdateFirmware.zip
```

The script verifies the **entire ZIP SHA-256**, its three members' SHA-256, ZIP CRC, decrypted E115 marker, plausible vector table and PE header, without opening the EXE, contacting USB/HID, writing a file, or running target code. It has no firmware upload function. An intact archive is a reproducible **offline packaging check**, not a recovery guarantee.

Expected archive SHA-256:
`20ed1e118745c25df8b3c4dda036a2cc0f1c45a0a3bae6955a41178517fb9ed9`.

Previous controlled static host-updater analysis found that normal Windows firmware update emits HID `0xC3`, start address 0, length equal to the chosen file's actual byte size. E115 V5.04 is 70,904 B; the patched Ron7 experimental BIN is 100,500 B. Neither value is a promise about which physical Flash pages LDROM erases. The Windows transport's success indication reflects host transfer completion; it is **not** an independent Flash readback or rollback certificate.

## Decision gate before any physical flashing

**Not yet approved:** the E115 has not undergone a demonstrated stock restore after CFW write, nor was the proprietary LDROM code or its erase/error handling obtained. Without dismantling, SWD, or a second expendable device, the exact brick risk cannot be eliminated in advance.

1. Keep the unmodified official stock ZIP and its hash in two accessible local copies. Do not publish any device-unique GETINFO image, serial number, or raw memory dump.
2. Confirm the only intended write would be an **APROM firmware update** for box E115; never an LDROM/config/bootloader write, recovery via unverified raw FMCREAD commands, or a logo write. No live action is authorized by this document.
3. Review the corrected build and its safety conditions: ARM clean-build reproducible, 100KiB ROM limit, specific USB stack path and ELF LOAD conflict resolved; interrupt stack margin and actual battery/thermal/short protection remain unverified.
4. Only after a separate **explicit risk/physical-test authorization** would a sacrificial-device or controlled E115 first-flash trial be considered. Before that trial, assess power stability, data-capable USB cable, battery/atomizer removal during update, cable interruption, thermal conditions, physical isolation, ability to use the manufacturer's `+` boot entry, and the possibility of an unrecoverable failed write.
5. After any future device work, verify startup, screen, USB recognition and normal protective shutoff in stages. Do not assume that a successful flash means the puff counter, temperature sensing or electrical safety are correct.

### Existing status

- **OFFLINE:** Manufacturer instructions and static firmware/update-program evidence reviewed.
- **USER_LOG:** E115 responds in LDROM mode when entering via **+** with battery/atomizer removed.
- **UNVERIFIED:** True CONFIG values, LDROM erasure range, firmware write/ack, interrupted-update recovery, and the complete runtime protection behavior.
- **DECISION: NO-GO for current flashing.** A technically plausible recovery pathway exists; it is **not** a guaranteed one. Further passive checks do not change this fundamental evidence gap.

This document is intentionally separate from the physical experiment authorisation.
