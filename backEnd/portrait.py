from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid
import cv2
import numpy as np
from tensorflow.keras.models import load_model

app = Flask(__name__)

# === CORS phải được khởi tạo NGAY sau app ===
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "http://127.0.0.1:3000"])

# === ROUTE TRANG CHỦ ===
@app.route('/')
def home():
    return render_template('portrait.html')

@app.route('/adjustment')
def adjustment():
    return render_template('adjustment.html')

# === CÁC HẰNG SỐ ===
REQUIRED = ["eye", "eyebrow", "nose", "mouth", "face", "ear", "hair"]
SCENERY_REQUIRED = ["house", "tree", "sun"]

# === LOAD MODELS ===
model = YOLO("portraityolo12n.pt")
scenery_model = YOLO("landscape.pt")
clf_model = load_model("phanLoaiAnh.h5")
CLASSES = ["ChanDung", "PhongCanh"]

# === TẠO THƯ MỤC ===
RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === PHÂN LOẠI ẢNH ===
def classify_image(img_path):
    img = cv2.imread(img_path)
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

# === CÁC HÀM TIỆN ÍCH ===
def get_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

def get_bottom(box):
    return box[3]

def get_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])

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
            
    # MỚI THÊM: Luật vị trí tai so với mắt
    ears = boxes_dict.get("ear", [])
    if ears and ey:
        ear_y = get_center(ears[0])[1]
        eye_y = get_center(ey[0])[1]
        if abs(ear_y - eye_y) > (ey[0][3] - ey[0][1]) * 1.5:
            nhan_xet.append("Vị trí tai đang bị vẽ lệch lên quá cao hoặc thấp hơn so với mắt khá nhiều.")
            
    return nhan_xet

def phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h):
    nhan_xet = []
    h, t, s = boxes_dict.get("house", []), boxes_dict.get("tree", []), boxes_dict.get("sun", [])
    
    # Luật xa gần
    if h and t:
        if get_bottom(h[0]) < get_bottom(t[0]): 
            nhan_xet.append("Lưu ý luật xa gần: Nhà ở gần nên vẽ thấp hơn cây ở xa em nha!")
        else: 
            nhan_xet.append("Em đã áp dụng rất tốt quy luật xa gần, amazing good job!")
        
    # Quy tắc 1/3 (Điểm nhấn)
    if h:
        hx = get_center(h[0])[0]
        if (img_w * 0.25) < hx < (img_w * 0.75): 
            nhan_xet.append("Nhà đặt ở trung tâm làm điểm nhấn rất tốt!")
        else: 
            nhan_xet.append("Ngôi nhà đặt lệch tạo quy tắc 1/3 rất nghệ thuật, đáng khen đó bảo bối.")
        
    # MỚI THÊM: Kích thước mặt trời so với ngôi nhà
    if h and s:
        sun_area = get_area(s[0])
        house_area = get_area(h[0])
        if sun_area > house_area:
            nhan_xet.append("Ông mặt trời em vẽ to hơn cả ngôi nhà kìa, thử vẽ nhỏ lại chút xíu cho cảnh vật thật hơn nhé!")
            
    return nhan_xet

# === API ENDPOINTS ===
@app.route("/classify", methods=["POST"])
def classify():
    if "image" not in request.files: 
        return jsonify({"error": "Không có ảnh"}), 400
    
    img_path = None
    try:
        img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.jpg")
        request.files["image"].save(img_path)
        
        loai_anh = classify_image(img_path)
        
        if loai_anh == "Unknown":
            return jsonify({
                "type": "Unknown",
                "message": "Ảnh của em không phải chân dung hoặc phong cảnh rõ ràng. Em hãy chụp lại bài vẽ của mình nhé!"
            }), 200
        
        if loai_anh == "ChanDung":
            results = model(img_path, verbose=False)[0]
            detected_objects = []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                raw_name = str(results.names[cls_id]).strip().lower()
                for req in REQUIRED:
                    if req in raw_name: detected_objects.append(req)
            
            unique_detected = list(set(detected_objects))
            total_detected = len(unique_detected)
            
            if total_detected < 2:
                return jsonify({
                    "type": "Unknown",
                    "message": f"Ảnh có vẻ là chân dung nhưng chỉ thấy {total_detected} chi tiết. Em hãy vẽ thêm mắt, mũi, miệng, tai, tóc cho rõ nét nhé!"
                }), 200
                
        else:
            results = scenery_model(img_path, verbose=False)[0]
            boxes_dict = {name: [] for name in SCENERY_REQUIRED}
            for box in results.boxes:
                cls_id = int(box.cls[0])
                raw_name = str(results.names[cls_id]).strip().lower()
                for req in SCENERY_REQUIRED:
                    if req in raw_name: boxes_dict[req].append(box)
            
            detected = [k for k, v in boxes_dict.items() if len(v) > 0]
            if len(detected) < 2:
                return jsonify({
                    "type": "Unknown",
                    "message": "Ảnh có vẻ là phong cảnh nhưng các chi tiết chưa rõ. Em hãy vẽ thêm nhà, cây hoặc ông mặt trời nhé!"
                }), 200
        
        if img_path and os.path.exists(img_path): os.remove(img_path)
        return jsonify({"type": loai_anh})
        
    except Exception as e:
        print("Lỗi classify:", str(e))
        if img_path and os.path.exists(img_path): os.remove(img_path)
        return jsonify({"type": "Unknown", "message": "Có lỗi xảy ra khi xử lý ảnh. Vui lòng thử lại!"}), 200

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files: 
        return jsonify({"error": "Không có ảnh"}), 400
    
    filename = None
    img_path = None
    
    try:
        filename = f"{uuid.uuid4().hex}.jpg"
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        request.files["image"].save(img_path)
        penalty = float(request.form.get("penalty", 1))
        
        img_cv = cv2.imread(img_path)
        if img_cv is None: raise Exception("Không thể đọc ảnh")
            
        img_h, img_w, _ = img_cv.shape
        results = model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

        if not results.boxes:
            if img_path and os.path.exists(img_path): os.remove(img_path)
            return jsonify({
                "score": 0, "missing": REQUIRED, 
                "loi_khuyen_giao_vien": ["Chưa thấy khuôn mặt, em đồ lại nét cho đậm hơn xem sao?"],
                "detected": [], "nhan_xet_bo_cuc": ["Tranh trống hoặc nét mờ quá."],
                "nhan_xet_ty_le": []
            })

        cls_ids = [int(cls) for cls in results.boxes.cls.cpu().numpy()]
        boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
        
        boxes_dict = {name: [] for name in REQUIRED}
        for cid, box in zip(cls_ids, boxes_xyxy):
            raw_name = str(results.names[cid]).strip().lower()
            for req in REQUIRED:
                if req in raw_name: boxes_dict[req].append(box)

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [k for k in REQUIRED if k not in detected]
        
        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        loi_ty_le = luat_ty_le_chan_dung(boxes_dict)
        
        loi_khuyen = []
        if "hair" not in detected and "ear" not in detected:
            loi_khuyen.append("Gợi ý: Khuôn mặt sẽ hoàn hảo hơn nếu em vẽ thêm phần viền khuôn mặt, tóc vành tai.")
        if missing:
            loi_khuyen.append(f"Em nhớ bổ sung các bộ phận còn thiếu nhé: {', '.join(missing)}.")
        
        # === TÍNH ĐIỂM CHÂN DUNG PHÂN HÓA ===
        trong_so_chan_dung = {"face": 1.5, "eye": 1.5, "nose": 1.0, "mouth": 1.0, "hair": 1.0, "eyebrow": 0.5, "ear": 0.5}
        diem_thanh_phan = sum([trong_so_chan_dung.get(obj, 0) for obj in detected])

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, 1.5 - so_loi_bo_cuc * 0.5) 

        so_loi_ty_le = len(loi_ty_le)
        diem_ty_le = max(0, 1.5 - so_loi_ty_le * 0.5) 

        score_base = diem_thanh_phan + diem_bo_cuc + diem_ty_le
        muc_phat = (so_loi_bo_cuc + so_loi_ty_le + len(missing) * 0.5) * (penalty - 1)
        score = score_base - muc_phat

        if img_path and os.path.exists(img_path): os.remove(img_path)
            
        return jsonify({
            "score": max(0, min(10, round(score, 1))),
            "detected": detected,
            "missing": missing,
            "nhan_xet_bo_cuc": loi_bo_cuc,
            "nhan_xet_ty_le": loi_ty_le,
            "loi_khuyen_giao_vien": loi_khuyen if loi_khuyen else ["Tranh em vẽ rất tốt, không có gì để chê!"],
            "boxed_image": f"/static/results/{boxed_name}"
        })
        
    except Exception as e:
        print("Lỗi predict:", str(e))
        if img_path and os.path.exists(img_path): os.remove(img_path)
        return jsonify({
            "score": 0, "detected": [], "missing": REQUIRED,
            "nhan_xet_bo_cuc": ["Có lỗi xảy ra khi xử lý ảnh."], "nhan_xet_ty_le": [],
            "loi_khuyen_giao_vien": ["Xin lỗi, đã có lỗi xảy ra. Em vui lòng thử lại với ảnh khác nhé!"]
        }), 200

@app.route("/predict_scenery", methods=["POST"])
def predict_scenery():
    if "image" not in request.files: 
        return jsonify({"error": "Không có ảnh"}), 400
    
    filename = None
    img_path = None
    
    try:
        filename = f"{uuid.uuid4().hex}.jpg"
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        request.files["image"].save(img_path)
        penalty = float(request.form.get("penalty", 1))
        
        img_cv = cv2.imread(img_path)
        if img_cv is None: raise Exception("Không thể đọc ảnh")
            
        img_h, img_w, _ = img_cv.shape
        results = scenery_model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

        if not results.boxes:
            if img_path and os.path.exists(img_path): os.remove(img_path)
            return jsonify({
                "score": 0, "missing": SCENERY_REQUIRED, 
                "loi_khuyen_giao_vien": ["Tranh trống quá, em thử vẽ thêm nhà và cây đi cục dàng!"],
                "detected": [], "nhan_xet_bo_cuc": ["Tranh trống hoặc nét mờ quá."],
                "nhan_xet_mau_sac": "", "nhan_xet_nghe_thuat": []
            })

        cls_ids = [int(cls) for cls in results.boxes.cls.cpu().numpy()]
        boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
        
        boxes_dict = {name: [] for name in SCENERY_REQUIRED}
        for cid, box in zip(cls_ids, boxes_xyxy):
            raw_name = str(results.names[cid]).strip().lower()
            for req in SCENERY_REQUIRED:
                if req in raw_name: boxes_dict[req].append(box)

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [v for v in SCENERY_REQUIRED if v not in detected]
        
        loi_khuyen = []
        if "house" not in detected: loi_khuyen.append("Em thiếu mất ngôi nhà rồi huhu, đây là điểm nhấn quan trọng nhất của tranh phong cảnh đó.")
        if "tree" not in detected: loi_khuyen.append("Thêm một vài bóng cây xanh sẽ giúp bức tranh có sức sống hơn rất nhiều.")
        if "sun" not in detected: loi_khuyen.append("Bầu trời hơi trống, em thử vẽ thêm ông mặt trời, mây và chim xem sao nha cục dàng.")
        if len(detected) == 3: loi_khuyen.append("Tranh của em rất đầy đủ chi tiết! Nếu muốn xuất sắc hơn, có thể điểm thêm bãi cỏ hoặc đàn chim trôi nhé.")

        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        nhan_xet_nghe_thuat_list = phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h)
        nhan_xet_mau_sac_str = phan_tich_mau_sac(img_cv)

        # === TÍNH ĐIỂM PHONG CẢNH PHÂN HÓA ===
        trong_so_phong_canh = {"house": 2.5, "tree": 2.0, "sun": 1.0}
        diem_thanh_phan = sum([trong_so_phong_canh.get(obj, 0) for obj in detected])

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, 1.5 - so_loi_bo_cuc * 0.5)

        diem_nghe_thuat = 0.0
        for nx in nhan_xet_nghe_thuat_list:
            if "tốt" in nx or "nghệ thuật" in nx or "amazing" in nx:
                diem_nghe_thuat += 1.0 
            elif "to hơn" in nx:
                diem_nghe_thuat -= 0.5 
        diem_nghe_thuat = max(0, min(2.0, diem_nghe_thuat))

        diem_mau_sac = 1.0
        if "nhạt nhòa" in nhan_xet_mau_sac_str or "hơi tối" in nhan_xet_mau_sac_str:
            diem_mau_sac -= 0.5 

        score_base = diem_thanh_phan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac
        muc_phat = (so_loi_bo_cuc + len(missing) * 0.5) * (penalty - 1)
        score = score_base - muc_phat

        if img_path and os.path.exists(img_path): os.remove(img_path)
            
        return jsonify({
            "score": max(0, min(10, round(score, 1))),
            "detected": detected,
            "missing": missing,
            "nhan_xet_bo_cuc": loi_bo_cuc,
            "nhan_xet_mau_sac": nhan_xet_mau_sac_str,
            "nhan_xet_nghe_thuat": nhan_xet_nghe_thuat_list,
            "loi_khuyen_giao_vien": loi_khuyen,
            "boxed_image": f"/static/results/{boxed_name}"
        })
        
    except Exception as e:
        print("Lỗi predict_scenery:", str(e))
        if img_path and os.path.exists(img_path): os.remove(img_path)
        return jsonify({
            "score": 0, "detected": [], "missing": SCENERY_REQUIRED,
            "nhan_xet_bo_cuc": ["Có lỗi xảy ra khi xử lý ảnh."], "nhan_xet_mau_sac": "",
            "nhan_xet_nghe_thuat": [], "loi_khuyen_giao_vien": ["Xin lỗi, đã có lỗi xảy ra. Em vui lòng thử lại!"]
        }), 200

if __name__ == "__main__":
    app.run(debug=True)