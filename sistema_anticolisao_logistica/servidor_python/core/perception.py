import os
import sys
import logging
from ultralytics import YOLO

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class PerceptionEngine:
    def __init__(self, model_path="weights/yolo11_topview.pt", conf_threshold=0.25, iou_threshold=0.45, device="cpu"):
        """
        Módulo de Percepção Visual: Executa inferência do YOLO-seg e gerencia o Tracking via ByteTrack.
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None

    def load_model(self):
        """Carrega os pesos do YOLO na memória e força uma inferência de aquecimento (warmup)"""
        if not os.path.exists(self.model_path):
            logging.error(f"[PERCEPTION] Arquivo de pesos não encontrado em: {self.model_path}")
            return False
            
        try:
            logging.info(f"[PERCEPTION] Carregando modelo YOLOv11 de {self.model_path} no dispositivo '{self.device}'...")
            self.model = YOLO(self.model_path)
            
            # Garante que o warmup encontre um arquivo válido ou usa um tensor vazio para aquecimento
            logging.info("[PERCEPTION] Executando warmup da rede neural...")
            self.model.predict(source=self.model_path, device=self.device, imgsz=640, verbose=False)
            logging.info("[PERCEPTION] Modelo YOLOv11 carregado e aquecido com sucesso.")
            return True
        except Exception as e:
            logging.error(f"[PERCEPTION] Falha crítica ao inicializar o modelo: {e}")
            return False

    def process_frame(self, frame, mqtt_manager=None):
        """
        Processa um único frame: executa detecção (YOLO-seg) e atualiza o rastreamento (ByteTrack).
        """
        if self.model is None:
            logging.error("[PERCEPTION] Tentativa de processar frame sem carregar o modelo primeiro.")
            return []

        if frame is None:
            return []

        # --- ALIMENTA O WATCHDOG DO HEARTBEAT ---
        if mqtt_manager:
            mqtt_manager.touch_yolo()

        tracked_objects = []

        try:
            # Executa a inferência utilizando o rastreador nativo ByteTrack da Ultralytics
            results = self.model.track(
                source=frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False
            )

            # Validação defensiva robusta para evitar IndexError se a lista for vazia
            if results is None or len(results) == 0:
                return []

            result = results[0]
            
            # Verifica se existem caixas delimitadoras válidas no frame
            if result.boxes is None or len(result.boxes) == 0:
                return []

            boxes = result.boxes

            # Varre todos os objetos rastreados no frame atual
            for i in range(len(boxes)):
                # Se o ByteTrack ainda não atribuiu ID para este objeto neste frame, ignora
                if boxes.id is None:
                    continue

                obj_id = int(boxes.id[i].item())
                cls_idx = int(boxes.cls[i].item())
                label = result.names[cls_idx]
                conf = float(boxes.conf[i].item())
                
                # Caixas delimitadoras coordenadas xyxy em formato numpy
                xyxy = boxes.xyxy[i].cpu().numpy()
                
                # Extração defensiva da máscara de segmentação polígono
                mask_xy = None
                if result.masks is not None and result.masks.xy is not None:
                    segments = result.masks.xy
                    if len(segments) > i:
                        mask_xy = segments[i] # Matriz de pontos (x, y) da borda do objeto

                # Monta a estrutura unificada para passar para a física (kinematics.py)
                obj_data = {
                    "id": obj_id,
                    "class_name": label,
                    "confidence": conf,
                    "bbox_xyxy": xyxy,      # [xmin, ymin, xmax, ymax] em pixels
                    "mask_polygon": mask_xy # Lista de pontos (x,y) do contorno ou None
                }
                
                tracked_objects.append(obj_data)

        except Exception as e:
            logging.error(f"[PERCEPTION] Erro durante o processamento do frame/tracking: {e}")

        return tracked_objects