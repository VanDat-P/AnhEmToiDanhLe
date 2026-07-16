from tensorflow.keras.models import load_model
from ultralytics import YOLO
import cv2
import numpy as np





print("📦 Đang tải models...")

model = YOLO("portraityolo12n.pt")
print("✅ Đã tải model chân dung")

scenery_model = YOLO("landscape.pt")
print("✅ Đã tải model phong cảnh")

clf_model = load_model("/Users/datphan/AnhEmToiDanhLe/backEnd/phanLoaiAnh.h5")
print("✅ Đã tải model phân loại ảnh")
CLASSES = ["ChanDung", "PhongCanh"]

def classify_image(img_path):
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    size = clf_model.input_shape[1]
    img = cv2.resize(img, (size, size))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    pred = clf_model.predict(img, verbose=0)[0]
    class_id = np.argmax(pred)
    return CLASSES[class_id]
