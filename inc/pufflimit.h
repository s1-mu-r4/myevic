#ifndef __PUFFLIMIT_H__
#define __PUFFLIMIT_H__

//=========================================================================
// Puff limiter: rolling window + time-of-day schedule
//-------------------------------------------------------------------------
// Gates the fire path. The gate lives in EventHandler() immediately before
// "gFlags.firing = 1" (eh.c), which is the single point where firing is
// armed, so a refusal here cannot be routed around.
//
// THE CENTRAL PROBLEM THIS SOLVES
//
// The puff counter is non-volatile (dataflash) but the wall clock is not
// (RTC, powered from the cell). Pull or drain the battery and the counter
// survives while the clock does not. A naive "now - windowStart >= windowLen"
// test then reads the reset/jumped clock as "the window elapsed" and hands
// out a fresh allowance. That fails OPEN: yanking the cell for ten seconds
// buys unlimited puffs.
//
// Worse, on boxes without the 32kHz crystal the corruption is silent and
// unbounded. myevic issue #122 measured forward jumps of 5s, 320s, 7min and
// 18min across battery swaps with no error signalled, and GetRTC() returns
// an all-zero time on clock failure rather than reporting an error. The
// upstream maintainer's verdict was that the clock is only reliable for as
// long as the cell stays in, and that it is a hardware problem he would not
// fix. So the firmware must not trust the clock; it must VERIFY it.
//=========================================================================

#include <time.h>

//-------------------------------------------------------------------------
// Clock seal
//-------------------------------------------------------------------------
// RTC spare register 3 (0,1,2 are taken by REF_DATE/VV_BASE/VV_MJOULES;
// there are 16). Spare registers are part of the RTC block, so they lose
// their contents at exactly the moment the clock does. That makes a magic
// value there a reliable "the RTC has been powered continuously since the
// time was last explicitly set" witness.
//
// The seal is written ONLY by SetRTC(), i.e. when the time is deliberately
// set from the menu or over USB. It is deliberately NOT written at boot:
// self-sealing at startup would re-bless a clock that had just been reset,
// which is precisely the case being defended against.
#define RTCSPARE_PL_SEAL        3
#define PL_SEAL_MAGIC           0x504C3031      // "PL01"

// Any RTC year below this is treated as a reset clock. The M451 RTC counts
// from 2000, so a cold RTC reads far below this.
#define PL_MIN_VALID_YEAR       2017

//-------------------------------------------------------------------------
// Policy on an untrusted clock
//-------------------------------------------------------------------------
// PL_FLAG_FAIL_CLOSED ON  (default): a lost clock does NOT roll the window.
//   The existing count stands, so a depleted or removed cell leaves the
//   device blocked until the clock is re-synced over USB ("evic-usb time").
//   Deliberate removal buys a lockout, not an allowance.
//
// PL_FLAG_FAIL_CLOSED OFF: a lost clock rolls the window, so pulling the
//   cell clears the allowance. This is a real bypass and it is meant to be.
//   Note it also triggers on ORDINARY battery depletion, which nobody
//   chooses, so a build with this off can silently stop enforcing at a
//   moment the wearer did not pick and will not notice.
//
// PL_FLAG_SHOW_MODE exists for that reason: it surfaces the active policy
// and flags that a clock loss reset the window, so silent non-enforcement
// becomes visible non-enforcement. It is separately switchable.
#define PL_FLAG_ENABLED         0x01
#define PL_FLAG_FAIL_CLOSED     0x02
#define PL_FLAG_SCHEDULE        0x04
#define PL_FLAG_SHOW_MODE       0x08

// Compile-time defaults, applied when the dataflash copy is absent or fails
// validation. Override at build time, e.g. -DPL_DEFAULT_FAIL_CLOSED=0.
#ifndef PL_DEFAULT_ENABLED
#define PL_DEFAULT_ENABLED      1
#endif
#ifndef PL_DEFAULT_FAIL_CLOSED
#define PL_DEFAULT_FAIL_CLOSED  1
#endif
#ifndef PL_DEFAULT_SHOW_MODE
#define PL_DEFAULT_SHOW_MODE    1
#endif
#ifndef PL_DEFAULT_MAX_PUFFS
#define PL_DEFAULT_MAX_PUFFS    40
#endif
#ifndef PL_DEFAULT_WINDOW_SECS
#define PL_DEFAULT_WINDOW_SECS  7200            // 2 hours
#endif
#ifndef PL_DEFAULT_SCHEDULE
#define PL_DEFAULT_SCHEDULE     0x00FFFFFF      // all 24 hours allowed
#endif

// Sanity bounds. A window is held in a uint16_t, so it cannot exceed 18h12m.
#define PL_MAX_WINDOW_SECS      65535
#define PL_MIN_WINDOW_SECS      60
#define PL_MAX_PUFFS_LIMIT      9999

//-------------------------------------------------------------------------
// Why the limiter refused
//-------------------------------------------------------------------------
enum
{
	PL_ALLOW = 0,
	PL_BLOCK_WINDOW,        // per-window allowance spent
	PL_BLOCK_SCHEDULE,      // outside permitted hours
	PL_BLOCK_NOCLOCK        // clock untrusted, fail-closed, allowance spent
};

//-------------------------------------------------------------------------
// State for the UI. Valid after PLCheckFire().
//-------------------------------------------------------------------------
typedef struct
{
	uint8_t     reason;         // PL_ALLOW / PL_BLOCK_*
	uint8_t     clockTrusted;
	uint8_t     clockLossSeen;  // a clock loss reset the window this session
	uint16_t    used;
	uint16_t    limit;
	uint32_t    secsToWindow;   // countdown to next window, 0 if unknown
}
PLStatus_t;

//-------------------------------------------------------------------------
// API
//-------------------------------------------------------------------------

// Apply compile-time defaults to the dataflash copy. Called when dataflash
// is reset, and whenever stored values fail validation.
extern void PLResetDefaults( void );

// Clamp out-of-range stored values. Adding fields to dfParams_t means an
// existing device carries whatever bytes were previously in that padding,
// so the stored config must never be trusted unchecked.
extern void PLValidate( void );

// Stamp the clock as trusted. Called from SetRTC() only.
extern void PLSealClock( void );

// THE GATE. Non-zero to permit this puff. Call immediately before arming.
extern int  PLCheckFire( void );

// Record a puff against the window. Call where the puff counter increments,
// i.e. only for draws long enough to count.
extern void PLCountPuff( void );

// Latched result of the last PLCheckFire(), for display.
extern void PLGetStatus( PLStatus_t *s );

#endif // __PUFFLIMIT_H__
