#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module: main
@description: Orquestrador de threads e loop principal do sistema anticolição.
"""

import os
import sys
import time
import logging
import cv2
import numpy as np
import yaml  # Biblioteca para leitura do arquivo config.yaml

# Importação dos módulos locais
from core.camera_stream import CameraStream
from core.perception import PerceptionEngine
from core.kinematics import KinematicsEngine
from core.risk_engine import RiskEngine
from comms.mqtt_manager import MQTTManager
from utils.data_logger import AsyncDataLogger
from utils.visualizer import Visualizer

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def main():
    logging.info("=== INICIALIZANDO SERVIDOR PYTHON ANTICOLISÃO (LOGÍSTICA) ===")

    # 1. LEITURA DINÂMICA DO ARQUIVO DE CONFIGURAÇÃO (config.yaml)
    try:
        logging.info("Carregando parâmetros do arquivo config.yaml...")
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Falha crítica ao ler o arquivo config.yaml: {e}")
        sys.exit(1)

    # 2. INICIALIZAÇÃO DOS COMPONENTES (Injeção de Dependências vindas do YAML)
    
    mqtt_manager = MQTTManager(
        broker=config["mqtt"]["broker"],
        port=config["mqtt"]["port"],
        client_id=config["mqtt"]["client_id"],
        topic_alerts=config["mqtt"]["topics"]["alerts"],
        topic_heartbeat=config["mqtt"]["topics"]["heartbeat"],
        username=config["mqtt"]["username"],
        password=config["mqtt"]["password"]
    )
    
    camera = CameraStream(
        src=config["camera"]["source"], 
        max_reconnect_tries=config["camera"]["max_reconnect_tries"], 
        reconnect_delay=config["camera"]["reconnect_delay"]
    )
    
    perception = PerceptionEngine(
        model_path=config["perception"]["model_path"], 
        conf_threshold=config["perception"]["confidence_threshold"], 
        iou_threshold=config["perception"]["iou_threshold"],
        device=config["perception"]["device"]
    )
    
    # Inicializa a cinemática com o dt padrão do arquivo de configuração
    kinematics = KinematicsEngine(
        homography_matrix=config["kinematics"]["homography_matrix"], 
        dt=config["kinematics"]["dt"]
    )
    
    risk_engine = RiskEngine(
        ttc_threshold=config["risk_engine"]["ttc_threshold"], 
        default_vehicle_width=config["risk_engine"]["default_vehicle_width"], 
        default_vehicle_length=config["risk_engine"]["default_vehicle_length"],
        safety_margin_m=config["risk_engine"]["safety_margin_meters"]
    )

    # --- UTILITÁRIOS ADICIONADOS ---
    data_logger = AsyncDataLogger(output_dir="logs", filename_prefix="telemetria_sistema")
    visualizer = Visualizer(draw_boxes=True, draw_velocities=True, draw_masks=True)

    # 3. DISPARO DAS CONEXÕES E THREADS EM BACKGROUND
    
    mqtt_manager.conectar()
    data_logger.start()  # Ativa a thread de gravação assíncrona em disco
    
    if not perception.load_model():
        logging.error("Falha crítica ao carregar modelo de IA. Encerrando orquestrador.")
        mqtt_manager.desconectar()
        data_logger.stop()
        sys.exit(1)
        
    if not camera.start():
        logging.error("Falha crítica ao iniciar o fluxo de vídeo. Encerrando orquestrador.")
        mqtt_manager.desconectar()
        data_logger.stop()
        sys.exit(1)

    logging.info("=== SISTEMA PRONTO! ENTRANDO NO LOOP CRÍTICO DE INFERÊNCIA ===")
    
    # Variável auxiliar para rastrear o tempo exato decorrido entre iterações
    last_loop_timestamp = time.time()
    
    try:
        while camera.running:
            current_timestamp = time.time()
            
            # Cálculo do delta de tempo (dt) dinâmico real para o Filtro de Kalman
            dynamic_dt = current_timestamp - last_loop_timestamp
            last_loop_timestamp = current_timestamp
            
            # Proteção contra divisão por zero ou saltos espúrios iniciais
            if dynamic_dt <= 0:
                dynamic_dt = 0.033
                
            # Atualiza o passo discreto de tempo interno do Filtro de Kalman dinamicamente
            kinematics.dt = dynamic_dt
            
            # Passo 1: Captura o frame mais recente exposto pela thread da câmera
            grabbed, frame = camera.read()
            if not grabbed or frame is None:
                time.sleep(0.01)
                continue

            # Passo 2: Executa IA (YOLOv11) e amarra IDs (ByteTrack)
            detections = perception.process_frame(frame, mqtt_manager=mqtt_manager)
            
            # Passo 3: Converte pixels para metros (Homografia) e aplica Filtro de Kalman com dt corrigido
            enriched_objects = kinematics.update_kinematics(detections)
            
            # Passo 4: Projeta trajetórias futuras no plano cartesiano (Shapely) e avalia colisões (TTC)
            collisions = risk_engine.calculate_collisions(enriched_objects, mqtt_manager=mqtt_manager)

            # --- Passo 5: REGISTRO DE DADOS ASSÍNCRONO (.jsonl) ---
            for obj in enriched_objects:
                data_logger.log({
                    "type": "telemetry",
                    "id": obj["id"],
                    "class": obj["class_name"],
                    "speed_kmh": obj["speed_kmh"],
                    "position_m": obj["position_m"]
                })
            for col in collisions:
                data_logger.log({
                    "type": "alert_event",
                    "v1": col["veiculo_1"],
                    "v2": col["veiculo_2"],
                    "ttc": col["time_to_collision"],
                    "severity": col["gravidade"]
                })

            # --- PROCESSAMENTO VISUAL DA TELA COM O CLASSE VISUALIZER ---
            if config["visualizer"]["show_window"]:
                fps = 1.0 / dynamic_dt
                
                # Renderiza o HUD técnico e as sobreposições poligonais completas
                frame = visualizer.draw_telemetry(frame, enriched_objects, collisions, fps)
                
                cv2.imshow(config["visualizer"]["window_name"], frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                time.sleep(0.001)

    except KeyboardInterrupt:
        logging.info("[MAIN] Interrupção manual do teclado detectada (Ctrl+C).")
        
    except Exception as e:
        logging.error(f"[MAIN] Erro inesperado no loop principal: {e}")
        
    finally:
        # 4. DESALOCAÇÃO COMPLETA DE RECURSOS (Rotina de encerramento seguro)
        logging.info("=== INICIANDO DESALOCAÇÃO SEGURA DO SISTEMA ===")
        camera.stop()
        mqtt_manager.desconectar()
        data_logger.stop()  # Garante o fechamento e gravação dos logs pendentes na fila
        cv2.destroyAllWindows()
        logging.info("=== BACKEND ENCERRADO COM SUCESSO ===")

if __name__ == "__main__":
    main()