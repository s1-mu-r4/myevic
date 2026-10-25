#ifndef __FLAPPY_BIRD_H__
#define __FLAPPY_BIRD_H__

//=========================================================================
// Flappy Bird game.
//
// WITH_GAME comes from the Makefile and defaults to 0, because the game's
// 4319 bytes are what the puff limiter UI is built out of. See the comment
// on WITH_GAME in the Makefile for the ROM arithmetic.
//
// When it is off, flappy.o and fbdata.o are not linked and the stubs below
// stand in. The four functions called from outside flappy.c (events.c,
// main.c, timers.c) all sit inside "if ( gFlags.playing_fb )" branches, and
// gFlags.playing_fb is only ever set inside flappy.c itself, so those
// branches can never be taken and the stubs are never actually reached.
// They exist so the guarded code still compiles, unchanged, which keeps the
// switch to one place instead of scattering #ifdefs through the event loop.
//=========================================================================

#ifndef WITH_GAME
#define WITH_GAME 0
#endif

#if WITH_GAME

extern void fbInitTimeouts();
extern int	fbCreateTimeout( void (*cb)( void ) );
extern void fbDeleteTimeout( int );
extern void fbSetTimeoutDelay( int );
extern void fbTickTimeouts();
extern void fbCallTimeouts();

extern void fbStartScreen();
extern void fbBirdAnim( int );
extern void fbStartGame();

#else

// Only the four called from outside flappy.c need a stub; the rest are
// internal to the game and have no callers once it is out of the build.
static inline void fbInitTimeouts() {}
static inline void fbTickTimeouts() {}
static inline void fbCallTimeouts() {}
static inline void fbStartGame() {}

#endif

//=========================================================================

#endif /* __FLAPPY_BIRD_H__ */
