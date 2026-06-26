#ifndef CAMERA_CONFIG_H
#define CAMERA_CONFIG_H

#define WIFI_SSID "your_ssid"
#define WIFI_PASSWORD "your_password"

#define CAMERA_STREAM_PORT 81
#define HTTP_USERNAME ""
#define HTTP_PASSWORD ""

// IP estático da câmera — manter sincronizado com config.yaml do servidor Python
#define CAM_IP      192, 168, 1, 108
#define CAM_GATEWAY 192, 168, 1, 1
#define CAM_SUBNET  255, 255, 255, 0

#endif // CAMERA_CONFIG_H
