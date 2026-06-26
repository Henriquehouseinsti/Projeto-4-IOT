#!/usr/bin/env python3
"""
Ferramenta de coleta de dataset a partir do stream da ESP32-CAM.

Controles:
  S - Salva frame atual como imagem JPG
  V - Inicia / para gravacao de clipe de video
  Q - Encerra
"""

import cv2
import os
from datetime import datetime

STREAM_URL = "http://192.168.137.108:81/stream"
IMG_DIR    = "dataset/images"
VID_DIR    = "dataset/videos"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(VID_DIR, exist_ok=True)

cap = cv2.VideoCapture(STREAM_URL)
if not cap.isOpened():
    print(f"[ERRO] Nao foi possivel abrir o stream: {STREAM_URL}")
    print("Verifique se a ESP32-CAM esta ligada e na rede correta.")
    exit(1)

print("Stream aberto. Controles: S=salvar imagem | V=gravar video | Q=sair")

frame_count = 0
writer      = None
gravando    = False

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[AVISO] Frame perdido, aguardando...")
        continue

    if gravando and writer:
        writer.write(frame)

    display = frame.copy()

    # Overlay de status
    cv2.putText(display, f"Imagens salvas: {frame_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    if gravando:
        cv2.putText(display, "GRAVANDO VIDEO [V para parar]", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.circle(display, (display.shape[1] - 20, 20), 10, (0, 0, 255), -1)
    else:
        cv2.putText(display, "S=foto | V=video | Q=sair", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.imshow("Coleta de Dataset - ESP32-CAM", display)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('s') or key == ord('S'):
        nome = os.path.join(IMG_DIR, f"frame_{timestamp()}.jpg")
        cv2.imwrite(nome, frame)
        frame_count += 1
        print(f"[OK] Imagem salva: {nome}  (total: {frame_count})")

    elif key == ord('v') or key == ord('V'):
        if not gravando:
            h, w = frame.shape[:2]
            nome_vid = os.path.join(VID_DIR, f"clip_{timestamp()}.avi")
            writer = cv2.VideoWriter(nome_vid,
                                     cv2.VideoWriter_fourcc(*"XVID"),
                                     20, (w, h))
            gravando = True
            print(f"[OK] Gravacao iniciada: {nome_vid}")
        else:
            writer.release()
            writer   = None
            gravando = False
            print("[OK] Gravacao encerrada.")

    elif key == ord('q') or key == ord('Q'):
        break

if writer:
    writer.release()
cap.release()
cv2.destroyAllWindows()
print(f"\nColeta encerrada. {frame_count} imagens salvas em '{IMG_DIR}'.")
