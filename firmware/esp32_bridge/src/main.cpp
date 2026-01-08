/**
 * @file main.cpp
 * @brief PMU-30 WiFi Bridge with WebSocket Telemetry Dashboard
 *
 * ESP32 acts as a transparent SerialTransfer bridge:
 * - Forwards UART <-> TCP bidirectionally (same protocol as USB)
 * - WebSocket server pushes telemetry JSON to web clients
 * - Web dashboard displays real-time output, input, and variable states
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiAP.h>
#include <ESPmDNS.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

// =============================================================================
// Configuration
// =============================================================================

#ifndef WIFI_AP_SSID
#define WIFI_AP_SSID "PMU30-BRIDGE"
#endif

#ifndef WIFI_AP_PASS
#define WIFI_AP_PASS "pmu30wifi"
#endif

#ifndef TCP_PORT
#define TCP_PORT 8266
#endif

#ifndef WS_PORT
#define WS_PORT 81
#endif

// UART pins for Nucleo connection
#define NUCLEO_UART_RX 25  // ESP32 RX <- Nucleo TX (PA9)
#define NUCLEO_UART_TX 26  // ESP32 TX -> Nucleo RX (PA10)
#define NUCLEO_UART_BAUD 115200

// Telemetry packet structure offsets
#define TELEM_OFFSET_STREAM_COUNTER  0
#define TELEM_OFFSET_TIMESTAMP       4
#define TELEM_OFFSET_OUTPUTS         8   // 30 bytes
#define TELEM_OFFSET_ADC             38  // 40 bytes (20 x uint16)
#define TELEM_OFFSET_DIN             78  // 1 byte bitmask
#define TELEM_OFFSET_UPTIME          79  // 4 bytes
#define TELEM_OFFSET_VIRT_COUNT      104 // 2 bytes
#define TELEM_OFFSET_VIRT_DATA       106 // 6 bytes per channel

#define TELEM_MIN_SIZE 106
#define TELEM_PACKET_ID 0x22  // DATA command ID

// =============================================================================
// Global Objects
// =============================================================================

// UART to Nucleo
HardwareSerial NucleoSerial(2);

// WiFi TCP server for SerialTransfer protocol
WiFiServer tcpServer(TCP_PORT);
WiFiClient tcpClient;

// Async WebSocket server for real-time dashboard
AsyncWebServer httpServer(80);
AsyncWebSocket ws("/ws");

// Status LED
#define LED_PIN 2

// Statistics
static uint32_t bytesFromNucleo = 0;
static uint32_t bytesFromTcp = 0;
static uint32_t tcpConnections = 0;
static uint32_t wsConnections = 0;
static uint32_t startTime = 0;
static uint32_t lastWsUpdate = 0;
static uint32_t telemetryPackets = 0;

// Telemetry parsing state
static uint8_t rxBuffer[512];
static uint16_t rxIndex = 0;
static bool inFrame = false;
static uint8_t lastTelemetry[256];
static uint16_t lastTelemetryLen = 0;

// Configuration info (parsed from GET_CONFIG response)
static uint16_t configChannelCount = 0;
static bool configLoaded = false;

// =============================================================================
// Telemetry Parser
// =============================================================================

/**
 * @brief Parse MIN protocol frame from UART stream
 *
 * MIN frame format: [0xAA 0xAA 0xAA] [ID] [LEN] [PAYLOAD...] [CRC32] [0x55]
 * We sniff DATA packets (0x22) for telemetry display
 */
bool parseMinFrame(uint8_t byte)
{
    static uint8_t headerCount = 0;
    static uint8_t frameId = 0;
    static uint8_t payloadLen = 0;
    static uint16_t payloadIdx = 0;
    static bool gotId = false;
    static bool gotLen = false;

    // Detect 0xAA header sequence
    if (byte == 0xAA) {
        headerCount++;
        if (headerCount >= 3) {
            // Start of new frame
            inFrame = true;
            rxIndex = 0;
            gotId = false;
            gotLen = false;
            payloadIdx = 0;
            return false;
        }
    } else {
        headerCount = 0;
    }

    if (!inFrame) return false;

    // Handle byte stuffing: 0x55 after two 0xAA means stuffed byte
    // For simplicity, we just collect bytes until EOF (0x55)

    if (byte == 0x55 && rxIndex > 5) {
        // Possible end of frame
        // Frame: [ID] [LEN] [PAYLOAD] [CRC32]
        if (rxIndex >= 6) {
            uint8_t id = rxBuffer[0];
            uint8_t len = rxBuffer[1];

            // Check if this is a DATA packet (0x22)
            if (id == TELEM_PACKET_ID && len >= TELEM_MIN_SIZE && rxIndex >= len + 6) {
                // Copy telemetry payload (skip ID, LEN, and CRC32)
                memcpy(lastTelemetry, &rxBuffer[2], len);
                lastTelemetryLen = len;
                telemetryPackets++;
                inFrame = false;
                return true;
            }

            // Check for CONFIG_DATA (0x11) to detect config info
            if (id == 0x11 && len >= 4) {
                // Parse channel count from config header
                configChannelCount = rxBuffer[4] | (rxBuffer[5] << 8);
                configLoaded = true;
            }
        }
        inFrame = false;
        return false;
    }

    // Store byte
    if (rxIndex < sizeof(rxBuffer)) {
        rxBuffer[rxIndex++] = byte;
    } else {
        // Buffer overflow, reset
        inFrame = false;
    }

    return false;
}

// =============================================================================
// WebSocket Telemetry Sender
// =============================================================================

void sendTelemetryToWs()
{
    if (lastTelemetryLen < TELEM_MIN_SIZE) return;
    if (ws.count() == 0) return;  // No clients connected

    // Parse telemetry packet
    uint32_t streamCounter = *(uint32_t*)&lastTelemetry[TELEM_OFFSET_STREAM_COUNTER];
    uint32_t timestamp = *(uint32_t*)&lastTelemetry[TELEM_OFFSET_TIMESTAMP];
    uint32_t uptime = *(uint32_t*)&lastTelemetry[TELEM_OFFSET_UPTIME];
    uint8_t digitalInputs = lastTelemetry[TELEM_OFFSET_DIN];
    uint16_t virtCount = *(uint16_t*)&lastTelemetry[TELEM_OFFSET_VIRT_COUNT];

    // Build JSON
    JsonDocument doc;
    doc["type"] = "telemetry";
    doc["stream"] = streamCounter;
    doc["timestamp"] = timestamp;
    doc["uptime"] = uptime;
    doc["packets"] = telemetryPackets;

    // Output states (30 channels)
    JsonArray outputs = doc["outputs"].to<JsonArray>();
    for (int i = 0; i < 30; i++) {
        outputs.add(lastTelemetry[TELEM_OFFSET_OUTPUTS + i]);
    }

    // Digital inputs (8 bits)
    JsonArray dins = doc["dins"].to<JsonArray>();
    for (int i = 0; i < 8; i++) {
        dins.add((digitalInputs >> i) & 1);
    }

    // ADC values (20 channels, uint16)
    JsonArray adcs = doc["adcs"].to<JsonArray>();
    for (int i = 0; i < 20; i++) {
        uint16_t val = *(uint16_t*)&lastTelemetry[TELEM_OFFSET_ADC + i * 2];
        adcs.add(val);
    }

    // Virtual channels
    if (virtCount > 0 && virtCount <= 16 && lastTelemetryLen >= TELEM_OFFSET_VIRT_DATA + virtCount * 6) {
        JsonArray virts = doc["virtuals"].to<JsonArray>();
        for (int i = 0; i < virtCount; i++) {
            uint16_t chId = *(uint16_t*)&lastTelemetry[TELEM_OFFSET_VIRT_DATA + i * 6];
            int32_t value = *(int32_t*)&lastTelemetry[TELEM_OFFSET_VIRT_DATA + i * 6 + 2];
            JsonObject v = virts.add<JsonObject>();
            v["id"] = chId;
            v["value"] = value;
        }
    }

    // Config info
    doc["configChannels"] = configChannelCount;
    doc["configLoaded"] = configLoaded;

    // Serialize and send to all WebSocket clients
    String json;
    serializeJson(doc, json);
    ws.textAll(json);
}

// =============================================================================
// WebSocket Event Handler
// =============================================================================

void onWsEvent(AsyncWebSocket* server, AsyncWebSocketClient* client,
               AwsEventType type, void* arg, uint8_t* data, size_t len)
{
    if (type == WS_EVT_CONNECT) {
        wsConnections++;
        Serial.printf("[WS] Client #%u connected from %s\n",
                     client->id(), client->remoteIP().toString().c_str());
    } else if (type == WS_EVT_DISCONNECT) {
        Serial.printf("[WS] Client #%u disconnected\n", client->id());
    }
}

// =============================================================================
// Web Dashboard HTML
// =============================================================================

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PMU-30 Dashboard</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #333;
}
.header h1 {
    color: #00ff88;
    font-size: 20px;
    font-weight: 600;
}
.status {
    display: flex;
    gap: 20px;
    font-size: 12px;
}
.status-item {
    display: flex;
    align-items: center;
    gap: 5px;
}
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #666;
}
.status-dot.connected { background: #00ff88; }
.status-dot.streaming { background: #00ccff; animation: pulse 1s infinite; }
@keyframes pulse { 50% { opacity: 0.5; } }

.container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 15px;
    padding: 15px;
}

.panel {
    background: #111118;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    overflow: hidden;
}
.panel-header {
    background: #1a1a2a;
    padding: 10px 15px;
    font-size: 13px;
    font-weight: 600;
    color: #00ccff;
    border-bottom: 1px solid #2a2a3a;
    display: flex;
    justify-content: space-between;
}
.panel-count {
    color: #888;
    font-weight: normal;
}
.panel-body {
    padding: 10px;
    max-height: 300px;
    overflow-y: auto;
}

/* Output Grid */
.output-grid {
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 4px;
}
.output-cell {
    aspect-ratio: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    transition: all 0.2s;
}
.output-cell.on { background: #004400; border-color: #00ff88; color: #00ff88; }
.output-cell.fault { background: #440000; border-color: #ff4444; color: #ff4444; }
.output-cell.pwm { background: #002244; border-color: #00aaff; color: #00aaff; }

/* Digital Inputs Grid */
.din-grid {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 6px;
}
.din-cell {
    padding: 15px 10px;
    text-align: center;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 4px;
    transition: all 0.2s;
}
.din-cell.active { background: #003344; border-color: #00ccff; }
.din-label { font-size: 11px; color: #888; }
.din-value { font-size: 16px; font-weight: bold; margin-top: 5px; }
.din-cell.active .din-value { color: #00ccff; }

/* ADC Table */
.adc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.adc-table th, .adc-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #222;
    text-align: left;
}
.adc-table th { color: #888; font-weight: normal; }
.adc-table td:last-child { text-align: right; font-family: monospace; }
.adc-bar {
    height: 4px;
    background: #333;
    border-radius: 2px;
    overflow: hidden;
}
.adc-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #00ccff, #00ff88);
    transition: width 0.2s;
}

/* Virtual Channels Table */
.virt-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.virt-table th, .virt-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #222;
    text-align: left;
}
.virt-table th { color: #888; font-weight: normal; }
.virt-table .ch-id { color: #00ccff; font-family: monospace; }
.virt-table .ch-value { font-family: monospace; font-weight: bold; }
.virt-table .ch-value.active { color: #00ff88; }
.virt-table .ch-value.zero { color: #666; }

/* System Info */
.info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}
.info-item {
    background: #1a1a1a;
    padding: 12px;
    border-radius: 4px;
}
.info-label { font-size: 11px; color: #888; margin-bottom: 4px; }
.info-value { font-size: 16px; font-weight: bold; font-family: monospace; }
.info-value.highlight { color: #00ff88; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #111; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #444; }
</style>
</head>
<body>
<div class="header">
    <h1>PMU-30 WiFi Dashboard</h1>
    <div class="status">
        <div class="status-item">
            <div class="status-dot" id="wsStatus"></div>
            <span id="wsText">Connecting...</span>
        </div>
        <div class="status-item">
            <div class="status-dot" id="streamStatus"></div>
            <span id="streamText">No data</span>
        </div>
    </div>
</div>

<div class="container">
    <!-- Outputs Panel -->
    <div class="panel">
        <div class="panel-header">
            Power Outputs
            <span class="panel-count" id="outputCount">0/30 active</span>
        </div>
        <div class="panel-body">
            <div class="output-grid" id="outputGrid"></div>
        </div>
    </div>

    <!-- Digital Inputs Panel -->
    <div class="panel">
        <div class="panel-header">
            Digital Inputs
            <span class="panel-count" id="dinCount">0/8 active</span>
        </div>
        <div class="panel-body">
            <div class="din-grid" id="dinGrid"></div>
        </div>
    </div>

    <!-- ADC Panel -->
    <div class="panel">
        <div class="panel-header">
            Analog Inputs
            <span class="panel-count">20 channels</span>
        </div>
        <div class="panel-body">
            <table class="adc-table" id="adcTable"></table>
        </div>
    </div>

    <!-- Virtual Channels Panel -->
    <div class="panel">
        <div class="panel-header">
            Virtual Channels
            <span class="panel-count" id="virtCount">0 channels</span>
        </div>
        <div class="panel-body">
            <table class="virt-table" id="virtTable"></table>
        </div>
    </div>

    <!-- System Info Panel -->
    <div class="panel">
        <div class="panel-header">System Info</div>
        <div class="panel-body">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Stream Counter</div>
                    <div class="info-value" id="infoStream">-</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Device Uptime</div>
                    <div class="info-value highlight" id="infoUptime">-</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Telemetry Packets</div>
                    <div class="info-value" id="infoPackets">-</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Config Channels</div>
                    <div class="info-value" id="infoConfig">-</div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Initialize grids
function initGrids() {
    // Output grid (30 outputs)
    const outGrid = document.getElementById('outputGrid');
    for (let i = 1; i <= 30; i++) {
        const cell = document.createElement('div');
        cell.className = 'output-cell';
        cell.id = 'out' + i;
        cell.textContent = i;
        outGrid.appendChild(cell);
    }

    // Digital input grid (8 inputs)
    const dinGrid = document.getElementById('dinGrid');
    for (let i = 1; i <= 8; i++) {
        const cell = document.createElement('div');
        cell.className = 'din-cell';
        cell.id = 'din' + i;
        cell.innerHTML = '<div class="din-label">DIN' + i + '</div><div class="din-value">0</div>';
        dinGrid.appendChild(cell);
    }

    // ADC table (show first 10 by default)
    const adcTable = document.getElementById('adcTable');
    adcTable.innerHTML = '<tr><th>Channel</th><th>Level</th><th>Value</th></tr>';
    for (let i = 1; i <= 10; i++) {
        const row = document.createElement('tr');
        row.id = 'adc' + i;
        row.innerHTML = '<td>A' + i + '</td><td><div class="adc-bar"><div class="adc-bar-fill" style="width:0%"></div></div></td><td>0</td>';
        adcTable.appendChild(row);
    }
}

// Format uptime
function formatUptime(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return h + 'h ' + m + 'm ' + s + 's';
}

// Update display from telemetry
function updateTelemetry(data) {
    // Update outputs
    let activeCount = 0;
    for (let i = 0; i < 30; i++) {
        const cell = document.getElementById('out' + (i + 1));
        const state = data.outputs[i];
        cell.className = 'output-cell';
        if (state === 1) { cell.classList.add('on'); activeCount++; }
        else if (state === 2) { cell.classList.add('fault'); }
        else if (state === 6) { cell.classList.add('pwm'); activeCount++; }
    }
    document.getElementById('outputCount').textContent = activeCount + '/30 active';

    // Update digital inputs
    let dinActive = 0;
    for (let i = 0; i < 8; i++) {
        const cell = document.getElementById('din' + (i + 1));
        const val = data.dins[i];
        cell.className = 'din-cell' + (val ? ' active' : '');
        cell.querySelector('.din-value').textContent = val;
        if (val) dinActive++;
    }
    document.getElementById('dinCount').textContent = dinActive + '/8 active';

    // Update ADC values
    for (let i = 0; i < 10 && i < data.adcs.length; i++) {
        const row = document.getElementById('adc' + (i + 1));
        const val = data.adcs[i];
        const pct = Math.min(100, (val / 4095) * 100);
        row.querySelector('.adc-bar-fill').style.width = pct + '%';
        row.querySelector('td:last-child').textContent = val;
    }

    // Update virtual channels
    const virtTable = document.getElementById('virtTable');
    if (data.virtuals && data.virtuals.length > 0) {
        let html = '<tr><th>ID</th><th>Name</th><th>Value</th></tr>';
        for (const v of data.virtuals) {
            const isActive = v.value !== 0;
            html += '<tr><td class="ch-id">' + v.id + '</td><td>Channel ' + v.id + '</td>' +
                    '<td class="ch-value ' + (isActive ? 'active' : 'zero') + '">' + v.value + '</td></tr>';
        }
        virtTable.innerHTML = html;
        document.getElementById('virtCount').textContent = data.virtuals.length + ' channels';
    } else {
        virtTable.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#666">No virtual channels</td></tr>';
        document.getElementById('virtCount').textContent = '0 channels';
    }

    // Update system info
    document.getElementById('infoStream').textContent = data.stream;
    document.getElementById('infoUptime').textContent = formatUptime(data.uptime);
    document.getElementById('infoPackets').textContent = data.packets;
    document.getElementById('infoConfig').textContent = data.configChannels + (data.configLoaded ? '' : ' (no config)');

    // Update stream status
    document.getElementById('streamStatus').className = 'status-dot streaming';
    document.getElementById('streamText').textContent = 'Streaming @ ' + data.stream;
}

// WebSocket connection
let ws;
let reconnectTimer;
let lastPacketTime = 0;

function connect() {
    const wsUrl = 'ws://' + window.location.hostname + ':81/ws';
    console.log('Connecting to', wsUrl);

    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        console.log('WebSocket connected');
        document.getElementById('wsStatus').className = 'status-dot connected';
        document.getElementById('wsText').textContent = 'Connected';
    };

    ws.onmessage = function(evt) {
        try {
            const data = JSON.parse(evt.data);
            if (data.type === 'telemetry') {
                lastPacketTime = Date.now();
                updateTelemetry(data);
            }
        } catch (e) {
            console.error('Parse error:', e);
        }
    };

    ws.onclose = function() {
        console.log('WebSocket disconnected');
        document.getElementById('wsStatus').className = 'status-dot';
        document.getElementById('wsText').textContent = 'Disconnected';
        document.getElementById('streamStatus').className = 'status-dot';
        document.getElementById('streamText').textContent = 'No data';
        // Reconnect after 2 seconds
        reconnectTimer = setTimeout(connect, 2000);
    };

    ws.onerror = function(err) {
        console.error('WebSocket error:', err);
        ws.close();
    };
}

// Check for stale data
setInterval(function() {
    if (Date.now() - lastPacketTime > 2000) {
        document.getElementById('streamStatus').className = 'status-dot';
        document.getElementById('streamText').textContent = 'Stale';
    }
}, 1000);

// Initialize and connect
initGrids();
connect();
</script>
</body>
</html>
)rawliteral";

// =============================================================================
// HTTP Handlers
// =============================================================================

void handleRoot(AsyncWebServerRequest* request)
{
    request->send_P(200, "text/html", INDEX_HTML);
}

void handleStatus(AsyncWebServerRequest* request)
{
    String json = "{";
    json += "\"ip\":\"" + (WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : WiFi.softAPIP().toString()) + "\",";
    json += "\"port\":" + String(TCP_PORT) + ",";
    json += "\"uptime\":" + String((millis() - startTime) / 1000) + ",";
    json += "\"tcp_connected\":" + String((tcpClient && tcpClient.connected()) ? "true" : "false") + ",";
    json += "\"ws_clients\":" + String(ws.count()) + ",";
    json += "\"bytes_nucleo\":" + String(bytesFromNucleo) + ",";
    json += "\"bytes_tcp\":" + String(bytesFromTcp) + ",";
    json += "\"telemetry_packets\":" + String(telemetryPackets);
    json += "}";
    request->send(200, "application/json", json);
}

// =============================================================================
// Setup
// =============================================================================

void setup()
{
    // Debug serial (USB)
    Serial.begin(115200);
    delay(500);
    Serial.println("\n\n=== PMU-30 WiFi Bridge (WebSocket) ===");

    // Status LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);

    // UART to Nucleo
    NucleoSerial.begin(NUCLEO_UART_BAUD, SERIAL_8N1, NUCLEO_UART_RX, NUCLEO_UART_TX);
    Serial.printf("UART: RX=GPIO%d TX=GPIO%d @ %d baud\n",
                  NUCLEO_UART_RX, NUCLEO_UART_TX, NUCLEO_UART_BAUD);

    // Connect to WiFi
    const char* ssid = "0888";
    const char* password = "vseravno#22042008";

    Serial.printf("Connecting to WiFi: %s\n", ssid);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    int timeout = 30;
    while (WiFi.status() != WL_CONNECTED && timeout > 0) {
        delay(500);
        Serial.print(".");
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        timeout--;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n*** CONNECTED! ***");
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nFailed! Starting AP mode...");
        WiFi.mode(WIFI_AP);
        WiFi.softAP("PMU30-BRIDGE", "pmu30wifi");
        Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
    }

    // mDNS
    if (MDNS.begin("pmu30")) {
        Serial.println("mDNS: pmu30.local");
        MDNS.addService("http", "tcp", 80);
        MDNS.addService("pmu30", "tcp", TCP_PORT);
    }

    // TCP server for SerialTransfer protocol
    tcpServer.begin();
    Serial.printf("TCP Server: port %d\n", TCP_PORT);

    // WebSocket server
    ws.onEvent(onWsEvent);
    httpServer.addHandler(&ws);

    // HTTP routes
    httpServer.on("/", HTTP_GET, handleRoot);
    httpServer.on("/status", HTTP_GET, handleStatus);
    httpServer.begin();
    Serial.println("HTTP Server: port 80");
    Serial.printf("WebSocket: port %d\n", WS_PORT);

    // Print connection info
    Serial.println("\n*** DASHBOARD: ***");
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("  http://%s/\n", WiFi.localIP().toString().c_str());
        Serial.printf("  http://pmu30.local/\n");
    } else {
        Serial.printf("  http://%s/\n", WiFi.softAPIP().toString().c_str());
    }

    startTime = millis();
    digitalWrite(LED_PIN, LOW);
    Serial.println("\n=== Ready ===\n");
}

// =============================================================================
// Main Loop
// =============================================================================

void loop()
{
    // Clean up disconnected WebSocket clients
    ws.cleanupClients();

    // Check for new TCP clients
    if (!tcpClient || !tcpClient.connected()) {
        WiFiClient newClient = tcpServer.available();
        if (newClient) {
            tcpClient = newClient;
            tcpConnections++;
            Serial.printf("[+] TCP client: %s\n", tcpClient.remoteIP().toString().c_str());
            digitalWrite(LED_PIN, HIGH);
        }
    }

    // Bridge: UART -> TCP + Parse telemetry
    while (NucleoSerial.available()) {
        uint8_t byte = NucleoSerial.read();
        bytesFromNucleo++;

        // Forward to TCP client
        if (tcpClient && tcpClient.connected()) {
            tcpClient.write(byte);
        }

        // Parse for telemetry
        if (parseMinFrame(byte)) {
            // New telemetry packet received
        }
    }

    // Bridge: TCP -> UART
    if (tcpClient && tcpClient.connected()) {
        while (tcpClient.available()) {
            uint8_t byte = tcpClient.read();
            NucleoSerial.write(byte);
            bytesFromTcp++;
        }
    } else if (tcpClient) {
        Serial.println("[-] TCP client disconnected");
        tcpClient.stop();
        digitalWrite(LED_PIN, LOW);
    }

    // Send telemetry to WebSocket clients (10Hz max)
    uint32_t now = millis();
    if (now - lastWsUpdate >= 100) {
        lastWsUpdate = now;
        sendTelemetryToWs();
    }
}
