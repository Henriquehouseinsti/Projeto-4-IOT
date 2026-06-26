#include "Arduino.h"
#include "WiFi.h"
#include "WebServer.h"
#include "esp_camera.h"
#include "config.h"

extern WebServer server;

const char* mjpegBoundary = "--frame";

void handleJPGStream() {
  WiFiClient client = server.client();

  String response = String("HTTP/1.1 200 OK\r\n") +
                    "Content-Type: multipart/x-mixed-replace; boundary=" + mjpegBoundary + "\r\n" +
                    "Cache-Control: no-cache\r\n" +
                    "Pragma: no-cache\r\n" +
                    "Connection: close\r\n";
  server.sendContent(response);

  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Erro: falha ao capturar frame da camera.");
      return;
    }

    server.sendContent(String("\r\n") + mjpegBoundary + "\r\n" +
                       "Content-Type: image/jpeg\r\n" +
                       "Content-Length: " + String(fb->len) + "\r\n\r\n");
    server.client().write(fb->buf, fb->len);
    esp_camera_fb_return(fb);
    server.sendContent("\r\n");

    if (!client.connected()) {
      break;
    }
  }
}

void handleRoot() {
  server.send(200, "text/html",
    "<html><body>"
    "<h1>ESP32-CAM - Stream ao Vivo</h1>"
    "<img src=\"/stream\" />"
    "</body></html>"
  );
}

void startCameraServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/stream", HTTP_GET, handleJPGStream);
  server.begin();
  Serial.println("Servidor HTTP iniciado. Stream disponivel em /stream");
}
