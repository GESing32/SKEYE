# NDVI+NDRE 2-Channel CNN Classifier with Balanced Dataset
import os
import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from collections import defaultdict
import random

# ---------- Compute NDVI and NDRE ----------
def compute_indices(nir, red, red_edge):
    nir = nir.astype(np.float32)
    red = red.astype(np.float32)
    red_edge = red_edge.astype(np.float32)

    ndvi = (nir - red) / (nir + red + 1e-6)
    ndre = (nir - red_edge) / (nir + red_edge + 1e-6)

    ndvi = np.clip(ndvi, -1, 1)
    ndre = np.clip(ndre, 0, 1)
    return ndvi, ndre

# ---------- Balanced Dataset Builder ----------
def build_balanced_ndvi_ndre_dataset(base_path, labels_csv, split='Train'):
    images = defaultdict(list)
    labels = defaultdict(list)

    df = pd.read_csv(labels_csv)
    df['filename'] = df['filename'].apply(lambda x: os.path.basename(x))
    grouped = df.groupby('filename')['class'].apply(list).to_dict()

    nir_dir = os.path.join(base_path, 'Near_Infrared_Channel', f'{split}_Images')
    red_dir = os.path.join(base_path, 'Red_Channel', f'{split}_Images')
    red_edge_dir = os.path.join(base_path, 'Red_Edge_Channel', f'{split}_Images')

    for filename in os.listdir(nir_dir):
        if not filename.lower().endswith('.jpg') or filename not in grouped:
            continue

        label = max(set(grouped[filename]), key=grouped[filename].count)

        nir = cv2.imread(os.path.join(nir_dir, filename), cv2.IMREAD_GRAYSCALE)
        red = cv2.imread(os.path.join(red_dir, filename), cv2.IMREAD_GRAYSCALE)
        red_edge = cv2.imread(os.path.join(red_edge_dir, filename), cv2.IMREAD_GRAYSCALE)

        if nir is None or red is None or red_edge is None:
            continue

        ndvi, ndre = compute_indices(nir, red, red_edge)
        ndvi = cv2.resize(ndvi, (64, 64))
        ndre = cv2.resize(ndre, (64, 64))
        stacked = np.stack([ndvi, ndre], axis=-1).astype(np.float32)

        images[label].append(stacked)
        labels[label].append(label)

    # Balance dataset by downsampling majority class
    min_count = min(len(lst) for lst in labels.values())
    all_imgs, all_lbls = [], []
    for lbl in images:
        selected_indices = random.sample(range(len(images[lbl])), min_count)
        for idx in selected_indices:
            all_imgs.append(images[lbl][idx])
            all_lbls.append(labels[lbl][idx])

    X = np.array(all_imgs)
    encoder = LabelEncoder()
    y = encoder.fit_transform(all_lbls)
    return X, y, encoder

# ---------- CNN Model ----------
def build_cnn_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(64, 64, 2)),
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D(),
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D(),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(2, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

# ---------- Main ----------
base_path = os.path.join(os.path.dirname(__file__), 'Spectral_Images1','Spectral_Images')
train_csv = os.path.join(base_path, 'Labels', 'Train_labels.csv')
test_csv = os.path.join(base_path, 'Labels', 'Test_labels.csv')

X_train, y_train, encoder = build_balanced_ndvi_ndre_dataset(base_path, train_csv, split='Train')
X_test, y_test, _ = build_balanced_ndvi_ndre_dataset(base_path, test_csv, split='Test')

# Augmentation
train_datagen = ImageDataGenerator(
    rotation_range=10,
    zoom_range=0.1,
    width_shift_range=0.1,
    height_shift_range=0.1
)
train_generator = train_datagen.flow(X_train, y_train, batch_size=32)

model = build_cnn_model()
model.fit(train_generator, validation_data=(X_test, y_test), epochs=15)
model.save("ndvi_ndre_cnn_model_balanced.h5")

# ---------- Batch Prediction ----------
def batch_ndvi_predictions(model, encoder, base_path, output_csv="ndvi_predictions.csv"):
    red_dir = os.path.join(base_path, "Red_Channel", "Test_Images")
    nir_dir = os.path.join(base_path, "Near_Infrared_Channel", "Test_Images")
    red_edge_dir = os.path.join(base_path, "Red_Edge_Channel", "Test_Images")

    results = []

    for filename in os.listdir(nir_dir):
        if not filename.endswith(".jpg"):
            continue

        nir = cv2.imread(os.path.join(nir_dir, filename), cv2.IMREAD_GRAYSCALE)
        red = cv2.imread(os.path.join(red_dir, filename), cv2.IMREAD_GRAYSCALE)
        red_edge = cv2.imread(os.path.join(red_edge_dir, filename), cv2.IMREAD_GRAYSCALE)

        if nir is None or red is None or red_edge is None:
            continue

        ndvi, ndre = compute_indices(nir, red, red_edge)
        mean_ndvi = float(np.mean(ndvi))
        mean_ndre = float(np.mean(ndre))

        ndvi = cv2.resize(ndvi, (64, 64))
        ndre = cv2.resize(ndre, (64, 64))
        input_img = np.stack([ndvi, ndre], axis=-1)[np.newaxis, ...].astype(np.float32)

        pred = model.predict(input_img)
        predicted_class = encoder.inverse_transform([np.argmax(pred)])[0]
        confidence = float(np.max(pred))

        results.append({
            "filename": filename,
            "mean_ndvi": mean_ndvi,
            "mean_ndre": mean_ndre,
            "predicted_class": predicted_class,
            "confidence": confidence
        })

    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"✅ Batch results saved to {output_csv}")

batch_ndvi_predictions(model, encoder, base_path)

# ---------- Visual Debug ----------
idx = random.randint(0, len(X_train)-1)
plt.imshow(X_train[idx][:,:,0], cmap='RdYlGn')
plt.title(f"True Label: {encoder.inverse_transform([y_train[idx]])[0]}")
plt.colorbar()
plt.show()
