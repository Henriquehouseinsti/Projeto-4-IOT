import numpy as np
import logging
from filterpy.kalman import KalmanFilter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class KinematicsEngine:
    def __init__(self, homography_matrix=None, dt=0.033):
        """
        Módulo de Cinemática: Converte coordenadas de pixel para metros e rastreia vetores com Filtro de Kalman.
        """
        self.H = np.array(homography_matrix) if homography_matrix is not None else np.eye(3)
        self.dt = dt
        self.trackers = {}
        self.max_missed_frames = 30
        self.missed_counters = {}

    def _pixel_to_meters(self, px_x, px_y):
        """Aplica a transformação geométrica de Homografia (Projeção de Perspectiva)"""
        pixel_point = np.array([px_x, px_y, 1.0])
        real_point_raw = np.dot(self.H, pixel_point)
        
        if real_point_raw[2] != 0:
            real_x = real_point_raw[0] / real_point_raw[2]
            real_y = real_point_raw[1] / real_point_raw[2]
            return real_x, real_y
        return 0.0, 0.0

    def _init_kalman_filter(self, init_x, init_y):
        """Inicializa um Filtro de Kalman Linear de Velocidade Constante para um novo objeto"""
        kf = KalmanFilter(dim_x=4, dim_z=2)
        
        # Estado inicial: [X, Y, Vx, Vy]
        kf.x = np.array([[init_x], [init_y], [0.0], [0.0]])
        
        # F: Matriz de Transição de Estado (S = S0 + V*dt)
        kf.F = np.array([[1.0, 0.0, self.dt, 0.0],
                         [0.0, 1.0, 0.0, self.dt],
                         [0.0, 0.0, 1.0, 0.0],
                         [0.0, 0.0, 0.0, 1.0]])
        
        # H: Matriz de Medição
        kf.H = np.array([[1.0, 0.0, 0.0, 0.0],
                         [0.0, 1.0, 0.0, 0.0]])
        
        # P: Incerteza inicial do sistema (valores altos indicam que confiamos mais na medição inicial)
        kf.P *= 10.0
        
        # R: Ruído da detecção óptica
        kf.R = np.array([[0.1, 0.0],
                         [0.0, 0.1]])
        
        # Q: Ruído do Processo (Incerteza do modelo físico linear)
        kf.Q = np.array([[0.05, 0.0,  0.0,  0.0],
                         [0.0,  0.05, 0.0,  0.0],
                         [0.0,  0.0,  0.01, 0.0],
                         [0.0,  0.0,  0.0,  0.01]])
        return kf

    def update_kinematics(self, tracked_objects):
        """
        Atualiza/prediz a cinemática de cada veículo usando o par estável Predict-Update do Kalman.
        """
        current_frame_ids = set()
        enriched_objects = []

        for obj in tracked_objects:
            obj_id = obj["id"]
            current_frame_ids.add(obj_id)
            self.missed_counters[obj_id] = 0
            
            bbox = obj["bbox_xyxy"]
            center_px_x = (bbox[0] + bbox[2]) / 2.0
            contact_px_y = bbox[3]
            
            real_x, real_y = self._pixel_to_meters(center_px_x, contact_px_y)
            
            # --- CICLO DE PASSOS DO FILTRO DE KALMAN ---
            if obj_id not in self.trackers:
                # Inicializa o filtro para o novo objeto
                self.trackers[obj_id] = self._init_kalman_filter(real_x, real_y)
                # Executa uma predição inicial interna fictícia para estruturar o vetor de estados
                self.trackers[obj_id].predict()
                
            # Atualiza o filtro com a medição do frame atual
            self.trackers[obj_id].update(np.array([[real_x], [real_y]]))
            
            # Agora executa o passo de predição preventiva para o próximo frame
            # Isso garante que a velocidade interna [Vx, Vy] seja calculada de imediato
            self.trackers[obj_id].predict()
            
            # Extrai o estado interno atualizado
            state = self.trackers[obj_id].x
            smooth_x = float(state[0][0])
            smooth_y = float(state[1][0])
            vel_x = float(state[2][0])
            vel_y = float(state[3][0])
            
            speed_ms = np.sqrt(vel_x**2 + vel_y**2)
            speed_kmh = speed_ms * 3.6
            
            obj["position_m"] = (smooth_x, smooth_y)
            obj["velocity_m_s"] = (vel_x, vel_y)
            obj["speed_kmh"] = speed_kmh
            
            enriched_objects.append(obj)

        # --- TRATAMENTO DE OCLUSÃO (PREDIÇÃO PURA VIA INÉRCIA) ---
        all_tracked_ids = list(self.trackers.keys())
        for old_id in all_tracked_ids:
            if old_id not in current_frame_ids:
                self.missed_counters[old_id] = self.missed_counters.get(old_id, 0) + 1
                
                if self.missed_counters[old_id] <= self.max_missed_frames:
                    # O objeto sumiu: o filtro continua prevendo a rota sozinho por inércia
                    self.trackers[old_id].predict()
                    state = self.trackers[old_id].x
                    
                    virtual_obj = {
                        "id": old_id,
                        "class_name": "occluded_vehicle",
                        "confidence": 0.0,
                        "bbox_xyxy": np.array([0, 0, 0, 0]),
                        "mask_polygon": None,
                        "position_m": (float(state[0][0]), float(state[1][0])),
                        "velocity_m_s": (float(state[2][0]), float(state[3][0])),
                        "speed_kmh": np.sqrt(float(state[2][0])**2 + float(state[3][0])**2) * 3.6
                    }
                    enriched_objects.append(virtual_obj)
                else:
                    del self.trackers[old_id]
                    del self.missed_counters[old_id]
                    logging.info(f"[KINEMATICS] Veículo ID #{old_id} removido por inatividade.")

        return enriched_objects