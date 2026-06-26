#!/usr/bin/env python3
import shutil
import os
from ultralytics import YOLO

print("Baixando modelo yolo11n (pode demorar alguns segundos)...")
model = YOLO("yolo11n.pt")

dest = os.path.join("weights", "yolo11_topview.pt")
shutil.copy("yolo11n.pt", dest)
print(f"Modelo generico instalado em {dest}")
print("Rode 'python main.py' para iniciar o servidor com deteccao ativa.")
