#!/usr/bin/env python3
"""
Script de treinamento do modelo YOLO customizado.
Uso: python treinar_modelo.py [--epochs 80] [--batch 8] [--device cpu]
"""

import argparse
import random
import shutil
import sys
from pathlib import Path

import yaml


def encontrar_data_yaml(dataset_dir: Path) -> Path:
    """Busca data.yaml em dataset/ ou em qualquer subpasta (ex: My First Project.v1i.yolov11/)."""
    candidato_direto = dataset_dir / "data.yaml"
    if candidato_direto.exists():
        return candidato_direto

    for yaml_file in dataset_dir.rglob("data.yaml"):
        return yaml_file

    return candidato_direto  # retorna o path padrao para gerar mensagem de erro


def criar_split_validacao(train_images_dir: Path, train_labels_dir: Path,
                          val_images_dir: Path, val_labels_dir: Path,
                          pct_val: float = 0.2):
    """Move 20% das imagens de treino para validacao."""
    imagens = list(train_images_dir.glob("*.*"))
    random.shuffle(imagens)
    n_val = max(1, int(len(imagens) * pct_val))
    selecionadas = imagens[:n_val]

    val_images_dir.mkdir(parents=True, exist_ok=True)
    val_labels_dir.mkdir(parents=True, exist_ok=True)

    movidas = 0
    for img in selecionadas:
        label = train_labels_dir / (img.stem + ".txt")
        shutil.move(str(img), val_images_dir / img.name)
        if label.exists():
            shutil.move(str(label), val_labels_dir / label.name)
        movidas += 1

    print(f"[OK] Split de validacao criado: {movidas} imagens movidas de train -> valid")


def resolver_paths_dataset(data_yaml_path: Path) -> Path:
    """
    O Roboflow exporta data.yaml com paths relativos como '../train/images'.
    Gera data_abs.yaml com paths absolutos corretos.
    Se valid nao existir, cria automaticamente a partir de 20% do train.
    """
    with open(data_yaml_path, "r") as f:
        data = yaml.safe_load(f)

    yaml_dir = data_yaml_path.parent

    def resolver_path(raw: str) -> Path | None:
        for tentativa in [
            (yaml_dir / raw).resolve(),
            (yaml_dir / Path(raw).name).resolve(),
            (yaml_dir / raw.lstrip("../")).resolve(),
        ]:
            if tentativa.exists():
                return tentativa
        return None

    # Resolve train primeiro (obrigatorio)
    train_path = resolver_path(data.get("train", "../train/images"))
    if train_path is None:
        print("[ERRO] Pasta train/images nao encontrada.")
        print(f"       Procurado a partir de: {yaml_dir}")
        sys.exit(1)

    data["train"] = str(train_path)
    train_labels = train_path.parent.parent / "labels" / "train" if "images" in str(train_path) else train_path.parent / "labels"
    # Caminho padrao de labels para train
    train_labels_dir = Path(str(train_path).replace("images", "labels"))

    # Resolve val — se nao existir, cria split automatico
    val_path = resolver_path(data.get("val", "../valid/images"))
    if val_path is None:
        print("[AVISO] Pasta valid/images nao encontrada. Criando split de 20% a partir do train...")
        val_images_dir = yaml_dir / "valid" / "images"
        val_labels_dir = yaml_dir / "valid" / "labels"
        criar_split_validacao(train_path, train_labels_dir, val_images_dir, val_labels_dir)
        val_path = val_images_dir

    data["val"] = str(val_path)

    # Resolve test (opcional)
    test_path = resolver_path(data.get("test", "../test/images"))
    if test_path:
        data["test"] = str(test_path)
    else:
        data.pop("test", None)

    abs_yaml_path = yaml_dir / "data_abs.yaml"
    with open(abs_yaml_path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    print(f"[OK] data_abs.yaml gerado: {abs_yaml_path}")
    return abs_yaml_path


def main():
    parser = argparse.ArgumentParser(description="Treina modelo YOLOv11 customizado")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", type=str, default="")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    dataset_dir = script_dir / "dataset"

    # --- Encontra data.yaml automaticamente (mesmo dentro de subpasta) ---
    data_yaml = encontrar_data_yaml(dataset_dir)

    if not data_yaml.exists():
        print(f"[ERRO] data.yaml nao encontrado em: {dataset_dir}")
        print("       Extraia o zip do Roboflow em servidor_python/dataset/ e tente novamente.")
        sys.exit(1)

    print(f"[OK] Dataset encontrado: {data_yaml}")

    weights_dir = script_dir / "weights"
    weights_dir.mkdir(exist_ok=True)

    # --- Corrige paths e cria split de validacao se necessario ---
    abs_yaml = resolver_paths_dataset(data_yaml)

    # --- Importa YOLO ---
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERRO] ultralytics nao instalado. Rode: pip install ultralytics")
        sys.exit(1)

    print("\n[INFO] Carregando yolo11n.pt como base para transfer learning...")
    model = YOLO("yolo11n.pt")

    device = args.device if args.device else ("0" if _tem_gpu() else "cpu")
    print(f"[INFO] Dispositivo: {device}")
    if device == "cpu":
        print("[AVISO] CPU detectada — treino pode demorar 1-3 horas.")

    print(f"\n[INFO] Iniciando treinamento | epocas={args.epochs} | imgsz={args.imgsz} | batch={args.batch}\n")

    model.train(
        data=str(abs_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=str(script_dir / "runs" / "detect"),
        name="treino_carrinho",
        exist_ok=True,
        patience=20,
        save_period=10,
        verbose=True,
    )

    # --- Copia melhor modelo ---
    best_pt = script_dir / "runs" / "detect" / "treino_carrinho" / "weights" / "best.pt"
    destino = weights_dir / "yolo11_carrinho.pt"

    if best_pt.exists():
        shutil.copy(best_pt, destino)
        print(f"\n[SUCESSO] Modelo salvo em: {destino}")
        print("\nProximo passo — atualize config.yaml:")
        print('  perception:')
        print('    model_path: "weights/yolo11_carrinho.pt"')
    else:
        print(f"\n[AVISO] best.pt nao encontrado em {best_pt}")


def _tem_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


if __name__ == "__main__":
    main()
