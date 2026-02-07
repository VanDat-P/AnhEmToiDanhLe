from flask import Flask, request, jsonify,render_template
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid





RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)

# phan loai anh
import cv2
import numpy as np
from tensorflow.keras.models import load_model

# phanloaianh

clf_model = load_model("phanLoaiAnh.h5")
CLASSES = ["ChanDung", "PhongCanh"]
def classify_image(img_path):
    img = cv2.imread(img_path)
    if img is None:
        raise Exception("Không đọc được ảnh (cv2.imread = None)")
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Danh sách các kích thước để thử
    test_sizes = [(56, 56), (224, 224), (112, 112), (64, 64)]
    
    for size in test_sizes:
        try:
            img_resized = cv2.resize(img, size)
            img_resized = img_resized / 255.0
            
            # Nếu model là dense (2D input)
            if len(clf_model.input_shape) == 2:
                img_processed = img_resized.flatten()
                # Kiểm tra số features
                if img_processed.shape[0] != clf_model.input_shape[1]:
                    # Pad hoặc crop để đúng số features
                    target_features = clf_model.input_shape[1]
                    if img_processed.shape[0] > target_features:
                        img_processed = img_processed[:target_features]
                    else:
                        img_processed = np.pad(img_processed, 
                                             (0, target_features - img_processed.shape[0]))
                img_processed = img_processed.reshape(1, -1)
            else:
                # Conv model
                img_processed = np.expand_dims(img_resized, axis=0)
            
            print(f"Testing with size {size}, input shape: {img_processed.shape}")
            
            pred = clf_model.predict(img_processed, verbose=0)
            class_id = int(np.argmax(pred))
            
            return CLASSES[class_id]
            
        except Exception as e:
            print(f"Failed with size {size}: {e}")
            continue
    
    raise Exception("Không thể phân loại với bất kỳ kích thước nào đã thử")
app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("portrait.html")
model = YOLO("portrait.pt")

REQUIRED = {
    0: "eyebrow",
    1: "eye",
    2: "nose",
    3: "mouth",
}

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def check_position(boxes):
    errors = []

    # Mắt phải trên mũi
    if "eye" in boxes and "nose" in boxes:
        if center(boxes["eye"])[1] > center(boxes["nose"])[1]:
            errors.append("Mắt phải nằm trên mũi")

    # Miệng phải dưới mũi
    if "mouth" in boxes and "nose" in boxes:
        if center(boxes["mouth"])[1] < center(boxes["nose"])[1]:
            errors.append("Miệng phải nằm dưới mũi")

    # Chân mày phải trên mắt
    if "eyebrow" in boxes and "eye" in boxes:
        if center(boxes["eyebrow"])[1] > center(boxes["eye"])[1]:
            errors.append("Chân mày phải nằm trên mắt")

    return errors



@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "Không có ảnh"}), 400

    image_file = request.files["image"]

    filename = f"{uuid.uuid4().hex}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    image_file.save(img_path)

    results = model(img_path, verbose=False)[0]
    boxed_img = results.plot()  

    if results.boxes is None or len(results.boxes) == 0:
        os.remove(img_path)
        return jsonify({
            "score": 0,
            "detected": [],
            "missing": list(REQUIRED.values()),
            "position_errors": ["Không detect được bộ phận nào"]
        })

    # bouding box
    boxed_name = f"boxed_{filename}"
    boxed_path = os.path.join(RESULT_FOLDER, boxed_name)
    cv2.imwrite(boxed_path, boxed_img)
    detected_classes = list(set([results.names[int(cls)] for cls in results.boxes.cls]))
    boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()

    boxes = {}
    for cid, box in zip(detected_classes, boxes_xyxy):
        name = REQUIRED.get(cid)
        if name and name not in boxes:
            boxes[name] = box

    position_errors = check_position(boxes)

    detected = [name for name in detected_classes if name in REQUIRED.values()]
    missing = [name for name in REQUIRED.values() if name not in detected]

    score = 10 - len(missing) * 1.5 - len(position_errors) * 2
    score = max(0, round(score, 1))

    os.remove(img_path)

    return jsonify({
        "score": score,
        "detected": detected,
        "missing": missing,
        "position_errors": position_errors,
         "boxed_image": f"/static/results/{boxed_name}"
    })


# phong canh cua binh kun va lac kun
scenery_model = YOLO("landscape.pt")

SCENERY_REQUIRED = {
    0: "house",
    1: "tree",
    2: "sun",
}
@app.route("/predict_scenery", methods=["POST"])
def predict_scenery():
    if "image" not in request.files:
        return jsonify({"error": "Không có ảnh"}), 400

    image_file = request.files["image"]

    filename = f"{uuid.uuid4().hex}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    image_file.save(img_path)

    results = scenery_model(img_path, verbose=False)[0]
    boxed_img = results.plot()
    boxed_name = f"boxed_{filename}"
    boxed_path = os.path.join(RESULT_FOLDER, boxed_name)
    cv2.imwrite(boxed_path, boxed_img)
    if results.boxes is None or len(results.boxes) == 0:
        os.remove(img_path)
        return jsonify({
            "score": 0,
            "detected": [],
            "missing": list(SCENERY_REQUIRED.values()),
            "position_errors": ["Tranh phong cảnh quá trống"]
        })
    detected_classes = list(set([results.names[int(cls)] for cls in results.boxes.cls]))
    detected = []
    for name in detected_classes:
        if name in SCENERY_REQUIRED.values():
            detected.append(name)
    missing = [v for v in SCENERY_REQUIRED.values() if v not in detected]

    score = 0
    if "house" in detected: score += 4
    if "tree" in detected: score += 4
    if "sun" in detected or len(detected) >= 3: score += 2

    os.remove(img_path)

    return jsonify({
        "score": score,
        "detected": detected,
        "missing": missing,
        "position_errors": [],
        "boxed_image": f"/static/results/{boxed_name}"
     

    })
@app.route("/classify", methods=["POST"])
def classify():
    if "image" not in request.files:
        return jsonify({"error": "Không có ảnh"}), 400

    image_file = request.files["image"]

    filename = f"{uuid.uuid4().hex}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    image_file.save(img_path)

    try:
        loai_anh = classify_image(img_path)
    except Exception as e:
        os.remove(img_path)
        return jsonify({"error": str(e)}), 500

    os.remove(img_path)

    return jsonify({
        "type": loai_anh
    })


if __name__ == "__main__":
    app.run(debug=False)
