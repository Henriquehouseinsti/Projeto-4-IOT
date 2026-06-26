#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include "hardware_ctrl.h"
#include "mqtt_client.h"

WiFiClient espClient;

static void conectarWiFi() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Conectando ao Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.print("Wi-Fi conectado! IP: ");
    Serial.println(WiFi.localIP());
}

void setup() {
    Serial.begin(115200);
    delay(500);

    initHardware();
    conectarWiFi();
    setupMQTT();

    ultimo_heartbeat = millis();
}

void loop() {
    // Reconecta WiFi se cair
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Wi-Fi perdido. Reconectando...");
        conectarWiFi();
    }

    handleMQTT();

    // Watchdog: sem heartbeat por 1s = emergência
    if (millis() - ultimo_heartbeat > TIMEOUT_HEARTBEAT_MS) {
        if (estado_atual != ESTADO_EMERGENCIA) {
            Serial.println("[ALERTA] Heartbeat perdido. Modo seguro ativado.");
            setModoEmergencia();
        }
    }

    processarHardware();
}
