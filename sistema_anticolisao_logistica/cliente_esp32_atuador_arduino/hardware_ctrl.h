#ifndef HARDWARE_CTRL_H
#define HARDWARE_CTRL_H

enum EstadoSistema {
    ESTADO_INICIALIZACAO,
    ESTADO_NORMAL,
    ESTADO_ALERTA_AMARELO,
    ESTADO_EMERGENCIA
};

extern EstadoSistema estado_atual;

void initHardware();
void setModoEmergencia();
void setModoNormal();
void setAlertaAmarelo();
void processarHardware();

#endif
