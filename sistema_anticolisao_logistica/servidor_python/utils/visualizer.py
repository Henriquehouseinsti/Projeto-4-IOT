# visualizer.py
# Renderização OpenCV (imshow)

import cv2
import numpy as np

class Visualizer:
    def __init__(self, draw_boxes=True, draw_velocities=True, draw_masks=True):
        """
        Utilitário especializado em renderizar na tela os resultados da inferência, 
        cinemática e alertas.
        """
        self.draw_boxes = draw_boxes
        self.draw_velocities = draw_velocities
        self.draw_masks = draw_masks

    def draw_telemetry(self, frame, enriched_objects, collision_events, fps):
        """
        Renderiza todas as informações visuais sobre o frame original do OpenCV.
        
        :param frame: Imagem BGR original da câmera
        :param enriched_objects: Lista de objetos contendo bboxes, posições e velocidades (m/s)
        :param collision_events: Lista de colisões iminentes detectadas no frame atual
        :param fps: Frames por Segundo atual do processamento
        :return: O frame modificado com os desenhos técnicos
        """
        if frame is None:
            return frame

        # 1. Renderiza os Objetos Rastreados
        for obj in enriched_objects:
            obj_id = obj["id"]
            label = obj["class_name"]
            speed = obj["speed_kmh"]
            pos = obj["position_m"]
            bbox = obj["bbox_xyxy"].astype(int)

            # Define cor dinâmica: se o veículo for oclusivo/virtual, usa cinza. Caso contrário, azul.
            color = (128, 128, 128) if label == "occluded_vehicle" else (255, 120, 0)

            # Desenha a caixa delimitadora retangular (Bounding Box)
            if self.draw_boxes and not np.all(bbox == 0):
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

            # Desenha a máscara de segmentação do polígono (se disponível)
            if self.draw_masks and obj.get("mask_polygon") is not None:
                poly_pts = obj["mask_polygon"].astype(np.int32)
                # Cria uma camada semi-transparente para a máscara
                overlay = frame.copy()
                cv2.fillPoly(overlay, [poly_pts], color)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

            # Texto informativo acoplado ao veículo (ID, Classe, Velocidade e Posição Real)
            text = f"ID:{obj_id} {label} | {speed:.1f}km/h"
            pos_text = f"X: {pos[0]:.2f}m , Y: {pos[1]:.2f}m"
            
            # Posiciona o texto logo acima da caixa do objeto
            y_pos = max(bbox[1] - 10, 20) if bbox[1] > 0 else 20
            cv2.putText(frame, text, (bbox[0], y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(frame, pos_text, (bbox[0], y_pos + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            # Desenha a linha indicativa do vetor velocidade (Se hove movimento)
            if self.draw_velocities and "velocity_m_s" in obj:
                vx, vy = obj["velocity_m_s"]
                if abs(vx) > 0.05 or abs(vy) > 0.05:
                    center_x = int((bbox[0] + bbox[2]) / 2)
                    center_y = int(bbox[3]) # Base do veículo
                    
                    # Multiplica o vetor por um fator de escala para que a seta fique visível na imagem
                    end_x = int(center_x + (vx * 20))
                    end_y = int(center_y + (vy * 20))
                    cv2.arrowedLine(frame, (center_x, center_y), (end_x, end_y), (0, 255, 255), 2, tipLength=0.3)

        # 2. Renderiza o HUD Superior Esquerdo (Estatísticas Gerais do Servidor)
        cv2.rectangle(frame, (10, 10), (280, 110), (0, 0, 0), -1) # Fundo preto
        cv2.rectangle(frame, (10, 10), (280, 110), (100, 100, 100), 1) # Borda cinza
        
        cv2.putText(frame, f"FPS: {fps:.1f}", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Maquinarios: {len(enriched_objects)}", (25, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        status_txt = "STATUS: MONITORANDO" if len(collision_events) == 0 else "STATUS: ALERTA EMITIDO"
        status_color = (0, 255, 0) if len(collision_events) == 0 else (0, 0, 255)
        cv2.putText(frame, status_txt, (25, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        # 3. Desenha Tarja Vermelha em caso de Alerta de Impacto iminente
        if len(collision_events) > 0:
            # Cria um overlay translúcido vermelho piscante/sólido no topo da imagem
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], 40), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
            
            # Texto centralizado de perigo
            evt = collision_events[0]
            alert_msg = f"!!! PERIGO DE COLISAO: VEICULO #{evt['veiculo_1']} e #{evt['veiculo_2']} | TTC: {evt['time_to_collision']:.2f}s !!!"
            cv2.putText(frame, alert_msg, (50, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame