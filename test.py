import cv2
import numpy as np
from tensorflow.keras.models import load_model

categories = ['ChanDung', 'PhongCanh']

model = load_model("phanLoaiAnh.h5")

img = cv2.imread("/Users/datphan/AnhEmToiDanhLe/backEnd/uploads/c13f92f06ae64d50b694351e90f3363d.jpg")
img = cv2.resize(img, (64, 64))
img = img / 255.0
img = np.expand_dims(img, axis=0)

pred = model.predict(img)
print("Kết quả:", categories[np.argmax(pred)])
