from flask import Flask, request, jsonify,render_template
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("portrait.html")
model = YOLO("MaTruongThanh.pt")

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

    if results.boxes is None or len(results.boxes) == 0:
        os.remove(img_path)
        return jsonify({
            "score": 0,
            "detected": [],
            "missing": list(REQUIRED.values()),
            "position_errors": ["Không detect được bộ phận nào"]
        })

    detected_classes = list(set([results.names[int(cls)] for cls in results.boxes.cls]))
    boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()

    boxes = {}
    for cid, box in zip(detected_classes, boxes_xyxy):
        name = REQUIRED.get(cid)
        if name and name not in boxes:
            boxes[name] = box
    position_errors = check_position(boxes)
    
    detected = []
    for name in detected_classes:
        if name in REQUIRED.values():
            detected.append(name)

    missing = [name for name in REQUIRED.values() if name not in detected]
    

    score = 10 - len(missing) * 1.5 - len(position_errors) * 2
    score = max(0, round(score, 1))

    os.remove(img_path)

    return jsonify({
        "score": score,
        "detected": detected,
        "missing": missing,
        "position_errors": position_errors
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
        "position_errors": []
    })


if __name__ == "__main__":
    app.run(debug=False)   

