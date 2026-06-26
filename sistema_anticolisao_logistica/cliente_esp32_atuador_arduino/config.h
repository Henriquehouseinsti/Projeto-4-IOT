#ifndef CONFIG_H
#define CONFIG_H

// --- Credenciais de Rede Wi-Fi ---
#define WIFI_SSID     "Henrique"
#define WIFI_PASSWORD "12345678"

// --- Configurações MQTT ---
// IP do PC rodando o servidor Python (verificar com ipconfig)
#define MQTT_BROKER "192.168.137.164"
#define MQTT_PORT   1883

// --- Tópicos MQTT ---
#define TOPIC_ALERTA    "logistica/alerta"
#define TOPIC_HEARTBEAT "logistica/heartbeat"

// --- Mapeamento de Hardware (GPIOs) ---
#define PIN_BUZZER  18   // Buzzer piezoelétrico
#define PIN_LED     2    // LED onboard (status de rede)

// --- Parâmetros de Segurança ---
#define TIMEOUT_HEARTBEAT_MS 1000  // 1s sem heartbeat = modo emergência

#endif
