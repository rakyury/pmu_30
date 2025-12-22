/**
 ******************************************************************************
 * @file           : emu_main.c
 * @brief          : PMU-30 Emulator Main Entry Point
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This is the main entry point for the PMU-30 hardware emulator.
 * It provides an interactive console for controlling the emulation
 * and can also run automated test scenarios.
 *
 * Usage:
 *   ./pmu30_emulator                    - Interactive mode
 *   ./pmu30_emulator --scenario test.json - Run scenario file
 *   ./pmu30_emulator --help             - Show help
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_emulator.h"
#include "stm32_hal_emu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

#ifdef _WIN32
#include <windows.h>
#include <conio.h>
#else
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include <pthread.h>
#endif

/* Private typedef -----------------------------------------------------------*/

typedef enum {
    EMU_MODE_INTERACTIVE,
    EMU_MODE_SCENARIO,
    EMU_MODE_HEADLESS
} EmuMode_t;

/* Private define ------------------------------------------------------------*/

#define EMU_VERSION         "1.0.0"
#define EMU_TICK_RATE_MS    1       /* 1kHz tick rate */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

static volatile bool g_running = true;
static EmuMode_t g_mode = EMU_MODE_INTERACTIVE;
static char g_scenario_file[256] = {0};

/* Private function prototypes -----------------------------------------------*/

static void PrintBanner(void);
static void PrintHelp(void);
static void PrintUsage(void);
static void SignalHandler(int sig);
static void RunInteractiveMode(void);
static void RunScenarioMode(const char* filename);
static void ProcessCommand(const char* cmd);
static int KeyboardHit(void);
static int GetChar(void);

/* External firmware functions (to be called from emulator) */
extern void PMU_ADC_Update(void);
extern void PMU_CAN_Update(void);
extern void PMU_PROFET_Update(void);
extern void PMU_HBridge_Update(void);
extern void PMU_Protection_Update(void);
extern void PMU_Channel_Update(void);

/* CAN TX callback */
static void OnCanTx(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len);

/* PROFET state change callback */
static void OnProfetChange(uint8_t channel, uint16_t value);

/* H-Bridge state change callback */
static void OnHBridgeChange(uint8_t channel, uint16_t value);

/* Main function -------------------------------------------------------------*/

int main(int argc, char* argv[])
{
    /* Parse command line arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            PrintUsage();
            return 0;
        }
        else if (strcmp(argv[i], "--scenario") == 0 || strcmp(argv[i], "-s") == 0) {
            if (i + 1 < argc) {
                strncpy(g_scenario_file, argv[i + 1], sizeof(g_scenario_file) - 1);
                g_mode = EMU_MODE_SCENARIO;
                i++;
            } else {
                fprintf(stderr, "Error: --scenario requires a filename\n");
                return 1;
            }
        }
        else if (strcmp(argv[i], "--headless") == 0) {
            g_mode = EMU_MODE_HEADLESS;
        }
        else if (strcmp(argv[i], "--version") == 0 || strcmp(argv[i], "-v") == 0) {
            printf("PMU-30 Emulator version %s\n", EMU_VERSION);
            return 0;
        }
        else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            PrintUsage();
            return 1;
        }
    }

    /* Setup signal handler */
    signal(SIGINT, SignalHandler);
    signal(SIGTERM, SignalHandler);

    /* Print banner */
    PrintBanner();

    /* Initialize emulator */
    if (PMU_Emu_Init() != 0) {
        fprintf(stderr, "Failed to initialize emulator\n");
        return 1;
    }

    /* Set callbacks */
    PMU_Emu_CAN_SetTxCallback(OnCanTx);
    PMU_Emu_PROFET_SetCallback(OnProfetChange);
    PMU_Emu_HBridge_SetCallback(OnHBridgeChange);

    /* Enable logging */
    PMU_Emu_SetLogging(true);

    /* Set default values */
    PMU_Emu_Protection_SetVoltage(12000);   /* 12V battery */
    PMU_Emu_Protection_SetTemperature(25);  /* 25C ambient */

    /* Run appropriate mode */
    switch (g_mode) {
        case EMU_MODE_INTERACTIVE:
            RunInteractiveMode();
            break;

        case EMU_MODE_SCENARIO:
            RunScenarioMode(g_scenario_file);
            break;

        case EMU_MODE_HEADLESS:
            printf("Running in headless mode. Press Ctrl+C to stop.\n");
            while (g_running) {
                PMU_Emu_Tick(EMU_TICK_RATE_MS);
#ifdef _WIN32
                Sleep(EMU_TICK_RATE_MS);
#else
                usleep(EMU_TICK_RATE_MS * 1000);
#endif
            }
            break;
    }

    /* Cleanup */
    PMU_Emu_Deinit();
    printf("\nEmulator terminated.\n");

    return 0;
}

/* Private functions ---------------------------------------------------------*/

static void PrintBanner(void)
{
    printf("\n");
    printf("╔═══════════════════════════════════════════════════════════════╗\n");
    printf("║               PMU-30 Firmware Emulator v%s                ║\n", EMU_VERSION);
    printf("║                   R2 m-sport (c) 2025                         ║\n");
    printf("╠═══════════════════════════════════════════════════════════════╣\n");
    printf("║  Hardware Emulation Layer for STM32H743 PMU Development       ║\n");
    printf("║                                                               ║\n");
    printf("║  Emulated Components:                                         ║\n");
    printf("║    - 20 ADC Inputs (analog/digital/frequency)                 ║\n");
    printf("║    - 4 CAN Buses (2x CAN FD + 2x CAN 2.0)                      ║\n");
    printf("║    - 30 PROFET Power Outputs                                  ║\n");
    printf("║    - 4 H-Bridge Motor Outputs                                 ║\n");
    printf("║    - Protection System (voltage, temp, current)               ║\n");
    printf("╚═══════════════════════════════════════════════════════════════╝\n");
    printf("\n");
}

static void PrintHelp(void)
{
    printf("\n--- Emulator Commands ---\n\n");
    printf("  ADC Commands:\n");
    printf("    adc <ch> <value>      - Set ADC channel (0-19) raw value (0-1023)\n");
    printf("    adcv <ch> <voltage>   - Set ADC channel voltage (0.0-3.3V)\n");
    printf("    freq <ch> <hz>        - Set frequency input (Hz)\n");
    printf("\n");
    printf("  CAN Commands:\n");
    printf("    can <bus> <id> <d0> [d1-d7] - Inject CAN message\n");
    printf("    canp <bus> <id> <int> <d0-d7> - Add periodic CAN message\n");
    printf("    canoff <bus>          - Set CAN bus offline\n");
    printf("    canon <bus>           - Set CAN bus online\n");
    printf("\n");
    printf("  Protection Commands:\n");
    printf("    volt <mV>             - Set battery voltage (mV)\n");
    printf("    temp <C>              - Set temperature (C)\n");
    printf("    fault <flags>         - Inject protection fault\n");
    printf("    clear                 - Clear all faults\n");
    printf("\n");
    printf("  PROFET Commands:\n");
    printf("    load <ch> <ohm>       - Set PROFET load resistance\n");
    printf("    pfault <ch> <flags>   - Inject PROFET fault\n");
    printf("\n");
    printf("  H-Bridge Commands:\n");
    printf("    hpos <br> <pos>       - Set H-Bridge position (0-1000)\n");
    printf("    hmotor <br> <spd> <i> - Set motor params (speed, inertia)\n");
    printf("    hfault <br> <flags>   - Inject H-Bridge fault\n");
    printf("\n");
    printf("  Control Commands:\n");
    printf("    pause                 - Pause emulator\n");
    printf("    resume                - Resume emulator\n");
    printf("    speed <x>             - Set time scale (1.0 = real-time)\n");
    printf("    reset                 - Reset emulator\n");
    printf("    status                - Print full status\n");
    printf("    tick                  - Run single tick\n");
    printf("\n");
    printf("  Scenario Commands:\n");
    printf("    load <file>           - Load scenario from JSON file\n");
    printf("    save <file>           - Save current state to JSON\n");
    printf("\n");
    printf("  General:\n");
    printf("    help                  - Show this help\n");
    printf("    quit / exit           - Exit emulator\n");
    printf("\n");
}

static void PrintUsage(void)
{
    printf("Usage: pmu30_emulator [OPTIONS]\n\n");
    printf("Options:\n");
    printf("  -h, --help              Show this help message\n");
    printf("  -v, --version           Show version\n");
    printf("  -s, --scenario <file>   Run scenario from JSON file\n");
    printf("  --headless              Run without interactive console\n");
    printf("\n");
    printf("Examples:\n");
    printf("  pmu30_emulator                      Interactive mode\n");
    printf("  pmu30_emulator -s test_can.json     Run CAN test scenario\n");
    printf("  pmu30_emulator --headless           Background mode\n");
    printf("\n");
}

static void SignalHandler(int sig)
{
    (void)sig;
    g_running = false;
    printf("\nShutting down...\n");
}

static void RunInteractiveMode(void)
{
    char cmd[256];

    printf("Interactive mode. Type 'help' for commands, 'quit' to exit.\n\n");
    PrintHelp();

    while (g_running) {
        printf("EMU> ");
        fflush(stdout);

        /* Read command */
        if (fgets(cmd, sizeof(cmd), stdin) == NULL) {
            break;
        }

        /* Remove newline */
        char* nl = strchr(cmd, '\n');
        if (nl) *nl = '\0';

        /* Skip empty commands */
        if (strlen(cmd) == 0) {
            continue;
        }

        /* Process command */
        ProcessCommand(cmd);

        /* Run emulator tick */
        PMU_Emu_Tick(10);  /* 10ms per command cycle */
    }
}

static void RunScenarioMode(const char* filename)
{
    printf("Loading scenario: %s\n", filename);

    if (PMU_Emu_LoadScenario(filename) != 0) {
        fprintf(stderr, "Failed to load scenario\n");
        return;
    }

    printf("Scenario loaded. Running...\n");

    /* Run for 10 seconds or until stopped */
    for (int i = 0; i < 10000 && g_running; i++) {
        PMU_Emu_Tick(EMU_TICK_RATE_MS);

#ifdef _WIN32
        Sleep(EMU_TICK_RATE_MS);
#else
        usleep(EMU_TICK_RATE_MS * 1000);
#endif

        /* Print status every second */
        if (i % 1000 == 0) {
            char stats[128];
            PMU_Emu_GetStatsString(stats, sizeof(stats));
            printf("[%d.%03ds] %s\n", i / 1000, i % 1000, stats);
        }
    }

    printf("\nScenario completed.\n");
    PMU_Emu_PrintState();
}

static void ProcessCommand(const char* cmd)
{
    char token[64];
    int n;

    /* Parse first token */
    if (sscanf(cmd, "%63s%n", token, &n) != 1) {
        return;
    }

    const char* args = cmd + n;

    /* Help */
    if (strcmp(token, "help") == 0) {
        PrintHelp();
    }
    /* Quit */
    else if (strcmp(token, "quit") == 0 || strcmp(token, "exit") == 0) {
        g_running = false;
    }
    /* Status */
    else if (strcmp(token, "status") == 0) {
        PMU_Emu_PrintState();
    }
    /* Reset */
    else if (strcmp(token, "reset") == 0) {
        PMU_Emu_Reset();
        printf("Emulator reset.\n");
    }
    /* Pause */
    else if (strcmp(token, "pause") == 0) {
        PMU_Emu_SetPaused(true);
    }
    /* Resume */
    else if (strcmp(token, "resume") == 0) {
        PMU_Emu_SetPaused(false);
    }
    /* Speed */
    else if (strcmp(token, "speed") == 0) {
        float scale;
        if (sscanf(args, "%f", &scale) == 1) {
            PMU_Emu_SetTimeScale(scale);
        } else {
            printf("Usage: speed <factor>\n");
        }
    }
    /* Tick */
    else if (strcmp(token, "tick") == 0) {
        PMU_Emu_Tick(1);
        printf("Tick executed.\n");
    }
    /* ADC raw */
    else if (strcmp(token, "adc") == 0) {
        int ch, val;
        if (sscanf(args, "%d %d", &ch, &val) == 2) {
            if (PMU_Emu_ADC_SetRaw(ch, val) == 0) {
                printf("ADC[%d] = %d\n", ch, val);
            } else {
                printf("Error: invalid channel\n");
            }
        } else {
            printf("Usage: adc <channel> <value>\n");
        }
    }
    /* ADC voltage */
    else if (strcmp(token, "adcv") == 0) {
        int ch;
        float v;
        if (sscanf(args, "%d %f", &ch, &v) == 2) {
            if (PMU_Emu_ADC_SetVoltage(ch, v) == 0) {
                printf("ADC[%d] = %.3fV\n", ch, v);
            } else {
                printf("Error: invalid channel\n");
            }
        } else {
            printf("Usage: adcv <channel> <voltage>\n");
        }
    }
    /* Frequency */
    else if (strcmp(token, "freq") == 0) {
        int ch;
        uint32_t hz;
        if (sscanf(args, "%d %u", &ch, &hz) == 2) {
            if (PMU_Emu_ADC_SetFrequency(ch, hz) == 0) {
                printf("ADC[%d] freq = %u Hz\n", ch, hz);
            } else {
                printf("Error: invalid channel\n");
            }
        } else {
            printf("Usage: freq <channel> <hz>\n");
        }
    }
    /* CAN inject */
    else if (strcmp(token, "can") == 0) {
        int bus;
        uint32_t id;
        uint8_t data[8] = {0};
        int d0, d1, d2, d3, d4, d5, d6, d7;

        int cnt = sscanf(args, "%d %x %x %x %x %x %x %x %x %x",
                        &bus, &id, &d0, &d1, &d2, &d3, &d4, &d5, &d6, &d7);

        if (cnt >= 3) {
            int len = cnt - 2;
            data[0] = d0; data[1] = d1; data[2] = d2; data[3] = d3;
            data[4] = d4; data[5] = d5; data[6] = d6; data[7] = d7;

            if (PMU_Emu_CAN_InjectMessage(bus, id, data, len) == 0) {
                printf("CAN[%d] TX: ID=0x%X, DLC=%d\n", bus, id, len);
            } else {
                printf("Error: CAN injection failed\n");
            }
        } else {
            printf("Usage: can <bus> <id> <d0> [d1-d7]\n");
        }
    }
    /* CAN bus online */
    else if (strcmp(token, "canon") == 0) {
        int bus;
        if (sscanf(args, "%d", &bus) == 1) {
            PMU_Emu_CAN_SetBusOnline(bus, true);
        } else {
            printf("Usage: canon <bus>\n");
        }
    }
    /* CAN bus offline */
    else if (strcmp(token, "canoff") == 0) {
        int bus;
        if (sscanf(args, "%d", &bus) == 1) {
            PMU_Emu_CAN_SetBusOnline(bus, false);
        } else {
            printf("Usage: canoff <bus>\n");
        }
    }
    /* Voltage */
    else if (strcmp(token, "volt") == 0) {
        int mv;
        if (sscanf(args, "%d", &mv) == 1) {
            PMU_Emu_Protection_SetVoltage(mv);
            printf("Voltage = %d mV\n", mv);
        } else {
            printf("Usage: volt <mV>\n");
        }
    }
    /* Temperature */
    else if (strcmp(token, "temp") == 0) {
        int temp;
        if (sscanf(args, "%d", &temp) == 1) {
            PMU_Emu_Protection_SetTemperature(temp);
            printf("Temperature = %d C\n", temp);
        } else {
            printf("Usage: temp <C>\n");
        }
    }
    /* Fault injection */
    else if (strcmp(token, "fault") == 0) {
        int flags;
        if (sscanf(args, "%x", &flags) == 1) {
            PMU_Emu_Protection_InjectFault(flags);
            printf("Fault injected: 0x%04X\n", flags);
        } else {
            printf("Usage: fault <hex_flags>\n");
        }
    }
    /* Clear faults */
    else if (strcmp(token, "clear") == 0) {
        PMU_Emu_Protection_ClearFaults();
        printf("Faults cleared.\n");
    }
    /* PROFET load */
    else if (strcmp(token, "load") == 0) {
        int ch;
        float ohm;
        if (sscanf(args, "%d %f", &ch, &ohm) == 2) {
            if (PMU_Emu_PROFET_SetLoad(ch, ohm) == 0) {
                printf("PROFET[%d] load = %.1f ohm\n", ch, ohm);
            } else {
                printf("Error: invalid channel\n");
            }
        } else {
            printf("Usage: load <channel> <ohm>\n");
        }
    }
    /* PROFET fault */
    else if (strcmp(token, "pfault") == 0) {
        int ch, flags;
        if (sscanf(args, "%d %x", &ch, &flags) == 2) {
            if (PMU_Emu_PROFET_InjectFault(ch, flags) == 0) {
                printf("PROFET[%d] fault: 0x%02X\n", ch, flags);
            } else {
                printf("Error: invalid channel\n");
            }
        } else {
            printf("Usage: pfault <channel> <hex_flags>\n");
        }
    }
    /* H-Bridge position */
    else if (strcmp(token, "hpos") == 0) {
        int br, pos;
        if (sscanf(args, "%d %d", &br, &pos) == 2) {
            if (PMU_Emu_HBridge_SetPosition(br, pos) == 0) {
                printf("HBridge[%d] position = %d\n", br, pos);
            } else {
                printf("Error: invalid bridge\n");
            }
        } else {
            printf("Usage: hpos <bridge> <position>\n");
        }
    }
    /* H-Bridge motor params */
    else if (strcmp(token, "hmotor") == 0) {
        int br;
        float spd, inertia;
        if (sscanf(args, "%d %f %f", &br, &spd, &inertia) == 3) {
            if (PMU_Emu_HBridge_SetMotorParams(br, spd, inertia) == 0) {
                printf("HBridge[%d] motor: speed=%.1f, inertia=%.1f\n", br, spd, inertia);
            } else {
                printf("Error: invalid bridge\n");
            }
        } else {
            printf("Usage: hmotor <bridge> <speed> <inertia>\n");
        }
    }
    /* H-Bridge fault */
    else if (strcmp(token, "hfault") == 0) {
        int br, flags;
        if (sscanf(args, "%d %x", &br, &flags) == 2) {
            if (PMU_Emu_HBridge_InjectFault(br, flags) == 0) {
                printf("HBridge[%d] fault: 0x%02X\n", br, flags);
            } else {
                printf("Error: invalid bridge\n");
            }
        } else {
            printf("Usage: hfault <bridge> <hex_flags>\n");
        }
    }
    /* Load scenario */
    else if (strcmp(token, "load") == 0 && strstr(args, ".json")) {
        char filename[256];
        if (sscanf(args, "%255s", filename) == 1) {
            if (PMU_Emu_LoadScenario(filename) == 0) {
                printf("Scenario loaded: %s\n", filename);
            } else {
                printf("Error loading scenario\n");
            }
        }
    }
    /* Save scenario */
    else if (strcmp(token, "save") == 0) {
        char filename[256];
        if (sscanf(args, "%255s", filename) == 1) {
            if (PMU_Emu_SaveScenario(filename) == 0) {
                printf("Scenario saved: %s\n", filename);
            } else {
                printf("Error saving scenario\n");
            }
        } else {
            printf("Usage: save <filename>\n");
        }
    }
    /* Unknown command */
    else {
        printf("Unknown command: %s. Type 'help' for available commands.\n", token);
    }
}

/* Callbacks -----------------------------------------------------------------*/

static void OnCanTx(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len)
{
    printf("[CAN TX] Bus=%d, ID=0x%X, DLC=%d, Data=", bus, id, len);
    for (int i = 0; i < len && i < 8; i++) {
        printf("%02X ", data[i]);
    }
    printf("\n");
}

static void OnProfetChange(uint8_t channel, uint16_t value)
{
    printf("[PROFET] Ch=%d, Value=%d\n", channel, value);
}

static void OnHBridgeChange(uint8_t channel, uint16_t value)
{
    printf("[HBRIDGE] Ch=%d, Value=%d\n", channel, value);
}

/* Utility functions ---------------------------------------------------------*/

#ifndef _WIN32
static int KeyboardHit(void)
{
    struct termios oldt, newt;
    int ch;
    int oldf;

    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);
    oldf = fcntl(STDIN_FILENO, F_GETFL, 0);
    fcntl(STDIN_FILENO, F_SETFL, oldf | O_NONBLOCK);

    ch = getchar();

    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    fcntl(STDIN_FILENO, F_SETFL, oldf);

    if (ch != EOF) {
        ungetc(ch, stdin);
        return 1;
    }

    return 0;
}

static int GetChar(void)
{
    return getchar();
}
#else
static int KeyboardHit(void)
{
    return _kbhit();
}

static int GetChar(void)
{
    return _getch();
}
#endif

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
