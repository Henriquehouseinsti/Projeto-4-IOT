#include <Arduino.h>
#include <WiFi.h>
#include "config.h"
#include "hardware_ctrl.h"
#include "network.h"
#include "mqtt_client.h"

WiFiClient espClient; // Cliente global para o MQTT usar

void setup() {
    Serial.begin(115200);
    
    // 1. Inicializa pinos (já entra em estado de emergência físico)
    initHardware();
    
    // 2. Conecta na rede
    setupWiFi();
    
    // 3. Configura o Broker
    setupMQTT();
    
    ultimo_heartbeat = millis();
}

void loop() {
    // 1. Mantém as conexões ativas
    checkWiFi();
    handleMQTT();
    
    // 2. Avalia o Watchdog de Segurança (Heartbeat)
    if (millis() - ultimo_heartbeat > TIMEOUT_HEARTBEAT_MS) {
        if (estado_atual != ESTADO_EMERGENCIA) {
            Serial.println("[ALERTA] Heartbeat perdido. Modo seguro ativado.");
            setModoEmergencia();
        }
    }
    
    // 3. Processa a máquina de estados física (Buzzer, LEDs)
    processarHardware();
}