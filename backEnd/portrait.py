from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)
REQUIRED = ["eye", "eyebrow", "nose", "mouth"]
SCENERY_REQUIRED = ["house", "tree", "sun"]

model = YOLO("best_portrait.pt")
scenery_model = YOLO("best_scenery.pt")

RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# phan loai anh
import cv2
import numpy as np
from tensorflow.keras.models import load_model

# phanloaianh

clf_model = load_model("phanLoaiAnh.h5")
CLASSES = ["ChanDung", "PhongCanh"]
def classify_image(img_path):

    img = cv2.imread(img_path)

    # thêm dòng này
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    size = clf_model.input_shape[1]

    img = cv2.resize(img, (size, size))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    pred = clf_model.predict(img)[0]

    print("Prediction:", pred)

    class_id = np.argmax(pred)

    print("Class:", CLASSES[class_id])

    return CLASSES[class_id]


def get_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

def get_bottom(box):
    return box[3]

def phan_tich_mau_sac(img_cv):
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    do_bao_hoa = np.mean(s)
    do_sang = np.mean(v)
    
    hot_mask = cv2.inRange(hsv, (0, 50, 50), (30, 255, 255)) + cv2.inRange(hsv, (150, 50, 50), (179, 255, 255))
    cold_mask = cv2.inRange(hsv, (45, 50, 50), (135, 255, 255))
    
    hot_pixels = cv2.countNonZero(hot_mask)
    cold_pixels = cv2.countNonZero(cold_mask)
    
    nhan_xet = []
    if do_bao_hoa < 40: nhan_xet.append("Lực tô màu còn hơi nhẹ, tranh nhạt nhòa. Em nhớ ấn bút mạnh tay hơn để tranh rực rỡ nhé!")
    elif do_bao_hoa > 160: nhan_xet.append("Kỹ năng tô màu rất tốt, màu sắc đậm đà và dứt khoát, em giỏi lắm bảo bối.")
    
    if hot_pixels > cold_pixels * 1.5: nhan_xet.append("Tone màu nóng (đỏ, vàng, cam) làm chủ đạo, bức tranh mang lại cảm giác ấm áp, vui tươi.")
    elif cold_pixels > hot_pixels * 1.5: nhan_xet.append("Tone màu lạnh (xanh, tím) làm chủ đạo, tạo ra không gian bình yên, trong trẻo.")
    
    if do_sang < 80: nhan_xet.append("Màu sắc tổng thể hơi tối, có vẻ em đang vẽ cảnh ban đêm hoặc hoàng hôn phải không?")
    return " ".join(nhan_xet) if nhan_xet else "Màu sắc kết hợp rất hài hòa và dịu mắt."

def kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h):
    if not boxes_xyxy: return ["Tranh trống hoặc nét mờ quá, thầy/cô không chấm được bố cục."]
    min_x, min_y = min([b[0] for b in boxes_xyxy]), min([b[1] for b in boxes_xyxy])
    max_x, max_y = max([b[2] for b in boxes_xyxy]), max([b[3] for b in boxes_xyxy])
    ty_le = ((max_x - min_x) * (max_y - min_y)) / (img_w * img_h)
    
    loi = []
    if ty_le < 0.05: loi.append("Lỗi tỷ lệ: Hình vẽ bị quá nhỏ và lọt thỏm giữa tờ giấy. Hãy vẽ to và tự tin lên cục dàng!")
    elif ty_le > 0.85: loi.append("Lỗi lề: Em vẽ hình to quá bị chạm vào sát mép giấy, bức tranh nhìn hơi chật chội rồi cưng ơi.")
    if abs(((min_x + max_x) / 2) - (img_w / 2)) > (img_w * 0.15):
        loi.append("Lỗi xô lệch: Trọng tâm hình vẽ đang bị lệch hẳn sang một bên, chưa căn giữa.")
    return loi if loi else ["Tuyệt vời! Bố cục cân đối, nằm ngay ngắn, amazing good job em!"]

def luat_ty_le_chan_dung(boxes_dict):
    nhan_xet = []
    eyes = boxes_dict.get("eye", [])
    if len(eyes) == 2:
        eyes.sort(key=lambda b: b[0])
        w_avg = ((eyes[0][2]-eyes[0][0]) + (eyes[1][2]-eyes[1][0])) / 2
        khoang_cach = eyes[1][0] - eyes[0][2]
        if khoang_cach > w_avg * 1.6: nhan_xet.append("Hai mắt đang bị vẽ cách xa nhau quá.")
        elif khoang_cach < w_avg * 0.5: nhan_xet.append("Hai mắt vẽ hơi sát nhau cưng ơi.")
            
    noses, mouths = boxes_dict.get("nose", []), boxes_dict.get("mouth", [])
    if noses and mouths:
        if abs(get_center(noses[0])[0] - get_center(mouths[0])[0]) > (mouths[0][2] - mouths[0][0]) * 0.2:
            nhan_xet.append("Mũi và miệng chưa thẳng hàng dọc em nha!")
            
    eb, ey = boxes_dict.get("eyebrow", []), boxes_dict.get("eye", [])
    if eb and ey:
        if (get_center(ey[0])[1] - get_center(eb[0])[1]) > (ey[0][3] - ey[0][1]) * 2.5:
            nhan_xet.append("Lông mày em vẽ cao quá, nhìn nhân vật như đang giật mình vậy.")
            
    return nhan_xet

def luat_xa_gan_va_quy_tac_1_3(boxes_dict, img_w, img_h):
    nhan_xet = []
    h, t, s = boxes_dict.get("house", []), boxes_dict.get("tree", []), boxes_dict.get("sun", [])
    if h and t:
        if get_bottom(h[0]) < get_bottom(t[0]): nhan_xet.append("Lưu ý luật xa gần: Nhà ở gần nên vẽ thấp hơn cây ở xa em nha!")
        else: nhan_xet.append("Em đã áp dụng rất tốt quy luật xa gần, amazing good job!")
    if h:
        hx = get_center(h[0])[0]
        if (img_w * 0.25) < hx < (img_w * 0.75): nhan_xet.append("Nhà đặt ở trung tâm làm điểm nhấn rất tốt!")
        else: nhan_xet.append("Ngôi nhà đặt lệch tạo quy tắc 1/3 rất nghệ thuật, đáng khen đó bảo bối.")
    return nhan_xet

@app.route("/")
def home():
    return render_template("portrait.html")

@app.route("/classify", methods=["POST"])
def classify():
    if "image" not in request.files: return jsonify({"error": "Không có ảnh"}), 400
    img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.jpg")
    request.files["image"].save(img_path)
    loai_anh = classify_image(img_path)
    os.remove(img_path)
    return jsonify({"type": loai_anh})

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files: return jsonify({"error": "Không có ảnh"}), 400
    filename = f"{uuid.uuid4().hex}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    request.files["image"].save(img_path)
    penalty = float(request.form.get("penalty", 1))
    print("🔥 PENALTY NHẬN ĐƯỢC:", penalty)
    img_cv = cv2.imread(img_path)
    img_h, img_w, _ = img_cv.shape
    results = model(img_path, verbose=False)[0]
    boxed_name = f"boxed_{filename}"
    cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

    if not results.boxes:
        os.remove(img_path)
        return jsonify({"score": 0, "missing": REQUIRED, "loi_khuyen_giao_vien": ["Chưa thấy khuôn mặt, em đồ lại nét cho đậm hơn xem sao?"]})

    cls_ids = [int(cls) for cls in results.boxes.cls.cpu().numpy()]
    boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
    
    boxes_dict = {name: [] for name in REQUIRED}
    
    print("\n--- [DEBUG] BẮT ĐẦU CHẤM ẢNH ---")
    for cid, box in zip(cls_ids, boxes_xyxy):
        goc = str(results.names[cid])
        raw_name = goc.strip().lower()
        print(f"🔍 YOLO đọc được chữ: '{goc}'")
        
        if "eyebrow" in raw_name:
            boxes_dict["eyebrow"].append(box)
        elif "eye" in raw_name:
            boxes_dict["eye"].append(box)
        elif "nose" in raw_name:
            boxes_dict["nose"].append(box)
        elif "mouth" in raw_name:
            boxes_dict["mouth"].append(box)

    detected = [k for k, v in boxes_dict.items() if len(v) > 0]
    missing = [k for k in REQUIRED if k not in detected]
    
    print(f"✅ Code đã chốt Phát hiện có: {detected}")
    print(f"❌ Code báo Thiếu: {missing}")
    print("--------------------------------\n")
    
    loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
    loi_ty_le = luat_ty_le_chan_dung(boxes_dict)
    
    loi_khuyen = []
    if "hair" not in detected and "ear" not in detected:
        loi_khuyen.append("Gợi ý: Khuôn mặt sẽ hoàn hảo hơn nếu em vẽ thêm phần viền khuôn mặt, tóc vành tai.")
    if missing:
        loi_khuyen.append(f"Em nhớ bổ sung các bộ phận còn thiếu nhé: {', '.join(missing)}.")

    # score = 10 - len(missing) * 1.5 - len(loi_ty_le) * 1 - (1 if "Lỗi" in loi_bo_cuc[0] else 0)
    score = 10 \
        - len(missing) * (1.5 * penalty) \
        - len(loi_ty_le) * (1 * penalty) \
        - ((1 * penalty) if "Lỗi" in loi_bo_cuc[0] else 0)

    os.remove(img_path)
    return jsonify({
        "score": max(0, min(10, round(score, 1))),
        "detected": detected,
        "missing": missing,
        "nhan_xet_bo_cuc": loi_bo_cuc,
        "nhan_xet_ty_le": loi_ty_le,
        "loi_khuyen_giao_vien": loi_khuyen if loi_khuyen else ["Tranh em vẽ rất tốt, không có gì để chê!"],
        "boxed_image": f"/static/results/{boxed_name}"
    })

@app.route("/predict_scenery", methods=["POST"])
def predict_scenery():
    if "image" not in request.files: return jsonify({"error": "Không có ảnh"}), 400
    filename = f"{uuid.uuid4().hex}.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    request.files["image"].save(img_path)
    penalty = float(request.form.get("penalty", 1))
    print("🔥 PENALTY NHẬN ĐƯỢC:", penalty)
    img_cv = cv2.imread(img_path)
    img_h, img_w, _ = img_cv.shape
    results = scenery_model(img_path, verbose=False)[0]
    boxed_name = f"boxed_{filename}"
    cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

    if not results.boxes:
        os.remove(img_path)
        return jsonify({"score": 0, "missing": SCENERY_REQUIRED, "loi_khuyen_giao_vien": ["Tranh trống quá, em thử vẽ thêm nhà và cây đi cục dàng!"]})

    cls_ids = [int(cls) for cls in results.boxes.cls.cpu().numpy()]
    boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
    
    boxes_dict = {name: [] for name in SCENERY_REQUIRED}
    for cid, box in zip(cls_ids, boxes_xyxy):
        goc = str(results.names[cid])
        raw_name = goc.strip().lower()
        
        if "house" in raw_name:
            boxes_dict["house"].append(box)
        elif "tree" in raw_name:
            boxes_dict["tree"].append(box)
        elif "sun" in raw_name:
            boxes_dict["sun"].append(box)

    detected = [k for k, v in boxes_dict.items() if len(v) > 0]
    missing = [v for v in SCENERY_REQUIRED if v not in detected]
    
    loi_khuyen = []
    if "house" not in detected:
        loi_khuyen.append("Em thiếu mất ngôi nhà rồi huhu, đây là điểm nhấn quan trọng nhất của tranh phong cảnh đó.")
    if "tree" not in detected:
        loi_khuyen.append("Thêm một vài bóng cây xanh sẽ giúp bức tranh có sức sống hơn rất nhiều.")
    if "sun" not in detected:
        loi_khuyen.append("Bầu trời hơi trống, em thử vẽ thêm ông mặt trời, mây và chim xem sao nha cục dàng.")
    if len(detected) == 3:
        loi_khuyen.append("Tranh của em rất đầy đủ chi tiết! Nếu muốn xuất sắc hơn, có thể điểm thêm bãi cỏ hoặc đàn chim lững lờ trôi nhé.")

    loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
    
    # score = (4 if "house" in detected else 0) + (4 if "tree" in detected else 0) + (2 if "sun" in detected else 0)
    # if "Lỗi" in loi_bo_cuc[0]: score -= 1.5
    score = (4 if "house" in detected else 0) \
      + (4 if "tree" in detected else 0) \
      + (2 if "sun" in detected else 0)

    if "Lỗi" in loi_bo_cuc[0]:
        score -= 1.5 * penalty
    
    os.remove(img_path)
    return jsonify({
        "score": max(0, min(10, round(score, 1))),
        "detected": detected,
        "missing": missing,
        "nhan_xet_bo_cuc": loi_bo_cuc,
        "nhan_xet_mau_sac": phan_tich_mau_sac(img_cv),
        "nhan_xet_nghe_thuat": luat_xa_gan_va_quy_tac_1_3(boxes_dict, img_w, img_h),
        "loi_khuyen_giao_vien": loi_khuyen,
        "boxed_image": f"/static/results/{boxed_name}"
    })

if __name__ == "__main__":
    app.run(debug=False)




    