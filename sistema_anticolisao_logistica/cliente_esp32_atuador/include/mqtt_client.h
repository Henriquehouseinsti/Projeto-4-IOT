#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <PubSubClient.h>

extern PubSubClient mqttClient;
extern unsigned long ultimo_heartbeat; // Variável global do temporizador

void setupMQTT();
void reconectarMQTT();
void handleMQTT();

#endif