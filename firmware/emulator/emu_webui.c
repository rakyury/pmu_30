/**
 ******************************************************************************
 * @file           : emu_webui.c
 * @brief          : Web UI Server Implementation - Extended Version
 * @author         : R2 m-sport
 * @date           : 2025-12-23
 ******************************************************************************
 * Extended features:
 * - PWM status and characteristics display
 * - Analog input voltage injection
 * - Battery voltage control for protection testing
 * - Load resistance control per channel (for retry/overcurrent testing)
 * - CAN message injection
 * - Detailed H-Bridge status
 * - Config loading/parsing logs
 * - Command log from configurator
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "emu_webui.h"
#include "pmu_emulator.h"
#include "pmu_channel.h"
#include "pmu_profet.h"
#include "emu_protocol_server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdarg.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    #define close closesocket
    #define SOCKET_ERROR_CODE WSAGetLastError()
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
    #include <errno.h>
    #define SOCKET int
    #define INVALID_SOCKET -1
    #define SOCKET_ERROR -1
    #define SOCKET_ERROR_CODE errno
#endif

/* Private defines -----------------------------------------------------------*/

#define WS_FIN_BIT          0x80
#define WS_OPCODE_TEXT      0x01
#define WS_OPCODE_BINARY    0x02
#define WS_OPCODE_CLOSE     0x08
#define WS_OPCODE_PING      0x09
#define WS_OPCODE_PONG      0x0A
#define WS_MASK_BIT         0x80

#define CMD_LOG_MAX_ENTRIES 100
#define CMD_LOG_ENTRY_SIZE  256

/* WebSocket GUID for handshake */
static const char* WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

/* Private types -------------------------------------------------------------*/

typedef struct {
    SOCKET socket;
    bool is_websocket;
    bool active;
    uint8_t recv_buffer[EMU_WEBUI_BUFFER_SIZE];
    size_t recv_len;
} WebClient_t;

/* Command log entry */
typedef struct {
    char message[CMD_LOG_ENTRY_SIZE];
    uint8_t level;      /* 0=debug, 1=info, 2=warning, 3=error */
    uint32_t timestamp;
} CmdLogEntry_t;

/* Private variables ---------------------------------------------------------*/

static bool s_initialized = false;
static bool s_running = false;
static SOCKET s_listen_socket = INVALID_SOCKET;
static EMU_WebUI_Config_t s_config;
static EMU_WebUI_Stats_t s_stats;
static WebClient_t s_clients[EMU_WEBUI_MAX_WS_CLIENTS];

/* Command log ring buffer */
static CmdLogEntry_t s_cmd_log[CMD_LOG_MAX_ENTRIES];
static int s_cmd_log_head = 0;
static int s_cmd_log_count = 0;

/* Embedded HTML Dashboard - Extended Version */
static const char* DASHBOARD_HTML =
"<!DOCTYPE html>\n"
"<html lang=\"en\">\n"
"<head>\n"
"    <meta charset=\"UTF-8\">\n"
"    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
"    <title>PMU-30 Emulator - Extended Monitor</title>\n"
"    <style>\n"
"        * { margin: 0; padding: 0; box-sizing: border-box; }\n"
"        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; font-size: 13px; }\n"
"        .header { background: #16213e; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f0; }\n"
"        .header h1 { font-size: 1.3em; color: #0f0; }\n"
"        .status { display: flex; align-items: center; gap: 10px; }\n"
"        .status-dot { width: 10px; height: 10px; border-radius: 50%; background: #f00; }\n"
"        .status-dot.connected { background: #0f0; animation: pulse 2s infinite; }\n"
"        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }\n"
"        .container { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 12px; padding: 15px; }\n"
"        .card { background: #16213e; border-radius: 6px; padding: 12px; overflow: hidden; }\n"
"        .card h2 { font-size: 0.9em; color: #888; margin-bottom: 8px; border-bottom: 1px solid #333; padding-bottom: 6px; display: flex; justify-content: space-between; }\n"
"        .card h2 span { color: #0f0; font-size: 0.85em; }\n"
"        /* PROFET Grid */\n"
"        .profet-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 4px; }\n"
"        .profet-ch { background: #0f3460; padding: 6px 2px; border-radius: 4px; text-align: center; cursor: pointer; transition: all 0.2s; position: relative; }\n"
"        .profet-ch:hover { transform: scale(1.05); z-index: 10; }\n"
"        .profet-ch.on { background: #0a5; }\n"
"        .profet-ch.pwm { background: #085; border: 1px solid #0ff; }\n"
"        .profet-ch.fault { background: #a00; animation: blink 0.5s infinite; }\n"
"        @keyframes blink { 50% { opacity: 0.5; } }\n"
"        .profet-ch .ch-num { font-size: 0.7em; color: #aaa; }\n"
"        .profet-ch .ch-val { font-size: 0.85em; font-weight: bold; }\n"
"        .profet-ch .ch-pwm { font-size: 0.65em; color: #0ff; }\n"
"        /* Tooltip */\n"
"        .tooltip { display: none; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #000; padding: 8px; border-radius: 4px; white-space: nowrap; z-index: 100; font-size: 0.75em; border: 1px solid #0f0; }\n"
"        .profet-ch:hover .tooltip { display: block; }\n"
"        /* H-Bridge */\n"
"        .hbridge-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }\n"
"        .hbridge-ch { background: #0f3460; padding: 10px; border-radius: 6px; }\n"
"        .hbridge-ch.active { border: 1px solid #0f0; }\n"
"        .hbridge-ch.fault { background: #500; border: 1px solid #f00; }\n"
"        .hbridge-ch .hb-title { font-weight: bold; color: #0ff; margin-bottom: 5px; }\n"
"        .hbridge-ch .hb-row { display: flex; justify-content: space-between; font-size: 0.8em; padding: 2px 0; }\n"
"        .hbridge-ch .hb-label { color: #888; }\n"
"        .hbridge-ch .hb-val { color: #fff; }\n"
"        .hbridge-ch .hb-val.fwd { color: #0f0; }\n"
"        .hbridge-ch .hb-val.rev { color: #fa0; }\n"
"        .pos-bar { height: 6px; background: #333; border-radius: 3px; margin-top: 5px; overflow: hidden; }\n"
"        .pos-bar .pos-fill { height: 100%; background: #0f0; transition: width 0.1s; }\n"
"        /* Analog Inputs */\n"
"        .analog-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }\n"
"        .analog-ch { background: #0f3460; padding: 6px; border-radius: 4px; cursor: pointer; }\n"
"        .analog-ch:hover { background: #1a5a8a; }\n"
"        .analog-ch .ain-label { font-size: 0.7em; color: #888; }\n"
"        .analog-ch .ain-val { font-size: 0.95em; color: #0ff; font-weight: bold; }\n"
"        .analog-ch input { width: 100%; background: #0a2540; border: 1px solid #0ff; color: #fff; padding: 3px; border-radius: 3px; font-size: 0.85em; }\n"
"        /* System Controls */\n"
"        .sys-controls { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }\n"
"        .sys-ctrl { background: #0f3460; padding: 10px; border-radius: 6px; }\n"
"        .sys-ctrl label { display: block; font-size: 0.8em; color: #888; margin-bottom: 5px; }\n"
"        .sys-ctrl .ctrl-row { display: flex; align-items: center; gap: 10px; }\n"
"        .sys-ctrl input[type=range] { flex: 1; accent-color: #0f0; }\n"
"        .sys-ctrl .ctrl-val { min-width: 60px; text-align: right; color: #0f0; font-weight: bold; }\n"
"        .sys-status { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 10px; }\n"
"        .sys-item { background: #0a2540; padding: 8px; border-radius: 4px; text-align: center; }\n"
"        .sys-item .si-label { font-size: 0.7em; color: #888; }\n"
"        .sys-item .si-val { font-size: 1em; color: #0f0; font-weight: bold; }\n"
"        /* CAN Injection */\n"
"        .can-form { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; }\n"
"        .can-form label { font-size: 0.8em; color: #888; }\n"
"        .can-form input, .can-form select { background: #0a2540; border: 1px solid #444; color: #fff; padding: 6px 8px; border-radius: 4px; }\n"
"        .can-form input:focus, .can-form select:focus { border-color: #0f0; outline: none; }\n"
"        .can-data { grid-column: 1 / -1; display: flex; gap: 4px; flex-wrap: wrap; }\n"
"        .can-data input { width: 40px; text-align: center; }\n"
"        .can-history { max-height: 120px; overflow-y: auto; background: #0a0a15; padding: 8px; border-radius: 4px; margin-top: 8px; font-family: monospace; font-size: 0.8em; }\n"
"        .can-msg { padding: 2px 0; border-bottom: 1px solid #222; }\n"
"        .can-msg.tx { color: #0f0; }\n"
"        .can-msg.rx { color: #0ff; }\n"
"        /* Load Control */\n"
"        .load-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px; }\n"
"        .load-ch { background: #0f3460; padding: 5px; border-radius: 4px; text-align: center; cursor: pointer; font-size: 0.75em; }\n"
"        .load-ch:hover { background: #1a5a8a; }\n"
"        .load-ch .ld-num { color: #888; }\n"
"        .load-ch .ld-val { color: #fa0; font-weight: bold; }\n"
"        .load-ch.short { background: #800; }\n"
"        .load-ch.open { background: #080; }\n"
"        .load-presets { display: flex; gap: 8px; margin-bottom: 10px; }\n"
"        .load-presets button { flex: 1; }\n"
"        /* Fault Injection */\n"
"        .fault-form { display: grid; grid-template-columns: 1fr 1fr auto; gap: 8px; }\n"
"        .fault-form select, .fault-form button { padding: 8px; border-radius: 4px; }\n"
"        .fault-list { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }\n"
"        .fault-tag { background: #800; padding: 4px 8px; border-radius: 4px; font-size: 0.75em; display: flex; align-items: center; gap: 4px; }\n"
"        .fault-tag button { background: none; border: none; color: #fff; cursor: pointer; font-size: 1em; }\n"
"        /* Buttons */\n"
"        .btn { background: #0f3460; color: #fff; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; font-size: 0.85em; transition: background 0.2s; }\n"
"        .btn:hover { background: #1a5a8a; }\n"
"        .btn.primary { background: #0a5; }\n"
"        .btn.primary:hover { background: #0b6; }\n"
"        .btn.danger { background: #a00; }\n"
"        .btn.danger:hover { background: #c00; }\n"
"        .btn.small { padding: 4px 8px; font-size: 0.75em; }\n"
"        /* Log Panel */\n"
"        .log-tabs { display: flex; gap: 5px; margin-bottom: 8px; }\n"
"        .log-tab { padding: 6px 12px; background: #0f3460; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 0.8em; }\n"
"        .log-tab.active { background: #0a2540; color: #0f0; }\n"
"        .log-container { height: 180px; overflow-y: auto; background: #0a0a15; border-radius: 0 4px 4px 4px; padding: 8px; font-family: monospace; font-size: 0.8em; }\n"
"        .log-entry { padding: 2px 0; border-bottom: 1px solid #222; }\n"
"        .log-entry.error { color: #f55; }\n"
"        .log-entry.warning { color: #fa0; }\n"
"        .log-entry.info { color: #5f5; }\n"
"        .log-entry.debug { color: #888; }\n"
"        .log-entry.cmd { color: #0ff; }\n"
"        .log-entry.config { color: #f0f; }\n"
"        /* Wide cards */\n"
"        .card.wide { grid-column: 1 / -1; }\n"
"        .card.half { }\n"
"        /* Modal */\n"
"        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; }\n"
"        .modal.show { display: flex; }\n"
"        .modal-content { background: #16213e; padding: 20px; border-radius: 8px; min-width: 300px; max-width: 500px; }\n"
"        .modal-header { display: flex; justify-content: space-between; margin-bottom: 15px; }\n"
"        .modal-header h3 { color: #0f0; }\n"
"        .modal-close { background: none; border: none; color: #fff; font-size: 1.5em; cursor: pointer; }\n"
"    </style>\n"
"</head>\n"
"<body>\n"
"    <div class=\"header\">\n"
"        <h1>PMU-30 Emulator - Extended Monitor</h1>\n"
"        <div class=\"status\">\n"
"            <div class=\"status-dot\" id=\"wsStatus\"></div>\n"
"            <span id=\"wsText\">Disconnected</span>\n"
"        </div>\n"
"    </div>\n"
"    <div class=\"container\">\n"
"        <!-- PROFET Channels -->\n"
"        <div class=\"card wide\">\n"
"            <h2>PROFET Channels <span id=\"profetActiveCount\">0/30 Active</span></h2>\n"
"            <div class=\"profet-grid\" id=\"profetGrid\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- H-Bridge Channels -->\n"
"        <div class=\"card\">\n"
"            <h2>H-Bridge Motors</h2>\n"
"            <div class=\"hbridge-grid\" id=\"hbridgeGrid\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- Analog Inputs -->\n"
"        <div class=\"card\">\n"
"            <h2>Analog Inputs (click to edit)</h2>\n"
"            <div class=\"analog-grid\" id=\"analogGrid\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- System Controls -->\n"
"        <div class=\"card\">\n"
"            <h2>System Controls</h2>\n"
"            <div class=\"sys-controls\">\n"
"                <div class=\"sys-ctrl\">\n"
"                    <label>Battery Voltage</label>\n"
"                    <div class=\"ctrl-row\">\n"
"                        <input type=\"range\" id=\"battVoltage\" min=\"6\" max=\"18\" step=\"0.1\" value=\"12\">\n"
"                        <span class=\"ctrl-val\" id=\"battVoltageVal\">12.0V</span>\n"
"                    </div>\n"
"                </div>\n"
"                <div class=\"sys-ctrl\">\n"
"                    <label>Board Temperature</label>\n"
"                    <div class=\"ctrl-row\">\n"
"                        <input type=\"range\" id=\"boardTemp\" min=\"-20\" max=\"100\" step=\"1\" value=\"25\">\n"
"                        <span class=\"ctrl-val\" id=\"boardTempVal\">25C</span>\n"
"                    </div>\n"
"                </div>\n"
"            </div>\n"
"            <div class=\"sys-status\" id=\"sysStatus\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- Load Simulation -->\n"
"        <div class=\"card\">\n"
"            <h2>Load Simulation (Resistance)</h2>\n"
"            <div class=\"load-presets\">\n"
"                <button class=\"btn small\" onclick=\"setAllLoads(10)\">All Normal (10R)</button>\n"
"                <button class=\"btn small danger\" onclick=\"setAllLoads(0.01)\">All Short (0.01R)</button>\n"
"                <button class=\"btn small\" onclick=\"setAllLoads(10000)\">All Open (10kR)</button>\n"
"            </div>\n"
"            <div class=\"load-grid\" id=\"loadGrid\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- CAN Injection -->\n"
"        <div class=\"card\">\n"
"            <h2>CAN Message Injection</h2>\n"
"            <div class=\"can-form\">\n"
"                <label>Bus:</label>\n"
"                <select id=\"canBus\">\n"
"                    <option value=\"0\">CAN 0</option>\n"
"                    <option value=\"1\">CAN 1</option>\n"
"                    <option value=\"2\">CAN 2</option>\n"
"                    <option value=\"3\">CAN 3</option>\n"
"                </select>\n"
"                <button class=\"btn primary\" onclick=\"sendCanMessage()\">Send</button>\n"
"                <label>ID (hex):</label>\n"
"                <input type=\"text\" id=\"canId\" value=\"100\" placeholder=\"0x100\">\n"
"                <span></span>\n"
"                <div class=\"can-data\">\n"
"                    <label style=\"width:100%\">Data (hex bytes):</label>\n"
"                    <input type=\"text\" id=\"canD0\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD1\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD2\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD3\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD4\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD5\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD6\" value=\"00\" maxlength=\"2\">\n"
"                    <input type=\"text\" id=\"canD7\" value=\"00\" maxlength=\"2\">\n"
"                </div>\n"
"            </div>\n"
"            <div class=\"can-history\" id=\"canHistory\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- Link ECU CAN Stream -->\n"
"        <div class=\"card wide\">\n"
"            <h2>Link ECU Generic Dashboard Stream <span id=\"linkStreamStatus\">Stopped</span></h2>\n"
"            <div style=\"display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:10px\">\n"
"                <div class=\"sys-ctrl\"><label>RPM</label><input type=\"number\" id=\"linkRpm\" value=\"3500\" min=\"0\" max=\"15000\"></div>\n"
"                <div class=\"sys-ctrl\"><label>TPS %</label><input type=\"number\" id=\"linkTps\" value=\"25\" min=\"0\" max=\"100\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>MAP kPa</label><input type=\"number\" id=\"linkMap\" value=\"100\" min=\"0\" max=\"400\"></div>\n"
"                <div class=\"sys-ctrl\"><label>CLT C</label><input type=\"number\" id=\"linkClt\" value=\"85\" min=\"-40\" max=\"150\"></div>\n"
"                <div class=\"sys-ctrl\"><label>IAT C</label><input type=\"number\" id=\"linkIat\" value=\"35\" min=\"-40\" max=\"150\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Battery V</label><input type=\"number\" id=\"linkBatt\" value=\"13.8\" min=\"0\" max=\"20\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Lambda 1</label><input type=\"number\" id=\"linkLambda1\" value=\"1.00\" min=\"0.5\" max=\"2\" step=\"0.01\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Lambda 2</label><input type=\"number\" id=\"linkLambda2\" value=\"1.00\" min=\"0.5\" max=\"2\" step=\"0.01\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Oil P bar</label><input type=\"number\" id=\"linkOilP\" value=\"4.5\" min=\"0\" max=\"10\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Oil T C</label><input type=\"number\" id=\"linkOilT\" value=\"95\" min=\"-40\" max=\"150\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Fuel P bar</label><input type=\"number\" id=\"linkFuelP\" value=\"3.0\" min=\"0\" max=\"10\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Speed km/h</label><input type=\"number\" id=\"linkSpeed\" value=\"120\" min=\"0\" max=\"400\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Gear</label><input type=\"number\" id=\"linkGear\" value=\"4\" min=\"0\" max=\"8\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Ign Angle</label><input type=\"number\" id=\"linkIgn\" value=\"28\" min=\"-20\" max=\"60\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Inj DC %</label><input type=\"number\" id=\"linkInjDC\" value=\"35\" min=\"0\" max=\"100\" step=\"0.1\"></div>\n"
"                <div class=\"sys-ctrl\"><label>Baro kPa</label><input type=\"number\" id=\"linkBaro\" value=\"101\" min=\"80\" max=\"110\"></div>\n"
"            </div>\n"
"            <div style=\"display:flex;gap:8px;flex-wrap:wrap\">\n"
"                <div class=\"sys-ctrl\" style=\"flex:1;min-width:150px\"><label>CAN Bus</label><select id=\"linkCanBus\"><option value=\"0\">CAN 0</option><option value=\"1\" selected>CAN 1</option><option value=\"2\">CAN 2</option><option value=\"3\">CAN 3</option></select></div>\n"
"                <div class=\"sys-ctrl\" style=\"flex:1;min-width:150px\"><label>Base ID (hex)</label><input type=\"text\" id=\"linkBaseId\" value=\"3E8\"></div>\n"
"                <div class=\"sys-ctrl\" style=\"flex:1;min-width:150px\"><label>Interval ms</label><input type=\"number\" id=\"linkInterval\" value=\"50\" min=\"10\" max=\"1000\"></div>\n"
"                <button class=\"btn primary\" id=\"linkStartBtn\" onclick=\"toggleLinkStream()\">Start Stream</button>\n"
"                <button class=\"btn\" onclick=\"sendLinkFrameOnce()\">Send Once</button>\n"
"            </div>\n"
"        </div>\n"
"        \n"
"        <!-- Config Statistics -->\n"
"        <div class=\"card\">\n"
"            <h2>Configuration <span id=\"configStatusBadge\" class=\"badge off\">Not loaded</span></h2>\n"
"            <div id=\"configStats\" style=\"font-size:0.9em\">\n"
"                <div style=\"color:#888\">No configuration loaded</div>\n"
"            </div>\n"
"            <div style=\"margin-top:10px;display:flex;gap:8px;flex-wrap:wrap\">\n"
"                <a id=\"configDownloadLink\" class=\"btn small\" style=\"display:none\" href=\"/config.json\" download=\"pmu30_config.json\">Download</a>\n"
"                <button class=\"btn small\" onclick=\"refreshConfigStats()\">Refresh</button>\n"
"                <button class=\"btn small danger\" onclick=\"clearConfig()\">Clear Config</button>\n"
"            </div>\n"
"        </div>\n"
"        \n"
"        <!-- Fault Injection -->\n"
"        <div class=\"card\">\n"
"            <h2>Fault Injection</h2>\n"
"            <div class=\"fault-form\">\n"
"                <select id=\"faultChannel\">\n"
"                    <optgroup label=\"PROFET\"></optgroup>\n"
"                </select>\n"
"                <select id=\"faultType\">\n"
"                    <option value=\"1\">Overcurrent</option>\n"
"                    <option value=\"2\">Short Circuit</option>\n"
"                    <option value=\"4\">Open Load</option>\n"
"                    <option value=\"8\">Overtemperature</option>\n"
"                </select>\n"
"                <button class=\"btn danger\" onclick=\"injectFault()\">Inject</button>\n"
"            </div>\n"
"            <div class=\"fault-list\" id=\"faultList\"></div>\n"
"        </div>\n"
"        \n"
"        <!-- Log Panel -->\n"
"        <div class=\"card wide\">\n"
"            <h2>System Logs</h2>\n"
"            <div class=\"log-tabs\">\n"
"                <div class=\"log-tab active\" data-log=\"all\" onclick=\"switchLogTab('all')\">All</div>\n"
"                <div class=\"log-tab\" data-log=\"cmd\" onclick=\"switchLogTab('cmd')\">Commands</div>\n"
"                <div class=\"log-tab\" data-log=\"config\" onclick=\"switchLogTab('config')\">Config</div>\n"
"                <div class=\"log-tab\" data-log=\"error\" onclick=\"switchLogTab('error')\">Errors</div>\n"
"            </div>\n"
"            <div class=\"log-container\" id=\"logContainer\"></div>\n"
"        </div>\n"
"    </div>\n"
"    \n"
"    <!-- Load Edit Modal -->\n"
"    <div class=\"modal\" id=\"loadModal\">\n"
"        <div class=\"modal-content\">\n"
"            <div class=\"modal-header\">\n"
"                <h3>Set Load Resistance - CH<span id=\"loadModalCh\">1</span></h3>\n"
"                <button class=\"modal-close\" onclick=\"closeLoadModal()\">&times;</button>\n"
"            </div>\n"
"            <div style=\"margin-bottom:15px\">\n"
"                <label>Resistance (Ohms):</label>\n"
"                <input type=\"number\" id=\"loadModalValue\" value=\"10\" min=\"0.001\" max=\"100000\" step=\"0.1\" style=\"width:100%;padding:8px;margin-top:5px;background:#0a2540;border:1px solid #444;color:#fff;border-radius:4px\">\n"
"            </div>\n"
"            <div style=\"display:flex;gap:8px\">\n"
"                <button class=\"btn\" onclick=\"setLoadValue(0.01)\">Short (0.01R)</button>\n"
"                <button class=\"btn\" onclick=\"setLoadValue(10)\">Normal (10R)</button>\n"
"                <button class=\"btn\" onclick=\"setLoadValue(10000)\">Open (10kR)</button>\n"
"                <button class=\"btn primary\" onclick=\"applyLoadModal()\">Apply</button>\n"
"            </div>\n"
"        </div>\n"
"    </div>\n"
"    \n"
"    <script>\n"
"        let ws = null;\n"
"        let reconnectTimer = null;\n"
"        let currentLogFilter = 'all';\n"
"        let telemetryData = {};\n"
"        let loadValues = new Array(30).fill(10);\n"
"        let editingAnalog = -1;\n"
"        let selectedLoadCh = 0;\n"
"        let activeFaults = [];\n"
"        \n"
"        const wsStatus = document.getElementById('wsStatus');\n"
"        const wsText = document.getElementById('wsText');\n"
"        \n"
"        function connect() {\n"
"            ws = new WebSocket(`ws://${location.host}/ws`);\n"
"            ws.onopen = () => {\n"
"                wsStatus.classList.add('connected');\n"
"                wsText.textContent = 'Connected';\n"
"                addLog('info', 'system', 'WebSocket connected');\n"
"            };\n"
"            ws.onclose = () => {\n"
"                wsStatus.classList.remove('connected');\n"
"                wsText.textContent = 'Disconnected';\n"
"                addLog('warning', 'system', 'WebSocket disconnected, reconnecting...');\n"
"                reconnectTimer = setTimeout(connect, 2000);\n"
"            };\n"
"            ws.onerror = (e) => addLog('error', 'system', 'WebSocket error');\n"
"            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));\n"
"        }\n"
"        \n"
"        function handleMessage(msg) {\n"
"            if (msg.type === 'telemetry') {\n"
"                telemetryData = msg.data;\n"
"                updateTelemetry(msg.data);\n"
"            } else if (msg.type === 'log') {\n"
"                addLog(msg.level, msg.source, msg.message);\n"
"            } else if (msg.type === 'can_tx') {\n"
"                addCanHistory('tx', msg.bus, msg.id, msg.data);\n"
"            } else if (msg.type === 'can_rx') {\n"
"                addCanHistory('rx', msg.bus, msg.id, msg.data);\n"
"            }\n"
"        }\n"
"        \n"
"        function updateTelemetry(data) {\n"
"            // Update PROFET channels\n"
"            let activeCount = 0;\n"
"            let html = '';\n"
"            for (let i = 0; i < 30; i++) {\n"
"                const ch = data.profets?.[i] || {};\n"
"                const state = ch.state || 0;\n"
"                /* ECUMaster states: 0=OFF, 1=ON, 2=OC, 3=OT, 4=SC, 5=OL, 6=PWM, 7=DIS */\n"
"                const isPwm = state === 6;\n"
"                const isFault = state >= 2 && state <= 5;\n"
"                const isOn = state === 1 || state === 6;\n"
"                if (isOn) activeCount++;\n"
"                \n"
"                let cls = isFault ? 'fault' : (isPwm ? 'pwm' : (isOn ? 'on' : ''));\n"
"                const current = (ch.current || 0).toFixed(1);\n"
"                const pwmPct = ((ch.pwm_duty || 0) / 10).toFixed(0);\n"
"                const temp = ch.temp || 25;\n"
"                const faultStr = getFaultString(ch.fault || 0);\n"
"                \n"
"                html += `<div class=\"profet-ch ${cls}\" onclick=\"toggleChannel(${i+1})\">`;\n"
"                html += `<div class=\"ch-num\">CH${i+1}</div>`;\n"
"                html += `<div class=\"ch-val\">${current}A</div>`;\n"
"                if (isPwm) html += `<div class=\"ch-pwm\">${pwmPct}%</div>`;\n"
"                html += `<div class=\"tooltip\">`;\n"
"                html += `<b>Channel ${i+1}</b><br>`;\n"
"                html += `State: ${['OFF','ON','OC','OT','SC','OL','PWM','DIS'][state] || 'UNK'}<br>`;\n"
"                html += `Current: ${current}A<br>`;\n"
"                html += `PWM: ${pwmPct}%<br>`;\n"
"                html += `Temp: ${temp}C<br>`;\n"
"                html += `Load: ${loadValues[i]}R<br>`;\n"
"                if (faultStr) html += `<span style=\"color:#f55\">Fault: ${faultStr}</span>`;\n"
"                html += `</div></div>`;\n"
"            }\n"
"            document.getElementById('profetGrid').innerHTML = html;\n"
"            document.getElementById('profetActiveCount').textContent = `${activeCount}/30 Active`;\n"
"            \n"
"            // Update H-Bridge channels\n"
"            html = '';\n"
"            for (let i = 0; i < 4; i++) {\n"
"                const ch = data.hbridges?.[i] || {};\n"
"                const mode = ch.mode || 0;\n"
"                const state = ch.state || 0;\n"
"                const isFault = ch.fault > 0;\n"
"                const isActive = ch.pwm > 0;\n"
"                const pos = ch.position || 0;\n"
"                const target = ch.target || 0;\n"
"                const current = ((ch.current || 0) / 1000).toFixed(2);\n"
"                \n"
"                const modeStr = ['COAST','FWD','REV','BRAKE','PARK','PID'][mode] || 'UNK';\n"
"                const stateStr = ['IDLE','RUN','PARKING','PARKED','FAULT'][state] || 'UNK';\n"
"                const dirClass = mode === 1 ? 'fwd' : (mode === 2 ? 'rev' : '');\n"
"                \n"
"                html += `<div class=\"hbridge-ch ${isFault ? 'fault' : (isActive ? 'active' : '')}\">`;\n"
"                html += `<div class=\"hb-title\">HB${i+1}</div>`;\n"
"                html += `<div class=\"hb-row\"><span class=\"hb-label\">Mode:</span><span class=\"hb-val ${dirClass}\">${modeStr}</span></div>`;\n"
"                html += `<div class=\"hb-row\"><span class=\"hb-label\">State:</span><span class=\"hb-val\">${stateStr}</span></div>`;\n"
"                html += `<div class=\"hb-row\"><span class=\"hb-label\">PWM:</span><span class=\"hb-val\">${ch.pwm || 0}%</span></div>`;\n"
"                html += `<div class=\"hb-row\"><span class=\"hb-label\">Current:</span><span class=\"hb-val\">${current}A</span></div>`;\n"
"                html += `<div class=\"hb-row\"><span class=\"hb-label\">Position:</span><span class=\"hb-val\">${(pos/10).toFixed(1)}%</span></div>`;\n"
"                html += `<div class=\"pos-bar\"><div class=\"pos-fill\" style=\"width:${pos/10}%\"></div></div>`;\n"
"                if (isFault) html += `<div class=\"hb-row\"><span class=\"hb-label\">Fault:</span><span class=\"hb-val\" style=\"color:#f55\">${getHBFaultString(ch.fault)}</span></div>`;\n"
"                html += `</div>`;\n"
"            }\n"
"            document.getElementById('hbridgeGrid').innerHTML = html;\n"
"            \n"
"            // Update analog inputs\n"
"            html = '';\n"
"            for (let i = 0; i < 20; i++) {\n"
"                const v = data.analogs?.[i] || 0;\n"
"                html += `<div class=\"analog-ch\" onclick=\"editAnalog(${i})\" style=\"cursor:pointer\">`;\n"
"                html += `<div class=\"ain-label\">AIN${i+1}</div>`;\n"
"                html += `<div class=\"ain-val\">${v.toFixed(2)}V</div>`;\n"
"                html += `</div>`;\n"
"            }\n"
"            document.getElementById('analogGrid').innerHTML = html;\n"
"            \n"
"            // System status\n"
"            document.getElementById('sysStatus').innerHTML = `\n"
"                <div class=\"sys-item\"><div class=\"si-label\">Voltage</div><div class=\"si-val\">${(data.voltage || 0).toFixed(1)}V</div></div>\n"
"                <div class=\"sys-item\"><div class=\"si-label\">Temp</div><div class=\"si-val\">${(data.temperature || 0).toFixed(0)}C</div></div>\n"
"                <div class=\"sys-item\"><div class=\"si-label\">Uptime</div><div class=\"si-val\">${data.uptime || 0}s</div></div>\n"
"                <div class=\"sys-item\"><div class=\"si-label\">Tick</div><div class=\"si-val\">${data.tick || 0}</div></div>\n"
"            `;\n"
"            \n"
"            // Update load grid\n"
"            updateLoadGrid();\n"
"            \n"
"            // Update active faults list\n"
"            updateFaultList(data);\n"
"        }\n"
"        \n"
"        function getFaultString(fault) {\n"
"            /* PMU_PROFET_Fault_t: 0x01=OC, 0x02=OT, 0x04=SC, 0x08=OL, 0x10=UV */\n"
"            let s = [];\n"
"            if (fault & 0x01) s.push('OC');\n"
"            if (fault & 0x02) s.push('OT');\n"
"            if (fault & 0x04) s.push('SC');\n"
"            if (fault & 0x08) s.push('OL');\n"
"            if (fault & 0x10) s.push('UV');\n"
"            return s.join(',');\n"
"        }\n"
"        \n"
"        function getHBFaultString(fault) {\n"
"            let s = [];\n"
"            if (fault & 1) s.push('OC_FWD');\n"
"            if (fault & 2) s.push('OC_REV');\n"
"            if (fault & 4) s.push('OVERTEMP');\n"
"            if (fault & 8) s.push('STALL');\n"
"            if (fault & 16) s.push('POS_LOST');\n"
"            return s.join(',') || 'None';\n"
"        }\n"
"        \n"
"        function toggleChannel(ch) {\n"
"            sendCommand({action: 'toggle', channel: ch});\n"
"        }\n"
"        \n"
"        function editAnalog(ch) {\n"
"            editingAnalog = ch;\n"
"            const v = telemetryData.analogs?.[ch] || 0;\n"
"            document.getElementById('analogModalTitle').textContent = 'AIN' + (ch + 1);\n"
"            document.getElementById('analogSlider').value = v;\n"
"            document.getElementById('analogValue').textContent = v.toFixed(2) + 'V';\n"
"            document.getElementById('analogModal').classList.add('show');\n"
"        }\n"
"        \n"
"        function closeAnalogModal() {\n"
"            document.getElementById('analogModal').classList.remove('show');\n"
"            editingAnalog = -1;\n"
"        }\n"
"        \n"
"        function updateAnalogValue() {\n"
"            const v = parseFloat(document.getElementById('analogSlider').value);\n"
"            document.getElementById('analogValue').textContent = v.toFixed(2) + 'V';\n"
"            // Live update - send immediately\n"
"            if (editingAnalog >= 0) {\n"
"                sendCommand({action: 'set_analog', channel: editingAnalog, voltage: v});\n"
"            }\n"
"        }\n"
"        \n"
"        function setAnalogPreset(v) {\n"
"            document.getElementById('analogSlider').value = v;\n"
"            document.getElementById('analogValue').textContent = v.toFixed(2) + 'V';\n"
"            if (editingAnalog >= 0) {\n"
"                sendCommand({action: 'set_analog', channel: editingAnalog, voltage: v});\n"
"            }\n"
"        }\n"
"        \n"
"        function applyAnalogValue() {\n"
"            const v = parseFloat(document.getElementById('analogSlider').value);\n"
"            if (editingAnalog >= 0) {\n"
"                sendCommand({action: 'set_analog', channel: editingAnalog, voltage: v});\n"
"            }\n"
"            closeAnalogModal();\n"
"        }\n"
"        \n"
"        // Battery voltage slider\n"
"        document.getElementById('battVoltage').addEventListener('input', function() {\n"
"            const v = parseFloat(this.value);\n"
"            document.getElementById('battVoltageVal').textContent = v.toFixed(1) + 'V';\n"
"        });\n"
"        document.getElementById('battVoltage').addEventListener('change', function() {\n"
"            const v = parseFloat(this.value);\n"
"            sendCommand({action: 'set_voltage', voltage: v * 1000});\n"
"        });\n"
"        \n"
"        // Board temperature slider\n"
"        document.getElementById('boardTemp').addEventListener('input', function() {\n"
"            const t = parseInt(this.value);\n"
"            document.getElementById('boardTempVal').textContent = t + 'C';\n"
"        });\n"
"        document.getElementById('boardTemp').addEventListener('change', function() {\n"
"            const t = parseInt(this.value);\n"
"            sendCommand({action: 'set_temperature', temperature: t});\n"
"        });\n"
"        \n"
"        // Load simulation\n"
"        function updateLoadGrid() {\n"
"            let html = '';\n"
"            for (let i = 0; i < 30; i++) {\n"
"                const r = loadValues[i];\n"
"                let cls = r < 0.1 ? 'short' : (r > 1000 ? 'open' : '');\n"
"                let rStr = r >= 1000 ? (r/1000).toFixed(1)+'k' : r.toFixed(1);\n"
"                html += `<div class=\"load-ch ${cls}\" onclick=\"openLoadModal(${i})\">`;\n"
"                html += `<div class=\"ld-num\">CH${i+1}</div>`;\n"
"                html += `<div class=\"ld-val\">${rStr}R</div></div>`;\n"
"            }\n"
"            document.getElementById('loadGrid').innerHTML = html;\n"
"        }\n"
"        \n"
"        function setAllLoads(r) {\n"
"            for (let i = 0; i < 30; i++) {\n"
"                loadValues[i] = r;\n"
"                sendCommand({action: 'set_load', channel: i, resistance: r});\n"
"            }\n"
"            updateLoadGrid();\n"
"        }\n"
"        \n"
"        function openLoadModal(ch) {\n"
"            selectedLoadCh = ch;\n"
"            document.getElementById('loadModalCh').textContent = ch + 1;\n"
"            document.getElementById('loadModalValue').value = loadValues[ch];\n"
"            document.getElementById('loadModal').classList.add('show');\n"
"        }\n"
"        \n"
"        function closeLoadModal() {\n"
"            document.getElementById('loadModal').classList.remove('show');\n"
"        }\n"
"        \n"
"        function setLoadValue(r) {\n"
"            document.getElementById('loadModalValue').value = r;\n"
"        }\n"
"        \n"
"        function applyLoadModal() {\n"
"            const r = parseFloat(document.getElementById('loadModalValue').value) || 10;\n"
"            loadValues[selectedLoadCh] = r;\n"
"            sendCommand({action: 'set_load', channel: selectedLoadCh, resistance: r});\n"
"            updateLoadGrid();\n"
"            closeLoadModal();\n"
"        }\n"
"        \n"
"        // CAN injection\n"
"        function sendCanMessage() {\n"
"            const bus = parseInt(document.getElementById('canBus').value);\n"
"            const id = parseInt(document.getElementById('canId').value, 16) || 0x100;\n"
"            let data = [];\n"
"            for (let i = 0; i < 8; i++) {\n"
"                data.push(parseInt(document.getElementById(`canD${i}`).value, 16) || 0);\n"
"            }\n"
"            sendCommand({action: 'inject_can', bus: bus, id: id, data: data});\n"
"            addCanHistory('tx', bus, id, data);\n"
"        }\n"
"        \n"
"        function addCanHistory(dir, bus, id, data) {\n"
"            const container = document.getElementById('canHistory');\n"
"            const entry = document.createElement('div');\n"
"            entry.className = `can-msg ${dir}`;\n"
"            const dataStr = data.map(b => b.toString(16).padStart(2,'0').toUpperCase()).join(' ');\n"
"            const time = new Date().toLocaleTimeString();\n"
"            entry.textContent = `[${time}] ${dir.toUpperCase()} CAN${bus} ID:${id.toString(16).toUpperCase()} [${dataStr}]`;\n"
"            container.appendChild(entry);\n"
"            container.scrollTop = container.scrollHeight;\n"
"            while (container.children.length > 50) container.removeChild(container.firstChild);\n"
"        }\n"
"        \n"
"        // Fault injection\n"
"        function initFaultChannelSelect() {\n"
"            const sel = document.getElementById('faultChannel');\n"
"            let html = '<optgroup label=\"PROFET\">';\n"
"            for (let i = 1; i <= 30; i++) html += `<option value=\"p${i}\">PROFET CH${i}</option>`;\n"
"            html += '</optgroup><optgroup label=\"H-Bridge\">';\n"
"            for (let i = 1; i <= 4; i++) html += `<option value=\"h${i}\">H-Bridge ${i}</option>`;\n"
"            html += '</optgroup>';\n"
"            sel.innerHTML = html;\n"
"        }\n"
"        \n"
"        function injectFault() {\n"
"            const ch = document.getElementById('faultChannel').value;\n"
"            const fault = parseInt(document.getElementById('faultType').value);\n"
"            if (ch.startsWith('p')) {\n"
"                const chNum = parseInt(ch.substring(1)) - 1;\n"
"                sendCommand({action: 'inject_fault', type: 'profet', channel: chNum, fault: fault});\n"
"            } else if (ch.startsWith('h')) {\n"
"                const chNum = parseInt(ch.substring(1)) - 1;\n"
"                sendCommand({action: 'inject_fault', type: 'hbridge', channel: chNum, fault: fault});\n"
"            }\n"
"        }\n"
"        \n"
"        function clearFault(type, ch) {\n"
"            sendCommand({action: 'clear_fault', type: type, channel: ch});\n"
"        }\n"
"        \n"
"        function updateFaultList(data) {\n"
"            let html = '';\n"
"            // PROFET faults\n"
"            for (let i = 0; i < 30; i++) {\n"
"                const f = data.profets?.[i]?.fault || 0;\n"
"                if (f > 0) {\n"
"                    html += `<div class=\"fault-tag\">CH${i+1}: ${getFaultString(f)} <button onclick=\"clearFault('profet',${i})\">&times;</button></div>`;\n"
"                }\n"
"            }\n"
"            // H-Bridge faults\n"
"            for (let i = 0; i < 4; i++) {\n"
"                const f = data.hbridges?.[i]?.fault || 0;\n"
"                if (f > 0) {\n"
"                    html += `<div class=\"fault-tag\">HB${i+1}: ${getHBFaultString(f)} <button onclick=\"clearFault('hbridge',${i})\">&times;</button></div>`;\n"
"                }\n"
"            }\n"
"            document.getElementById('faultList').innerHTML = html || '<span style=\"color:#888\">No active faults</span>';\n"
"        }\n"
"        \n"
"        // Logging\n"
"        function addLog(level, source, message) {\n"
"            const container = document.getElementById('logContainer');\n"
"            const entry = document.createElement('div');\n"
"            let cls = level;\n"
"            if (source === 'cmd' || source === 'protocol') cls = 'cmd';\n"
"            if (source === 'config' || source === 'json') cls = 'config';\n"
"            entry.className = `log-entry ${cls}`;\n"
"            entry.dataset.source = source;\n"
"            entry.dataset.level = level;\n"
"            const time = new Date().toLocaleTimeString();\n"
"            entry.textContent = `[${time}] [${source}] ${message}`;\n"
"            container.appendChild(entry);\n"
"            container.scrollTop = container.scrollHeight;\n"
"            while (container.children.length > 200) container.removeChild(container.firstChild);\n"
"            applyLogFilter();\n"
"        }\n"
"        \n"
"        function switchLogTab(filter) {\n"
"            currentLogFilter = filter;\n"
"            document.querySelectorAll('.log-tab').forEach(t => t.classList.remove('active'));\n"
"            document.querySelector(`.log-tab[data-log=\"${filter}\"]`).classList.add('active');\n"
"            applyLogFilter();\n"
"        }\n"
"        \n"
"        function applyLogFilter() {\n"
"            document.querySelectorAll('.log-entry').forEach(entry => {\n"
"                const src = entry.dataset.source;\n"
"                const lvl = entry.dataset.level;\n"
"                let show = currentLogFilter === 'all';\n"
"                if (currentLogFilter === 'cmd' && (src === 'cmd' || src === 'protocol')) show = true;\n"
"                if (currentLogFilter === 'config' && (src === 'config' || src === 'json')) show = true;\n"
"                if (currentLogFilter === 'error' && lvl === 'error') show = true;\n"
"                entry.style.display = show ? '' : 'none';\n"
"            });\n"
"        }\n"
"        \n"
"        function sendCommand(cmd) {\n"
"            if (ws && ws.readyState === WebSocket.OPEN) {\n"
"                ws.send(JSON.stringify(cmd));\n"
"            }\n"
"        }\n"
"        \n"
"        // Config Stats\n"
"        function refreshConfigStats() {\n"
"            fetch('/config-stats.json')\n"
"                .then(r => r.json())\n"
"                .then(data => {\n"
"                    const badge = document.getElementById('configStatusBadge');\n"
"                    const stats = document.getElementById('configStats');\n"
"                    const dl = document.getElementById('configDownloadLink');\n"
"                    if (data.loaded) {\n"
"                        badge.textContent = 'Loaded';\n"
"                        badge.className = 'badge on';\n"
"                        stats.innerHTML = `<div style=\"display:grid;grid-template-columns:repeat(2,1fr);gap:4px 12px\">`\n"
"                            + `<span>Total Channels:</span><strong>${data.channels}</strong>`\n"
"                            + `<span>Power Outputs:</span><strong>${data.powerOutputs}</strong>`\n"
"                            + `<span>Digital Inputs:</span><strong>${data.digitalInputs}</strong>`\n"
"                            + `<span>Analog Inputs:</span><strong>${data.analogInputs}</strong>`\n"
"                            + `<span>Logic Functions:</span><strong>${data.logic}</strong>`\n"
"                            + `<span>Switches:</span><strong>${data.switches}</strong>`\n"
"                            + `<span>Timers:</span><strong>${data.timers}</strong>`\n"
"                            + `<span>CAN Messages:</span><strong>${data.canMessages}</strong>`\n"
"                            + `<span>CAN RX:</span><strong>${data.canRx}</strong>`\n"
"                            + `<span>CAN TX:</span><strong>${data.canTx}</strong>`\n"
"                            + `<span>Tables 2D/3D:</span><strong>${data.tables2d}/${data.tables3d}</strong>`\n"
"                            + `<span>Lua Scripts:</span><strong>${data.luaScripts}</strong>`\n"
"                            + `</div>`;\n"
"                        dl.style.display = '';\n"
"                    } else {\n"
"                        badge.textContent = 'Not loaded';\n"
"                        badge.className = 'badge off';\n"
"                        stats.innerHTML = '<div style=\"color:#888\">No configuration loaded</div>';\n"
"                        dl.style.display = 'none';\n"
"                    }\n"
"                })\n"
"                .catch(e => console.error('Config stats error:', e));\n"
"        }\n"
"        \n"
"        function clearConfig() {\n"
"            if (confirm('Clear saved configuration? The emulator will reset to defaults.')) {\n"
"                sendCommand({action: 'clear_config'});\n"
"                setTimeout(refreshConfigStats, 500);\n"
"            }\n"
"        }\n"
"        \n"
"        // ==================== Link ECU CAN Stream ====================\n"
"        let linkStreamTimer = null;\n"
"        let linkFrameIdx = 0;\n"
"        \n"
"        function getLinkParams() {\n"
"            return {\n"
"                rpm: parseInt(document.getElementById('linkRpm').value) || 0,\n"
"                tps: parseFloat(document.getElementById('linkTps').value) || 0,\n"
"                map: parseInt(document.getElementById('linkMap').value) || 0,\n"
"                clt: parseInt(document.getElementById('linkClt').value) || 0,\n"
"                iat: parseInt(document.getElementById('linkIat').value) || 0,\n"
"                batt: parseFloat(document.getElementById('linkBatt').value) || 0,\n"
"                lambda1: parseFloat(document.getElementById('linkLambda1').value) || 1,\n"
"                lambda2: parseFloat(document.getElementById('linkLambda2').value) || 1,\n"
"                oilP: parseFloat(document.getElementById('linkOilP').value) || 0,\n"
"                oilT: parseInt(document.getElementById('linkOilT').value) || 0,\n"
"                fuelP: parseFloat(document.getElementById('linkFuelP').value) || 0,\n"
"                speed: parseInt(document.getElementById('linkSpeed').value) || 0,\n"
"                gear: parseInt(document.getElementById('linkGear').value) || 0,\n"
"                ign: parseFloat(document.getElementById('linkIgn').value) || 0,\n"
"                injDC: parseFloat(document.getElementById('linkInjDC').value) || 0,\n"
"                baro: parseInt(document.getElementById('linkBaro').value) || 101,\n"
"                bus: parseInt(document.getElementById('linkCanBus').value) || 1,\n"
"                baseId: parseInt(document.getElementById('linkBaseId').value, 16) || 0x3E8\n"
"            };\n"
"        }\n"
"        \n"
"        function buildLinkFrame(frameIdx, p) {\n"
"            let data = [frameIdx, 0, 0, 0, 0, 0, 0, 0];\n"
"            switch(frameIdx) {\n"
"                case 0: // RPM, MAP, MGP\n"
"                    data[2] = p.rpm & 0xFF; data[3] = (p.rpm >> 8) & 0xFF;\n"
"                    let mapVal = Math.round(p.map * 10);\n"
"                    data[4] = mapVal & 0xFF; data[5] = (mapVal >> 8) & 0xFF;\n"
"                    let mgpVal = Math.round((p.map - 100) * 10) + 1000;\n"
"                    data[6] = mgpVal & 0xFF; data[7] = (mgpVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 1: // Baro, TPS, InjDC\n"
"                    let baroVal = Math.round(p.baro * 10);\n"
"                    data[2] = baroVal & 0xFF; data[3] = (baroVal >> 8) & 0xFF;\n"
"                    let tpsVal = Math.round(p.tps * 10);\n"
"                    data[4] = tpsVal & 0xFF; data[5] = (tpsVal >> 8) & 0xFF;\n"
"                    let injDCVal = Math.round(p.injDC * 10);\n"
"                    data[6] = injDCVal & 0xFF; data[7] = (injDCVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 2: // InjPW, CLT\n"
"                    let injPW = Math.round(p.injDC * 0.2 * 10); // estimate\n"
"                    data[4] = injPW & 0xFF; data[5] = (injPW >> 8) & 0xFF;\n"
"                    let cltVal = Math.round((p.clt + 50) * 10);\n"
"                    data[6] = cltVal & 0xFF; data[7] = (cltVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 3: // IAT, Battery, MAF\n"
"                    let iatVal = Math.round((p.iat + 50) * 10);\n"
"                    data[2] = iatVal & 0xFF; data[3] = (iatVal >> 8) & 0xFF;\n"
"                    let battVal = Math.round(p.batt * 100);\n"
"                    data[4] = battVal & 0xFF; data[5] = (battVal >> 8) & 0xFF;\n"
"                    let mafVal = Math.round(p.rpm * 0.1); // estimate\n"
"                    data[6] = mafVal & 0xFF; data[7] = (mafVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 4: // Gear, IgnAngle\n"
"                    data[2] = p.gear & 0xFF; data[3] = 0;\n"
"                    let ignVal = Math.round((p.ign + 100) * 10);\n"
"                    data[6] = ignVal & 0xFF; data[7] = (ignVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 6: // Lambda1, Lambda2\n"
"                    let l1 = Math.round(p.lambda1 * 1000);\n"
"                    data[4] = l1 & 0xFF; data[5] = (l1 >> 8) & 0xFF;\n"
"                    let l2 = Math.round(p.lambda2 * 1000);\n"
"                    data[6] = l2 & 0xFF; data[7] = (l2 >> 8) & 0xFF;\n"
"                    break;\n"
"                case 7: // Trig errors, fault count, FuelP\n"
"                    data[2] = 0; data[3] = 0; // trig errors\n"
"                    data[4] = 0; data[5] = 0; // fault count\n"
"                    let fuelPVal = Math.round(p.fuelP * 10);\n"
"                    data[6] = fuelPVal & 0xFF; data[7] = (fuelPVal >> 8) & 0xFF;\n"
"                    break;\n"
"                case 8: // OilT, OilP, WheelSpeedLF\n"
"                    let oilTVal = Math.round((p.oilT + 50) * 10);\n"
"                    data[2] = oilTVal & 0xFF; data[3] = (oilTVal >> 8) & 0xFF;\n"
"                    let oilPVal = Math.round(p.oilP * 100);\n"
"                    data[4] = oilPVal & 0xFF; data[5] = (oilPVal >> 8) & 0xFF;\n"
"                    let wsLF = Math.round(p.speed * 10);\n"
"                    data[6] = wsLF & 0xFF; data[7] = (wsLF >> 8) & 0xFF;\n"
"                    break;\n"
"                case 9: // WheelSpeedLR, RF, RR\n"
"                    let ws = Math.round(p.speed * 10);\n"
"                    data[2] = ws & 0xFF; data[3] = (ws >> 8) & 0xFF;\n"
"                    data[4] = ws & 0xFF; data[5] = (ws >> 8) & 0xFF;\n"
"                    data[6] = ws & 0xFF; data[7] = (ws >> 8) & 0xFF;\n"
"                    break;\n"
"                default:\n"
"                    break;\n"
"            }\n"
"            return data;\n"
"        }\n"
"        \n"
"        function sendLinkFrame() {\n"
"            const p = getLinkParams();\n"
"            const frames = [0,1,2,3,4,6,7,8,9]; // Active frames\n"
"            const fIdx = frames[linkFrameIdx % frames.length];\n"
"            const data = buildLinkFrame(fIdx, p);\n"
"            sendCommand({action: 'inject_can', bus: p.bus, id: p.baseId, data: data});\n"
"            linkFrameIdx++;\n"
"        }\n"
"        \n"
"        function sendLinkFrameOnce() {\n"
"            const p = getLinkParams();\n"
"            const frames = [0,1,2,3,4,6,7,8,9];\n"
"            for (let fIdx of frames) {\n"
"                const data = buildLinkFrame(fIdx, p);\n"
"                sendCommand({action: 'inject_can', bus: p.bus, id: p.baseId, data: data});\n"
"                addCanHistory('tx', p.bus, p.baseId, data);\n"
"            }\n"
"            addLog('info', 'link', 'Sent all Link ECU frames once');\n"
"        }\n"
"        \n"
"        function toggleLinkStream() {\n"
"            if (linkStreamTimer) {\n"
"                clearInterval(linkStreamTimer);\n"
"                linkStreamTimer = null;\n"
"                document.getElementById('linkStartBtn').textContent = 'Start Stream';\n"
"                document.getElementById('linkStartBtn').classList.remove('danger');\n"
"                document.getElementById('linkStartBtn').classList.add('primary');\n"
"                document.getElementById('linkStreamStatus').textContent = 'Stopped';\n"
"                document.getElementById('linkStreamStatus').style.color = '#888';\n"
"                addLog('info', 'link', 'Link ECU stream stopped');\n"
"            } else {\n"
"                const interval = parseInt(document.getElementById('linkInterval').value) || 50;\n"
"                linkFrameIdx = 0;\n"
"                linkStreamTimer = setInterval(sendLinkFrame, interval);\n"
"                document.getElementById('linkStartBtn').textContent = 'Stop Stream';\n"
"                document.getElementById('linkStartBtn').classList.remove('primary');\n"
"                document.getElementById('linkStartBtn').classList.add('danger');\n"
"                document.getElementById('linkStreamStatus').textContent = 'Running @ ' + interval + 'ms';\n"
"                document.getElementById('linkStreamStatus').style.color = '#0f0';\n"
"                addLog('info', 'link', 'Link ECU stream started @ ' + interval + 'ms');\n"
"            }\n"
"        }\n"
"        \n"
"        // Initialize\n"
"        initFaultChannelSelect();\n"
"        updateLoadGrid();\n"
"        refreshConfigStats();\n"
"        connect();\n"
"    </script>\n"
"    \n"
"    <!-- Analog Input Dialog -->\n"
"    <div class=\"modal\" id=\"analogModal\">\n"
"        <div class=\"modal-content\" style=\"width: 350px;\">\n"
"            <div class=\"modal-header\">\n"
"                <h3 id=\"analogModalTitle\">AIN1</h3>\n"
"                <button class=\"modal-close\" onclick=\"closeAnalogModal()\">&times;</button>\n"
"            </div>\n"
"            <div style=\"padding: 15px 0;\">\n"
"                <div style=\"display: flex; align-items: center; gap: 15px; margin-bottom: 20px;\">\n"
"                    <input type=\"range\" id=\"analogSlider\" min=\"0\" max=\"3.3\" step=\"0.01\" value=\"0\" \n"
"                           style=\"flex: 1; height: 30px; cursor: pointer;\" \n"
"                           oninput=\"updateAnalogValue()\">\n"
"                    <span id=\"analogValue\" style=\"font-size: 1.5em; color: #0ff; min-width: 70px; text-align: right;\">0.00V</span>\n"
"                </div>\n"
"                <div style=\"display: flex; gap: 10px; justify-content: center;\">\n"
"                    <button class=\"btn small\" onclick=\"setAnalogPreset(0)\">0V</button>\n"
"                    <button class=\"btn small\" onclick=\"setAnalogPreset(1.65)\">1.65V</button>\n"
"                    <button class=\"btn small\" onclick=\"setAnalogPreset(2.5)\">2.5V</button>\n"
"                    <button class=\"btn small\" onclick=\"setAnalogPreset(3.3)\">3.3V</button>\n"
"                </div>\n"
"            </div>\n"
"            <div style=\"display: flex; justify-content: flex-end; gap: 10px; margin-top: 15px;\">\n"
"                <button class=\"btn\" onclick=\"closeAnalogModal()\">Close</button>\n"
"                <button class=\"btn primary\" onclick=\"applyAnalogValue()\">Apply</button>\n"
"            </div>\n"
"        </div>\n"
"    </div>\n"
"</body>\n"
"</html>\n";

/* Private function prototypes -----------------------------------------------*/

static void set_nonblocking(SOCKET sock);
static int find_free_client(void);
static void close_client(int idx);
static void handle_http_request(int client_idx);
static void handle_websocket_frame(int client_idx);
static void send_http_response(SOCKET sock, int status, const char* content_type, const char* body, size_t body_len);
static void send_websocket_frame(SOCKET sock, uint8_t opcode, const uint8_t* data, size_t len);
static int websocket_handshake(int client_idx, const char* key);
static void base64_encode(const uint8_t* input, size_t len, char* output);
static void sha1(const uint8_t* data, size_t len, uint8_t* hash);
static void handle_webui_command(const char* json);
static int parse_int_field(const char* json, const char* field);
static float parse_float_field(const char* json, const char* field);
static int parse_int_array(const char* json, const char* field, int* out, int max_count);

/* Public functions ----------------------------------------------------------*/

void EMU_WebUI_AddCmdLog(uint8_t level, const char* format, ...)
{
    if (!s_initialized) return;

    CmdLogEntry_t* entry = &s_cmd_log[s_cmd_log_head];

    va_list args;
    va_start(args, format);
    vsnprintf(entry->message, CMD_LOG_ENTRY_SIZE, format, args);
    va_end(args);

    entry->level = level;
    PMU_Emulator_t* state = PMU_Emu_GetState();
    entry->timestamp = state ? state->tick_ms : 0;

    s_cmd_log_head = (s_cmd_log_head + 1) % CMD_LOG_MAX_ENTRIES;
    if (s_cmd_log_count < CMD_LOG_MAX_ENTRIES) s_cmd_log_count++;

    /* Also send via WebSocket immediately */
    const char* level_str[] = {"debug", "info", "warning", "error"};
    if (level > 3) level = 3;

    EMU_WebUI_SendLog(level, "cmd", entry->message);
}

int EMU_WebUI_Init(const EMU_WebUI_Config_t* config)
{
    if (s_initialized) {
        return 0;
    }

#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("[WebUI] WSAStartup failed\n");
        return -1;
    }
#endif

    /* Apply configuration */
    if (config) {
        s_config = *config;
    } else {
        s_config.http_port = EMU_WEBUI_DEFAULT_PORT;
        s_config.auto_open_browser = true;
        s_config.verbose = false;
    }

    /* Clear state */
    memset(&s_stats, 0, sizeof(s_stats));
    memset(s_clients, 0, sizeof(s_clients));
    memset(s_cmd_log, 0, sizeof(s_cmd_log));
    s_cmd_log_head = 0;
    s_cmd_log_count = 0;

    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        s_clients[i].socket = INVALID_SOCKET;
    }

    s_initialized = true;
    printf("[WebUI] Initialized on port %d\n", s_config.http_port);
    return 0;
}

int EMU_WebUI_Start(void)
{
    if (!s_initialized) {
        if (EMU_WebUI_Init(NULL) != 0) {
            return -1;
        }
    }

    if (s_running) {
        return 0;
    }

    /* Create listen socket */
    s_listen_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s_listen_socket == INVALID_SOCKET) {
        printf("[WebUI] Failed to create socket\n");
        return -1;
    }

    /* Allow address reuse */
    int opt = 1;
    setsockopt(s_listen_socket, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    /* Bind */
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(s_config.http_port);

    if (bind(s_listen_socket, (struct sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        printf("[WebUI] Bind failed: %d\n", SOCKET_ERROR_CODE);
        close(s_listen_socket);
        s_listen_socket = INVALID_SOCKET;
        return -1;
    }

    /* Listen */
    if (listen(s_listen_socket, 5) == SOCKET_ERROR) {
        printf("[WebUI] Listen failed\n");
        close(s_listen_socket);
        s_listen_socket = INVALID_SOCKET;
        return -1;
    }

    set_nonblocking(s_listen_socket);
    s_running = true;

    printf("[WebUI] Server started at http://localhost:%d\n", s_config.http_port);

    if (s_config.auto_open_browser) {
        EMU_WebUI_OpenBrowser();
    }

    return 0;
}

void EMU_WebUI_Stop(void)
{
    if (!s_running) {
        return;
    }

    /* Close all clients */
    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET) {
            close_client(i);
        }
    }

    /* Close listen socket */
    if (s_listen_socket != INVALID_SOCKET) {
        close(s_listen_socket);
        s_listen_socket = INVALID_SOCKET;
    }

    s_running = false;
    printf("[WebUI] Server stopped\n");
}

void EMU_WebUI_Process(uint32_t timeout_ms)
{
    if (!s_running) {
        return;
    }

    fd_set read_fds;
    FD_ZERO(&read_fds);
    FD_SET(s_listen_socket, &read_fds);

    SOCKET max_fd = s_listen_socket;

    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET) {
            FD_SET(s_clients[i].socket, &read_fds);
            if (s_clients[i].socket > max_fd) {
                max_fd = s_clients[i].socket;
            }
        }
    }

    struct timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;

    int result = select((int)(max_fd + 1), &read_fds, NULL, NULL, &tv);
    if (result <= 0) {
        return;
    }

    /* Check for new connections */
    if (FD_ISSET(s_listen_socket, &read_fds)) {
        struct sockaddr_in client_addr;
        int addr_len = sizeof(client_addr);
        SOCKET client_socket = accept(s_listen_socket, (struct sockaddr*)&client_addr, &addr_len);

        if (client_socket != INVALID_SOCKET) {
            int idx = find_free_client();
            if (idx >= 0) {
                set_nonblocking(client_socket);
                s_clients[idx].socket = client_socket;
                s_clients[idx].is_websocket = false;
                s_clients[idx].active = true;
                s_clients[idx].recv_len = 0;

                if (s_config.verbose) {
                    printf("[WebUI] New connection from %s\n", inet_ntoa(client_addr.sin_addr));
                }
            } else {
                close(client_socket);
            }
        }
    }

    /* Process client data */
    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket == INVALID_SOCKET) {
            continue;
        }

        if (FD_ISSET(s_clients[i].socket, &read_fds)) {
            /* Receive data */
            int space = EMU_WEBUI_BUFFER_SIZE - s_clients[i].recv_len - 1;
            if (space > 0) {
                int n = recv(s_clients[i].socket,
                           (char*)(s_clients[i].recv_buffer + s_clients[i].recv_len),
                           space, 0);

                if (n <= 0) {
                    close_client(i);
                    continue;
                }

                s_clients[i].recv_len += n;
                s_clients[i].recv_buffer[s_clients[i].recv_len] = '\0';
            }

            /* Process data */
            if (s_clients[i].is_websocket) {
                handle_websocket_frame(i);
            } else {
                handle_http_request(i);
            }
        }
    }
}

bool EMU_WebUI_IsRunning(void)
{
    return s_running;
}

void EMU_WebUI_SendTelemetry(void)
{
    if (!s_running) {
        return;
    }

    /* Build telemetry JSON */
    PMU_Emulator_t* state = PMU_Emu_GetState();
    if (!state) {
        return;
    }

    char json[8192];
    int pos = 0;

    pos += snprintf(json + pos, sizeof(json) - pos, "{\"type\":\"telemetry\",\"data\":{");

    /* PROFET channels (30 total) - extended info */
    pos += snprintf(json + pos, sizeof(json) - pos, "\"profets\":[");
    for (int i = 0; i < 30; i++) {
        /* Get channel state from firmware PROFET module */
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        uint8_t ch_state = profet ? profet->state : state->profet[i].state;
        uint16_t current_mA = profet ? profet->current_mA : state->profet[i].current_mA;
        uint8_t fault = profet ? profet->fault_flags : state->profet[i].fault_flags;
        uint16_t pwm_duty = profet ? profet->pwm_duty : state->profet[i].pwm_duty;
        int16_t temp = profet ? profet->temperature_C : state->profet[i].temperature_C;

        pos += snprintf(json + pos, sizeof(json) - pos,
            "%s{\"state\":%d,\"current\":%.2f,\"fault\":%d,\"pwm_duty\":%d,\"temp\":%d}",
            i > 0 ? "," : "",
            ch_state,
            (float)current_mA / 1000.0f,
            fault,
            pwm_duty,
            temp);
    }
    pos += snprintf(json + pos, sizeof(json) - pos, "],");

    /* H-Bridge channels - extended info */
    pos += snprintf(json + pos, sizeof(json) - pos, "\"hbridges\":[");
    for (int i = 0; i < 4; i++) {
        pos += snprintf(json + pos, sizeof(json) - pos,
            "%s{\"mode\":%d,\"state\":%d,\"pwm\":%d,\"direction\":%d,\"current\":%d,\"position\":%d,\"target\":%d,\"fault\":%d}",
            i > 0 ? "," : "",
            state->hbridge[i].mode,
            state->hbridge[i].state,
            state->hbridge[i].duty_cycle / 10,  /* Convert 0-1000 to 0-100% */
            state->hbridge[i].mode,  /* Use mode for direction */
            state->hbridge[i].current_mA,
            state->hbridge[i].position,
            state->hbridge[i].target_position,
            state->hbridge[i].fault_flags);
    }
    pos += snprintf(json + pos, sizeof(json) - pos, "],");

    /* Analog inputs (20 total) */
    pos += snprintf(json + pos, sizeof(json) - pos, "\"analogs\":[");
    for (int i = 0; i < 20; i++) {
        pos += snprintf(json + pos, sizeof(json) - pos,
            "%s%.3f",
            i > 0 ? "," : "",
            state->adc[i].voltage_v);
    }
    pos += snprintf(json + pos, sizeof(json) - pos, "],");

    /* System status - use max board temp for display */
    int16_t max_temp = state->protection.board_temp_L_C;
    if (state->protection.board_temp_R_C > max_temp) {
        max_temp = state->protection.board_temp_R_C;
    }
    pos += snprintf(json + pos, sizeof(json) - pos,
        "\"voltage\":%.1f,\"temperature\":%.1f,\"uptime\":%u,\"tick\":%u",
        (float)state->protection.battery_voltage_mV / 1000.0f,
        (float)max_temp,
        state->uptime_seconds,
        state->tick_ms);

    pos += snprintf(json + pos, sizeof(json) - pos, "}}");

    /* Send to all WebSocket clients */
    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET && s_clients[i].is_websocket) {
            send_websocket_frame(s_clients[i].socket, WS_OPCODE_TEXT,
                               (uint8_t*)json, strlen(json));
            s_stats.ws_messages_sent++;
        }
    }
}

void EMU_WebUI_SendLog(uint8_t level, const char* source, const char* message)
{
    if (!s_running) {
        return;
    }

    const char* level_str[] = {"debug", "info", "warning", "error"};
    if (level > 3) level = 3;

    char json[1024];
    snprintf(json, sizeof(json),
        "{\"type\":\"log\",\"level\":\"%s\",\"source\":\"%s\",\"message\":\"%s\"}",
        level_str[level], source ? source : "system", message);

    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET && s_clients[i].is_websocket) {
            send_websocket_frame(s_clients[i].socket, WS_OPCODE_TEXT,
                               (uint8_t*)json, strlen(json));
            s_stats.ws_messages_sent++;
        }
    }
}

void EMU_WebUI_SendCanTx(uint8_t bus, uint32_t id, const uint8_t* data, uint8_t len)
{
    if (!s_running) {
        return;
    }

    char json[256];
    int pos = snprintf(json, sizeof(json),
        "{\"type\":\"can_tx\",\"bus\":%d,\"id\":%u,\"data\":[", bus, id);

    for (int i = 0; i < len && i < 8; i++) {
        pos += snprintf(json + pos, sizeof(json) - pos, "%s%d", i > 0 ? "," : "", data[i]);
    }
    pos += snprintf(json + pos, sizeof(json) - pos, "]}");

    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET && s_clients[i].is_websocket) {
            send_websocket_frame(s_clients[i].socket, WS_OPCODE_TEXT,
                               (uint8_t*)json, strlen(json));
        }
    }
}

const EMU_WebUI_Stats_t* EMU_WebUI_GetStats(void)
{
    return &s_stats;
}

void EMU_WebUI_OpenBrowser(void)
{
    char url[128];
    snprintf(url, sizeof(url), "http://localhost:%d", s_config.http_port);

#ifdef _WIN32
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "start %s", url);
    system(cmd);
#elif defined(__APPLE__)
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "open %s", url);
    system(cmd);
#else
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "xdg-open %s", url);
    system(cmd);
#endif

    printf("[WebUI] Opening browser: %s\n", url);
}

/* Private functions ---------------------------------------------------------*/

static void set_nonblocking(SOCKET sock)
{
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(sock, FIONBIO, &mode);
#else
    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);
#endif
}

static int find_free_client(void)
{
    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket == INVALID_SOCKET) {
            return i;
        }
    }
    return -1;
}

static void close_client(int idx)
{
    if (idx < 0 || idx >= EMU_WEBUI_MAX_WS_CLIENTS) {
        return;
    }

    if (s_clients[idx].socket != INVALID_SOCKET) {
        if (s_clients[idx].is_websocket) {
            s_stats.active_ws_clients--;
        }
        close(s_clients[idx].socket);
        s_clients[idx].socket = INVALID_SOCKET;
        s_clients[idx].active = false;
        s_clients[idx].is_websocket = false;
        s_clients[idx].recv_len = 0;
    }
}

static void handle_http_request(int client_idx)
{
    WebClient_t* client = &s_clients[client_idx];

    /* Wait for complete request (double CRLF) */
    if (strstr((char*)client->recv_buffer, "\r\n\r\n") == NULL) {
        return;
    }

    s_stats.http_requests++;

    /* Parse request line */
    char method[16], path[256], version[16];
    if (sscanf((char*)client->recv_buffer, "%15s %255s %15s", method, path, version) != 3) {
        send_http_response(client->socket, 400, "text/plain", "Bad Request", 11);
        close_client(client_idx);
        return;
    }

    /* Check for WebSocket upgrade */
    char* ws_key = strstr((char*)client->recv_buffer, "Sec-WebSocket-Key:");
    if (ws_key && strcmp(path, "/ws") == 0) {
        ws_key += 18;
        while (*ws_key == ' ') ws_key++;

        char key[64];
        int i = 0;
        while (ws_key[i] && ws_key[i] != '\r' && ws_key[i] != '\n' && i < 63) {
            key[i] = ws_key[i];
            i++;
        }
        key[i] = '\0';

        if (websocket_handshake(client_idx, key) == 0) {
            client->is_websocket = true;
            client->recv_len = 0;
            s_stats.ws_connections++;
            s_stats.active_ws_clients++;

            if (s_config.verbose) {
                printf("[WebUI] WebSocket connection established\n");
            }
        }
        return;
    }

    /* Serve dashboard */
    if (strcmp(path, "/") == 0 || strcmp(path, "/index.html") == 0) {
        send_http_response(client->socket, 200, "text/html", DASHBOARD_HTML, strlen(DASHBOARD_HTML));
    } else if (strcmp(path, "/config.json") == 0) {
        /* Serve current configuration JSON */
        size_t json_size = 0;
        const char* json = EMU_Server_GetConfigJSON(&json_size);
        if (json && json_size > 0) {
            send_http_response(client->socket, 200, "application/json", json, json_size);
        } else {
            send_http_response(client->socket, 404, "application/json", "{\"error\":\"No config loaded\"}", 28);
        }
    } else if (strcmp(path, "/config-stats.json") == 0) {
        /* Serve configuration statistics */
        char stats_json[512];
        const PMU_JSON_LoadStats_t* stats = EMU_Server_GetConfigStats();
        if (stats) {
            int len = snprintf(stats_json, sizeof(stats_json),
                "{\"loaded\":true,\"channels\":%lu,\"powerOutputs\":%lu,\"logic\":%lu,"
                "\"switches\":%lu,\"canRx\":%lu,\"canTx\":%lu,\"analogInputs\":%lu,"
                "\"digitalInputs\":%lu,\"timers\":%lu,\"tables2d\":%lu,\"tables3d\":%lu,"
                "\"canMessages\":%lu,\"luaScripts\":%lu}",
                (unsigned long)stats->total_channels, (unsigned long)stats->power_outputs,
                (unsigned long)stats->logic_functions, (unsigned long)stats->switches,
                (unsigned long)stats->can_rx, (unsigned long)stats->can_tx,
                (unsigned long)stats->analog_inputs, (unsigned long)stats->digital_inputs,
                (unsigned long)stats->timers, (unsigned long)stats->tables_2d,
                (unsigned long)stats->tables_3d, (unsigned long)stats->can_messages,
                (unsigned long)stats->lua_scripts);
            send_http_response(client->socket, 200, "application/json", stats_json, len);
        } else {
            send_http_response(client->socket, 200, "application/json", "{\"loaded\":false}", 16);
        }
    } else {
        send_http_response(client->socket, 404, "text/plain", "Not Found", 9);
    }

    close_client(client_idx);
}

static void handle_websocket_frame(int client_idx)
{
    WebClient_t* client = &s_clients[client_idx];

    if (client->recv_len < 2) {
        return;
    }

    uint8_t* data = client->recv_buffer;
    uint8_t opcode = data[0] & 0x0F;
    bool masked = (data[1] & WS_MASK_BIT) != 0;
    size_t payload_len = data[1] & 0x7F;
    size_t header_len = 2;

    if (payload_len == 126) {
        if (client->recv_len < 4) return;
        payload_len = (data[2] << 8) | data[3];
        header_len = 4;
    } else if (payload_len == 127) {
        /* Large frames not supported */
        close_client(client_idx);
        return;
    }

    if (masked) {
        header_len += 4;
    }

    size_t total_len = header_len + payload_len;
    if (client->recv_len < total_len) {
        return;
    }

    /* Unmask payload */
    uint8_t* payload = data + header_len;
    if (masked) {
        uint8_t* mask = data + header_len - 4;
        for (size_t i = 0; i < payload_len; i++) {
            payload[i] ^= mask[i % 4];
        }
    }

    s_stats.ws_messages_recv++;

    switch (opcode) {
        case WS_OPCODE_TEXT:
            /* Handle JSON command */
            if (payload_len > 0) {
                payload[payload_len] = '\0';
                handle_webui_command((char*)payload);
            }
            break;

        case WS_OPCODE_PING:
            send_websocket_frame(client->socket, WS_OPCODE_PONG, payload, payload_len);
            break;

        case WS_OPCODE_CLOSE:
            close_client(client_idx);
            return;
    }

    /* Remove processed frame from buffer */
    if (total_len < client->recv_len) {
        memmove(client->recv_buffer, client->recv_buffer + total_len,
                client->recv_len - total_len);
    }
    client->recv_len -= total_len;
}

/* Parse integer field from JSON */
static int parse_int_field(const char* json, const char* field)
{
    char search[64];
    snprintf(search, sizeof(search), "\"%s\":", field);

    char* pos = strstr(json, search);
    if (!pos) return 0;

    pos += strlen(search);
    while (*pos == ' ') pos++;

    return atoi(pos);
}

/* Parse float field from JSON */
static float parse_float_field(const char* json, const char* field)
{
    char search[64];
    snprintf(search, sizeof(search), "\"%s\":", field);

    char* pos = strstr(json, search);
    if (!pos) return 0.0f;

    pos += strlen(search);
    while (*pos == ' ') pos++;

    return (float)atof(pos);
}

/* Parse integer array from JSON */
static int parse_int_array(const char* json, const char* field, int* out, int max_count)
{
    char search[64];
    snprintf(search, sizeof(search), "\"%s\":[", field);

    char* pos = strstr(json, search);
    if (!pos) return 0;

    pos += strlen(search);
    int count = 0;

    while (*pos && *pos != ']' && count < max_count) {
        while (*pos == ' ' || *pos == ',') pos++;
        if (*pos == ']') break;
        out[count++] = atoi(pos);
        while (*pos && *pos != ',' && *pos != ']') pos++;
    }

    return count;
}

/* Handle WebUI commands */
static void handle_webui_command(const char* json)
{
    if (s_config.verbose) {
        printf("[WebUI] Command: %s\n", json);
    }

    /* Toggle channel */
    if (strstr(json, "\"action\":\"toggle\"")) {
        int channel = parse_int_field(json, "channel");
        if (channel >= 1 && channel <= 30) {
            PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(channel - 1);
            if (profet) {
                uint8_t new_state = (profet->state == PMU_PROFET_STATE_ON) ?
                                    PMU_PROFET_STATE_OFF : PMU_PROFET_STATE_ON;
                PMU_PROFET_SetState(channel - 1, new_state);
                EMU_WebUI_SendLog(1, "cmd", new_state ? "Channel ON" : "Channel OFF");
            }
        }
    }

    /* Set analog voltage */
    else if (strstr(json, "\"action\":\"set_analog\"")) {
        int channel = parse_int_field(json, "channel");
        float voltage = parse_float_field(json, "voltage");
        if (channel >= 0 && channel < 20) {
            PMU_Emu_ADC_SetVoltage(channel, voltage);
            char msg[64];
            snprintf(msg, sizeof(msg), "AIN%d = %.2fV", channel + 1, voltage);
            EMU_WebUI_SendLog(1, "cmd", msg);
        }
    }

    /* Set battery voltage */
    else if (strstr(json, "\"action\":\"set_voltage\"")) {
        float voltage = parse_float_field(json, "voltage");
        PMU_Emu_Protection_SetVoltage((uint16_t)voltage);
        char msg[64];
        snprintf(msg, sizeof(msg), "Battery voltage = %.1fV", voltage / 1000.0f);
        EMU_WebUI_SendLog(1, "cmd", msg);
    }

    /* Set temperature */
    else if (strstr(json, "\"action\":\"set_temperature\"")) {
        int temp = parse_int_field(json, "temperature");
        PMU_Emu_Protection_SetTemperature((int16_t)temp);
        char msg[64];
        snprintf(msg, sizeof(msg), "Board temperature = %dC", temp);
        EMU_WebUI_SendLog(1, "cmd", msg);
    }

    /* Set load resistance */
    else if (strstr(json, "\"action\":\"set_load\"")) {
        int channel = parse_int_field(json, "channel");
        float resistance = parse_float_field(json, "resistance");
        if (channel >= 0 && channel < 30) {
            PMU_Emu_PROFET_SetLoad(channel, resistance);
            char msg[64];
            snprintf(msg, sizeof(msg), "CH%d load = %.2f Ohm", channel + 1, resistance);
            EMU_WebUI_SendLog(1, "cmd", msg);
        }
    }

    /* Inject CAN message */
    else if (strstr(json, "\"action\":\"inject_can\"")) {
        int bus = parse_int_field(json, "bus");
        int id = parse_int_field(json, "id");
        int data[8] = {0};
        int len = parse_int_array(json, "data", data, 8);

        uint8_t can_data[8];
        for (int i = 0; i < 8; i++) {
            can_data[i] = (uint8_t)data[i];
        }

        PMU_Emu_CAN_InjectMessage(bus, id, can_data, len > 0 ? len : 8);

        char msg[128];
        snprintf(msg, sizeof(msg), "CAN%d inject ID=0x%X len=%d", bus, id, len);
        EMU_WebUI_SendLog(1, "cmd", msg);
    }

    /* Inject fault */
    else if (strstr(json, "\"action\":\"inject_fault\"")) {
        int channel = parse_int_field(json, "channel");
        int fault = parse_int_field(json, "fault");

        if (strstr(json, "\"type\":\"profet\"")) {
            if (channel >= 0 && channel < 30) {
                PMU_Emu_PROFET_InjectFault(channel, fault);
                char msg[64];
                snprintf(msg, sizeof(msg), "PROFET CH%d fault injected: 0x%02X", channel + 1, fault);
                EMU_WebUI_SendLog(2, "cmd", msg);
            }
        } else if (strstr(json, "\"type\":\"hbridge\"")) {
            if (channel >= 0 && channel < 4) {
                PMU_Emu_HBridge_InjectFault(channel, fault);
                char msg[64];
                snprintf(msg, sizeof(msg), "H-Bridge %d fault injected: 0x%02X", channel + 1, fault);
                EMU_WebUI_SendLog(2, "cmd", msg);
            }
        }
    }

    /* Clear fault */
    else if (strstr(json, "\"action\":\"clear_fault\"")) {
        int channel = parse_int_field(json, "channel");

        if (strstr(json, "\"type\":\"profet\"")) {
            if (channel >= 0 && channel < 30) {
                PMU_Emu_PROFET_ClearFault(channel);
                char msg[64];
                snprintf(msg, sizeof(msg), "PROFET CH%d fault cleared", channel + 1);
                EMU_WebUI_SendLog(1, "cmd", msg);
            }
        } else if (strstr(json, "\"type\":\"hbridge\"")) {
            if (channel >= 0 && channel < 4) {
                /* Clear H-Bridge fault directly in emulator state */
                PMU_Emulator_t* state = PMU_Emu_GetState();
                if (state) {
                    state->hbridge[channel].fault_flags = 0;
                }
                char msg[64];
                snprintf(msg, sizeof(msg), "H-Bridge %d fault cleared", channel + 1);
                EMU_WebUI_SendLog(1, "cmd", msg);
            }
        }
    }

    /* Clear saved configuration */
    else if (strstr(json, "\"action\":\"clear_config\"")) {
        if (remove("last_config.json") == 0) {
            EMU_WebUI_SendLog(1, "config", "Saved configuration cleared (last_config.json deleted)");
            PMU_Emu_Reset();
            EMU_WebUI_SendLog(1, "config", "Emulator reset to defaults");
        } else {
            EMU_WebUI_SendLog(2, "config", "No saved configuration to clear");
        }
    }
}

static void send_http_response(SOCKET sock, int status, const char* content_type, const char* body, size_t body_len)
{
    const char* status_text = "OK";
    if (status == 400) status_text = "Bad Request";
    else if (status == 404) status_text = "Not Found";
    else if (status == 500) status_text = "Internal Server Error";

    char header[512];
    int header_len = snprintf(header, sizeof(header),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n",
        status, status_text, content_type, body_len);

    send(sock, header, header_len, 0);
    if (body && body_len > 0) {
        send(sock, body, (int)body_len, 0);
    }
}

static void send_websocket_frame(SOCKET sock, uint8_t opcode, const uint8_t* data, size_t len)
{
    uint8_t header[10];
    size_t header_len = 2;

    header[0] = WS_FIN_BIT | opcode;

    if (len < 126) {
        header[1] = (uint8_t)len;
    } else if (len < 65536) {
        header[1] = 126;
        header[2] = (len >> 8) & 0xFF;
        header[3] = len & 0xFF;
        header_len = 4;
    } else {
        /* Large frames not supported */
        return;
    }

    send(sock, (char*)header, (int)header_len, 0);
    if (data && len > 0) {
        send(sock, (char*)data, (int)len, 0);
    }
}

static int websocket_handshake(int client_idx, const char* key)
{
    /* Compute accept key: base64(SHA1(key + GUID)) */
    char concat[128];
    snprintf(concat, sizeof(concat), "%s%s", key, WS_GUID);

    uint8_t hash[20];
    sha1((uint8_t*)concat, strlen(concat), hash);

    char accept_key[32];
    base64_encode(hash, 20, accept_key);

    char response[512];
    int len = snprintf(response, sizeof(response),
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: %s\r\n"
        "\r\n",
        accept_key);

    send(s_clients[client_idx].socket, response, len, 0);
    return 0;
}

/* Simple Base64 encoder */
static const char base64_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static void base64_encode(const uint8_t* input, size_t len, char* output)
{
    size_t i, j;
    for (i = 0, j = 0; i < len;) {
        size_t start = i;
        uint32_t a = i < len ? input[i++] : 0;
        uint32_t b = i < len ? input[i++] : 0;
        uint32_t c = i < len ? input[i++] : 0;
        uint32_t triple = (a << 16) | (b << 8) | c;

        size_t remaining = len - start;

        output[j++] = base64_table[(triple >> 18) & 0x3F];
        output[j++] = base64_table[(triple >> 12) & 0x3F];
        output[j++] = remaining > 1 ? base64_table[(triple >> 6) & 0x3F] : '=';
        output[j++] = remaining > 2 ? base64_table[triple & 0x3F] : '=';
    }
    output[j] = '\0';
}

/* Simple SHA1 implementation */
static void sha1(const uint8_t* data, size_t len, uint8_t* hash)
{
    uint32_t h0 = 0x67452301;
    uint32_t h1 = 0xEFCDAB89;
    uint32_t h2 = 0x98BADCFE;
    uint32_t h3 = 0x10325476;
    uint32_t h4 = 0xC3D2E1F0;

    /* Pre-processing */
    size_t new_len = len + 1;
    while (new_len % 64 != 56) new_len++;
    new_len += 8;

    uint8_t* msg = (uint8_t*)calloc(new_len, 1);
    memcpy(msg, data, len);
    msg[len] = 0x80;

    /* Length in bits (big endian) */
    uint64_t bit_len = len * 8;
    for (int i = 0; i < 8; i++) {
        msg[new_len - 1 - i] = (bit_len >> (i * 8)) & 0xFF;
    }

    /* Process each 512-bit chunk */
    for (size_t chunk = 0; chunk < new_len; chunk += 64) {
        uint32_t w[80];

        for (int i = 0; i < 16; i++) {
            w[i] = (msg[chunk + i*4] << 24) | (msg[chunk + i*4 + 1] << 16) |
                   (msg[chunk + i*4 + 2] << 8) | msg[chunk + i*4 + 3];
        }

        for (int i = 16; i < 80; i++) {
            uint32_t tmp = w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16];
            w[i] = (tmp << 1) | (tmp >> 31);
        }

        uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;

        for (int i = 0; i < 80; i++) {
            uint32_t f, k;
            if (i < 20) {
                f = (b & c) | ((~b) & d);
                k = 0x5A827999;
            } else if (i < 40) {
                f = b ^ c ^ d;
                k = 0x6ED9EBA1;
            } else if (i < 60) {
                f = (b & c) | (b & d) | (c & d);
                k = 0x8F1BBCDC;
            } else {
                f = b ^ c ^ d;
                k = 0xCA62C1D6;
            }

            uint32_t temp = ((a << 5) | (a >> 27)) + f + e + k + w[i];
            e = d;
            d = c;
            c = (b << 30) | (b >> 2);
            b = a;
            a = temp;
        }

        h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
    }

    free(msg);

    /* Output hash (big endian) */
    hash[0] = (h0 >> 24) & 0xFF; hash[1] = (h0 >> 16) & 0xFF;
    hash[2] = (h0 >> 8) & 0xFF; hash[3] = h0 & 0xFF;
    hash[4] = (h1 >> 24) & 0xFF; hash[5] = (h1 >> 16) & 0xFF;
    hash[6] = (h1 >> 8) & 0xFF; hash[7] = h1 & 0xFF;
    hash[8] = (h2 >> 24) & 0xFF; hash[9] = (h2 >> 16) & 0xFF;
    hash[10] = (h2 >> 8) & 0xFF; hash[11] = h2 & 0xFF;
    hash[12] = (h3 >> 24) & 0xFF; hash[13] = (h3 >> 16) & 0xFF;
    hash[14] = (h3 >> 8) & 0xFF; hash[15] = h3 & 0xFF;
    hash[16] = (h4 >> 24) & 0xFF; hash[17] = (h4 >> 16) & 0xFF;
    hash[18] = (h4 >> 8) & 0xFF; hash[19] = h4 & 0xFF;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
