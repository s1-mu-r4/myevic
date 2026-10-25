TARGET := myevic

# Flappy Bird game: in or out of the build.
#
# This is a ROM budget decision, not a taste one. ROM is 100K (0x19000) and
# that is a hard wall: DATAFLASH_LOGO_1327_BASE is 0x19000 and those two logo
# pages are at addresses hardcoded inside Joyetech's custom-logo utility, so
# the image cannot grow past them. Upstream already used 102212 of the 102400
# bytes available, leaving 188. The puff limiter's countdown screen and config
# menu need about 1250, and flappy.o + fbdata.o are 4319 of sprite data and
# game loop, which is the largest block of pure entertainment in the image.
#
# Build with WITH_GAME=1 to put the game back; the limiter UI then will not
# fit and something else has to give.
#
# Nothing else needs changing when this is off: every call site is guarded by
# gFlags.playing_fb, which only flappy.c ever sets, so those branches are
# statically dead. flappy.h supplies no-op stubs so they still compile.
WITH_GAME ?= 0

# We make the following assumptions on Windows:
# arm-none-eabi gcc and binutils are compiled for Windows,
# so if you are using Cygwin, we will need path translations
# NUVOSDK must be lazily evaluated, so that we can later
# change EVICSDK when building include paths.

# Small fix to bug where cygpath -w mistranslates paths with mixed slashes (/, \)
EVICSDK := $(subst \,/,$(EVICSDK))
NUVOSDK = $(EVICSDK)/nuvoton-sdk/Library

OBJS := $(NUVOSDK)/Device/Nuvoton/M451Series/Source/system_M451Series.o \
	$(NUVOSDK)/StdDriver/src/clk.o \
	$(NUVOSDK)/StdDriver/src/fmc.o \
	$(NUVOSDK)/StdDriver/src/gpio.o \
	$(NUVOSDK)/StdDriver/src/spi.o \
	$(NUVOSDK)/StdDriver/src/sys.o \
	$(NUVOSDK)/StdDriver/src/timer.o \
	$(NUVOSDK)/StdDriver/src/rtc.o \
	$(NUVOSDK)/StdDriver/src/usbd.o \
	$(NUVOSDK)/StdDriver/src/eadc.o \
	$(NUVOSDK)/StdDriver/src/pwm.o \
	$(NUVOSDK)/StdDriver/src/wdt.o \
	$(NUVOSDK)/StdDriver/src/uart.o \
	$(NUVOSDK)/StdDriver/src/crc.o

MYEVIC_OBJS := src/myevic.o \
	src/main.o \
	src/myprintf.o \
	src/atomizer.o \
	src/dataflash.o \
	src/screens.o \
	src/menus.o \
	src/mainview.o \
	src/battery.o \
	src/events.o \
	src/myrtc.o \
	src/miscs.o \
	src/eh.o \
	src/timers.o \
	src/meadc.o \
	src/megpio.o \
	src/strings.o \
	src/meusbd.o \
	src/vcom.o \
	src/storage.o \
	src/pufflimit.o \
	src/fonts.o \
	src/display.o \
	src/SSD1306.o \
	src/SSD1327.o

AEABI_OBJS := src/aeabi/aeabi_memset-thumb2.o \
	src/aeabi/aeabi_memclr.o

OUTDIR := bin
DOCDIR := doc

CPU := cortex-m4
FPU := fpv4-sp-d16

# We need to find out if on cygwin or not
ifeq ($(OS),Windows_NT)
	ifeq (, $(findstring cygwin, $(shell gcc -dumpmachine)))
		WIN_CYG := 0
	else
		WIN_CYG := 1
	endif
endif

ifeq ($(shell $(CC) -v 2>&1 | grep -c "clang version"), 1)
	CC_IS_CLANG := 1
endif

ifeq ($(ARMGCC),)
	ARMGCC := $(shell cd $(shell arm-none-eabi-gcc --print-search-dir | grep 'libraries' | \
		tr '=$(if $(filter Windows_NT,$(OS)),;,:)' '\n' | \
		grep -E '/arm-none-eabi/lib/?$$' | head -1)/../.. && pwd)
endif

ifeq ($(OS),Windows_NT)
	# Always fix binutils path
	ifneq ($(ARMGCC),)
		# If using cygwin, use cygpath
		ifeq ($(WIN_CYG),1)
			ARMGCC := $(shell cygpath -w $(ARMGCC))
		endif
	endif

	ifndef CC_IS_CLANG
		NEED_FIXPATH := 1
	endif
endif

ifneq ($(ARMGCC),)
	ifdef CC_IS_CLANG
		CFLAGS += -target armv7em-none-eabi -fshort-enums

#		AEABI_COUNT := $(shell arm-none-eabi-nm -g $(ARMGCC)/arm-none-eabi/lib/armv7e-m/libc.a | grep -Ec 'T __aeabi_mem(set|clr)[48]?$$')
		AEABI_COUNT := $(shell arm-none-eabi-nm -g $(ARMGCC)/arm-none-eabi/lib/thumb/v7e-m/libc.a | grep -Ec 'T __aeabi_mem(set|clr)[48]?$$')
		ifeq ($(AEABI_COUNT), 0)
			# __aeabi_memset* and __aeabi_memclr* are not exported by libc
			# We provide our own implementations
			OBJS += $(AEABI_OBJS)
		else ifneq ($(AEABI_COUNT), 6)
			# Only part of __aeabi_memset* and __aeabi_memclr* are exported by libc
			# This should never happen, bail out in env_check
			AEABI_ERROR := 1
		endif
	else
		CC := arm-none-eabi-gcc
	endif
	
	ifdef NEED_FIXPATH
		ifeq ($(WIN_CYG), 0)
			OBJS_FIXPATH := $(OBJS)
		else
			OBJS_FIXPATH := $(shell cygpath -w $(OBJS))
			EVICSDK := $(shell cygpath -w $(EVICSDK))
		endif
	else
		OBJS_FIXPATH := $(OBJS)
	endif
endif

ifeq ($(WIN_CYG),0)
	SDKTAG := $(shell git describe --abbrev --dirty --always --tags 2> NUL ) # Fix for Windows w/o cygwin (NUL instead of /dev/null)
else
	SDKTAG := $(shell git describe --abbrev --dirty --always --tags 2> /dev/null ) 
endif
ifeq ($(SDKTAG),)
	SDKTAG := unknown
endif

AS := arm-none-eabi-as
LD := arm-none-eabi-ld
AR := arm-none-eabi-ar
OBJCOPY := arm-none-eabi-objcopy

INCDIRS := $(foreach d,$(shell arm-none-eabi-gcc -x c -v -E /dev/null 2>&1 | sed -n -e '/<\.\.\.>/,/End/ p' | tail -n +2 | head -n -1 | sed 's/^\s*//'),-I$d) \
	-I$(NUVOSDK)/CMSIS/Include \
	-I$(NUVOSDK)/Device/Nuvoton/M451Series/Include \
	-I$(NUVOSDK)/StdDriver/inc \
	-Iinc \
	-Isrc

INCDIRS += -I$(ARMGCC)/arm-none-eabi/include

GCC_VERSION := $(shell arm-none-eabi-gcc -dumpversion)

# Ask the compiler which multilib variant our -mcpu/-mfpu/-mthumb flags select
# (e.g. "thumb/v7e-m/nofp") instead of hardcoding it. Older toolchains laid the
# libs out as a bare "thumb" subdir; current ones nest by arch and FPU.
MULTIDIR := $(shell arm-none-eabi-gcc -mcpu=$(CPU) -mfpu=$(FPU) -mthumb -print-multi-directory)

# Both $(ARMGCC)/lib/gcc/... (current) and $(ARMGCC)/gcc/... (older layout) are
# listed so this works across toolchain packagings; a nonexistent -L is harmless.
# ORDER MATTERS: ld takes the first match across -L in order, and the base
# directories also contain a libc.a/libgcc.a built for ARM (not Thumb). Listing
# them first yields "Unknown destination type (ARM/Thumb)" / "dangerous
# relocation" at link. The multilib directories must therefore come FIRST.
LIBDIRS := -L$(ARMGCC)/arm-none-eabi/lib/$(MULTIDIR) \
	-L$(ARMGCC)/arm-none-eabi/newlib/$(MULTIDIR) \
	-L$(ARMGCC)/lib/gcc/arm-none-eabi/$(GCC_VERSION)/$(MULTIDIR) \
	-L$(ARMGCC)/gcc/arm-none-eabi/$(GCC_VERSION)/$(MULTIDIR) \
	-L$(ARMGCC)/arm-none-eabi/lib \
	-L$(ARMGCC)/arm-none-eabi/newlib \
	-L$(ARMGCC)/lib/gcc/arm-none-eabi/$(GCC_VERSION) \
	-L$(ARMGCC)/gcc/arm-none-eabi/$(GCC_VERSION)

CFLAGS += -Wall -mcpu=$(CPU) -mfpu=$(FPU) -mthumb -Os -fdata-sections -ffunction-sections -std=c99
CFLAGS += -fno-builtin-printf
# GCC 10 flipped the default to -fno-common, which turns this codebase's
# tentative definitions (e.g. NewMillis in both atomizer.c and eh.c) into
# duplicate-symbol link errors. Pre-GCC-10 they merged into ONE common symbol,
# which is the behaviour the code was written against, so restore it rather
# than refactor 2017 code we have not tested yet. Worth cleaning up later by
# giving each such variable a single definition plus an extern declaration.
CFLAGS += -fcommon
CFLAGS += -DWITH_GAME=$(WITH_GAME)
CFLAGS += $(INCDIRS)

# The game objects are named unconditionally for `clean`, but only LINKED when
# WITH_GAME=1. Cleaning only what the current flag selects would strand the
# other pair of .o files in the tree.
GAME_OBJS := src/flappy.o src/fbdata.o

ifeq ($(WITH_GAME),1)
MYEVIC_OBJS += $(GAME_OBJS)
endif

# Flipping WITH_GAME changes the CODE in menus.o (the Game menu entry and
# GameIClick's call to fbStartGame), so every object must be rebuilt when it
# changes. Without this, `make WITH_GAME=1` followed by a plain `make` leaves a
# stale menus.o calling fbStartGame() while flappy.o is no longer linked, and
# the result is an undefined-reference failure that reads like a source bug.
# The stamp file carries the flag value in its name, so changing the flag makes
# it a missing prerequisite and forces the rebuild.
WITH_GAME_STAMP := .with_game.$(WITH_GAME)

$(WITH_GAME_STAMP):
	rm -f .with_game.* $(MYEVIC_OBJS) $(GAME_OBJS)
	touch $@

ASFLAGS := -mcpu=$(CPU) -mfpu=$(FPU)
ASFLAGS += $(INCDIRS)

LINKSCRIPT := linker.ld

LDFLAGS += -u __aeabi_uldivmod
LDFLAGS += $(LIBDIRS)
# We invoke `ld` directly, not the gcc driver. -nostartfiles is a gcc DRIVER
# option that ld never had; older binutils silently tolerated it, but >= 2.40
# rejects it ("unable to disambiguate: -nostartfiles"). It was always a no-op
# here anyway: with -nostdlib, an explicit linker script and an explicit object
# list, no startfiles are pulled in. Dropped.
LDFLAGS += --gc-sections -nostdlib -T$(LINKSCRIPT)
#LDFLAGS += --verbose --cref -Map=blah.map

SRCDIR   = src
INCDIR   = inc
OBJDIR   = src
BINDIR   = bin

INCLUDEH := $(wildcard $(INCDIR)/*.h)
INCLUDES := $(wildcard $(SRCDIR)/*.s)

all: env_check $(TARGET).bin

$(OBJS_FIXPATH): %.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.c $(INCLUDEH) $(WITH_GAME_STAMP)
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.s $(INCLUDES) $(WITH_GAME_STAMP)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET)_dec.bin: $(OBJS_FIXPATH) $(MYEVIC_OBJS)
	test -d $(OUTDIR) || mkdir $(OUTDIR)
	$(LD) --start-group $(LIBS) $(OBJS_FIXPATH) $(MYEVIC_OBJS) --end-group $(LDFLAGS) -o $(OUTDIR)/$(TARGET).elf
# .raminit MUST be listed here. It carries RAMInitTable, which the startup code
# reads to copy .data from ROM into RAM and to zero .bss. Upstream got it in via
# "-j .text" because it was a second output section also named .text; now that it
# has its own name, omitting it would silently produce a binary that fails to
# initialise RAM at boot.
	$(OBJCOPY) -O binary -j .text -j .data -j .raminit $(OUTDIR)/$(TARGET).elf $(OUTDIR)/$(TARGET)_dec.bin

$(TARGET).bin: $(TARGET)_dec.bin
	evic convert $(OUTDIR)/$(TARGET)_dec.bin -o $(OUTDIR)/$(TARGET).bin

docs:
	doxygen

clean:
	rm -rf $(OBJS) $(MYEVIC_OBJS) $(GAME_OBJS) $(AEABI_OBJS) .with_game.* $(OUTDIR)/$(TARGET).bin $(OUTDIR) $(DOCDIR)

env_check:
ifeq ($(ARMGCC),)
	$(error You must set the ARMGCC environment variable)
endif
ifneq ($(AEABI_ERROR),)
	$(error Your libc is exporting only part of __aeabi symbols)
endif

.PHONY: all clean docs env_check gen_tag
