/**
 ******************************************************************************
 * @file           : STM32H743_APPLICATION.ld
 * @brief          : Linker script for PMU-30 Application (STM32H743)
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 *
 * Application Memory Layout (with bootloader):
 *
 * Internal Flash (2 MB):
 * - 0x08000000 - 0x0800FFFF: Bootloader (64 KB) - DO NOT USE
 * - 0x08010000 - 0x08010FFF: Application Header (4 KB)
 * - 0x08011000 - 0x080FFFFF: Application Code (960 KB)
 * - 0x08100000 - 0x081EFFFF: Backup Region (960 KB) - Managed by bootloader
 * - 0x081F0000 - 0x081FFFFF: Configuration (64 KB)
 *
 * RAM Usage:
 * - D1 AXI SRAM (512 KB): Main application RAM
 * - DTCM RAM (128 KB): Fast RAM for critical data
 * - D2 SRAM (288 KB): DMA buffers, shared memory
 * - D3 SRAM (64 KB): Low-power domain
 * - Backup SRAM (4 KB): Persistent data
 *
 ******************************************************************************
 */

/* Entry Point */
ENTRY(Reset_Handler)

/* Highest address of the user mode stack */
_estack = ORIGIN(RAM_D1) + LENGTH(RAM_D1);

/* Generate a link error if heap and stack don't fit into RAM */
_Min_Heap_Size = 0x8000;   /* 32 KB heap */
_Min_Stack_Size = 0x2000;  /* 8 KB stack */

/* Memory regions */
MEMORY
{
    /* Application header (4 KB) - contains version, CRC, signature */
    APP_HEADER (rx) : ORIGIN = 0x08010000, LENGTH = 4K

    /* Application code (960 KB) - main application */
    FLASH (rx)      : ORIGIN = 0x08011000, LENGTH = 960K

    /* Configuration storage (64 KB) - user settings */
    CONFIG (r)      : ORIGIN = 0x081F0000, LENGTH = 64K

    /* DTCM RAM - Fast RAM, zero wait states */
    DTCMRAM (xrw)   : ORIGIN = 0x20000000, LENGTH = 128K

    /* Main RAM - D1 domain AXI SRAM */
    RAM_D1 (xrw)    : ORIGIN = 0x24000000, LENGTH = 512K

    /* D2 SRAM1 - For DMA buffers */
    RAM_D2_1 (xrw)  : ORIGIN = 0x30000000, LENGTH = 128K

    /* D2 SRAM2 - For ethernet/USB buffers */
    RAM_D2_2 (xrw)  : ORIGIN = 0x30020000, LENGTH = 128K

    /* D2 SRAM3 - Additional DMA buffers */
    RAM_D2_3 (xrw)  : ORIGIN = 0x30040000, LENGTH = 32K

    /* D3 SRAM4 - Low power domain */
    RAM_D3 (xrw)    : ORIGIN = 0x38000000, LENGTH = 64K

    /* Backup SRAM (4 KB, battery-backed) */
    BKPSRAM (rw)    : ORIGIN = 0x38800000, LENGTH = 4K

    /* ITCM RAM (64 KB, instruction tightly coupled) */
    ITCMRAM (xrw)   : ORIGIN = 0x00000000, LENGTH = 64K
}

/* Sections */
SECTIONS
{
    /* Firmware header - must be at beginning of APP_HEADER region */
    .firmware_header :
    {
        . = ALIGN(4);
        KEEP(*(.firmware_header))
        . = ALIGN(4);
    } >APP_HEADER

    /* Interrupt vector table - at beginning of FLASH region */
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
        *(.RamFunc)
        *(.RamFunc*)
        . = ALIGN(4);
        _edata = .;
    } >RAM_D1 AT> FLASH

    /* DTCM data for fast access variables */
    .dtcm_data :
    {
        . = ALIGN(4);
        _sdtcm = .;
        *(.dtcm_data)
        *(.dtcm_data*)
        . = ALIGN(4);
        _edtcm = .;
    } >DTCMRAM AT> FLASH

    _sidtcm = LOADADDR(.dtcm_data);

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

    /* DMA buffers in D2 SRAM1 (accessible by DMA1/DMA2) */
    .dma_buffers (NOLOAD) :
    {
        . = ALIGN(32);
        *(.dma_buffer)
        *(.dma_buffer*)
        . = ALIGN(32);
    } >RAM_D2_1

    /* ADC/DAC buffers in D2 SRAM2 */
    .adc_buffers (NOLOAD) :
    {
        . = ALIGN(32);
        *(.adc_buffer)
        *(.adc_buffer*)
        . = ALIGN(32);
    } >RAM_D2_2

    /* Ethernet/USB buffers */
    .eth_buffers (NOLOAD) :
    {
        . = ALIGN(32);
        *(.eth_buffer)
        *(.eth_buffer*)
        . = ALIGN(32);
    } >RAM_D2_3

    /* D3 SRAM for low-power accessible data */
    .d3_sram (NOLOAD) :
    {
        . = ALIGN(4);
        *(.d3_sram)
        *(.d3_sram*)
        . = ALIGN(4);
    } >RAM_D3

    /* Backup SRAM for persistent data (survives reset) */
    .bkpsram (NOLOAD) :
    {
        . = ALIGN(4);
        *(.bkpsram)
        *(.bkpsram*)
        . = ALIGN(4);
    } >BKPSRAM

    /* ITCM for time-critical code */
    .itcm_text :
    {
        . = ALIGN(4);
        *(.itcm_text)
        *(.itcm_text*)
        . = ALIGN(4);
    } >ITCMRAM AT> FLASH

    _siitcm = LOADADDR(.itcm_text);
    _sitcm = ORIGIN(ITCMRAM);
    _eitcm = _sitcm + SIZEOF(.itcm_text);

    /* DTCM uninitialized data */
    .dtcm_bss (NOLOAD) :
    {
        . = ALIGN(4);
        *(.dtcm_bss)
        *(.dtcm_bss*)
        . = ALIGN(4);
    } >DTCMRAM

    /* Remove info from final binary */
    /DISCARD/ :
    {
        libc.a(*)
        libm.a(*)
        libgcc.a(*)
    }

    /* ARM attributes */
    .ARM.attributes 0 : { *(.ARM.attributes) }
}

/* Provide symbols for startup code */
__flash_start__ = ORIGIN(FLASH);
__flash_size__ = LENGTH(FLASH);
__ram_start__ = ORIGIN(RAM_D1);
__ram_size__ = LENGTH(RAM_D1);
