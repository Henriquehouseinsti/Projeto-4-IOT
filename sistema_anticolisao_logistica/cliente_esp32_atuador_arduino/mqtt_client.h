#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <PubSubClient.h>

extern unsigned long ultimo_heartbeat;

void setupMQTT();
void handleMQTT();

#endif
