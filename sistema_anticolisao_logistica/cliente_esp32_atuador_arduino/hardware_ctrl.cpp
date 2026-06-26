#include "Arduino.h"
#include "hardware_ctrl.h"
#include "config.h"

EstadoSistema estado_atual = ESTADO_INICIALIZACAO;

static unsigned long ultimo_bip = 0;
static bool estado_buzzer = false;

void initHardware() {
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED, LOW);
    setModoEmergencia();
}

void setModoEmergencia() {
    if (estado_atual != ESTADO_EMERGENCIA) {
        Serial.println("[FALHA] MODO DE EMERGENCIA ATIVADO!");
        digitalWrite(PIN_BUZZER, HIGH);
        estado_atual = ESTADO_EMERGENCIA;
    }
}

void setModoNormal() {
    if (estado_atual != ESTADO_NORMAL) {
        Serial.println("[INFO] Sistema Normalizado.");
        digitalWrite(PIN_BUZZER, LOW);
        estado_buzzer = false;
        estado_atual = ESTADO_NORMAL;
    }
}

void setAlertaAmarelo() {
    if (estado_atual != ESTADO_ALERTA_AMARELO) {
        Serial.println("[AVISO] Risco Amarelo — objeto proximo!");
        estado_atual = ESTADO_ALERTA_AMARELO;
    }
}

void processarHardware() {
    unsigned long agora = millis();

    // LED pisca enquanto a rede estiver ok
    digitalWrite(PIN_LED, (agora % 1000) < 500);

    // Buzzer intermitente no alerta amarelo
    if (estado_atual == ESTADO_ALERTA_AMARELO) {
        if (agora - ultimo_bip > 300) {
            estado_buzzer = !estado_buzzer;
            digitalWrite(PIN_BUZZER, estado_buzzer);
            ultimo_bip = agora;
        }
    }
}
