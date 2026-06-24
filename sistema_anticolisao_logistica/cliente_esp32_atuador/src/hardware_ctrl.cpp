#include <Arduino.h>
#include "hardware_ctrl.h"
#include "config.h"

EstadoSistema estado_atual = ESTADO_INICIALIZACAO;
unsigned long ultimo_bip_buzzer = 0;
bool estado_buzzer = false;

void initHardware() {
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_FREIO, OUTPUT);
    pinMode(PIN_LED_STATUS, OUTPUT);
    
    // Inicia travado por segurança
    setModoEmergencia();
}

void setModoEmergencia() {
    if (estado_atual != ESTADO_EMERGENCIA) {
        Serial.println("[FALHA] MODO DE EMERGÊNCIA ATIVADO!");
        digitalWrite(PIN_FREIO, HIGH);
        digitalWrite(PIN_BUZZER, HIGH); // Buzzer contínuo
        estado_atual = ESTADO_EMERGENCIA;
    }
}

void setModoNormal() {
    if (estado_atual != ESTADO_NORMAL) {
        Serial.println("[INFO] Sistema Normalizado.");
        digitalWrite(PIN_FREIO, LOW);
        digitalWrite(PIN_BUZZER, LOW);
        estado_atual = ESTADO_NORMAL;
    }
}

void setAlertaAmarelo() {
    if (estado_atual != ESTADO_ALERTA_AMARELO) {
        Serial.println("[AVISO] Risco Amarelo.");
        digitalWrite(PIN_FREIO, LOW); // Não freia, só apita
        estado_atual = ESTADO_ALERTA_AMARELO;
    }
}

void processarHardware() {
    unsigned long tempo_atual = millis();
    
    // Pisca o LED de status se a rede estiver ok
    digitalWrite(PIN_LED_STATUS, (tempo_atual % 1000) < 500);

    // Bip intermitente para Alerta Amarelo
    if (estado_atual == ESTADO_ALERTA_AMARELO) {
        if (tempo_atual - ultimo_bip_buzzer > 300) {
            estado_buzzer = !estado_buzzer;
            digitalWrite(PIN_BUZZER, estado_buzzer);
            ultimo_bip_buzzer = tempo_atual;
        }
    }
}