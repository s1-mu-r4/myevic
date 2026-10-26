/* Memory regions */
MEMORY {
	ROM (rx)  : ORIGIN = 0x00000000, LENGTH = 100K
	RAM (rwx) : ORIGIN = 0x20000000, LENGTH =  32K
}

/* Library configurations */
/* No multilib subdirectory prefix here. It was "armv7e-m/", then "v7e-m/",
   and on a current toolchain it is "thumb/v7e-m/nofp/": hardcoding it means
   re-patching this file for every toolchain. Name the libraries bare and let
   the Makefile put the right multilib directory on the -L search path, which
   it derives from `arm-none-eabi-gcc -print-multi-directory`. */
GROUP(
	libnosys.a
	libgcc.a
	libc.a
	libm.a
)

ENTRY(Reset_Handler)

SECTIONS {
	.text : {
		KEEP(*(.isr_vectors))

		LONG(0x5746594D)
		LONG(images1_start)
		LONG(images1_end)
		LONG(images2_start)
		LONG(images2_end)
		LONG(Strings_Start)
		LONG(Strings_End)

		. = ALIGN(4);
		*(.text*)

		. = ALIGN(4);
		KEEP(*(.myevic*))

		. = ALIGN(4);
		KEEP(*(.productid*))

		. = ALIGN(4);
		*(.rodata*)

		. = ALIGN(4);
		Strings_Start = .;
		*(.strings*)
		Strings_End = .;

		. = ALIGN(4);
		images1_start = .;
		*(.imgblock1)
		images1_end = .;

		images2_start = .;
		*(.imgblock2)
		images2_end = .;

	} > ROM

	. = ALIGN(4);
	Data_Start_ROM = .;

	.data : AT (Data_Start_ROM) {
		Data_Start_RAM = .;
		*(vtable)
		*(.data*)

		. = ALIGN(4);
		Data_End_RAM = .;
	} > RAM

	Data_Size = Data_End_RAM - Data_Start_RAM;

	.sram (NOLOAD) : {
		SRAMZ_Start = .;

		. = ALIGN(4);
		*(COMMON)
		*(.bss*)

		end = .;

		. = ALIGN(8);
		*(.stack)

		SRAMZ_End = .;
	} > RAM

	SRAMZ_Size = SRAMZ_End - SRAMZ_Start;

	/* The .data initialiser image lives in ROM at Data_Start_ROM for SIZEOF(.data)
	   bytes, but .data was assigned "> RAM", so the ROM region pointer never
	   advanced past it and still sits at Data_Start_ROM. Without advancing it by
	   hand, the table below is laid down ON TOP of the .data load image, which
	   current ld reports as:
	     section .text LMA [..] overlaps section .data LMA [..]

	   Older binutils advanced the region pointer past the AT() load image by
	   itself, so upstream was NOT emitting a corrupt image. Verified: both the
	   upstream-shipped bin/myevic.bin and a build with this fix carry exactly
	   452 (0x1C4) bytes after img1_end, i.e. .data (0x1A4) + this table (0x18)
	   + alignment. This fix reproduces the original layout, it does not just
	   silence the diagnostic.

	   The address MUST be an explicit address expression on the output section:
	   a bare ". = ..." before it is ignored, because for a section carrying
	   "> REGION" and no address expression ld takes the region's next free
	   address instead of the location counter. */
	.raminit (Data_Start_ROM + SIZEOF(.data)) : {
		. = ALIGN(4);
		RAMInitTable = .;

		LONG(Data_Start_ROM)
		LONG(Data_Start_RAM)
		LONG(Data_Size)

		LONG(SRAMZ_Start)
		LONG(SRAMZ_Start)
		LONG(SRAMZ_Size)

		RAMInitEnd = .;

	} > ROM
}

/* Renamed from ".text" to ".raminit": upstream had TWO output sections both
   named .text, which is legal but made the overlap diagnostic above read as
   ".text overlaps .data" when the real culprit was this trailing table. Nothing
   references the section by name; RAMInitTable/RAMInitEnd are used as symbols. */
