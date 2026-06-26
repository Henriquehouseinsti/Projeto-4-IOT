#include "Arduino.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include "mqtt_client.h"
#include "hardware_ctrl.h"
#include "config.h"

extern WiFiClient espClient;
static PubSubClient mqttClient(espClient);

unsigned long ultimo_heartbeat = 0;

static void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    String topico = String(topic);

    if (topico == TOPIC_HEARTBEAT) {
        ultimo_heartbeat = millis();
        if (msg == "ok" && estado_atual == ESTADO_EMERGENCIA) {
            setModoNormal();
        }
    } else if (topico == TOPIC_ALERTA) {
        if (msg == "RISCO_VERMELHO")      setModoEmergencia();
        else if (msg == "RISCO_AMARELO")  setAlertaAmarelo();
        else if (msg == "SEGURO")         setModoNormal();
    }
}

static void reconectarMQTT() {
    Serial.print("Conectando ao broker MQTT...");
    String clientId = "ESP32-Atuador-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
        Serial.println(" OK");
        mqttClient.subscribe(TOPIC_ALERTA);
        mqttClient.subscribe(TOPIC_HEARTBEAT);
    } else {
        Serial.print(" Falha, rc=");
        Serial.println(mqttClient.state());
    }
}

void setupMQTT() {
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void handleMQTT() {
    if (!mqttClient.connected()) {
        reconectarMQTT();
    } else {
        mqttClient.loop();
    }
}
