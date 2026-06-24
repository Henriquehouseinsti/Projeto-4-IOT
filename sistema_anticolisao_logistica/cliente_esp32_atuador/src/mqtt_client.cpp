#include <Arduino.h>
#include <WiFi.h>
#include "mqtt_client.h"
#include "include/hardware_ctrl.h"
#include "include/config.h"

extern WiFiClient espClient; // Instanciado no main.cpp
PubSubClient mqttClient(espClient);
unsigned long ultimo_heartbeat = 0;

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    String topico_recebido = String(topic);

    if (topico_recebido == TOPIC_HEARTBEAT) {
        ultimo_heartbeat = millis();
        if (estado_atual == ESTADO_EMERGENCIA && msg == "ok") {
            setModoNormal();
        }
    } 
    else if (topico_recebido == TOPIC_ALERTA) {
        if (msg == "RISCO_VERMELHO") setModoEmergencia();
        else if (msg == "RISCO_AMARELO") setAlertaAmarelo();
        else if (msg == "SEGURO") setModoNormal();
    }
}

void setupMQTT() {
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void reconectarMQTT() {
    if (!mqttClient.connected()) {
        Serial.print("Reconectando MQTT...");
        String clientId = "ESP32-Atuador-" + String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("OK");
            mqttClient.subscribe(TOPIC_ALERTA);
            mqttClient.subscribe(TOPIC_HEARTBEAT);
        } else {
            Serial.println("Falha.");
        }
    }
}

void handleMQTT() {
    if (!mqttClient.connected()) {
        reconectarMQTT();
    } else {
        mqttClient.loop();
    }
}