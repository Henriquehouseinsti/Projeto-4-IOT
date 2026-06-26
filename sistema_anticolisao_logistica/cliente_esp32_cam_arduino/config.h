#ifndef CAMERA_CONFIG_H
#define CAMERA_CONFIG_H

#define WIFI_SSID "Henrique"
#define WIFI_PASSWORD "12345678"

#define CAMERA_STREAM_PORT 81
#define HTTP_USERNAME ""
#define HTTP_PASSWORD ""

// IP estático da câmera — manter sincronizado com config.yaml do servidor Python
#define CAM_IP      192, 168, 137, 108
#define CAM_GATEWAY 192, 168, 137, 1
#define CAM_SUBNET  255, 255, 255, 0

#endif // CAMERA_CONFIG_H
