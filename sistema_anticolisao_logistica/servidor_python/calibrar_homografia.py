#!/usr/bin/env python3
"""
Ferramenta de calibracao da homografia (pixel -> metros).

Instrucoes:
1. Posicione 4 marcas no chao formando um retangulo de dimensoes conhecidas
   (ex: 1m x 1m usando fita ou cones)
2. Rode este script e clique nos 4 cantos NA ORDEM: TL -> TR -> BR -> BL
3. Informe as dimensoes reais do retangulo quando solicitado
4. Copie a matriz impressa para o campo homography_matrix do config.yaml

Controles:
  Clique esquerdo - seleciona ponto
  R              - reinicia selecao
  C              - calcula (apos 4 pontos selecionados)
  Q              - sai sem calcular
"""

import cv2
import numpy as np
import yaml

STREAM_URL = "http://192.168.137.108:81/stream"

pontos_pixel = []

def click_handler(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(pontos_pixel) < 4:
        pontos_pixel.append((x, y))
        print(f"  Ponto {len(pontos_pixel)}: ({x}, {y})")

cap = cv2.VideoCapture(STREAM_URL)
if not cap.isOpened():
    print(f"[ERRO] Nao foi possivel abrir: {STREAM_URL}")
    exit(1)

# Captura um frame limpo para trabalhar
ret, frame_base = cap.read()
cap.release()
if not ret:
    print("[ERRO] Falha ao capturar frame.")
    exit(1)

cv2.namedWindow("Calibracao - clique nos 4 cantos (TL TR BR BL)")
cv2.setMouseCallback("Calibracao - clique nos 4 cantos (TL TR BR BL)", click_handler)

LABELS = ["1: Superior Esq (TL)", "2: Superior Dir (TR)",
          "3: Inferior Dir (BR)", "4: Inferior Esq (BL)"]
CORES  = [(0,255,0), (0,255,255), (0,0,255), (255,0,255)]

print("\nClique nos 4 cantos do retangulo de referencia na ORDEM:")
for l in LABELS:
    print(f"  {l}")
print("Teclas: R=reiniciar | C=calcular | Q=sair\n")

while True:
    display = frame_base.copy()

    instrucao = LABELS[len(pontos_pixel)] if len(pontos_pixel) < 4 else "Pressione C para calcular"
    cv2.putText(display, instrucao, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    for i, (px, py) in enumerate(pontos_pixel):
        cv2.circle(display, (px, py), 8, CORES[i], -1)
        cv2.putText(display, str(i+1), (px + 10, py - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, CORES[i], 2)

    if len(pontos_pixel) == 4:
        pts = np.array(pontos_pixel, dtype=np.int32)
        cv2.polylines(display, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

    cv2.imshow("Calibracao - clique nos 4 cantos (TL TR BR BL)", display)
    key = cv2.waitKey(20) & 0xFF

    if key == ord('r') or key == ord('R'):
        pontos_pixel.clear()
        print("Selecao reiniciada.")

    elif key == ord('c') or key == ord('C'):
        if len(pontos_pixel) < 4:
            print(f"[AVISO] Selecione os 4 pontos primeiro (selecionados: {len(pontos_pixel)})")
            continue

        print("\nInforme as dimensoes reais do retangulo no chao:")
        try:
            larg = float(input("  Largura (metros, distancia TL->TR): "))
            alt  = float(input("  Altura  (metros, distancia TL->BL): "))
        except ValueError:
            print("[ERRO] Valor invalido.")
            continue

        pts_destino = np.array([
            [0,    0   ],
            [larg, 0   ],
            [larg, alt ],
            [0,    alt ]
        ], dtype=np.float32)

        pts_origem = np.array(pontos_pixel, dtype=np.float32)
        H, _ = cv2.findHomography(pts_origem, pts_destino)

        print("\n" + "="*60)
        print("MATRIZ DE HOMOGRAFIA CALCULADA")
        print("Copie o trecho abaixo para o config.yaml:\n")
        print("  homography_matrix:")
        for row in H:
            print(f"    - [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}]")
        print("="*60)
        break

    elif key == ord('q') or key == ord('Q'):
        print("Saindo sem calcular.")
        break

cv2.destroyAllWindows()
