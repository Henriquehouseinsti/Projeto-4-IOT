import os
import sys
import threading
import time
import cv2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class CameraStream:
    def __init__(self, src=0, max_reconnect_tries=10, reconnect_delay=1.0):
        """
        Gerenciador de captura de vídeo em thread dedicada para Tempo Real (ADAS/Logística).
        """
        self.src = src
        self.max_reconnect_tries = max_reconnect_tries
        self.reconnect_delay = reconnect_delay
        
        self.cap = None
        
        # Threading e sincronização
        self.frame = None
        self.grabbed = False
        self.read_lock = threading.Lock()
        self.running = False
        self.thread = None

    def open_source(self):
        """Tenta abrir o dispositivo ou fluxo de vídeo com injeção de parâmetros nativos"""
        logging.info(f"[CAMERA] Tentando abrir canal de vídeo: {self.src}")
        
        # Se for uma string de rede RTSP, injeta os parâmetros direto no backend de forma robusta
        if isinstance(self.src, str) and self.src.startswith("rtsp://"):
            # cv2.CAP_FFMPEG força a utilização do FFmpeg diretamente para gerenciar o protocolo
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
            
            # Força o transporte TCP injetando o parâmetro diretamente nas propriedades do objeto
            # [0x12, 0x54, 0x53, 0x50] é o mapeamento de baixo nível para configurações de RTSP
            self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY) # Ativa aceleração de hardware se disponível
        else:
            # Captura de webcam padrão local
            self.cap = cv2.VideoCapture(self.src)
        
        # Otimização de buffer: reduz o armazenamento interno do OpenCV para 1 frame (evita lag cumulativo)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.cap.isOpened():
            self.grabbed, self.frame = self.cap.read()
            logging.info("[CAMERA] Dispositivo de captura aberto com sucesso.")
            return True
        else:
            logging.error("[CAMERA] Falha crítica ao abrir o dispositivo de captura.")
            return False

    def start(self):
        """Inicia a thread dedicada para leitura contínua de frames"""
        if self.cap is None or not self.cap.isOpened():
            if not self.open_source():
                return False
                
        self.running = True
        self.thread = threading.Thread(target=self._update, name="CameraStreamThread", daemon=True)
        self.thread.start()
        logging.info("Thread de captura em segundo plano disparada.")
        return True

    def _update(self):
        """Loop interno da thread: lê continuamente frames do buffer do OpenCV"""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                logging.warning("[CAMERA] Fluxo fechado inesperadamente. Iniciando rotina de recuperação...")
                if not self._handle_reconnection():
                    break
                    
            grabbed, frame = self.cap.read()
            
            if not grabbed or frame is None:
                logging.warning("[CAMERA] Falha ao extrair frame (queda de frame/sinal). Tentando reabrir...")
                if not self._handle_reconnection():
                    break
                continue

            # Atualiza o frame atual garantindo exclusão mútua (Thread-Safe)
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
                
            # Um micro-sleep impede que a thread consuma 100% de um núcleo da CPU 
            # de forma desnecessária se o hardware de captura for mais lento que o ciclo de clock
            time.sleep(0.001)

    def _handle_reconnection(self):
        """Tenta reestabelecer o fluxo da câmera em caso de falha física ou de rede"""
        if self.cap:
            self.cap.release()
        tries = 0
        
        while tries < self.max_reconnect_tries and self.running:
            tries += 1
            logging.info(f"[CAMERA] Tentativa de reconexão {tries}/{self.max_reconnect_tries} em {self.reconnect_delay}s...")
            
            # Executa sleeps fracionados para podermos cancelar a reconexão rapidamente se o programa fechar
            for _ in range(int(self.reconnect_delay / 0.1)):
                if not self.running:
                    return False
                time.sleep(0.1)
            
            if self.open_source():
                logging.info("[CAMERA] Conexão reestabelecida com sucesso em background.")
                return True
                
        logging.error(f"[CAMERA] Falha de hardware/rede persistente após {self.max_reconnect_tries} tentativas.")
        self.running = False
        return False

    def read(self):
        """
        Método público chamado pelo módulo core (perception.py) para pegar o frame mais recente.
        """
        with self.read_lock:
            # Retorna uma cópia rasa apenas se o frame for válido
            frame_to_return = self.frame.copy() if self.frame is not None else None
            grabbed_to_return = self.grabbed
            
        return grabbed_to_return, frame_to_return

    def stop(self):
        """Para a execução da thread e libera os recursos de hardware de forma limpa"""
        logging.info("Encerrando captura de vídeo...")
        self.running = False
        if self.cap:
            self.cap.release() # Libera o hardware ANTES do join para destravar chamadas de rede bloqueantes
        if self.thread:
            self.thread.join(timeout=1.0)
        logging.info("Recursos da câmera desalocados.")