#include "myevic.h"
#include "myrtc.h"
#include "dataflash.h"
#include "pufflimit.h"

//=========================================================================
// Puff limiter. See inc/pufflimit.h for the rationale.
//=========================================================================

//-------------------------------------------------------------------------
// Compile-time layout guards.
//
// The limiter fields live in the tail padding of dfParams_t. That padding is
// free ONLY while sizeof(dfParams_t) stays <= 256, because the flash layout
// is derived from ALIGN256(sizeof(dfParams_t)): cross 256 and the params
// region silently doubles to 512, moving DATAFLASH_PARAMS_BASE and walking
// over the profiles and counter pages beneath it. That corruption would show
// up on a device, not in a build, so catch it here instead.
//
// -std=c99, so no _Static_assert. The negative-array-size idiom gives a
// compile error with the offending line named.
//-------------------------------------------------------------------------
#define PL_BUILD_ASSERT(name,cond) typedef char pl_assert_##name[(cond)?1:-1]

PL_BUILD_ASSERT( params_fit_one_page, sizeof(dfParams_t) <= 256 );
PL_BUILD_ASSERT( flags_offset,       __builtin_offsetof(dfParams_t,PLFlags)       == 0xE7 );
PL_BUILD_ASSERT( maxpuffs_offset,    __builtin_offsetof(dfParams_t,PLMaxPuffs)    == 0xE8 );
PL_BUILD_ASSERT( windowsecs_offset,  __builtin_offsetof(dfParams_t,PLWindowSecs)  == 0xEA );
PL_BUILD_ASSERT( windowcount_offset, __builtin_offsetof(dfParams_t,PLWindowCount) == 0xEC );
// 4-byte fields must stay naturally aligned or the M451 faults on access.
PL_BUILD_ASSERT( windowstart_offset, __builtin_offsetof(dfParams_t,PLWindowStart) == 0xF0 );
PL_BUILD_ASSERT( schedule_offset,    __builtin_offsetof(dfParams_t,PLSchedule)    == 0xF4 );

static PLStatus_t PLStatus;

// Sticky for the session: a clock loss rolled the window while fail-open.
// Not persisted; it describes this power-on, which is exactly the span a
// wearer would want flagged.
static uint8_t PLClockLossSeen;

//-------------------------------------------------------------------------

__myevic__ void PLResetDefaults()
{
	dfPLFlags = ( PL_DEFAULT_ENABLED     ? PL_FLAG_ENABLED     : 0 )
	          | ( PL_DEFAULT_FAIL_CLOSED ? PL_FLAG_FAIL_CLOSED : 0 )
	          | ( PL_DEFAULT_SHOW_MODE   ? PL_FLAG_SHOW_MODE   : 0 )
	          | PL_FLAG_SCHEDULE;

	dfPLMaxPuffs    = PL_DEFAULT_MAX_PUFFS;
	dfPLWindowSecs  = PL_DEFAULT_WINDOW_SECS;
	dfPLSchedule    = PL_DEFAULT_SCHEDULE;
	dfPLWindowCount = 0;
	dfPLWindowStart = 0;
}

//-------------------------------------------------------------------------
// These fields occupy padding that previously held arbitrary bytes, and the
// page CRC validates whatever was there. So every stored value has to be
// range-checked rather than assumed sane.
//-------------------------------------------------------------------------

__myevic__ void PLValidate()
{
	int dirty = 0;

	if ( dfPLWindowSecs < PL_MIN_WINDOW_SECS )
	{
		dfPLWindowSecs = PL_DEFAULT_WINDOW_SECS;
		dirty = 1;
	}

	if ( dfPLMaxPuffs > PL_MAX_PUFFS_LIMIT )
	{
		dfPLMaxPuffs = PL_DEFAULT_MAX_PUFFS;
		dirty = 1;
	}

	// Only the low 24 bits are meaningful (one bit per hour). A schedule of
	// zero would block every hour forever, which is never a wanted config.
	dfPLSchedule &= 0x00FFFFFF;
	if ( dfPLSchedule == 0 )
	{
		dfPLSchedule = PL_DEFAULT_SCHEDULE;
		dirty = 1;
	}

	if ( dfPLWindowCount > dfPLMaxPuffs )
	{
		dfPLWindowCount = dfPLMaxPuffs;
		dirty = 1;
	}

	if ( dirty ) UpdateDFTimer = 50;
}

//-------------------------------------------------------------------------

__myevic__ void PLSealClock()
{
	RTCWriteRegister( RTCSPARE_PL_SEAL, PL_SEAL_MAGIC );
}

//-------------------------------------------------------------------------
// Is the wall clock believable?
//
// Three independent things must hold. The seal is the load-bearing one: it
// lives in the RTC block, so it cannot survive the power loss that resets
// the clock. The year check catches a cold RTC that still reads as "valid".
//-------------------------------------------------------------------------

__myevic__ static int PLClockTrusted( S_RTC_TIME_DATA_T *rtd )
{
	if ( gFlags.noclock || !gFlags.rtcinit )
		return 0;

	if ( RTCReadRegister( RTCSPARE_PL_SEAL ) != PL_SEAL_MAGIC )
		return 0;

	GetRTC( rtd );

	// GetRTC() zero-fills on failure rather than reporting an error, so a
	// zeroed year is indistinguishable from "clock gone" and is rejected.
	if ( rtd->u32Year < PL_MIN_VALID_YEAR )
		return 0;

	return 1;
}

//-------------------------------------------------------------------------

__myevic__ static void PLRollWindow( time_t now )
{
	dfPLWindowStart = now;
	dfPLWindowCount = 0;
	UpdateDFTimer = 50;
}

//-------------------------------------------------------------------------

__myevic__ int PLCheckFire()
{
	S_RTC_TIME_DATA_T rtd;
	time_t now;
	uint32_t elapsed;

	PLStatus.used         = dfPLWindowCount;
	PLStatus.limit        = dfPLMaxPuffs;
	PLStatus.secsToWindow = 0;
	PLStatus.clockLossSeen= PLClockLossSeen;

	if ( !( dfPLFlags & PL_FLAG_ENABLED ) )
	{
		PLStatus.reason = PL_ALLOW;
		PLStatus.clockTrusted = 1;
		return 1;
	}

	PLStatus.clockTrusted = PLClockTrusted( &rtd );

	//---------------------------------------------------------------------
	// Untrusted clock. The whole design turns on this branch.
	//---------------------------------------------------------------------
	if ( !PLStatus.clockTrusted )
	{
		if ( dfPLFlags & PL_FLAG_FAIL_CLOSED )
		{
			// Do NOT roll the window: we have no idea how much time passed,
			// and assuming "enough" is what hands out a free allowance. Judge
			// on the surviving count. Once spent it stays spent until the
			// clock is set again over USB, which re-seals via SetRTC().
			if ( dfPLWindowCount >= dfPLMaxPuffs )
			{
				PLStatus.reason = PL_BLOCK_NOCLOCK;
				return 0;
			}
			PLStatus.reason = PL_ALLOW;
			return 1;
		}
		else
		{
			// Fail open. Deliberate bypass, and it fires on ordinary battery
			// depletion too, so record it for the UI.
			if ( dfPLWindowCount )
			{
				PLClockLossSeen = 1;
				PLStatus.clockLossSeen = 1;
				PLRollWindow( 0 );
				PLStatus.used = 0;
			}
			PLStatus.reason = PL_ALLOW;
			return 1;
		}
	}

	//---------------------------------------------------------------------
	// Trusted clock.
	//---------------------------------------------------------------------
	RTCTimeToEpoch( &now, &rtd );

	// Time-of-day schedule, one bit per hour, bit set means permitted.
	if ( dfPLFlags & PL_FLAG_SCHEDULE )
	{
		if ( !( dfPLSchedule & ( 1UL << ( rtd.u32Hour & 31 ) ) ) )
		{
			PLStatus.reason = PL_BLOCK_SCHEDULE;
			// Seconds until the top of the next hour. Good enough: the next
			// hour may also be barred, and the UI re-reads this each attempt.
			PLStatus.secsToWindow = 3600 - ( rtd.u32Minute * 60 + rtd.u32Second );
			return 0;
		}
	}

	// Rolling window.
	if ( now < (time_t)dfPLWindowStart )
	{
		// Clock moved backwards under a valid seal, so it was deliberately
		// set back. Re-anchor the window but KEEP the count: re-anchoring
		// alone must never be a way to earn puffs.
		dfPLWindowStart = now;
		UpdateDFTimer = 50;
	}
	else
	{
		elapsed = (uint32_t)( now - (time_t)dfPLWindowStart );
		if ( elapsed >= dfPLWindowSecs )
		{
			PLRollWindow( now );
			PLStatus.used = 0;
		}
		else
		{
			PLStatus.secsToWindow = dfPLWindowSecs - elapsed;
		}
	}

	if ( dfPLWindowCount >= dfPLMaxPuffs )
	{
		PLStatus.reason = PL_BLOCK_WINDOW;
		return 0;
	}

	PLStatus.reason = PL_ALLOW;
	return 1;
}

//-------------------------------------------------------------------------

__myevic__ void PLCountPuff()
{
	if ( !( dfPLFlags & PL_FLAG_ENABLED ) )
		return;

	if ( dfPLWindowCount < 0xFFFF )
	{
		++dfPLWindowCount;
		// Batched like the stock counters; writing flash on every puff would
		// wear the page out.
		UpdateDFTimer = 50;
	}
}

//-------------------------------------------------------------------------

__myevic__ void PLGetStatus( PLStatus_t *s )
{
	*s = PLStatus;
	s->used = dfPLWindowCount;
}
