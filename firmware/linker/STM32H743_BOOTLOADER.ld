/**
 ******************************************************************************
 * @file           : STM32H743_BOOTLOADER.ld
 * @brief          : Linker script for PMU-30 Bootloader (STM32H743)
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 *
 * Bootloader Memory Layout:
 * - Flash: 64 KB (0x08000000 - 0x0800FFFF)
 * - RAM: Full access to all SRAM regions
 *
 * This is a minimal bootloader - keeps flash footprint small to leave
 * maximum space for the application.
 *
 ******************************************************************************
 */

/* Entry Point */
ENTRY(Reset_Handler)

/* Highest address of the user mode stack */
_estack = ORIGIN(RAM_D1) + LENGTH(RAM_D1);

/* Generate a link error if heap and stack don't fit into RAM */
_Min_Heap_Size = 0x400;   /* 1 KB heap for bootloader */
_Min_Stack_Size = 0x800;  /* 2 KB stack for bootloader */

/* Memory regions */
MEMORY
{
    /* Bootloader flash region (64 KB) */
    FLASH (rx)       : ORIGIN = 0x08000000, LENGTH = 64K

    /* DTCM RAM - Fast RAM for stack and critical data */
    DTCMRAM (xrw)    : ORIGIN = 0x20000000, LENGTH = 128K

    /* Main RAM - D1 domain AXI SRAM */
    RAM_D1 (xrw)     : ORIGIN = 0x24000000, LENGTH = 512K

    /* D2 SRAM1 */
    RAM_D2_1 (xrw)   : ORIGIN = 0x30000000, LENGTH = 128K

    /* D2 SRAM2 */
    RAM_D2_2 (xrw)   : ORIGIN = 0x30020000, LENGTH = 128K

    /* D2 SRAM3 */
    RAM_D2_3 (xrw)   : ORIGIN = 0x30040000, LENGTH = 32K

    /* D3 SRAM4 */
    RAM_D3 (xrw)     : ORIGIN = 0x38000000, LENGTH = 64K

    /* Backup SRAM (4 KB, battery-backed) */
    BKPSRAM (rw)     : ORIGIN = 0x38800000, LENGTH = 4K

    /* ITCM RAM (64 KB, instruction tightly coupled) */
    ITCMRAM (xrw)    : ORIGIN = 0x00000000, LENGTH = 64K
}

/* Sections */
SECTIONS
{
    /* Interrupt vector table - must be at beginning of flash */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } >FLASH

    /* Code and read-only data */
    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame)

        KEEP(*(.init))
        KEEP(*(.fini))

        . = ALIGN(4);
        _etext = .;
    } >FLASH

    /* Constant data */
    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } >FLASH

    /* ARM exception handling */
    .ARM.extab :
    {
        *(.ARM.extab* .gnu.linkonce.armextab.*)
    } >FLASH

    .ARM :
    {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } >FLASH

    /* Pre-init array */
    .preinit_array :
    {
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array*))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    } >FLASH

    /* Init array */
    .init_array :
    {
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT(.init_array.*)))
        KEEP(*(.init_array*))
        PROVIDE_HIDDEN(__init_array_end = .);
    } >FLASH

    /* Fini array */
    .fini_array :
    {
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT(.fini_array.*)))
        KEEP(*(.fini_array*))
        PROVIDE_HIDDEN(__fini_array_end = .);
    } >FLASH

    /* Used by startup to initialize data */
    _sidata = LOADADDR(.data);

    /* Initialized data - in RAM, loaded from flash */
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } >RAM_D1 AT> FLASH

    /* Uninitialized data (zeroed by startup) */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        __bss_start__ = _sbss;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
        __bss_end__ = _ebss;
    } >RAM_D1

    /* User heap and stack */
    ._user_heap_stack :
    {
        . = ALIGN(8);
        PROVIDE(end = .);
        PROVIDE(_end = .);
        . = . + _Min_Heap_Size;
        . = . + _Min_Stack_Size;
        . = ALIGN(8);
    } >RAM_D1

    /* Backup SRAM for boot shared data */
    .bkpsram (NOLOAD) :
    {
        . = ALIGN(4);
        *(.bkpsram)
        *(.bkpsram*)
        . = ALIGN(4);
    } >BKPSRAM

    /* DTCM RAM for fast stack */
    .dtcmram (NOLOAD) :
    {
        . = ALIGN(4);
        *(.dtcmram)
        *(.dtcmram*)
        . = ALIGN(4);
    } >DTCMRAM

    /* Remove debug info from final binary */
    /DISCARD/ :
    {
        libc.a(*)
        libm.a(*)
        libgcc.a(*)
    }

    /* ARM attributes */
    .ARM.attributes 0 : { *(.ARM.attributes) }
}
