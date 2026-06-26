#ifndef CAMERA_CONFIG_H
#define CAMERA_CONFIG_H

#define WIFI_SSID "GD03"
#define WIFI_PASSWORD "Gd#03!@8"

#define CAMERA_STREAM_PORT 81
#define HTTP_USERNAME ""
#define HTTP_PASSWORD ""

// IP estático da câmera — manter sincronizado com config.yaml do servidor Python
#define CAM_IP      10, 10, 115, 108
#define CAM_GATEWAY 10, 10, 115, 1
#define CAM_SUBNET  255, 255, 255, 0

#endif // CAMERA_CONFIG_H
