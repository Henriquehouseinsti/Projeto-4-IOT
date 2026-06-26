import json
import logging
import threading
import time
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class MQTTManager:
    def __init__(self, broker="localhost", port=1883, client_id="servidor_python_anticolisao", 
                 topic_alerts="telemetria/colisao", topic_heartbeat="telemetria/heartbeat", 
                 username=None, password=None, keepalive=60):
        
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.topic_alerts = topic_alerts
        self.topic_heartbeat = topic_heartbeat
        self.keepalive = keepalive
        
        self.client = mqtt.Client(client_id=self.client_id)
        
        if username:
            self.client.username_pw_set(username, password)
            
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # --- Mecanismo de Watchdog para o YOLO ---
        self._last_yolo_inference_time = time.time()
        self._watchdog_timeout = 1.0
        
        # Controle da thread do Heartbeat
        self._heartbeat_thread = None
        self._stop_heartbeat = threading.Event()
        self.is_connected = False # Flag interna para monitorar o status real da rede

    def touch_yolo(self):
        """Alimenta o cão de guarda da IA a cada frame processado"""
        self._last_yolo_inference_time = time.time()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Conectado com sucesso ao Broker MQTT!")
            self.is_connected = True
            self._start_heartbeat_loop()
        else:
            logging.error(f"Falha na conexão. Código: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logging.warning("Conexão perdida com o Broker!")
        self.is_connected = False
        # NOTA: Não matamos a thread aqui para permitir que ela continue viva 
        # esperando a reconexão automática do Paho em background.

    def _start_heartbeat_loop(self):
        # Garante que só existirá uma thread de heartbeat rodando por vez
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._stop_heartbeat.clear()
            self._last_yolo_inference_time = time.time() 
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
            self._heartbeat_thread.start()
            logging.info("Thread de Heartbeat (200ms) com Watchdog iniciada.")

    def _heartbeat_worker(self):
        """Thread assíncrona desacoplada do tempo de processamento visual"""
        while not self._stop_heartbeat.is_set():
            current_time = time.time()
            
            # Verifica a integridade do loop do YOLO
            yolo_alive = (current_time - self._last_yolo_inference_time) < self._watchdog_timeout
            
            # Só envia o pacote se a IA estiver viva E se o cliente estiver conectado na rede
            if yolo_alive and self.is_connected:
                try:
                    self.client.publish(self.topic_heartbeat, "ok", qos=0)
                except Exception as e:
                    logging.error(f"Erro ao enviar Heartbeat: {e}")
            elif not yolo_alive:
                logging.error("[WATCHDOG] O loop do YOLO travou! Heartbeat suspenso para alertar o ESP32.")
            
            # Aguarda estritamente 200ms de forma segura
            self._stop_heartbeat.wait(timeout=0.2)

    def conectar(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=self.keepalive)
            self.client.loop_start() 
        except Exception as e:
            logging.error(f"Erro na conexão MQTT: {e}")

    def enviar_alerta_colisao(self, id_veiculo_1, id_veiculo_2, ttc, gravidade="ALTA"):
        if not self.is_connected:
            logging.error("Tentativa de enviar alerta sem conexão ativa com o Broker.")
            return

        payload = {
            "evento": "ALERTA_COLISAO",
            "timestamp": time.time(),
            "veiculos_envolvidos": [id_veiculo_1, id_veiculo_2],
            "time_to_collision_s": round(ttc, 2),
            "gravidade": gravidade
        }
        try:
            result = self.client.publish(self.topic_alerts, json.dumps(payload), qos=1)
            result.wait_for_publish(timeout=1.0) # Adicionado timeout para não travar o core se a rede sumir aqui
            logging.info(f"Alerta publicado com sucesso: {payload}")
        except Exception as e:
            logging.error(f"Falha ao publicar alerta: {e}")

    def enviar_alerta_esp32(self, nivel: str):
        """Publica string simples para o ESP32 Atuador interpretar diretamente.
        nivel: 'RISCO_VERMELHO', 'RISCO_AMARELO' ou 'SEGURO'
        """
        if not self.is_connected:
            return
        try:
            self.client.publish(self.topic_alerts, nivel, qos=1)
        except Exception as e:
            logging.error(f"Falha ao publicar alerta ESP32: {e}")

    def desconectar(self):
        logging.info("Encerrando conexões do MQTT Manager...")
        self._stop_heartbeat.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1.0)
        self.client.loop_stop()
        self.client.disconnect()
        logging.info("MQTT Manager encerrado com sucesso.")