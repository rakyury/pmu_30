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
#include "pmu_blinkmarine.h"
#include "pmu_wifi.h"
#include "pmu_bluetooth.h"
#include "pmu_log.h"
#include "pmu_datalog.h"
#include "emu_protocol_server.h"
#include "emu_webui_html.h"  /* Embedded HTML Dashboard */
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


/* HTML Dashboard is in emu_webui_html.h */


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

    /* Build telemetry JSON - optimized with static buffer */
    PMU_Emulator_t* state = PMU_Emu_GetState();
    if (!state) {
        return;
    }

    static char json[8192];  /* Static to avoid stack allocation each tick */
    char* p = json;
    char* end = json + sizeof(json) - 1;

    /* Fixed header - use memcpy for speed */
    static const char header[] = "{\"type\":\"telemetry\",\"data\":{\"profets\":[";
    memcpy(p, header, sizeof(header) - 1);
    p += sizeof(header) - 1;

    /* PROFET channels (30 total) - optimized with direct formatting */
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        uint8_t ch_state = profet ? profet->state : state->profet[i].state;
        uint16_t current_mA = profet ? profet->current_mA : state->profet[i].current_mA;
        uint8_t fault = profet ? profet->fault_flags : state->profet[i].fault_flags;
        uint16_t pwm_duty = profet ? profet->pwm_duty : state->profet[i].pwm_duty;
        int16_t temp = profet ? profet->temperature_C : state->profet[i].temperature_C;

        if (i > 0) *p++ = ',';
        p += snprintf(p, end - p,
            "{\"state\":%d,\"current\":%.2f,\"fault\":%d,\"pwm_duty\":%d,\"temp\":%d}",
            ch_state, (float)current_mA / 1000.0f, fault, pwm_duty, temp);
    }

    /* H-Bridge section with motor physics state */
    memcpy(p, "],\"hbridges\":[", 14);
    p += 14;

    for (int i = 0; i < 4; i++) {
        if (i > 0) *p++ = ',';
        const PMU_Emu_MotorState_t* ms = &state->hbridge[i].motor_state;
        p += snprintf(p, end - p,
            "{\"mode\":%d,\"state\":%d,\"pwm\":%d,\"direction\":%d,"
            "\"current\":%.2f,\"position\":%d,\"target\":%d,\"fault\":%d,"
            "\"omega\":%.2f,\"theta\":%.3f,\"backEmf\":%.2f,"
            "\"torque\":%.3f,\"temp\":%.1f,\"stalled\":%d,\"endstop\":%d}",
            state->hbridge[i].mode, state->hbridge[i].state,
            state->hbridge[i].duty_cycle / 10, state->hbridge[i].mode,
            ms->current_A, state->hbridge[i].position,
            state->hbridge[i].target_position, state->hbridge[i].fault_flags,
            ms->omega, ms->theta, ms->back_emf_V,
            ms->torque_motor, ms->temperature_C, ms->stalled, ms->at_end_stop);
    }

    /* Analog inputs section */
    memcpy(p, "],\"analogs\":[", 13);
    p += 13;

    for (int i = 0; i < 20; i++) {
        if (i > 0) *p++ = ',';
        p += snprintf(p, end - p, "%.3f", state->adc[i].voltage_v);
    }

    /* Digital inputs section */
    memcpy(p, "],\"digitalInputs\":[", 19);
    p += 19;

    for (int i = 0; i < PMU_EMU_DIGITAL_INPUTS; i++) {
        if (i > 0) *p++ = ',';
        p += snprintf(p, end - p, "%d", state->digital_inputs[i].debounced_state ? 1 : 0);
    }

    /* BlinkMarine keypads section */
    memcpy(p, "],\"keypads\":[", 13);
    p += 13;

    uint8_t keypad_count = PMU_BlinkMarine_GetKeypadCount();
    for (int i = 0; i < keypad_count; i++) {
        if (i > 0) *p++ = ',';
        PMU_BlinkMarine_Keypad_t* kp = PMU_BlinkMarine_GetKeypadByIndex(i);
        if (!kp) continue;

        uint8_t btn_count = PMU_BlinkMarine_GetButtonCount(kp->type);
        uint16_t button_states = 0;
        uint32_t led_states_low = 0;
        (void)led_states_low;  /* Will be used for extended LED status in future */

        for (uint8_t b = 0; b < btn_count; b++) {
            if (kp->buttons[b].state) button_states |= (1 << b);
            if (b < 16) {
                led_states_low |= ((uint32_t)kp->buttons[b].current_led_state << (b * 2));
            }
        }

        p += snprintf(p, end - p,
            "{\"id\":\"%s\",\"type\":\"%s\",\"online\":%d,\"buttons\":%d,\"leds\":%u}",
            kp->name,
            kp->type == PMU_BLINKMARINE_PKP2600SI ? "2x6" : "2x8",
            kp->online,
            button_states,
            (unsigned int)led_states_low);
    }

    /* System status - calculate max temp inline */
    int16_t max_temp = state->protection.board_temp_L_C > state->protection.board_temp_R_C
                     ? state->protection.board_temp_L_C : state->protection.board_temp_R_C;

    /* WiFi status */
    PMU_WiFi_Status_t wifi_status;
    PMU_WiFi_GetStatus(&wifi_status);
    char wifi_ip[16] = "0.0.0.0";
    PMU_WiFi_IPtoString(wifi_status.ip_address, wifi_ip);

    /* Bluetooth status */
    PMU_BT_Status_t bt_status;
    PMU_BT_GetStatus(&bt_status);
    char bt_mac[18] = "00:00:00:00:00:00";
    PMU_BT_MACtoString(bt_status.mac_address, bt_mac);

    p += snprintf(p, end - p,
        "],\"voltage\":%.1f,\"temperature\":%.1f,\"uptime\":%u,\"tick\":%u,"
        "\"wifi\":{\"state\":%d,\"mode\":%d,\"ip\":\"%s\",\"rssi\":%d,\"clients\":%d},"
        "\"bluetooth\":{\"state\":%d,\"mode\":%d,\"mac\":\"%s\",\"connections\":%d},"
        "\"lin\":[",
        (float)state->protection.battery_voltage_mV / 1000.0f,
        (float)max_temp, state->uptime_seconds, state->tick_ms,
        wifi_status.state, wifi_status.active_mode, wifi_ip,
        wifi_status.rssi, wifi_status.connected_clients,
        bt_status.state, bt_status.active_mode, bt_mac,
        bt_status.num_connections);

    /* LIN bus status */
    for (int i = 0; i < PMU_EMU_LIN_BUS_COUNT; i++) {
        const PMU_Emu_LIN_Bus_t* lin = PMU_Emu_LIN_GetBus(i);
        if (i > 0) *p++ = ',';
        p += snprintf(p, end - p,
            "{\"state\":%d,\"is_master\":%d,\"baudrate\":%u,"
            "\"frames_rx\":%u,\"frames_tx\":%u,\"errors\":%u}",
            lin ? lin->state : 0,
            lin ? (lin->is_master ? 1 : 0) : 0,
            lin ? lin->baudrate : 0,
            lin ? lin->frames_rx : 0,
            lin ? lin->frames_tx : 0,
            lin ? lin->errors : 0);
    }
    p += snprintf(p, end - p, "]}}");

    /* Pre-calculate length once for all clients */
    size_t json_len = p - json;

    /* Send to all WebSocket clients */
    for (int i = 0; i < EMU_WEBUI_MAX_WS_CLIENTS; i++) {
        if (s_clients[i].socket != INVALID_SOCKET && s_clients[i].is_websocket) {
            send_websocket_frame(s_clients[i].socket, WS_OPCODE_TEXT,
                               (uint8_t*)json, json_len);
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

/* Save emulator state to JSON file */
int EMU_WebUI_SaveState(const char* filename)
{
    FILE* f = fopen(filename, "w");
    if (!f) {
        printf("[WebUI] Failed to open %s for writing\n", filename);
        return -1;
    }

    PMU_Emulator_t* state = PMU_Emu_GetState();
    if (!state) {
        fclose(f);
        return -1;
    }

    fprintf(f, "{\n");
    fprintf(f, "  \"version\": 1,\n");
    fprintf(f, "  \"voltage_mv\": %u,\n", state->protection.battery_voltage_mV);
    fprintf(f, "  \"temperature\": %d,\n", state->protection.board_temp_L_C);

    /* Save analog voltages */
    fprintf(f, "  \"analogs\": [");
    for (int i = 0; i < 20; i++) {
        fprintf(f, "%.3f%s", state->adc[i].voltage_v, i < 19 ? ", " : "");
    }
    fprintf(f, "],\n");

    /* Save load resistances */
    fprintf(f, "  \"loads\": [");
    for (int i = 0; i < 30; i++) {
        fprintf(f, "%.2f%s", state->profet[i].load_resistance_ohm, i < 29 ? ", " : "");
    }
    fprintf(f, "],\n");

    /* Save PROFET states */
    fprintf(f, "  \"profet_states\": [");
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        fprintf(f, "%d%s", ch ? ch->state : 0, i < 29 ? ", " : "");
    }
    fprintf(f, "],\n");

    /* Save PROFET PWM duties */
    fprintf(f, "  \"profet_duties\": [");
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        fprintf(f, "%d%s", ch ? ch->pwm_duty : 0, i < 29 ? ", " : "");
    }
    fprintf(f, "]\n");

    fprintf(f, "}\n");
    fclose(f);

    printf("[WebUI] State saved to %s\n", filename);
    return 0;
}

/* Load emulator state from JSON file */
int EMU_WebUI_LoadState(const char* filename)
{
    FILE* f = fopen(filename, "r");
    if (!f) {
        printf("[WebUI] State file %s not found\n", filename);
        return -1;
    }

    /* Read file content */
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size > 65536 || size <= 0) {
        fclose(f);
        return -1;
    }

    char* json = (char*)malloc(size + 1);
    if (!json) {
        fclose(f);
        return -1;
    }

    size_t read_size = fread(json, 1, size, f);
    fclose(f);
    json[read_size] = '\0';

    PMU_Emulator_t* state = PMU_Emu_GetState();
    if (!state) {
        free(json);
        return -1;
    }

    /* Parse voltage */
    float voltage_mv = parse_float_field(json, "voltage_mv");
    if (voltage_mv > 0) {
        state->protection.battery_voltage_mV = (uint16_t)voltage_mv;
        PMU_Emu_Protection_SetVoltage((uint16_t)voltage_mv);
    }

    /* Parse temperature */
    int temp = parse_int_field(json, "temperature");
    if (temp != 0 || strstr(json, "\"temperature\":0")) {
        state->protection.board_temp_L_C = (int16_t)temp;
        PMU_Emu_Protection_SetTemperature((int16_t)temp);
    }

    /* Parse analog voltages */
    const char* analogs = strstr(json, "\"analogs\":");
    if (analogs) {
        analogs = strchr(analogs, '[');
        if (analogs) {
            analogs++;
            for (int i = 0; i < 20 && *analogs; i++) {
                float v = 0;
                if (sscanf(analogs, "%f", &v) == 1) {
                    PMU_Emu_ADC_SetVoltage(i, v);
                }
                analogs = strchr(analogs, ',');
                if (!analogs) break;
                analogs++;
            }
        }
    }

    /* Parse load resistances */
    const char* loads = strstr(json, "\"loads\":");
    if (loads) {
        loads = strchr(loads, '[');
        if (loads) {
            loads++;
            for (int i = 0; i < 30 && *loads; i++) {
                float r = 0;
                if (sscanf(loads, "%f", &r) == 1) {
                    PMU_Emu_PROFET_SetLoad(i, r);
                }
                loads = strchr(loads, ',');
                if (!loads) break;
                loads++;
            }
        }
    }

    free(json);
    printf("[WebUI] State loaded from %s\n", filename);
    return 0;
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
    }
    /* === TEST API ENDPOINTS === */
    else if (strcmp(path, "/api/state") == 0 && strcmp(method, "GET") == 0) {
        /* Get full emulator state snapshot */
        PMU_Emulator_t* state = PMU_Emu_GetState();
        char* json = malloc(16384);
        if (json && state) {
            int len = snprintf(json, 16384,
                "{\"voltage_mV\":%u,\"temp_L\":%d,\"temp_R\":%d,"
                "\"total_current_mA\":%lu,\"uptime_s\":%lu,\"tick_ms\":%lu,\"profets\":[",
                state->protection.battery_voltage_mV,
                state->protection.board_temp_L_C,
                state->protection.board_temp_R_C,
                (unsigned long)state->protection.total_current_mA,
                (unsigned long)state->uptime_seconds,
                (unsigned long)state->tick_ms);
            for (int i = 0; i < 30; i++) {
                len += snprintf(json + len, 16384 - len,
                    "%s{\"ch\":%d,\"state\":%d,\"pwm\":%u,\"current\":%u,\"temp\":%d,\"fault\":%u}",
                    i > 0 ? "," : "", i,
                    state->profet[i].state, state->profet[i].pwm_duty,
                    state->profet[i].current_mA, state->profet[i].temperature_C,
                    state->profet[i].fault_flags);
            }
            len += snprintf(json + len, 16384 - len, "],\"analogs\":[");
            for (int i = 0; i < 20; i++) {
                len += snprintf(json + len, 16384 - len, "%s%.3f",
                    i > 0 ? "," : "", state->adc[i].voltage_v);
            }
            len += snprintf(json + len, 16384 - len, "]}");
            send_http_response(client->socket, 200, "application/json", json, len);
            free(json);
        } else {
            send_http_response(client->socket, 500, "application/json", "{\"error\":\"malloc failed\"}", 25);
        }
    }
    else if (strncmp(path, "/api/channel/", 13) == 0 && strcmp(method, "POST") == 0) {
        /* Set channel state: /api/channel/0/set?state=1&pwm=500 */
        int ch = atoi(path + 13);
        if (ch >= 0 && ch < 30) {
            char* query = strchr(path, '?');
            int state = -1, pwm = -1;
            if (query) {
                char* p = strstr(query, "state=");
                if (p) state = atoi(p + 6);
                p = strstr(query, "pwm=");
                if (p) pwm = atoi(p + 4);
            }
            if (state >= 0) {
                /* Set channel state via firmware API */
                PMU_PROFET_Channel_t* fw_ch = PMU_PROFET_GetChannelData(ch);
                if (fw_ch) {
                    fw_ch->state = state;
                    if (pwm >= 0) fw_ch->pwm_duty = pwm;
                }
            }
            char resp[64];
            int len = snprintf(resp, sizeof(resp), "{\"ok\":true,\"ch\":%d,\"state\":%d,\"pwm\":%d}", ch, state, pwm);
            send_http_response(client->socket, 200, "application/json", resp, len);
        } else {
            send_http_response(client->socket, 400, "application/json", "{\"error\":\"invalid channel\"}", 27);
        }
    }
    else if (strncmp(path, "/api/analog/", 12) == 0 && strcmp(method, "POST") == 0) {
        /* Set analog input: /api/analog/0/set?voltage=2.5 */
        int ch = atoi(path + 12);
        if (ch >= 0 && ch < 20) {
            char* query = strchr(path, '?');
            float voltage = 0.0f;
            if (query) {
                char* p = strstr(query, "voltage=");
                if (p) voltage = (float)atof(p + 8);
            }
            PMU_Emu_ADC_SetVoltage(ch, voltage);
            char resp[64];
            int len = snprintf(resp, sizeof(resp), "{\"ok\":true,\"ch\":%d,\"voltage\":%.3f}", ch, voltage);
            send_http_response(client->socket, 200, "application/json", resp, len);
        } else {
            send_http_response(client->socket, 400, "application/json", "{\"error\":\"invalid channel\"}", 27);
        }
    }
    else if (strncmp(path, "/api/load/", 10) == 0 && strcmp(method, "POST") == 0) {
        /* Set load resistance: /api/load/0/set?resistance=12.0 */
        int ch = atoi(path + 10);
        if (ch >= 0 && ch < 30) {
            char* query = strchr(path, '?');
            float resistance = 12.0f;
            if (query) {
                char* p = strstr(query, "resistance=");
                if (p) resistance = (float)atof(p + 11);
            }
            PMU_Emu_PROFET_SetLoad(ch, resistance);
            char resp[64];
            int len = snprintf(resp, sizeof(resp), "{\"ok\":true,\"ch\":%d,\"resistance\":%.2f}", ch, resistance);
            send_http_response(client->socket, 200, "application/json", resp, len);
        } else {
            send_http_response(client->socket, 400, "application/json", "{\"error\":\"invalid channel\"}", 27);
        }
    }
    else if (strcmp(path, "/api/fault/inject") == 0 && strcmp(method, "POST") == 0) {
        /* Inject fault: /api/fault/inject?ch=0&type=OC */
        char* query = strchr(path, '?');
        int ch = -1;
        uint8_t fault = 0;
        if (query) {
            char* p = strstr(query, "ch=");
            if (p) ch = atoi(p + 3);
            p = strstr(query, "type=");
            if (p) {
                if (strncmp(p + 5, "OC", 2) == 0) fault = 0x01;
                else if (strncmp(p + 5, "OT", 2) == 0) fault = 0x02;
                else if (strncmp(p + 5, "SC", 2) == 0) fault = 0x04;
                else if (strncmp(p + 5, "OL", 2) == 0) fault = 0x08;
            }
        }
        if (ch >= 0 && ch < 30 && fault != 0) {
            PMU_Emu_PROFET_InjectFault(ch, fault);
            char resp[64];
            int len = snprintf(resp, sizeof(resp), "{\"ok\":true,\"ch\":%d,\"fault\":\"0x%02X\"}", ch, fault);
            send_http_response(client->socket, 200, "application/json", resp, len);
        } else {
            send_http_response(client->socket, 400, "application/json", "{\"error\":\"invalid params\"}", 26);
        }
    }
    else if (strcmp(path, "/api/fault/clear") == 0 && strcmp(method, "POST") == 0) {
        /* Clear faults: /api/fault/clear?ch=0 or /api/fault/clear (all) */
        char* query = strchr(path, '?');
        int ch = -1;
        if (query) {
            char* p = strstr(query, "ch=");
            if (p) ch = atoi(p + 3);
        }
        if (ch >= 0 && ch < 30) {
            PMU_Emu_PROFET_ClearFault(ch);
            char resp[64];
            int len = snprintf(resp, sizeof(resp), "{\"ok\":true,\"ch\":%d}", ch);
            send_http_response(client->socket, 200, "application/json", resp, len);
        } else {
            /* Clear all faults */
            for (int i = 0; i < 30; i++) PMU_Emu_PROFET_ClearFault(i);
            PMU_Emu_Protection_ClearFaults();
            send_http_response(client->socket, 200, "application/json", "{\"ok\":true,\"cleared\":\"all\"}", 27);
        }
    }
    else if (strcmp(path, "/api/reset") == 0 && strcmp(method, "POST") == 0) {
        /* Reset emulator state */
        PMU_Emu_Reset();
        send_http_response(client->socket, 200, "application/json", "{\"ok\":true,\"action\":\"reset\"}", 28);
    }
    else if (strcmp(path, "/api/help") == 0) {
        /* API documentation */
        const char* help =
            "{\"endpoints\":["
            "{\"method\":\"GET\",\"path\":\"/api/state\",\"desc\":\"Get full emulator state\"},"
            "{\"method\":\"POST\",\"path\":\"/api/channel/{ch}/set?state=X&pwm=Y\",\"desc\":\"Set channel state (0=OFF,1=ON,6=PWM)\"},"
            "{\"method\":\"POST\",\"path\":\"/api/analog/{ch}/set?voltage=X\",\"desc\":\"Set analog input voltage (0-5V)\"},"
            "{\"method\":\"POST\",\"path\":\"/api/load/{ch}/set?resistance=X\",\"desc\":\"Set load resistance (ohms)\"},"
            "{\"method\":\"POST\",\"path\":\"/api/fault/inject?ch=X&type=OC|OT|SC|OL\",\"desc\":\"Inject fault\"},"
            "{\"method\":\"POST\",\"path\":\"/api/fault/clear?ch=X\",\"desc\":\"Clear fault (omit ch for all)\"},"
            "{\"method\":\"POST\",\"path\":\"/api/reset\",\"desc\":\"Reset emulator\"}"
            "]}";
        send_http_response(client->socket, 200, "application/json", help, strlen(help));
    }
    else {
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

    /* Set channel state and PWM */
    else if (strstr(json, "\"action\":\"set_channel\"")) {
        int channel = parse_int_field(json, "channel");
        int state = parse_int_field(json, "state");
        float pwm = parse_float_field(json, "pwm");
        uint16_t pwm_duty = (uint16_t)pwm;
        printf("[WebUI] set_channel: ch=%d, state=%d, pwm=%.0f\n", channel, state, pwm);
        if (channel >= 0 && channel < 30) {
            char msg[64];
            /* Determine if PWM mode based on duty value */
            bool is_pwm_mode = (state == 6) || (state == 1 && pwm_duty > 0 && pwm_duty < 1000);

            if (is_pwm_mode) {
                /* PWM mode - set ON with manual override, then set PWM duty */
                printf("[WebUI] Setting PWM mode for CH%d, duty=%u\n", channel + 1, pwm_duty);
                PMU_PROFET_SetStateManual(channel, 1);
                PMU_PROFET_SetPWM(channel, pwm_duty);
                snprintf(msg, sizeof(msg), "CH%d PWM %.1f%%", channel + 1, pwm_duty / 10.0f);
            } else if (state == 1) {
                /* Full ON (100%) */
                printf("[WebUI] Setting CH%d ON (100%%)\n", channel + 1);
                PMU_PROFET_SetStateManual(channel, 1);
                PMU_PROFET_SetPWM(channel, 1000);  /* 100% duty */
                snprintf(msg, sizeof(msg), "CH%d ON", channel + 1);
            } else {
                /* OFF */
                printf("[WebUI] Setting CH%d OFF\n", channel + 1);
                PMU_PROFET_SetStateManual(channel, 0);
                PMU_PROFET_SetPWM(channel, 0);
                snprintf(msg, sizeof(msg), "CH%d OFF", channel + 1);
            }
            EMU_WebUI_SendLog(1, "cmd", msg);
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

    /* Set digital input state */
    else if (strstr(json, "\"action\":\"set_digital_input\"")) {
        int channel = parse_int_field(json, "channel");
        int state_val = parse_int_field(json, "state");
        if (channel >= 0 && channel < PMU_EMU_DIGITAL_INPUTS) {
            PMU_Emu_DI_SetState((uint8_t)channel, state_val != 0);
            char msg[64];
            snprintf(msg, sizeof(msg), "DI%d = %s", channel + 1, state_val ? "HIGH" : "LOW");
            EMU_WebUI_SendLog(1, "di", msg);
        }
    }

    /* Toggle digital input */
    else if (strstr(json, "\"action\":\"toggle_digital_input\"")) {
        int channel = parse_int_field(json, "channel");
        if (channel >= 0 && channel < PMU_EMU_DIGITAL_INPUTS) {
            PMU_Emu_DI_Toggle((uint8_t)channel);
            const PMU_Emu_Digital_Input_t* di = PMU_Emu_DI_GetChannel((uint8_t)channel);
            char msg[64];
            snprintf(msg, sizeof(msg), "DI%d toggled to %s", channel + 1, di && di->state ? "HIGH" : "LOW");
            EMU_WebUI_SendLog(1, "di", msg);
        }
    }

    /* Set all digital inputs */
    else if (strstr(json, "\"action\":\"set_all_digital_inputs\"")) {
        int states = parse_int_field(json, "states");
        PMU_Emu_DI_SetAll((uint16_t)states);
        char msg[64];
        snprintf(msg, sizeof(msg), "All DI set to 0x%04X", states);
        EMU_WebUI_SendLog(1, "di", msg);
    }

    /* Set H-Bridge mode and PWM */
    else if (strstr(json, "\"action\":\"set_hbridge\"")) {
        int bridge = parse_int_field(json, "bridge");
        int mode = parse_int_field(json, "mode");
        int pwm = parse_int_field(json, "pwm");

        if (bridge >= 0 && bridge < 4) {
            /* Convert 0-255 PWM to 0-1000 */
            uint16_t duty = (pwm < 0) ? 1000 : (uint16_t)((pwm * 1000) / 255);
            if (PMU_Emu_HBridge_SetMode((uint8_t)bridge, (uint8_t)mode, duty) == 0) {
                const char* mode_names[] = {"COAST", "FWD", "REV", "BRAKE"};
                const char* mode_str = (mode >= 0 && mode < 4) ? mode_names[mode] : "?";
                char msg[80];
                snprintf(msg, sizeof(msg), "HB%d: %s PWM=%d%%", bridge + 1, mode_str, (pwm * 100) / 255);
                EMU_WebUI_SendLog(1, "hbridge", msg);
            }
        }
    }

    /* Set H-Bridge target position */
    else if (strstr(json, "\"action\":\"set_hbridge_target\"")) {
        int bridge = parse_int_field(json, "bridge");
        int target = parse_int_field(json, "target");

        if (bridge >= 0 && bridge < 4 && target >= 0) {
            if (PMU_Emu_HBridge_SetTarget((uint8_t)bridge, (uint16_t)target) == 0) {
                char msg[64];
                snprintf(msg, sizeof(msg), "HB%d target=%d", bridge + 1, target);
                EMU_WebUI_SendLog(1, "hbridge", msg);
            }
        }
    }

    /* Simulate keypad button press */
    else if (strstr(json, "\"action\":\"keypad_press\"")) {
        int idx = parse_int_field(json, "keypad");
        int btn = parse_int_field(json, "button");
        int state = parse_int_field(json, "state");

        PMU_BlinkMarine_Keypad_t* kp = PMU_BlinkMarine_GetKeypadByIndex((uint8_t)idx);
        if (kp && btn >= 0 && btn < PMU_BlinkMarine_GetButtonCount(kp->type)) {
            /* Use SimulateButton for proper J1939 button simulation */
            HAL_StatusTypeDef result = PMU_BlinkMarine_SimulateButton(
                (uint8_t)idx, (uint8_t)btn, state ? 1 : 0);

            char msg[80];
            if (result == HAL_OK) {
                snprintf(msg, sizeof(msg), "Keypad %s button %d: %s",
                         kp->name, btn + 1, state ? "PRESSED" : "RELEASED");
                EMU_WebUI_SendLog(1, "keypad", msg);
            } else {
                snprintf(msg, sizeof(msg), "Keypad %s button %d: FAILED",
                         kp->name, btn + 1);
                EMU_WebUI_SendLog(2, "keypad", msg);
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

    /* Save emulator state */
    else if (strstr(json, "\"action\":\"save_state\"")) {
        if (EMU_WebUI_SaveState("emu_state.json") == 0) {
            EMU_WebUI_SendLog(1, "system", "Emulator state saved to emu_state.json");
        } else {
            EMU_WebUI_SendLog(3, "system", "Failed to save emulator state");
        }
    }

    /* Load emulator state */
    else if (strstr(json, "\"action\":\"load_state\"")) {
        if (EMU_WebUI_LoadState("emu_state.json") == 0) {
            EMU_WebUI_SendLog(1, "system", "Emulator state loaded from emu_state.json");
        } else {
            EMU_WebUI_SendLog(2, "system", "No saved state found or load failed");
        }
    }

    /* Get current state (used on WebSocket connect) */
    else if (strstr(json, "\"action\":\"get_state\"")) {
        /* State will be sent in next telemetry update */
        EMU_WebUI_SendLog(0, "system", "State sync requested");
    }

    /* WiFi control */
    else if (strstr(json, "\"action\":\"set_wifi\"")) {
        int enabled = parse_int_field(json, "enabled");
        (void)enabled;  /* WiFi control via PMU_WiFi module */

        PMU_Emu_WiFi_SetEnabled(enabled != 0);

        char msg[80];
        snprintf(msg, sizeof(msg), "WiFi %s", enabled ? "enabled" : "disabled");
        EMU_WebUI_SendLog(1, "wifi", msg);
    }

    /* WiFi connect to network */
    else if (strstr(json, "\"action\":\"wifi_connect\"")) {
        /* Parse SSID from JSON */
        char* ssid_ptr = strstr(json, "\"ssid\":\"");
        if (ssid_ptr) {
            ssid_ptr += 8;
            char ssid[33] = {0};
            int i = 0;
            while (*ssid_ptr && *ssid_ptr != '"' && i < 32) {
                ssid[i++] = *ssid_ptr++;
            }
            ssid[i] = '\0';

            PMU_WiFi_Connect(ssid, NULL);  /* Use actual WiFi module */

            char msg[80];
            snprintf(msg, sizeof(msg), "WiFi connecting to '%s'", ssid);
            EMU_WebUI_SendLog(1, "wifi", msg);
        }
    }

    /* WiFi disconnect */
    else if (strstr(json, "\"action\":\"wifi_disconnect\"")) {
        PMU_WiFi_Disconnect();  /* Use actual WiFi module */
        EMU_WebUI_SendLog(1, "wifi", "WiFi disconnected");
    }

    /* Bluetooth control */
    else if (strstr(json, "\"action\":\"set_bluetooth\"")) {
        int enabled = parse_int_field(json, "enabled");
        (void)enabled;  /* Bluetooth control via PMU_BT module */

        PMU_Emu_BT_SetEnabled(enabled != 0);

        char msg[80];
        snprintf(msg, sizeof(msg), "Bluetooth %s", enabled ? "enabled" : "disabled");
        EMU_WebUI_SendLog(1, "bluetooth", msg);
    }

    /* Bluetooth set discoverable/advertising */
    else if (strstr(json, "\"action\":\"bt_advertise\"")) {
        int advertise = parse_int_field(json, "advertise");
        if (advertise) {
            PMU_BT_StartAdvertising();  /* Use actual BT module */
        } else {
            PMU_BT_StopAdvertising();
        }

        char msg[64];
        snprintf(msg, sizeof(msg), "Bluetooth %s",
                 advertise ? "advertising" : "not advertising");
        EMU_WebUI_SendLog(1, "bluetooth", msg);
    }

    /* LIN bus control */
    else if (strstr(json, "\"action\":\"set_lin\"")) {
        int bus = parse_int_field(json, "bus");
        int enabled = parse_int_field(json, "enabled");

        if (bus >= 0 && bus < PMU_EMU_LIN_BUS_COUNT) {
            PMU_Emu_LIN_SetEnabled(bus, enabled != 0);

            char msg[64];
            snprintf(msg, sizeof(msg), "LIN%d %s", bus, enabled ? "enabled" : "disabled");
            EMU_WebUI_SendLog(1, "lin", msg);
        }
    }

    /* LIN wakeup */
    else if (strstr(json, "\"action\":\"lin_wakeup\"")) {
        int bus = parse_int_field(json, "bus");

        if (bus >= 0 && bus < PMU_EMU_LIN_BUS_COUNT) {
            PMU_Emu_LIN_SendWakeup(bus);

            char msg[64];
            snprintf(msg, sizeof(msg), "LIN%d wakeup sent", bus);
            EMU_WebUI_SendLog(1, "lin", msg);
        }
    }

    /* LIN sleep */
    else if (strstr(json, "\"action\":\"lin_sleep\"")) {
        int bus = parse_int_field(json, "bus");

        if (bus >= 0 && bus < PMU_EMU_LIN_BUS_COUNT) {
            PMU_Emu_LIN_SetSleep(bus);

            char msg[64];
            snprintf(msg, sizeof(msg), "LIN%d sleep mode", bus);
            EMU_WebUI_SendLog(1, "lin", msg);
        }
    }

    /* LIN frame injection */
    else if (strstr(json, "\"action\":\"inject_lin\"")) {
        int bus = parse_int_field(json, "bus");
        int id = parse_int_field(json, "id");
        int data[8] = {0};
        int len = parse_int_array(json, "data", data, 8);

        if (bus >= 0 && bus < PMU_EMU_LIN_BUS_COUNT && id >= 0 && id <= 63) {
            uint8_t lin_data[8];
            for (int i = 0; i < 8; i++) {
                lin_data[i] = (uint8_t)data[i];
            }

            PMU_Emu_LIN_InjectFrame(bus, id, lin_data, len > 0 ? len : 8);

            char msg[128];
            snprintf(msg, sizeof(msg), "LIN%d inject ID=0x%02X len=%d", bus, id, len);
            EMU_WebUI_SendLog(1, "lin", msg);
        }
    }
    /* Device restart action */
    else if (strstr(json, "\"action\":\"restart_device\"")) {
        printf("\n");
        printf("+============================================================+\n");
        printf("|          DEVICE RESTART REQUESTED (FROM WEBUI)             |\n");
        printf("+============================================================+\n");
        printf("\n");

        EMU_WebUI_SendLog(2, "system", "Device restart requested from WebUI");

        /* Reset emulator state - simulates device restart */
        PMU_Emu_Reset();

        EMU_WebUI_SendLog(1, "system", "Device restarted successfully");
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
