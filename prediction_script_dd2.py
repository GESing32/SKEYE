"""
Use trained NDVI+NDRE CNN model (.h5) to predict classes on new images.

Example usage (batch mode):
    python predict_with_model.py \
        --model ndvi_ndre_cnn_model_balanced.h5 \
        --classes ndvi_ndre_classes.json \
        --nir_dir ./Near_Infrared_Channel/Test_Images \
        --red_dir ./Red_Channel/Test_Images \
        --red_edge_dir ./Red_Edge_Channel/Test_Images \
        --out_csv predictions.csv

Example usage (single image):
    python predict_with_model.py \
        --model ndvi_ndre_cnn_model_balanced.h5 \
        --classes ndvi_ndre_classes.json \
        --nir_dir ./Near_Infrared_Channel/Test_Images \
        --red_dir ./Red_Channel/Test_Images \
        --red_edge_dir ./Red_Edge_Channel/Test_Images \
        --filename IMG_001.jpg \
        --out_png ndvi_preview.png
"""
import os
import cv2
import json
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt

IMG_SIZE = (64, 64)

# ---------- Compute indices ----------
def compute_indices(nir, red, red_edge):
    nir = nir.astype(np.float32)
    red = red.astype(np.float32)
    red_edge = red_edge.astype(np.float32)
    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    ndre = (nir - red_edge) / (nir + red_edge + eps)
    ndvi = np.clip(ndvi, -1.0, 1.0)
    ndre = np.clip(ndre, -1.0, 1.0)
    return ndvi, ndre

def prepare_tensor(nir, red, re):
    ndvi, ndre = compute_indices(nir, red, re)
    ndvi_r = cv2.resize(ndvi, IMG_SIZE, interpolation=cv2.INTER_AREA)
    ndre_r = cv2.resize(ndre, IMG_SIZE, interpolation=cv2.INTER_AREA)
    X = np.stack([ndvi_r, ndre_r], axis=-1).astype(np.float32)[np.newaxis, ...]
    return X, float(np.mean(ndvi)), float(np.mean(ndre)), ndvi

def save_quicklook(ndvi, out_png):
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.title("NDVI quicklook")
    plt.colorbar()
    plt.savefig(out_png, dpi=200)
    plt.close()

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Path to trained .h5 model")
    ap.add_argument("--classes", required=True, help="Path to classes JSON")
    ap.add_argument("--nir_dir", required=True, help="NIR folder")
    ap.add_argument("--red_dir", required=True, help="Red folder")
    ap.add_argument("--red_edge_dir", required=True, help="Red-Edge folder")
    ap.add_argument("--filename", help="Single image filename (must exist in all three folders)")
    ap.add_argument("--out_csv", help="CSV file for batch mode")
    ap.add_argument("--out_png", help="Save NDVI preview PNG for single image")
    args = ap.parse_args()

    # load model and classes
    model = tf.keras.models.load_model(args.model)
    with open(args.classes, "r") as f:
        classes = json.load(f)

    if args.filename:  # ---- single image mode ----
        nir = cv2.imread(os.path.join(args.nir_dir, args.filename), cv2.IMREAD_GRAYSCALE)
        red = cv2.imread(os.path.join(args.red_dir, args.filename), cv2.IMREAD_GRAYSCALE)
        re  = cv2.imread(os.path.join(args.red_edge_dir, args.filename), cv2.IMREAD_GRAYSCALE)
        X, mean_ndvi, mean_ndre, ndvi_full = prepare_tensor(nir, red, re)
        preds = model.predict(X, verbose=0)[0]
        idx = int(np.argmax(preds))
        print("--------------- Prediction ---------------")
        print(f"Filename:        {args.filename}")
        print(f"Predicted class: {classes[idx]}")
        print(f"Confidence:      {preds[idx]:.4f}")
        print(f"Mean NDVI:       {mean_ndvi:.5f}")
        print(f"Mean NDRE:       {mean_ndre:.5f}")
        if args.out_png:
            save_quicklook(ndvi_full, args.out_png)
            print(f"Saved NDVI preview to {args.out_png}")
        return

    # ---- batch mode ----
    results = []
    nir_files = set(os.listdir(args.nir_dir))
    red_files = set(os.listdir(args.red_dir))
    re_files  = set(os.listdir(args.red_edge_dir))
    common = sorted(nir_files & red_files & re_files)
    for fname in common:
        nir = cv2.imread(os.path.join(args.nir_dir, fname), cv2.IMREAD_GRAYSCALE)
        red = cv2.imread(os.path.join(args.red_dir, fname), cv2.IMREAD_GRAYSCALE)
        re  = cv2.imread(os.path.join(args.red_edge_dir, fname), cv2.IMREAD_GRAYSCALE)
        X, mean_ndvi, mean_ndre, _ = prepare_tensor(nir, red, re)
        preds = model.predict(X, verbose=0)[0]
        idx = int(np.argmax(preds))
        results.append({
            "filename": fname,
            "mean_ndvi": mean_ndvi,
            "mean_ndre": mean_ndre,
            "predicted_class": classes[idx],
            "confidence": float(preds[idx])
        })
    if args.out_csv:
        pd.DataFrame(results).to_csv(args.out_csv, index=False)
        print(f"✅ Wrote {len(results)} rows to {args.out_csv}")

if __name__ == "__main__":
    main()
