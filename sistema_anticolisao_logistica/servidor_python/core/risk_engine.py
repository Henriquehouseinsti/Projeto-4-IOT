import numpy as np
import logging
import time
from shapely.geometry import Polygon

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class RiskEngine:
    def __init__(self, ttc_threshold=1.5, default_vehicle_width=1.5, default_vehicle_length=3.0, safety_margin_m=0.5):
        """
        Módulo de Avaliação de Risco: Calcula a probabilidade de impacto usando extrapolação espacial e Shapely.
        """
        self.ttc_threshold = ttc_threshold
        self.default_width = default_vehicle_width
        self.default_length = default_vehicle_length
        self.safety_margin = safety_margin_m
        
        self.max_prediction_time = 4.0
        self.sim_dt = 0.1 

        # --- CONTROLE DE HISTERESE (SUPRESSÃO DE ALERTAS) ---
        # Estrutura: { "idA_idB": timestamp_do_ultimo_envio }
        self._last_alert_sent = {}
        self.alert_cooldown_s = 1.0  # Janela de espera mínima (1 segundo) para retransmitir o mesmo alerta

    def _create_vehicle_polygon(self, pos_m, mask_polygon=None):
        """Cria um objeto Polygon do Shapely representando a base física do veículo"""
        x, y = pos_m
        
        w = self.default_width + self.safety_margin
        l = self.default_length + self.safety_margin
        
        coords = [
            (x - w/2, y - l/2),
            (x + w/2, y - l/2),
            (x + w/2, y + l/2),
            (x - w/2, y + l/2)
        ]
        return Polygon(coords)

    def _extrapolate_polygon(self, polygon, velocity_m_s, t):
        """Desloca (extrapola) o polígono no tempo 't' com base no vetor velocidade [Vx, Vy]"""
        vx, vy = velocity_m_s
        dx = vx * t
        dy = vy * t
        new_coords = [(cx + dx, cy + dy) for cx, cy in polygon.exterior.coords]
        return Polygon(new_coords)

    def calculate_collisions(self, enriched_objects, mqtt_manager=None):
        """
        Calcula o risco de impacto e gerencia a emissão inteligente de alertas com controle de histerese.
        """
        num_objs = len(enriched_objects)
        if num_objs < 2:
            return []

        collision_events = []
        polygons = {}
        current_time = time.time()
        
        # Cria os polígonos base do Shapely
        for obj in enriched_objects:
            polygons[obj["id"]] = self._create_vehicle_polygon(obj["position_m"], obj.get("mask_polygon"))

        # Combinação par a par estrita
        for i in range(num_objs):
            for j in range(i + 1, num_objs):
                obj_a = enriched_objects[i]
                obj_b = enriched_objects[j]
                
                id_a, id_b = obj_a["id"], obj_b["id"]
                poly_a, poly_b = polygons[id_a], polygons[id_b]
                
                v_a = obj_a["velocity_m_s"]
                v_b = obj_b["velocity_m_s"]
                if np.linalg.norm(v_a) < 0.1 and np.linalg.norm(v_b) < 0.1:
                    continue

                # --- SIMULAÇÃO DA EXTRAPOLAÇÃO TEMPORAL ---
                ttc_detected = None
                t = 0.0
                
                while t <= self.max_prediction_time:
                    future_poly_a = self._extrapolate_polygon(poly_a, v_a, t)
                    future_poly_b = self._extrapolate_polygon(poly_b, v_b, t)
                    
                    if future_poly_a.intersects(future_poly_b):
                        ttc_detected = t
                        break
                    
                    t += self.sim_dt

                # --- TOMADA DE DECISÃO COM HISTERESE ---
                if ttc_detected is not None and ttc_detected <= self.ttc_threshold:
                    gravidade = "CRITICA" if ttc_detected < (self.ttc_threshold / 2) else "ALTA"
                    
                    logging.warning(f"[RISK ENGINE] RISCO DETECTADO! Veículo #{id_a} -> Veículo #{id_b} | TTC: {ttc_detected:.2f}s")
                    
                    event = {
                        "veiculo_1": id_a,
                        "veiculo_2": id_b,
                        "time_to_collision": ttc_detected,
                        "gravidade": gravidade
                    }
                    collision_events.append(event)
                    
                    # Chave única bidirecional para identificar o par (independe de quem é A ou B)
                    pair_key = f"{min(id_a, id_b)}_{max(id_a, id_b)}"
                    last_sent = self._last_alert_sent.get(pair_key, 0.0)
                    
                    # Só autoriza o disparo do pacote se o cooldown de 1 segundo tiver expirado
                    if (current_time - last_sent) >= self.alert_cooldown_s:
                        if mqtt_manager:
                            mqtt_manager.enviar_alerta_colisao(
                                id_veiculo_1=id_a,
                                id_veiculo_2=id_b,
                                ttc=ttc_detected,
                                gravidade=gravidade
                            )
                            nivel_esp32 = "RISCO_VERMELHO" if gravidade == "CRITICA" else "RISCO_AMARELO"
                            mqtt_manager.enviar_alerta_esp32(nivel_esp32)
                            self._last_alert_sent[pair_key] = current_time
                    else:
                        logging.info(f"[RISK ENGINE] Alerta para o par {pair_key} suprimido por histerese de rede.")
                        
        # Limpeza defensiva do dicionário de histerese para evitar acúmulo de IDs antigas na RAM
        active_pairs = [f"{min(enriched_objects[i]['id'], enriched_objects[j]['id'])}_{max(enriched_objects[i]['id'], enriched_objects[j]['id'])}" 
                        for i in range(num_objs) for j in range(i + 1, num_objs)]
        for old_pair in list(self._last_alert_sent.keys()):
            if old_pair not in active_pairs and (current_time - self._last_alert_sent[old_pair]) > 10.0:
                del self._last_alert_sent[old_pair]

        return collision_events