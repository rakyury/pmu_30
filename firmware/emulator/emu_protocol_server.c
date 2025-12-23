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

    LOG_SERVER("RX msg 0x%02X, len %d", msg_type, len);

    /* Send protocol command to WebUI log */
    {
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
            FILE* f = fopen(config_file, "rb");

            if (!f) {
                /* No config file - send empty config */
                LOG_SERVER("GET_CONFIG: No config file found, sending empty config");
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

    /* Timestamp/Uptime (4 bytes) - use uptime_seconds * 1000 for more accurate display */
    uint32_t uptime_ms = emu->uptime_seconds * 1000 + (emu->tick_ms % 1000);
    memcpy(buffer + offset, &uptime_ms, 4);
    offset += 4;

    /* Voltage (2 bytes) - from system channel or emulator */
    int32_t voltage_val = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    uint16_t voltage = (voltage_val > 0) ? (uint16_t)voltage_val : emu->protection.battery_voltage_mV;
    memcpy(buffer + offset, &voltage, 2);
    offset += 2;

    /* Temperature (2 bytes, signed) - Board temp Left from emulator */
    int32_t temp_val = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_L);
    int16_t temp = (temp_val != 0) ? (int16_t)temp_val : emu->protection.board_temp_L_C;
    memcpy(buffer + offset, &temp, 2);
    offset += 2;

    /* Total current (4 bytes) - from system channel or emulator */
    int32_t current_val = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    uint32_t current = (current_val > 0) ? (uint32_t)current_val : emu->protection.total_current_mA;
    memcpy(buffer + offset, &current, 4);
    offset += 4;

    /* ADC values (20 x 2 bytes) - from firmware channels if available */
    for (int i = 0; i < 20; i++) {
        int32_t ch_val = PMU_Channel_GetValue(i);  /* Channels 0-19 are inputs */
        uint16_t adc = (ch_val != 0) ? (uint16_t)ch_val : emu->adc[i].raw_value;
        memcpy(buffer + offset, &adc, 2);
        offset += 2;
    }

    /* PROFET states (30 x 1 byte) - from firmware PROFET module */
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        if (profet) {
            buffer[offset++] = profet->state;
        } else {
            buffer[offset++] = emu->profet[i].state;
        }
    }

    /* PROFET duties (30 x 2 bytes) - from firmware PROFET module */
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(i);
        uint16_t duty;
        if (profet) {
            duty = profet->pwm_duty;
        } else {
            duty = emu->profet[i].pwm_duty;
        }
        memcpy(buffer + offset, &duty, 2);
        offset += 2;
    }

    /* H-Bridge states (4 x 1 byte) */
    for (int i = 0; i < 4; i++) {
        int32_t ch_val = PMU_Channel_GetValue(130 + i);  /* Channels 130-133 are H-bridges */
        if (ch_val != 0) {
            buffer[offset++] = (ch_val > 0) ? 1 : 0;
        } else {
            buffer[offset++] = emu->hbridge[i].state;
        }
    }

    /* H-Bridge positions (4 x 2 bytes) */
    for (int i = 0; i < 4; i++) {
        uint16_t pos = emu->hbridge[i].position;
        memcpy(buffer + offset, &pos, 2);
        offset += 2;
    }

    /* Extended system fields (16 bytes) */

    /* Board temperature Right (2 bytes, signed) - ECUMaster: boardTemperatureR */
    int16_t temp_r = emu->protection.board_temp_R_C;
    memcpy(buffer + offset, &temp_r, 2);
    offset += 2;

    /* 5V output (2 bytes) - from emulator state */
    uint16_t v5_out = emu->protection.output_5v_mV;
    memcpy(buffer + offset, &v5_out, 2);
    offset += 2;

    /* 3.3V output (2 bytes) - from emulator state */
    uint16_t v33_out = emu->protection.output_3v3_mV;
    memcpy(buffer + offset, &v33_out, 2);
    offset += 2;

    /* Flash temperature (2 bytes, signed) - simulate as board_temp_L - 5 */
    int16_t flash_temp = emu->protection.board_temp_L_C - 5;
    memcpy(buffer + offset, &flash_temp, 2);
    offset += 2;

    /* System status (4 bytes) - bit flags (ECUMaster compatible) */
    uint32_t sys_status = emu->protection.system_status;
    /* Bit 0: reset detector */
    /* Bit 1: user error */
    sys_status |= (emu->protection.user_error ? 0x02 : 0);
    /* Bit 2: is turning off */
    sys_status |= (emu->protection.is_turning_off ? 0x04 : 0);
    memcpy(buffer + offset, &sys_status, 4);
    offset += 4;

    /* Fault flags (4 bytes) - from emulator protection state */
    uint32_t faults = emu->protection.fault_flags;
    memcpy(buffer + offset, &faults, 4);
    offset += 4;

    *len = offset;  /* Should be 170 bytes */
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
