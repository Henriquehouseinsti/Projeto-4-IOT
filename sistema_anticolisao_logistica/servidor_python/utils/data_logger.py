# data_logger.py
# Gravação assíncrona em .jsonl

import os
import json
import queue
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class AsyncDataLogger:
    def __init__(self, output_dir="logs", filename_prefix="telemetry"):
        """
        Logger assíncrono em formato JSON Lines (.jsonl).
        Salva os dados no disco em background para não engasgar o loop da IA.
        """
        self.output_dir = output_dir
        self.filename_prefix = filename_prefix
        
        # Garante que a pasta de logs existe
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Gera o nome do arquivo com a data/hora de inicialização do sistema
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_filepath = os.path.join(self.output_dir, f"{self.filename_prefix}_{timestamp}.jsonl")
        
        # Fila thread-safe para receber os logs e controle da thread
        self.log_queue = queue.Queue()
        self.running = False
        self.worker_thread = None

    def start(self):
        """Inicia a thread de escrita em disco"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._write_loop, name="DataLoggerThread", daemon=True)
        self.worker_thread.start()
        logging.info(f"[LOGGER] Gravação assíncrona iniciada. Arquivo: {self.log_filepath}")

    def log(self, data_dict):
        """
        Método público e rápido. Apenas joga o dicionário na fila e libera o main.py instantaneamente.
        """
        if not self.running:
            return
        
        # Adiciona um timestamp Unix se já não houver um
        if "timestamp" not in data_dict:
            data_dict["timestamp"] = time.time()
            
        self.log_queue.put(data_dict)

    def _write_loop(self):
        """Loop interno executado pela thread em background"""
        # Abre o arquivo em modo append ("a")
        with open(self.log_filepath, "a", encoding="utf-8") as f:
            while self.running or not self.log_queue.empty():
                try:
                    # Aguarda por um item na fila com timeout para não travar o encerramento do app
                    data = self.log_queue.get(timeout=0.5)
                    
                    # Converte o dicionário em uma única linha JSON string e quebra a linha
                    json_line = json.dumps(data, ensure_ascii=False)
                    f.write(json_line + "\n")
                    
                    # Força a gravação física imediata do buffer no disco (segurança contra quedas de energia)
                    f.flush()
                    
                    self.log_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logging.error(f"[LOGGER] Erro ao gravar dados no arquivo: {e}")

    def stop(self):
        """Para o logger de forma limpa, garantindo que tudo que estava na fila seja salvo"""
        logging.info("[LOGGER] Encerrando gravação e esvaziando fila de logs...")
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        logging.info("[LOGGER] Arquivo de log fechado e salvo.")