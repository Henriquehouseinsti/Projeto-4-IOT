#ifndef CONFIG_H
#define CONFIG_H

// --- Credenciais de Rede Wi-Fi ---
const char* WIFI_SSID = "SUA_REDE_WIFI";
const char* WIFI_PASSWORD = "SUA_SENHA_WIFI";

// --- Configurações MQTT ---
const char* MQTT_BROKER = "192.168.1.100"; // IP da máquina rodando o Servidor Python
const int MQTT_PORT = 1883;

// --- Tópicos MQTT ---
const char* TOPIC_ALERTA = "logistica/alerta";
const char* TOPIC_HEARTBEAT = "logistica/heartbeat";

// --- Mapeamento de Hardware (GPIOs) ---
const int PIN_BUZZER = 18;      // Alerta sonoro para o operador
const int PIN_FREIO = 19;       // Relé de corte de aceleração/frenagem
const int PIN_LED_STATUS = 2;   // LED onboard da ESP32 (Status de Rede)

// --- Parâmetros de Segurança ---
const unsigned long TIMEOUT_HEARTBEAT_MS = 1000; // 1 segundo sem rede = falha crítica

#endif