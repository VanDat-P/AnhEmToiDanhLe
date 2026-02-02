from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid

app = Flask(__name__)
CORS(app)

model = YOLO("MaTruongThanh.pt")

REQUIRED = {

    0: "ear",
    1: "eyebrow",
    2: "eye",
    3: "nose",
    4: "mouth",
  
}

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def check_position(boxes):
    errors = []

    if "face" not in boxes:
        return ["Không detect được khuôn mặt"]

    face = boxes["face"]
    fy1, fy2 = face[1], face[3]

    if "eye" in boxes and "nose" in boxes:
        if center(boxes["eye"])[1] > center(boxes["nose"])[1]:
            errors.append("Mắt phải nằm trên mũi")

    if "mouth" in boxes and "nose" in boxes:
        if center(boxes["mouth"])[1] < center(boxes["nose"])[1]:
            errors.append("Miệng phải nằm dưới mũi")

    if "eyebrow" in boxes and "eye" in boxes:
        if center(boxes["eyebrow"])[1] > center(boxes["eye"])[1]:
            errors.append("Chân mày phải nằm trên mắt")

    if "hair" in boxes:
        if center(boxes["hair"])[1] > center(face)[1]:
            errors.append("Tóc phải nằm trên khuôn mặt")

    if "ear" in boxes and "eye" in boxes:
        if abs(center(boxes["ear"])[1] - center(boxes["eye"])[1]) > (fy2 - fy1) * 0.25:
            errors.append("Tai nên nằm ngang mức mắt")

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

    detected_classes = [int(c) for c in results.boxes.cls.cpu().numpy()]
    boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()

    boxes = {}
    for cid, box in zip(detected_classes, boxes_xyxy):
        name = REQUIRED.get(cid)
        if name and name not in boxes:
            boxes[name] = box

    missing = [name for name in REQUIRED.values() if name not in boxes]
    position_errors = check_position(boxes)

    score = 10 - len(missing) * 1.5 - len(position_errors) * 2
    score = max(0, round(score, 1))

    os.remove(img_path)

    return jsonify({
        "score": score,
        "detected": list(boxes.keys()),
        "missing": missing,
        "position_errors": position_errors
    })



if __name__ == "__main__":
    app.run(debug=True)

