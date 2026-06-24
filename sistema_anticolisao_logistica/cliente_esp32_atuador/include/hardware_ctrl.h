#ifndef HARDWARE_CTRL_H
#define HARDWARE_CTRL_H

enum EstadoSistema {
    ESTADO_INICIALIZACAO,
    ESTADO_NORMAL,
    ESTADO_ALERTA_AMARELO,
    ESTADO_EMERGENCIA
};

extern EstadoSistema estado_atual; // Permite que outros arquivos leiam o estado

void initHardware();
void setModoEmergencia();
void setModoNormal();
void setAlertaAmarelo();
void processarHardware(); // Lógica do buzzer não-bloqueante

#endif