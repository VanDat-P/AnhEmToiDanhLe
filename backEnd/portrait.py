from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid

app = Flask(__name__)
CORS(app)

# Load model
model = YOLO("MaTruongThanh.pt")

# Các bộ phận bắt buộc
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

    # Không detect được gì
    if results.boxes is None or len(results.boxes) == 0:
        os.remove(img_path)
        return jsonify({
            "score": 3,
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

    # =======================
    # 🎯 TÍNH ĐIỂM (NHẸ TAY)
    # =======================
    score = 10

    # Thiếu bộ phận: -1 điểm
    score -= len(missing) * 1

    # Sai vị trí: -1 điểm
    score -= len(position_errors) * 1

    # Thưởng nếu đầy đủ và đúng vị trí
    if len(missing) == 0 and len(position_errors) == 0:
        score += 1

    # Giới hạn điểm
    score = max(3, min(10, round(score, 1)))

    os.remove(img_path)

    return jsonify({
        "score": score,
        "detected": list(boxes.keys()),
        "missing": missing,
        "position_errors": position_errors
    })


if __name__ == "__main__":
    app.run(debug=False)
