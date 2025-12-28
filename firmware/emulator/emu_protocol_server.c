/**
 ******************************************************************************
 * @file           : emu_protocol_server.c
 * @brief          : TCP Server Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "emu_protocol_server.h"
#include "emu_webui.h"
#include "pmu_emulator.h"
#include "pmu_config_json.h"
#include "pmu_channel.h"
#include "pmu_profet.h"
#include "pmu_blinkmarine.h"
#include "pmu_adc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef int socklen_t;
#define close closesocket
#define SHUT_RDWR SD_BOTH
#else
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#endif

/* Private typedef -----------------------------------------------------------*/

typedef struct {
    int socket;
    bool active;
    bool telemetry_enabled;
    uint16_t telemetry_rate_hz;
    uint32_t last_telemetry_tick;
    uint8_t rx_buffer[EMU_SERVER_BUFFER_SIZE];
    size_t rx_len;
    /* Config upload state */
    uint8_t* config_buffer;
    size_t config_buffer_size;
    size_t config_received;
    uint16_t config_chunks_received;
    uint16_t config_total_chunks;
} EMU_Client_t;

/* Private define ------------------------------------------------------------*/

#define LOG_SERVER(fmt, ...) do { if (server.config.verbose) printf("[SRV] " fmt "\n", ##__VA_ARGS__); } while(0)

/* Private variables ---------------------------------------------------------*/

static struct {
    EMU_ServerConfig_t config;
    int listen_socket;
    bool running;
    EMU_Client_t clients[EMU_SERVER_MAX_CLIENTS];
    EMU_ServerStats_t stats;
#ifdef _WIN32
    bool wsa_initialized;
#endif
} server = {0};

/* Device info for INFO_RESP */
static const char* DEVICE_NAME = "PMU-30 Emulator";
static const char* SERIAL_NUMBER = "EMU-00000001";
static const uint8_t FW_VERSION[3] = {1, 0, 0};
static const uint8_t HW_REVISION = 0xFF;  /* Emulator */

/* Config statistics (updated on each config load) */
static PMU_JSON_LoadStats_t last_config_stats = {0};
static bool config_loaded = false;
static char* last_config_json = NULL;
static size_t last_config_size = 0;

/* Private function prototypes -----------------------------------------------*/

static int Server_SetNonBlocking(int socket);
static void Server_AcceptConnections(void);
static void Server_ProcessClient(int client_idx);
static int Server_ProcessFrame(int client_idx, uint8_t* data, size_t len);
static void Server_HandleMessage(int client_idx, uint8_t msg_type, uint8_t* payload, uint16_t len);
static int Server_SendResponse(int client_idx, uint8_t msg_type, const uint8_t* payload, uint16_t len);
static uint16_t Server_CRC16(const uint8_t* data, size_t len);
static void Server_BuildTelemetry(uint8_t* buffer, size_t* len);
static int Server_ApplyConfig(const char* json, size_t len);

/* Exported functions --------------------------------------------------------*/

int EMU_Server_Init(const EMU_ServerConfig_t* config)
{
    memset(&server, 0, sizeof(server));

    /* Apply config or defaults */
    if (config) {
        server.config = *config;
    } else {
        server.config.port = EMU_SERVER_DEFAULT_PORT;
        server.config.timeout_ms = 100;
        server.config.verbose = true;
    }

    server.listen_socket = -1;

    /* Initialize clients */
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        server.clients[i].socket = -1;
        server.clients[i].active = false;
    }

#ifdef _WIN32
    /* Initialize Winsock */
    WSADATA wsa_data;
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        printf("WSAStartup failed\n");
        return -1;
    }
    server.wsa_initialized = true;
#endif

    LOG_SERVER("Server initialized, port %d", server.config.port);
    return 0;
}

int EMU_Server_Start(void)
{
    struct sockaddr_in addr;

    /* Create socket */
    server.listen_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server.listen_socket < 0) {
        perror("socket");
        return -1;
    }

    /* Set socket options */
    int opt = 1;
    setsockopt(server.listen_socket, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    /* Set non-blocking */
    Server_SetNonBlocking(server.listen_socket);

    /* Bind */
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(server.config.port);

    if (bind(server.listen_socket, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server.listen_socket);
        server.listen_socket = -1;
        return -1;
    }

    /* Listen */
    if (listen(server.listen_socket, 5) < 0) {
        perror("listen");
        close(server.listen_socket);
        server.listen_socket = -1;
        return -1;
    }

    server.running = true;
    LOG_SERVER("Server started on port %d", server.config.port);
    printf("\n>>> Configurator can connect to: localhost:%d\n\n", server.config.port);

    return 0;
}

void EMU_Server_Stop(void)
{
    /* Close all client connections */
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) {
            close(server.clients[i].socket);
            server.clients[i].active = false;
            server.clients[i].socket = -1;
        }
        /* Free config buffer if allocated */
        if (server.clients[i].config_buffer) {
            free(server.clients[i].config_buffer);
            server.clients[i].config_buffer = NULL;
        }
    }

    /* Close listen socket */
    if (server.listen_socket >= 0) {
        close(server.listen_socket);
        server.listen_socket = -1;
    }

    server.running = false;

#ifdef _WIN32
    if (server.wsa_initialized) {
        WSACleanup();
        server.wsa_initialized = false;
    }
#endif

    LOG_SERVER("Server stopped");
}

void EMU_Server_Process(uint32_t timeout_ms)
{
    if (!server.running) return;

    fd_set read_fds;
    struct timeval tv;
    int max_fd = server.listen_socket;

    FD_ZERO(&read_fds);
    FD_SET(server.listen_socket, &read_fds);

    /* Add client sockets */
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) {
            FD_SET(server.clients[i].socket, &read_fds);
            if (server.clients[i].socket > max_fd) {
                max_fd = server.clients[i].socket;
            }
        }
    }

    /* Set timeout */
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;

    int result = select(max_fd + 1, &read_fds, NULL, NULL, &tv);
    if (result < 0) {
#ifdef _WIN32
        if (WSAGetLastError() != WSAEINTR)
#else
        if (errno != EINTR)
#endif
        {
            perror("select");
        }
        return;
    }

    if (result == 0) {
        /* Timeout - check for telemetry */
        EMU_Server_SendTelemetry();
        return;
    }

    /* Check for new connections */
    if (FD_ISSET(server.listen_socket, &read_fds)) {
        Server_AcceptConnections();
    }

    /* Process client data */
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active && FD_ISSET(server.clients[i].socket, &read_fds)) {
            Server_ProcessClient(i);
        }
    }

    /* Send telemetry */
    EMU_Server_SendTelemetry();
}

bool EMU_Server_IsRunning(void)
{
    return server.running;
}

bool EMU_Server_HasClients(void)
{
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) return true;
    }
    return false;
}

const EMU_ServerStats_t* EMU_Server_GetStats(void)
{
    /* Update active connections count */
    server.stats.connections_active = 0;
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) {
            server.stats.connections_active++;
        }
    }
    return &server.stats;
}

void EMU_Server_SendTelemetry(void)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    uint32_t now = emu->tick_ms;

    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (!server.clients[i].active || !server.clients[i].telemetry_enabled) {
            continue;
        }

        uint32_t interval_ms = 1000 / server.clients[i].telemetry_rate_hz;
        if (now - server.clients[i].last_telemetry_tick >= interval_ms) {
            server.clients[i].last_telemetry_tick = now;

            uint8_t buffer[512];
            size_t len = 0;
            Server_BuildTelemetry(buffer, &len);

            Server_SendResponse(i, EMU_MSG_TELEMETRY_DATA, buffer, (uint16_t)len);
        }
    }
}

int EMU_Server_Broadcast(uint8_t msg_type, const uint8_t* payload, uint16_t len)
{
    int count = 0;
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) {
            if (Server_SendResponse(i, msg_type, payload, len) >= 0) {
                count++;
            }
        }
    }
    return count;
}

/* Private functions ---------------------------------------------------------*/

static int Server_SetNonBlocking(int sock)
{
#ifdef _WIN32
    u_long mode = 1;
    return ioctlsocket(sock, FIONBIO, &mode);
#else
    int flags = fcntl(sock, F_GETFL, 0);
    return fcntl(sock, F_SETFL, flags | O_NONBLOCK);
#endif
}

static void Server_AcceptConnections(void)
{
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);

    int client_sock = accept(server.listen_socket, (struct sockaddr*)&client_addr, &addr_len);
    if (client_sock < 0) {
        return;
    }

    /* Find free slot */
    int slot = -1;
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (!server.clients[i].active) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        LOG_SERVER("Max clients reached, rejecting connection");
        close(client_sock);
        return;
    }

    /* Setup client */
    Server_SetNonBlocking(client_sock);
    server.clients[slot].socket = client_sock;
    server.clients[slot].active = true;
    server.clients[slot].telemetry_enabled = false;
    server.clients[slot].rx_len = 0;

    server.stats.connections_total++;
    server.stats.connections_active++;

    char* ip = inet_ntoa(client_addr.sin_addr);
    LOG_SERVER("Client %d connected from %s:%d", slot, ip, ntohs(client_addr.sin_port));
}

static void Server_ProcessClient(int client_idx)
{
    EMU_Client_t* client = &server.clients[client_idx];

    /* Receive data */
    int bytes = recv(client->socket, (char*)client->rx_buffer + client->rx_len,
                     EMU_SERVER_BUFFER_SIZE - client->rx_len, 0);

    if (bytes <= 0) {
        /* Connection closed or error */
        LOG_SERVER("Client %d disconnected", client_idx);
        close(client->socket);
        client->socket = -1;
        client->active = false;
        /* Free config buffer if allocated */
        if (client->config_buffer) {
            free(client->config_buffer);
            client->config_buffer = NULL;
        }
        server.stats.connections_active--;
        return;
    }

    client->rx_len += bytes;

    /* Process frames */
    while (client->rx_len > 0) {
        int consumed = Server_ProcessFrame(client_idx, client->rx_buffer, client->rx_len);
        if (consumed <= 0) break;

        /* Remove consumed bytes */
        if (consumed < (int)client->rx_len) {
            memmove(client->rx_buffer, client->rx_buffer + consumed, client->rx_len - consumed);
        }
        client->rx_len -= consumed;
    }
}

static int Server_ProcessFrame(int client_idx, uint8_t* data, size_t len)
{
    /* Find start byte */
    size_t start = 0;
    while (start < len && data[start] != EMU_PROTO_START_BYTE) {
        start++;
    }

    if (start > 0) {
        return (int)start;  /* Skip garbage */
    }

    /* Need header */
    if (len < EMU_PROTO_HEADER_SIZE) {
        return 0;
    }

    /* Parse header */
    uint16_t payload_len = data[1] | (data[2] << 8);
    uint8_t msg_type = data[3];

    if (payload_len > EMU_PROTO_MAX_PAYLOAD) {
        server.stats.errors++;
        return 1;  /* Skip start byte */
    }

    /* Need full frame */
    size_t frame_len = EMU_PROTO_HEADER_SIZE + payload_len + EMU_PROTO_CRC_SIZE;
    if (len < frame_len) {
        return 0;
    }

    /* Verify CRC */
    uint16_t received_crc = data[frame_len - 2] | (data[frame_len - 1] << 8);
    uint16_t calculated_crc = Server_CRC16(data + 1, frame_len - 3);  /* Skip start, exclude CRC */

    if (received_crc != calculated_crc) {
        LOG_SERVER("CRC error: received 0x%04X, calculated 0x%04X", received_crc, calculated_crc);
        server.stats.errors++;
        return 1;  /* Skip start byte */
    }

    /* Handle message */
    server.stats.messages_rx++;
    Server_HandleMessage(client_idx, msg_type, data + EMU_PROTO_HEADER_SIZE, payload_len);

    return (int)frame_len;
}

static void Server_HandleMessage(int client_idx, uint8_t msg_type, uint8_t* payload, uint16_t len)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    uint8_t resp[512];
    uint16_t resp_len = 0;

    /* Skip logging for frequent messages (PING=0x01, TELEMETRY_SUB=0x51) */
    if (msg_type != 0x01 && msg_type != 0x51) {
        LOG_SERVER("RX msg 0x%02X, len %d", msg_type, len);
        /* Send protocol command to WebUI log */
        char log_msg[128];
        snprintf(log_msg, sizeof(log_msg), "CMD 0x%02X len=%d", msg_type, len);
        EMU_WebUI_SendLog(0, "protocol", log_msg);
    }

    switch (msg_type) {
        case EMU_MSG_PING:
            /* Respond with PONG */
            Server_SendResponse(client_idx, EMU_MSG_PONG, NULL, 0);
            break;

        case EMU_MSG_GET_INFO: {
            /* Build INFO_RESP */
            resp[0] = FW_VERSION[0];
            resp[1] = FW_VERSION[1];
            resp[2] = FW_VERSION[2];
            resp[3] = HW_REVISION;

            /* Serial number (16 bytes) */
            memset(resp + 4, 0, 16);
            strncpy((char*)resp + 4, SERIAL_NUMBER, 16);

            /* Device name (32 bytes) */
            memset(resp + 20, 0, 32);
            strncpy((char*)resp + 20, DEVICE_NAME, 32);

            resp_len = 52;
            Server_SendResponse(client_idx, EMU_MSG_INFO_RESP, resp, resp_len);
            break;
        }

        case EMU_MSG_SUBSCRIBE_TELEM: {
            uint16_t rate_hz = 50;
            if (len >= 2) {
                rate_hz = payload[0] | (payload[1] << 8);
            }
            if (rate_hz > 100) rate_hz = 100;
            if (rate_hz < 1) rate_hz = 1;

            server.clients[client_idx].telemetry_enabled = true;
            server.clients[client_idx].telemetry_rate_hz = rate_hz;
            server.clients[client_idx].last_telemetry_tick = emu->tick_ms;

            LOG_SERVER("Telemetry enabled at %d Hz", rate_hz);
            break;
        }

        case EMU_MSG_UNSUBSCRIBE_TELEM:
            server.clients[client_idx].telemetry_enabled = false;
            LOG_SERVER("Telemetry disabled");
            break;

        case EMU_MSG_SET_CHANNEL: {
            if (len >= 6) {
                uint16_t channel_id = payload[0] | (payload[1] << 8);
                float value;
                memcpy(&value, payload + 2, 4);

                LOG_SERVER("SET_CHANNEL %d = %.2f", channel_id, value);

                /* Send to WebUI log */
                {
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "SET_CHANNEL %d = %.2f", channel_id, value);
                    EMU_WebUI_SendLog(1, "cmd", log_msg);
                }

                /* Apply to firmware channel system */
                HAL_StatusTypeDef result = PMU_Channel_SetValue(channel_id, (int32_t)value);

                /* Also update emulator and firmware state for outputs */
                if (channel_id >= 100 && channel_id < 130) {
                    /* PROFET output - update both emulator and firmware state */
                    uint8_t profet_idx = channel_id - 100;
                    uint8_t new_state = (value > 0) ? 1 : 0;

                    /* Update firmware PROFET state */
                    PMU_PROFET_SetState(profet_idx, new_state);

                    /* Also update emulator state */
                    emu->profet[profet_idx].state = new_state;
                    emu->profet[profet_idx].pwm_duty = (value > 0) ? (uint16_t)value : 0;

                    LOG_SERVER("PROFET[%d] state=%d duty=%d", profet_idx, new_state, (int)value);
                } else if (channel_id < 20) {
                    /* Input channel - update emulator ADC */
                    PMU_Emu_ADC_SetRaw(channel_id, (uint16_t)value);
                }

                /* Send ACK */
                resp[0] = (uint8_t)(channel_id & 0xFF);
                resp[1] = (uint8_t)(channel_id >> 8);
                resp[2] = (result == HAL_OK) ? 1 : 0;  /* Success flag */
                resp[3] = 0;  /* Error code low */
                resp[4] = 0;  /* Error code high */
                Server_SendResponse(client_idx, EMU_MSG_CHANNEL_ACK, resp, 5);
            }
            break;
        }

        case EMU_MSG_GET_CHANNEL: {
            if (len >= 2) {
                uint16_t channel_id = payload[0] | (payload[1] << 8);

                /* Get from firmware channel system first */
                int32_t ch_value = PMU_Channel_GetValue(channel_id);
                float value = (float)ch_value;

                /* Fall back to emulator state if channel not registered */
                if (ch_value == 0) {
                    if (channel_id < 20) {
                        value = (float)emu->adc[channel_id].raw_value;
                    } else if (channel_id >= 100 && channel_id < 130) {
                        const PMU_Emu_PROFET_Channel_t* ch = PMU_Emu_PROFET_GetState(channel_id - 100);
                        if (ch) value = (float)ch->pwm_duty;
                    }
                }

                resp[0] = (uint8_t)(channel_id & 0xFF);
                resp[1] = (uint8_t)(channel_id >> 8);
                memcpy(resp + 2, &value, 4);
                Server_SendResponse(client_idx, EMU_MSG_CHANNEL_DATA, resp, 6);
            }
            break;
        }

        case EMU_MSG_GET_CONFIG: {
            /* Read config from last_config.json and send it */
            const char* config_file = "last_config.json";
            printf("[SRV] GET_CONFIG request received, opening %s\n", config_file);
            fflush(stdout);
            FILE* f = fopen(config_file, "rb");

            if (!f) {
                /* No config file - send empty config */
                LOG_SERVER("GET_CONFIG: No config file found, sending empty config");
                printf("[SRV] GET_CONFIG: File not found!\n");
                fflush(stdout);
                resp[0] = 0;  /* Chunk index low */
                resp[1] = 0;  /* Chunk index high */
                resp[2] = 1;  /* Total chunks low */
                resp[3] = 0;  /* Total chunks high */
                resp[4] = '{';
                resp[5] = '}';
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_DATA, resp, 6);
                break;
            }

            /* Get file size */
            fseek(f, 0, SEEK_END);
            long file_size = ftell(f);
            fseek(f, 0, SEEK_SET);

            if (file_size <= 0 || file_size > 100 * 1024) {
                fclose(f);
                LOG_SERVER("GET_CONFIG: Invalid config file size %ld", file_size);
                resp[0] = 0; resp[1] = 0; resp[2] = 1; resp[3] = 0;
                resp[4] = '{'; resp[5] = '}';
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_DATA, resp, 6);
                break;
            }

            /* Allocate and read config */
            char* config_data = (char*)malloc(file_size + 1);
            if (!config_data) {
                fclose(f);
                LOG_SERVER("GET_CONFIG: Failed to allocate memory");
                resp[0] = 0; resp[1] = 0; resp[2] = 1; resp[3] = 0;
                resp[4] = '{'; resp[5] = '}';
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_DATA, resp, 6);
                break;
            }

            size_t bytes_read = fread(config_data, 1, file_size, f);
            fclose(f);
            config_data[bytes_read] = '\0';

            LOG_SERVER("GET_CONFIG: Sending config (%zu bytes)", bytes_read);

            /* Send config in chunks (max 500 bytes payload per chunk to fit in buffer) */
            const size_t MAX_CHUNK_DATA = 500;
            uint16_t total_chunks = (uint16_t)((bytes_read + MAX_CHUNK_DATA - 1) / MAX_CHUNK_DATA);
            if (total_chunks == 0) total_chunks = 1;

            /* Allocate chunk buffer (header + data) */
            uint8_t* chunk_buf = (uint8_t*)malloc(MAX_CHUNK_DATA + 4);
            if (!chunk_buf) {
                LOG_SERVER("GET_CONFIG: Failed to allocate chunk buffer");
                free(config_data);
                resp[0] = 0; resp[1] = 0; resp[2] = 1; resp[3] = 0;
                resp[4] = '{'; resp[5] = '}';
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_DATA, resp, 6);
                break;
            }

            size_t offset = 0;
            for (uint16_t chunk_idx = 0; chunk_idx < total_chunks; chunk_idx++) {
                size_t chunk_size = bytes_read - offset;
                if (chunk_size > MAX_CHUNK_DATA) chunk_size = MAX_CHUNK_DATA;

                /* Build response: header + data */
                chunk_buf[0] = (uint8_t)(chunk_idx & 0xFF);
                chunk_buf[1] = (uint8_t)(chunk_idx >> 8);
                chunk_buf[2] = (uint8_t)(total_chunks & 0xFF);
                chunk_buf[3] = (uint8_t)(total_chunks >> 8);
                memcpy(chunk_buf + 4, config_data + offset, chunk_size);

                LOG_SERVER("GET_CONFIG: Sending chunk %d/%d (%zu bytes)", chunk_idx + 1, total_chunks, chunk_size);
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_DATA, chunk_buf, 4 + chunk_size);
                offset += chunk_size;
            }

            free(chunk_buf);
            free(config_data);
            break;
        }

        case EMU_MSG_SET_CONFIG: {
            /* Parse chunk header */
            if (len < 4) {
                resp[0] = 0;  /* Failure */
                resp[1] = 1;  /* Error code: invalid length */
                resp[2] = 0;
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_ACK, resp, 3);
                break;
            }

            uint16_t chunk_idx = payload[0] | (payload[1] << 8);
            uint16_t total_chunks = payload[2] | (payload[3] << 8);
            uint8_t* chunk_data = payload + 4;
            uint16_t chunk_len = len - 4;

            EMU_Client_t* client = &server.clients[client_idx];

            LOG_SERVER("SET_CONFIG chunk %d/%d, %d bytes", chunk_idx + 1, total_chunks, chunk_len);

            /* Send to WebUI log */
            {
                char log_msg[64];
                snprintf(log_msg, sizeof(log_msg), "Config chunk %d/%d (%d bytes)", chunk_idx + 1, total_chunks, chunk_len);
                EMU_WebUI_SendLog(1, "config", log_msg);
            }

            /* First chunk - allocate buffer */
            if (chunk_idx == 0) {
                /* Free previous buffer if any */
                if (client->config_buffer) {
                    free(client->config_buffer);
                }
                /* Allocate generous buffer (100KB max) */
                client->config_buffer_size = 100 * 1024;
                client->config_buffer = (uint8_t*)malloc(client->config_buffer_size);
                client->config_received = 0;
                client->config_chunks_received = 0;
                client->config_total_chunks = total_chunks;

                if (!client->config_buffer) {
                    LOG_SERVER("Failed to allocate config buffer");
                    resp[0] = 0;  /* Failure */
                    resp[1] = 2;  /* Error: out of memory */
                    resp[2] = 0;
                    Server_SendResponse(client_idx, EMU_MSG_CONFIG_ACK, resp, 3);
                    break;
                }
            }

            /* Store chunk data */
            if (client->config_buffer &&
                client->config_received + chunk_len <= client->config_buffer_size) {
                memcpy(client->config_buffer + client->config_received, chunk_data, chunk_len);
                client->config_received += chunk_len;
                client->config_chunks_received++;
            }

            /* All chunks received? */
            if (client->config_chunks_received >= client->config_total_chunks) {
                /* Null-terminate for JSON parsing */
                if (client->config_received < client->config_buffer_size) {
                    client->config_buffer[client->config_received] = '\0';
                }

                LOG_SERVER("Config complete: %zu bytes", client->config_received);

                /* Send to WebUI log */
                {
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Config upload complete: %zu bytes", client->config_received);
                    EMU_WebUI_SendLog(1, "config", log_msg);
                }

                /* Apply configuration */
                int result = Server_ApplyConfig((char*)client->config_buffer, client->config_received);

                /* Send ACK */
                resp[0] = (result == 0) ? 1 : 0;
                resp[1] = (result != 0) ? 3 : 0;  /* Error: parse error */
                resp[2] = 0;
                Server_SendResponse(client_idx, EMU_MSG_CONFIG_ACK, resp, 3);

                /* Free buffer */
                free(client->config_buffer);
                client->config_buffer = NULL;
                client->config_buffer_size = 0;
                client->config_received = 0;
            }
            break;
        }

        case EMU_MSG_SAVE_TO_FLASH: {
            LOG_SERVER("SAVE_TO_FLASH requested");
            /* In emulator, we simulate flash save */
            printf("\n");
            printf("+============================================================+\n");
            printf("|          CONFIGURATION SAVED TO FLASH (SIMULATED)          |\n");
            printf("+============================================================+\n");
            printf("\n");

            /* Send ACK */
            resp[0] = 1;  /* Success */
            resp[1] = 0;  /* Error code low */
            resp[2] = 0;  /* Error code high */
            Server_SendResponse(client_idx, EMU_MSG_FLASH_ACK, resp, 3);
            break;
        }

        case EMU_MSG_RESTART: {
            LOG_SERVER("RESTART requested");
            printf("\n");
            printf("+============================================================+\n");
            printf("|          DEVICE RESTART REQUESTED (SIMULATED)              |\n");
            printf("+============================================================+\n");
            printf("\n");

            /* Send ACK before "restarting" */
            resp[0] = 1;  /* Success */
            Server_SendResponse(client_idx, EMU_MSG_RESTART_ACK, resp, 1);

            /* Simulate restart by resetting emulator state */
            /* In real firmware this would trigger a system reset */
            break;
        }

        /* ===== Emulator Control Commands ===== */

        case EMU_MSG_INJECT_FAULT: {
            if (len >= 2) {
                uint8_t channel = payload[0];
                uint8_t fault_type = payload[1];

                LOG_SERVER("INJECT_FAULT: CH%d, fault=0x%02X", channel + 1, fault_type);

                if (channel < 30) {
                    emu->profet[channel].fault_flags = fault_type;

                    /* Send to WebUI log */
                    char log_msg[64];
                    const char* fault_name = (fault_type & 1) ? "OC" :
                                            (fault_type & 2) ? "OT" :
                                            (fault_type & 4) ? "SC" :
                                            (fault_type & 8) ? "OL" : "?";
                    snprintf(log_msg, sizeof(log_msg), "Injected %s fault on CH%d", fault_name, channel + 1);
                    EMU_WebUI_SendLog(2, "fault", log_msg);
                }

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_CLEAR_FAULT: {
            if (len >= 1) {
                uint8_t channel = payload[0];

                LOG_SERVER("CLEAR_FAULT: CH%d", channel + 1);

                if (channel < 30) {
                    emu->profet[channel].fault_flags = 0;

                    /* Send to WebUI log */
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Cleared fault on CH%d", channel + 1);
                    EMU_WebUI_SendLog(1, "fault", log_msg);
                }

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_VOLTAGE: {
            if (len >= 2) {
                uint16_t voltage_mv = payload[0] | (payload[1] << 8);

                LOG_SERVER("SET_VOLTAGE: %d mV", voltage_mv);

                /* Clamp to valid range */
                if (voltage_mv < 6000) voltage_mv = 6000;
                if (voltage_mv > 18000) voltage_mv = 18000;

                /* Use the protection API to set voltage */
                PMU_Emu_Protection_SetVoltage(voltage_mv);

                /* Send to WebUI log */
                char log_msg[64];
                snprintf(log_msg, sizeof(log_msg), "Set battery voltage to %.1fV", voltage_mv / 1000.0f);
                EMU_WebUI_SendLog(1, "system", log_msg);

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_TEMPERATURE: {
            if (len >= 2) {
                int16_t temp_c = (int16_t)(payload[0] | (payload[1] << 8));

                LOG_SERVER("SET_TEMPERATURE: %d C", temp_c);

                /* Clamp to valid range */
                if (temp_c < -40) temp_c = -40;
                if (temp_c > 150) temp_c = 150;

                /* Use the protection API to set temperature */
                PMU_Emu_Protection_SetTemperature(temp_c);

                /* Send to WebUI log */
                char log_msg[64];
                snprintf(log_msg, sizeof(log_msg), "Set temperature to %d C", temp_c);
                EMU_WebUI_SendLog(1, "system", log_msg);

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_DIGITAL_INPUT: {
            if (len >= 2) {
                uint8_t channel = payload[0];
                uint8_t state = payload[1];

                LOG_SERVER("SET_DIGITAL_INPUT: DI%d = %s", channel + 1, state ? "HIGH" : "LOW");

                if (channel < 16) {
                    /* Use the DI API to set state */
                    PMU_Emu_DI_SetState(channel, state ? true : false);

                    /* Send to WebUI log */
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Set DI%d to %s", channel + 1, state ? "HIGH" : "LOW");
                    EMU_WebUI_SendLog(1, "input", log_msg);
                }

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_ANALOG_INPUT: {
            if (len >= 3) {
                uint8_t channel = payload[0];
                uint16_t voltage_mv = payload[1] | (payload[2] << 8);
                float voltage_v = voltage_mv / 1000.0f;

                LOG_SERVER("SET_ANALOG_INPUT: AIN%d = %dmV (%.2fV)", channel + 1, voltage_mv, voltage_v);

                if (channel < 16) {
                    /* Use the ADC API to set voltage */
                    PMU_Emu_ADC_SetVoltage(channel, voltage_v);

                    /* Send to WebUI log */
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Set AIN%d to %.2fV", channel + 1, voltage_v);
                    EMU_WebUI_SendLog(1, "input", log_msg);
                }

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_OUTPUT: {
            if (len >= 4) {
                uint8_t channel = payload[0];
                uint8_t on = payload[1];
                uint16_t pwm = payload[2] | (payload[3] << 8);

                LOG_SERVER("SET_OUTPUT: CH%d %s, PWM=%d", channel + 1, on ? "ON" : "OFF", pwm);

                if (channel < 30) {
                    emu->profet[channel].state = on ? 1 : 0;
                    emu->profet[channel].pwm_duty = pwm;

                    /* Also update firmware PROFET state */
                    PMU_PROFET_SetState(channel, on ? 1 : 0);
                    PMU_PROFET_SetPWM(channel, pwm);

                    /* Send to WebUI log */
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Set CH%d %s PWM=%d%%", channel + 1,
                             on ? "ON" : "OFF", pwm / 10);
                    EMU_WebUI_SendLog(1, "output", log_msg);
                }

                /* Send ACK */
                resp[0] = 1;  /* Success */
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_SET_BUTTON: {
            if (len >= 3) {
                uint8_t keypad_idx = payload[0];
                uint8_t button_idx = payload[1];
                uint8_t pressed = payload[2];

                LOG_SERVER("SET_BUTTON: Keypad %d, Button %d, %s",
                          keypad_idx, button_idx, pressed ? "PRESS" : "RELEASE");

                /* Call BlinkMarine button simulation */
                HAL_StatusTypeDef result = PMU_BlinkMarine_SimulateButton(keypad_idx, button_idx, pressed);

                /* Send to WebUI log */
                {
                    char log_msg[64];
                    snprintf(log_msg, sizeof(log_msg), "Button %d.%d %s",
                             keypad_idx, button_idx, pressed ? "PRESSED" : "RELEASED");
                    EMU_WebUI_SendLog(1, "button", log_msg);
                }

                /* Send ACK */
                resp[0] = (result == HAL_OK) ? 1 : 0;
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        case EMU_MSG_INJECT_CAN: {
            /* Inject CAN message for testing CAN inputs
             * Payload format: [bus_id:1][can_id:4][dlc:1][data:0-8]
             * Minimum length: 6 (bus_id + can_id + dlc + 0 data bytes)
             */
            if (len >= 6) {
                uint8_t bus_id = payload[0];
                uint32_t can_id = payload[1] | (payload[2] << 8) |
                                  (payload[3] << 16) | (payload[4] << 24);
                uint8_t dlc = payload[5];

                if (dlc > 8) dlc = 8;

                uint8_t data[8] = {0};
                for (int i = 0; i < dlc && i + 6 < len; i++) {
                    data[i] = payload[6 + i];
                }

                LOG_SERVER("INJECT_CAN: Bus%d ID=0x%03X DLC=%d", bus_id, can_id, dlc);

                /* Inject CAN message into the CAN subsystem */
                HAL_StatusTypeDef result = PMU_CAN_InjectMessage(bus_id, can_id, data, dlc);

                /* Send to WebUI log */
                {
                    char log_msg[80];
                    snprintf(log_msg, sizeof(log_msg), "CAN Inject: Bus%d ID=0x%03X [%02X %02X %02X %02X %02X %02X %02X %02X]",
                             bus_id, can_id, data[0], data[1], data[2], data[3],
                             data[4], data[5], data[6], data[7]);
                    EMU_WebUI_SendLog(1, "can", log_msg);
                }

                /* Send ACK */
                resp[0] = (result == HAL_OK) ? 1 : 0;
                Server_SendResponse(client_idx, EMU_MSG_EMU_ACK, resp, 1);
            }
            break;
        }

        default:
            LOG_SERVER("Unknown message type 0x%02X", msg_type);
            /* Send error */
            resp[0] = 0x01;  /* Error code low */
            resp[1] = 0x00;  /* Error code high */
            resp[2] = 15;    /* Message length */
            memcpy(resp + 3, "Unknown command", 15);
            Server_SendResponse(client_idx, EMU_MSG_ERROR, resp, 18);
            break;
    }
}

static int Server_SendResponse(int client_idx, uint8_t msg_type, const uint8_t* payload, uint16_t len)
{
    if (!server.clients[client_idx].active) {
        return -1;
    }

    uint8_t frame[EMU_PROTO_HEADER_SIZE + EMU_PROTO_MAX_PAYLOAD + EMU_PROTO_CRC_SIZE];
    size_t frame_len = EMU_PROTO_HEADER_SIZE + len + EMU_PROTO_CRC_SIZE;

    /* Build frame */
    frame[0] = EMU_PROTO_START_BYTE;
    frame[1] = (uint8_t)(len & 0xFF);
    frame[2] = (uint8_t)(len >> 8);
    frame[3] = msg_type;

    if (payload && len > 0) {
        memcpy(frame + EMU_PROTO_HEADER_SIZE, payload, len);
    }

    /* Calculate CRC */
    uint16_t crc = Server_CRC16(frame + 1, EMU_PROTO_HEADER_SIZE - 1 + len);
    frame[frame_len - 2] = (uint8_t)(crc & 0xFF);
    frame[frame_len - 1] = (uint8_t)(crc >> 8);

    /* Send */
    int sent = send(server.clients[client_idx].socket, (char*)frame, (int)frame_len, 0);
    if (sent > 0) {
        server.stats.messages_tx++;
    }

    return sent;
}

static uint16_t Server_CRC16(const uint8_t* data, size_t len)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

static void Server_BuildTelemetry(uint8_t* buffer, size_t* len)
{
    PMU_Emulator_t* emu = PMU_Emu_GetState();
    size_t offset = 0;

    /*
     * Standard PMU telemetry format (174 bytes) - matches configurator's parse_telemetry():
     * - timestamp_ms (4 bytes)
     * - voltage_mv (2 bytes)
     * - temperature_c (2 bytes, signed)
     * - total_current_ma (4 bytes)
     * - adc_values (40 bytes, 20 x uint16)
     * - profet_states (30 bytes)
     * - profet_duties (60 bytes, 30 x uint16)
     * - hbridge_states (4 bytes)
     * - hbridge_positions (8 bytes, 4 x uint16)
     * - board_temp_2 (2 bytes, signed)
     * - 5v_output_mv (2 bytes)
     * - 3v3_output_mv (2 bytes)
     * - flash_temp (2 bytes, signed)
     * - system_status (4 bytes)
     * - fault_flags (4 bytes)
     * - digital_inputs (4 bytes, bitmask for 20 inputs)
     * Total: 174 bytes
     */

    /* 1. timestamp_ms (4 bytes) */
    uint32_t timestamp = emu->tick_ms;
    memcpy(buffer + offset, &timestamp, 4);
    offset += 4;

    /* 2. voltage_mv (2 bytes) */
    int32_t voltage_val = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    uint16_t voltage = (voltage_val > 0) ? (uint16_t)voltage_val : emu->protection.battery_voltage_mV;
    memcpy(buffer + offset, &voltage, 2);
    offset += 2;

    /* 3. temperature_c (2 bytes, signed) */
    int32_t temp_val = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_L);
    int16_t temp = (temp_val != 0) ? (int16_t)temp_val : emu->protection.board_temp_L_C;
    memcpy(buffer + offset, &temp, 2);
    offset += 2;

    /* 4. total_current_ma (4 bytes) */
    uint32_t total_current = emu->protection.total_current_mA;
    memcpy(buffer + offset, &total_current, 4);
    offset += 4;

    /* 5. adc_values (40 bytes, 20 x uint16) */
    for (int i = 0; i < 20; i++) {
        uint16_t adc = emu->adc[i].raw_value << 2;  /* 10-bit to 12-bit */
        memcpy(buffer + offset, &adc, 2);
        offset += 2;
    }

    /* 6. profet_states (30 bytes) */
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        buffer[offset++] = profet ? profet->state : emu->profet[i].state;
    }

    /* 7. profet_duties (60 bytes, 30 x uint16) */
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        uint16_t duty = profet ? profet->pwm_duty : emu->profet[i].pwm_duty;
        memcpy(buffer + offset, &duty, 2);
        offset += 2;
    }

    /* 8. hbridge_states (4 bytes) */
    for (int i = 0; i < 4; i++) {
        buffer[offset++] = emu->hbridge[i].state;
    }

    /* 9. hbridge_positions (8 bytes, 4 x uint16) */
    for (int i = 0; i < 4; i++) {
        uint16_t pos = emu->hbridge[i].position;
        memcpy(buffer + offset, &pos, 2);
        offset += 2;
    }

    /* 10. board_temp_2 (2 bytes, signed) */
    int16_t board_temp_2 = emu->protection.board_temp_R_C;
    memcpy(buffer + offset, &board_temp_2, 2);
    offset += 2;

    /* 11. 5v_output_mv (2 bytes) */
    uint16_t output_5v = emu->protection.output_5v_mV;
    memcpy(buffer + offset, &output_5v, 2);
    offset += 2;

    /* 12. 3v3_output_mv (2 bytes) */
    uint16_t output_3v3 = emu->protection.output_3v3_mV;
    memcpy(buffer + offset, &output_3v3, 2);
    offset += 2;

    /* 13. flash_temp (2 bytes, signed) */
    int16_t flash_temp = emu->flash_temp_C;
    memcpy(buffer + offset, &flash_temp, 2);
    offset += 2;

    /* 14. system_status (4 bytes) */
    uint32_t system_status = emu->protection.system_status;
    memcpy(buffer + offset, &system_status, 4);
    offset += 4;

    /* 15. fault_flags (4 bytes) */
    uint32_t fault_flags = emu->protection.fault_flags;
    memcpy(buffer + offset, &fault_flags, 4);
    offset += 4;

    /* 16. digital_inputs (4 bytes, bitmask for 20 inputs) */
    /* Digital inputs are SEPARATE GPIO pins from analog ADC inputs!
     * Read directly from emulator's digital_inputs[] state. */
    uint32_t di_states = 0;
    for (int i = 0; i < 20; i++) {
        const PMU_Emu_Digital_Input_t* di = PMU_Emu_DI_GetChannel((uint8_t)i);
        if (di != NULL && di->debounced_state) {
            di_states |= (1U << i);
        }
    }
    memcpy(buffer + offset, &di_states, 4);
    offset += 4;

    /* === Extended: Virtual Channels (logic, timer, switch, number, etc.) === */
    /* Format:
     * - virtual_channel_count (2 bytes)
     * - For each virtual channel:
     *   - channel_id (2 bytes)
     *   - value (4 bytes, int32)
     */

    /* Get list of all registered virtual channels */
    PMU_Channel_t channels[64];
    uint16_t channel_count = PMU_Channel_List(channels, 64);

    /* Count virtual channels (ID >= 200) */
    uint16_t virtual_count = 0;
    for (uint16_t i = 0; i < channel_count; i++) {
        if (channels[i].channel_id >= PMU_CHANNEL_ID_VIRTUAL_START &&
            channels[i].channel_id <= PMU_CHANNEL_ID_VIRTUAL_END) {
            virtual_count++;
        }
    }

    /* Write virtual channel count */
    memcpy(buffer + offset, &virtual_count, 2);
    offset += 2;

    /* Debug: print virtual channel info periodically */
    static uint32_t debug_counter = 0;
    if (++debug_counter % 500 == 1) {
        printf("[TELEM] Virtual channels: count=%d (total registered=%d)\n", virtual_count, channel_count);
        for (uint16_t i = 0; i < channel_count; i++) {
            if (channels[i].channel_id >= PMU_CHANNEL_ID_VIRTUAL_START &&
                channels[i].channel_id <= PMU_CHANNEL_ID_VIRTUAL_END) {
                printf("  [%d] '%s' = %d\n", channels[i].channel_id, channels[i].name, channels[i].value);
            }
        }
    }

    /* Write each virtual channel: id (2 bytes) + value (4 bytes) */
    for (uint16_t i = 0; i < channel_count && offset < 500; i++) {
        if (channels[i].channel_id >= PMU_CHANNEL_ID_VIRTUAL_START &&
            channels[i].channel_id <= PMU_CHANNEL_ID_VIRTUAL_END) {
            /* Channel ID */
            uint16_t ch_id = channels[i].channel_id;
            memcpy(buffer + offset, &ch_id, 2);
            offset += 2;

            /* Channel value */
            int32_t ch_value = channels[i].value;
            memcpy(buffer + offset, &ch_value, 4);
            offset += 4;
        }
    }

    *len = offset;  /* 174 bytes + 2 + (virtual_count * 6) */
}

/**
 * @brief Apply configuration JSON to emulator using firmware's JSON parser
 * @param json JSON string
 * @param len JSON length
 * @return 0 on success, -1 on error
 */
static int Server_ApplyConfig(const char* json, size_t len)
{
    if (!json || len == 0) {
        return -1;
    }

    LOG_SERVER("Applying configuration (%zu bytes) using firmware parser...", len);

    /* Initialize JSON loader */
    PMU_JSON_Init();

    /* Use firmware's JSON parser */
    PMU_JSON_LoadStats_t stats = {0};
    PMU_JSON_Status_t result = PMU_JSON_LoadFromString(json, (uint32_t)len, &stats);

    if (result != PMU_JSON_OK) {
        const char* error = PMU_JSON_GetLastError();
        LOG_SERVER("JSON parse error: %s", error ? error : "unknown");
        EMU_WebUI_SendLog(3, "config", error ? error : "JSON parse error");
        printf("\n");
        printf("+============================================================+\n");
        printf("|          CONFIGURATION LOAD FAILED                         |\n");
        printf("+============================================================+\n");
        printf("|  Error: %-50s |\n", error ? error : "Parse error");
        printf("+============================================================+\n");
        printf("\n");
        return -1;
    }

    /* Store stats globally */
    memcpy(&last_config_stats, &stats, sizeof(PMU_JSON_LoadStats_t));
    config_loaded = true;

    /* Store config JSON for download */
    if (last_config_json) {
        free(last_config_json);
    }
    last_config_json = (char*)malloc(len + 1);
    if (last_config_json) {
        memcpy(last_config_json, json, len);
        last_config_json[len] = '\0';
        last_config_size = len;
    }

    /* Send success to WebUI log */
    {
        char log_msg[128];
        snprintf(log_msg, sizeof(log_msg), "Config loaded: %lu channels, %lu CAN msgs, %lu Lua scripts",
                 (unsigned long)stats.total_channels, (unsigned long)stats.can_messages, (unsigned long)stats.lua_scripts);
        EMU_WebUI_SendLog(1, "config", log_msg);
    }

    /* Save config to file for reference */
    FILE* f = fopen("last_config.json", "w");
    if (f) {
        fwrite(json, 1, len, f);
        fclose(f);
        LOG_SERVER("Config saved to last_config.json");
    }

    /* Print success with statistics */
    printf("\n");
    printf("+============================================================+\n");
    printf("|          CONFIGURATION LOADED FROM CONFIGURATOR            |\n");
    printf("+============================================================+\n");
    printf("|  Total Channels:    %-5lu                                  |\n", (unsigned long)stats.total_channels);
    printf("|    - Digital Inputs: %-5lu                                 |\n", (unsigned long)stats.digital_inputs);
    printf("|    - Analog Inputs:  %-5lu                                 |\n", (unsigned long)stats.analog_inputs);
    printf("|    - Power Outputs:  %-5lu                                 |\n", (unsigned long)stats.power_outputs);
    printf("|    - Logic Functions:%-5lu                                 |\n", (unsigned long)stats.logic_functions);
    printf("|    - CAN RX:         %-5lu                                 |\n", (unsigned long)stats.can_rx);
    printf("|    - CAN TX:         %-5lu                                 |\n", (unsigned long)stats.can_tx);
    printf("|  CAN Messages:      %-5lu                                  |\n", (unsigned long)stats.can_messages);
    printf("|  Lua Scripts:       %-5lu                                  |\n", (unsigned long)stats.lua_scripts);
    printf("|  CAN Stream:        %-5s                                  |\n", stats.stream_enabled ? "ON" : "OFF");
    printf("|  Parse Time:        %-5lu ms                               |\n", (unsigned long)stats.parse_time_ms);
    printf("|  Config saved to:   last_config.json                       |\n");
    printf("+============================================================+\n");
    printf("\n");

    return 0;
}

int EMU_Server_LoadConfig(const char* filename)
{
    const char* config_file = filename ? filename : "last_config.json";

    /* Try to open the config file */
    FILE* f = fopen(config_file, "rb");
    if (!f) {
        printf("[CONFIG] No saved config found: %s\n", config_file);
        return -1;
    }

    /* Get file size */
    fseek(f, 0, SEEK_END);
    long file_size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (file_size <= 0 || file_size > 100 * 1024) {
        fclose(f);
        printf("[CONFIG] Invalid config file size: %ld bytes\n", file_size);
        return -1;
    }

    /* Allocate buffer */
    char* json_buffer = (char*)malloc(file_size + 1);
    if (!json_buffer) {
        fclose(f);
        printf("[CONFIG] Failed to allocate memory for config\n");
        return -1;
    }

    /* Read file */
    size_t bytes_read = fread(json_buffer, 1, file_size, f);
    fclose(f);

    if (bytes_read != (size_t)file_size) {
        free(json_buffer);
        printf("[CONFIG] Failed to read config file\n");
        return -1;
    }

    json_buffer[file_size] = '\0';

    /* Apply configuration using firmware parser */
    printf("[CONFIG] Loading saved configuration from %s (%ld bytes)...\n", config_file, file_size);

    PMU_JSON_Init();
    PMU_JSON_LoadStats_t stats = {0};
    PMU_JSON_Status_t result = PMU_JSON_LoadFromString(json_buffer, (uint32_t)file_size, &stats);

    free(json_buffer);

    if (result != PMU_JSON_OK) {
        const char* error = PMU_JSON_GetLastError();
        printf("[CONFIG] Failed to parse saved config: %s\n", error ? error : "unknown error");
        return -1;
    }

    printf("\n");
    printf("+============================================================+\n");
    printf("|          SAVED CONFIGURATION LOADED                        |\n");
    printf("+============================================================+\n");
    printf("|  Channels: %-5lu    CAN Messages: %-5lu                    |\n",
           (unsigned long)stats.total_channels, (unsigned long)stats.can_messages);
    printf("|  Lua Scripts: %-5lu                                        |\n",
           (unsigned long)stats.lua_scripts);
    printf("+============================================================+\n");
    printf("\n");

    return 0;
}

void EMU_Server_SendLog(uint8_t level, const char* source, const char* message)
{
    if (!server.running) {
        return;
    }

    size_t source_len = source ? strlen(source) : 0;
    size_t msg_len = message ? strlen(message) : 0;

    if (source_len > 32) source_len = 32;
    if (msg_len > 200) msg_len = 200;

    /* Log message format:
     * [0] level (1 byte)
     * [1] source_len (1 byte)
     * [2..source_len+1] source string
     * [source_len+2] message_len (1 byte)
     * [source_len+3..] message string
     */
    uint8_t buffer[256];
    size_t offset = 0;

    buffer[offset++] = level;
    buffer[offset++] = (uint8_t)source_len;
    if (source_len > 0) {
        memcpy(buffer + offset, source, source_len);
        offset += source_len;
    }
    buffer[offset++] = (uint8_t)msg_len;
    if (msg_len > 0) {
        memcpy(buffer + offset, message, msg_len);
        offset += msg_len;
    }

    /* Send to all connected clients */
    for (int i = 0; i < EMU_SERVER_MAX_CLIENTS; i++) {
        if (server.clients[i].active) {
            Server_SendResponse(i, EMU_MSG_LOG, buffer, (uint16_t)offset);
        }
    }
}

/* Accessor functions for config stats */
bool EMU_Server_IsConfigLoaded(void)
{
    return config_loaded;
}

const PMU_JSON_LoadStats_t* EMU_Server_GetConfigStats(void)
{
    return config_loaded ? &last_config_stats : NULL;
}

const char* EMU_Server_GetConfigJSON(size_t* out_size)
{
    if (out_size) {
        *out_size = last_config_size;
    }
    return last_config_json;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
