from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ultralytics import YOLO
import os
import uuid
import cv2
import numpy as np
from tensorflow.keras.models import load_model
import json
from datetime import datetime
from underthesea import pos_tag
from deep_translator import GoogleTranslator
import re

app = Flask(__name__)

# === CORS ===
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5000", "http://127.0.0.1:5000"])

# === Khởi tạo translator ===
translator = GoogleTranslator(source='vi', target='en')

# === ROUTE TRANG CHỦ ===
@app.route('/')
def home():
    return render_template('portrait.html')

@app.route('/adjustment')
def adjustment():
    return render_template('adjustment.html')

@app.route('/about_us')
def aboutus():
    return render_template('about_us.html')

@app.route('/guide')
def guide():
    return render_template('guide.html')

# === DANH SÁCH NOUNS HỢP LỆ ===
VALID_PORTRAIT_NOUNS = {
    "face", "eye", "eyebrow", "nose", "mouth", "ear", "hair",
    "eyes", "eyebrows", "ears", "hairs", "head"
}

VALID_SCENERY_NOUNS = {
    "house", "tree", "sun", "moon", "cloud", "flower", "grass", 
    "mountain", "river", "lake", "sky", "bird", "buffalo", 
    "butterfly", "fish", "boat", "bridge",
    "trees", "clouds", "flowers", "mountains", "rivers", "lakes", 
    "birds", "buffaloes", "butterflies", "fishes", "boats", "bridges", "roads"
}

VALID_VERBS = {
    "have", "has", "include", "contain",
    "illustrate", "feature", "present", "add", "added"
}

# === OBJECT MAPPING ===
SCENERY_OBJECT_MAPPING = {
    "cây": "tree",
    "nhà": "house",
    "mặt trời": "sun"
}

PORTRAIT_OBJECT_MAPPING = {
    "mắt": "eye",
    "mũi": "nose",
    "miệng": "mouth",
    "tai": "ear",
    "mày": "eyebrow",
    "lông mày": "eyebrow",
    "tóc": "hair",
    "khuôn mặt": "face",
    "mặt": "face"
}

PORTRAIT_OBJECT_VI = {
    "eye": "mắt",
    "nose": "mũi",
    "mouth": "miệng",
    "ear": "tai",
    "eyebrow": "lông mày",
    "hair": "tóc",
    "face": "khuôn mặt"
}

SCENERY_OBJECT_VI = {
    "tree": "cây",
    "house": "nhà",
    "sun": "mặt trời"
}

RELATION_MAPPING = {
    "cao hơn": "higher_than",
    "thấp hơn": "lower_than",
    "bên trái": "left_of",
    "bên phải": "right_of",
    "ở trên": "above",
    "ở dưới": "below",
    "cao hon": "higher_than",
    "thap hon": "lower_than",
    "ben trai": "left_of",
    "ben phai": "right_of",
    "o tren": "above",
    "o duoi": "below"
}

RELATION_VI = {
    "higher_than": "cao hơn",
    "lower_than": "thấp hơn",
    "left_of": "bên trái",
    "right_of": "bên phải",
    "above": "ở trên",
    "below": "ở dưới"
}

def filter_valid_nouns_en(nouns_list, art_type="portrait"):
    valid_nouns = []
    
    if art_type == "portrait":
        allowed_nouns = VALID_PORTRAIT_NOUNS
    else:
        allowed_nouns = VALID_SCENERY_NOUNS
    
    for noun in nouns_list:
        noun_lower = noun.lower().strip()
        
        if noun_lower in allowed_nouns:
            valid_nouns.append(noun_lower)
        elif noun_lower.endswith('s') and noun_lower[:-1] in allowed_nouns:
            valid_nouns.append(noun_lower[:-1])
        elif noun_lower.endswith('es') and noun_lower[:-2] in allowed_nouns:
            valid_nouns.append(noun_lower[:-2])
        elif noun_lower.endswith('ies') and noun_lower[:-3] + 'y' in allowed_nouns:
            valid_nouns.append(noun_lower[:-3] + 'y')
    
    return valid_nouns

def filter_valid_verbs_en(verbs_list):
    valid_verbs = []
    for verb in verbs_list:
        verb_lower = verb.lower().strip()
        if verb_lower in VALID_VERBS:
            valid_verbs.append(verb_lower)
    return valid_verbs

def parse_rules(user_text, art_type="scenery"):
    rules = []
    
    if not user_text or not user_text.strip():
        return rules
    
    if art_type == "portrait":
        pattern = r"(mắt|mũi|miệng|tai|mày|lông mày|tóc|khuôn mặt|mặt)\s*(?:phải|nên|cần)?\s*(cao hơn|thấp hơn|bên trái|bên phải|ở trên|ở dưới|cao hon|thap hon|ben trai|ben phai|o tren|o duoi)\s*(?:so với)?\s*(mắt|mũi|miệng|tai|mày|lông mày|tóc|khuôn mặt|mặt)"
        matches = re.findall(pattern, user_text.lower())
        
        for obj1_vi, rel_vi, obj2_vi in matches:
            obj1_en = PORTRAIT_OBJECT_MAPPING.get(obj1_vi, obj1_vi)
            obj2_en = PORTRAIT_OBJECT_MAPPING.get(obj2_vi, obj2_vi)
            
            if obj1_en in VALID_PORTRAIT_NOUNS and obj2_en in VALID_PORTRAIT_NOUNS:
                rules.append({
                    "object1": obj1_en,
                    "relation": RELATION_MAPPING.get(rel_vi, rel_vi),
                    "object2": obj2_en,
                    "object1_vi": obj1_vi,
                    "object2_vi": obj2_vi,
                    "relation_vi": RELATION_VI.get(RELATION_MAPPING.get(rel_vi, rel_vi), rel_vi)
                })
    else:
        pattern = r"(mặt trời|cây|nhà)\s*(?:phải|nên|cần)?\s*(cao hơn|thấp hơn|bên trái|bên phải|ở trên|ở dưới|cao hon|thap hon|ben trai|ben phai|o tren|o duoi)\s*(?:so với)?\s*(mặt trời|cây|nhà)"
        matches = re.findall(pattern, user_text.lower())
        
        for obj1_vi, rel_vi, obj2_vi in matches:
            obj1_en = SCENERY_OBJECT_MAPPING.get(obj1_vi, obj1_vi)
            obj2_en = SCENERY_OBJECT_MAPPING.get(obj2_vi, obj2_vi)
            
            if obj1_en in VALID_SCENERY_NOUNS and obj2_en in VALID_SCENERY_NOUNS:
                rules.append({
                    "object1": obj1_en,
                    "relation": RELATION_MAPPING.get(rel_vi, rel_vi),
                    "object2": obj2_en,
                    "object1_vi": obj1_vi,
                    "object2_vi": obj2_vi,
                    "relation_vi": RELATION_VI.get(RELATION_MAPPING.get(rel_vi, rel_vi), rel_vi)
                })
    
    return rules

def check_rule(rule, boxes_dict):
    obj1 = rule["object1"]
    obj2 = rule["object2"]
    relation = rule["relation"]

    if obj1 not in boxes_dict or obj2 not in boxes_dict:
        return False
    if len(boxes_dict[obj1]) == 0:
        return False
    if len(boxes_dict[obj2]) == 0:
        return False

    box1 = boxes_dict[obj1][0]
    box2 = boxes_dict[obj2][0]

    center1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
    center2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
    height1 = box1[3] - box1[1]
    height2 = box2[3] - box2[1]

    if relation == "higher_than":
        return height1 > height2
    elif relation == "lower_than":
        return height1 < height2
    elif relation == "left_of":
        return center1[0] < center2[0]
    elif relation == "right_of":
        return center1[0] > center2[0]
    elif relation == "above":
        return center1[1] < center2[1]
    elif relation == "below":
        return center1[1] > center2[1]

    return False

# === API LƯU CÀI ĐẶT ===
@app.route("/save_settings", methods=["POST"])
def save_settings():
    try:
        data = request.get_json()
        user_text = data.get("text", "")
        penalty = float(data.get("penalty", 1.5))
        art_type = data.get("art_type", "")
        
        verbs_list = []
        nouns_list = []
        verbs_en_list = []
        nouns_en_list = []
        
        settings_file = "user_settings.json"
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        if user_text and user_text.strip():
            try:
                pos_tags = pos_tag(user_text)
                
                for word, tag in pos_tags:
                    if tag.startswith('V'):
                        verbs_list.append(word)
                    elif tag.startswith('N'):
                        nouns_list.append(word)
                
                verbs_list = list(set(verbs_list))
                nouns_list = list(set(nouns_list))
                
                if verbs_list:
                    for verb in verbs_list:
                        try:
                            translated = translator.translate(verb)
                            verbs_en_list.append(translated)
                        except:
                            verbs_en_list.append(verb)
                
                if nouns_list:
                    for noun in nouns_list:
                        try:
                            translated = translator.translate(noun)
                            nouns_en_list.append(translated)
                        except:
                            nouns_en_list.append(noun)
                
                if art_type:
                    nouns_en_list = filter_valid_nouns_en(nouns_en_list, art_type)
                
            except Exception as e:
                print(f"Lỗi extract: {e}")
        
        rules = parse_rules(user_text, art_type)
        
        settings['text'] = user_text
        settings['penalty'] = penalty
        settings['art_type'] = art_type
        settings['verbs_vi'] = verbs_list
        settings['nouns_vi'] = nouns_list
        settings['verbs_en'] = verbs_en_list
        settings['nouns_en'] = nouns_en_list
        settings['rules'] = rules
        settings['last_updated'] = str(datetime.now())
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã lưu settings cho {art_type}")
        
        return jsonify({
            "success": True,
            "message": "Đã lưu cài đặt lên server!",
            "art_type": art_type,
            "verbs_vi": verbs_list,
            "nouns_vi": nouns_list,
            "verbs_en": verbs_en_list,
            "nouns_en": nouns_en_list,
            "rules": rules
        })
        
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# === API LẤY CÀI ĐẶT ===
@app.route("/get_settings", methods=["GET"])
def get_settings():
    try:
        settings_file = "user_settings.json"
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            return jsonify({
                "success": True,
                "text": settings.get("text", ""),
                "penalty": settings.get("penalty", 1.5),
                "art_type": settings.get("art_type", ""),
                "verbs_vi": settings.get("verbs_vi", []),
                "nouns_vi": settings.get("nouns_vi", []),
                "verbs_en": settings.get("verbs_en", []),
                "nouns_en": settings.get("nouns_en", []),
                "rules": settings.get("rules", [])
            })
        else:
            return jsonify({
                "success": True,
                "text": "",
                "penalty": 1.5,
                "art_type": "",
                "verbs_vi": [],
                "nouns_vi": [],
                "verbs_en": [],
                "nouns_en": [],
                "rules": []
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# === CÁC HẰNG SỐ ===
REQUIRED = ["eye", "eyebrow", "nose", "mouth", "face", "ear", "hair"]
SCENERY_REQUIRED = ["house", "tree", "sun"]

print("📦 Đang tải models...")

model = YOLO("portraityolo12n.pt")
print("✅ Đã tải model chân dung")

scenery_model = YOLO("landscape.pt")
print("✅ Đã tải model phong cảnh")

clf_model = load_model("phanLoaiAnh.h5")
print("✅ Đã tải model phân loại ảnh")

CLASSES = ["ChanDung", "PhongCanh"]

RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

print("\n✅ SERVER ĐÃ SẴN SÀNG!\n")

# === CÁC HÀM TIỆN ÍCH ===
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
    if do_bao_hoa < 40:
        nhan_xet.append("Lực tô màu còn hơi nhẹ, tranh nhạt nhòa. Em nhớ ấn bút mạnh tay hơn để tranh rực rỡ nhé!")
    elif do_bao_hoa > 160:
        nhan_xet.append("Kỹ năng tô màu rất tốt, màu sắc đậm đà và dứt khoát, em giỏi lắm bảo bối.")
    
    if hot_pixels > cold_pixels * 1.5:
        nhan_xet.append("Tone màu nóng (đỏ, vàng, cam) làm chủ đạo, bức tranh mang lại cảm giác ấm áp, vui tươi.")
    elif cold_pixels > hot_pixels * 1.5:
        nhan_xet.append("Tone màu lạnh (xanh, tím) làm chủ đạo, tạo ra không gian bình yên, trong trẻo.")
    if do_sang < 80:
        nhan_xet.append("Màu sắc tổng thể hơi tối, có vẻ em đang vẽ cảnh ban đêm hoặc hoàng hôn phải không?")
    
    return " ".join(nhan_xet) if nhan_xet else "Màu sắc kết hợp rất hài hòa và dịu mắt."

def kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h):
    if not boxes_xyxy:
        return ["Tranh trống hoặc nét mờ quá, thầy/cô không chấm được bố cục."]
    min_x, min_y = min([b[0] for b in boxes_xyxy]), min([b[1] for b in boxes_xyxy])
    max_x, max_y = max([b[2] for b in boxes_xyxy]), max([b[3] for b in boxes_xyxy])
    ty_le = ((max_x - min_x) * (max_y - min_y)) / (img_w * img_h)
    
    loi = []
    if ty_le < 0.05:
        loi.append("Lỗi tỷ lệ: Hình vẽ bị quá nhỏ và lọt thỏm giữa tờ giấy. Hãy vẽ to và tự tin lên cục dàng!")
    elif ty_le > 0.85:
        loi.append("Lỗi lề: Em vẽ hình to quá bị chạm vào sát mép giấy, bức tranh nhìn hơi chật chội rồi cưng ơi.")
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
        if khoang_cach > w_avg * 1.6:
            nhan_xet.append("Hai mắt đang bị vẽ cách xa nhau quá.")
        elif khoang_cach < w_avg * 0.5:
            nhan_xet.append("Hai mắt vẽ hơi sát nhau cưng ơi.")
            
    noses, mouths = boxes_dict.get("nose", []), boxes_dict.get("mouth", [])
    if noses and mouths:
        if abs(((noses[0][0] + noses[0][2]) / 2) - ((mouths[0][0] + mouths[0][2]) / 2)) > (mouths[0][2] - mouths[0][0]) * 0.2:
            nhan_xet.append("Mũi và miệng chưa thẳng hàng dọc em nha!")
            
    eb, ey = boxes_dict.get("eyebrow", []), boxes_dict.get("eye", [])
    if eb and ey:
        if (((ey[0][1] + ey[0][3]) / 2) - ((eb[0][1] + eb[0][3]) / 2)) > (ey[0][3] - ey[0][1]) * 2.5:
            nhan_xet.append("Lông mày em vẽ cao quá, nhìn nhân vật như đang giật mình vậy.")
            
    ears = boxes_dict.get("ear", [])
    if ears and ey:
        ear_y = (ears[0][1] + ears[0][3]) / 2
        eye_y = (ey[0][1] + ey[0][3]) / 2
        if abs(ear_y - eye_y) > (ey[0][3] - ey[0][1]) * 1.5:
            nhan_xet.append("Vị trí tai đang bị vẽ lệch lên quá cao hoặc thấp hơn so với mắt khá nhiều.")
    
    return nhan_xet if nhan_xet else ["Tỷ lệ tốt!"]

def phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h):
    nhan_xet = []
    h, t, s = boxes_dict.get("house", []), boxes_dict.get("tree", []), boxes_dict.get("sun", [])
    
    if h and t:
        if h[0][3] < t[0][3]:
            nhan_xet.append("Lưu ý luật xa gần: Nhà ở gần nên vẽ thấp hơn cây ở xa em nha!")
        else:
            nhan_xet.append("Em đã áp dụng rất tốt quy luật xa gần, amazing good job!")
        
    if h:
        hx = (h[0][0] + h[0][2]) / 2
        if (img_w * 0.25) < hx < (img_w * 0.75):
            nhan_xet.append("Nhà đặt ở trung tâm làm điểm nhấn rất tốt!")
        else:
            nhan_xet.append("Ngôi nhà đặt lệch tạo quy tắc 1/3 rất nghệ thuật, đáng khen đó bảo bối.")
        
    if h and s:
        sun_area = (s[0][2] - s[0][0]) * (s[0][3] - s[0][1])
        house_area = (h[0][2] - h[0][0]) * (h[0][3] - h[0][1])
        if sun_area > house_area:
            nhan_xet.append("Ông mặt trời em vẽ to hơn cả ngôi nhà kìa, thử vẽ nhỏ lại chút xíu cho cảnh vật thật hơn nhé!")
    
    return nhan_xet if nhan_xet else ["Bố cục nghệ thuật tốt!"]

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
                    if req == raw_name:
                        detected_objects.append(req)
            
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
                    if req == raw_name:
                        boxes_dict[req].append(box)
            
            detected = [k for k, v in boxes_dict.items() if len(v) > 0]
            
            if len(detected) < 2:
                return jsonify({
                    "type": "Unknown",
                    "message": "Ảnh có vẻ là phong cảnh nhưng các chi tiết chưa rõ. Em hãy vẽ thêm nhà, cây hoặc ông mặt trời nhé!"
                }), 200
        
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        
        return jsonify({"type": loai_anh})
        
    except Exception as e:
        print(f"Lỗi classify: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        return jsonify({"type": "Unknown", "message": "Có lỗi xảy ra khi xử lý ảnh!"}), 200

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
        
        settings_file = "user_settings.json"
        rules = []
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                rules = settings.get("rules", [])
        
        img_cv = cv2.imread(img_path)
        img_h, img_w, _ = img_cv.shape
        
        results = model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

        if not results.boxes:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
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
                if req == raw_name:
                    boxes_dict[req].append(box)

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [k for k in REQUIRED if k not in detected]
        
        rule_errors = []
        rule_success = []
        
        for rule in rules:
            ok = check_rule(rule, boxes_dict)
            obj1_vi = rule.get('object1_vi', PORTRAIT_OBJECT_VI.get(rule['object1'], rule['object1']))
            obj2_vi = rule.get('object2_vi', PORTRAIT_OBJECT_VI.get(rule['object2'], rule['object2']))
            relation_vi = rule.get('relation_vi', RELATION_VI.get(rule['relation'], rule['relation']))
            
            if ok:
                rule_success.append(f"{obj1_vi} {relation_vi} {obj2_vi}")
            else:
                rule_errors.append(f"{obj1_vi} không {relation_vi} {obj2_vi}")
        
        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        loi_ty_le = luat_ty_le_chan_dung(boxes_dict)
        
        loi_khuyen = []
        if "hair" not in detected and "ear" not in detected:
            loi_khuyen.append("Gợi ý: Khuôn mặt sẽ hoàn hảo hơn nếu em vẽ thêm phần viền khuôn mặt, tóc vành tai.")
        if missing:
            loi_khuyen.append(f"Em nhớ bổ sung các bộ phận còn thiếu nhé: {', '.join(missing)}.")
        
        trong_so_chan_dung = {"face": 1.5, "eye": 1.5, "nose": 1.0, "mouth": 1.0, "hair": 1.0, "eyebrow": 0.5, "ear": 0.5}
        diem_thanh_phan = sum([trong_so_chan_dung.get(obj, 0) for obj in detected])

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, 1.5 - so_loi_bo_cuc * 0.5) 

        so_loi_ty_le = len(loi_ty_le)
        diem_ty_le = max(0, 1.5 - so_loi_ty_le * 0.5) 

        bonus_rules = min(len(rule_success) * 0.3, 1.0)
        penalt_rules = len(rule_errors) * 0.2

        score_base = diem_thanh_phan + diem_bo_cuc + diem_ty_le + bonus_rules - penalt_rules
        muc_phat = (so_loi_bo_cuc + so_loi_ty_le + len(missing) * 0.5) * (penalty - 1)
        score = max(0, min(10, round(score_base - muc_phat, 1)))

        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            
        return jsonify({
            "score": score,
            "detected": detected,
            "missing": missing,
            "rule_errors": rule_errors,
            "rule_success": rule_success,
            "nhan_xet_bo_cuc": loi_bo_cuc,
            "nhan_xet_ty_le": loi_ty_le,
            "loi_khuyen_giao_vien": loi_khuyen if loi_khuyen else ["Tranh em vẽ rất tốt, không có gì để chê!"],
            "boxed_image": f"/static/results/{boxed_name}"
        })
        
    except Exception as e:
        print(f"Lỗi predict: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        return jsonify({
            "score": 0, "detected": [], "missing": REQUIRED,
            "rule_errors": [], "rule_success": [],
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
        
        settings_file = "user_settings.json"
        nouns_from_settings = []
        rules = []

        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                nouns_from_settings = settings.get("nouns_en", [])
                rules = settings.get("rules", [])
        
        base_required = SCENERY_REQUIRED.copy()
        
        for noun in nouns_from_settings:
            noun_lower = noun.lower().strip()
            if noun_lower not in base_required and noun_lower not in ["house", "tree", "sun"]:
                base_required.append(noun_lower)
        
        img_cv = cv2.imread(img_path)
        img_h, img_w, _ = img_cv.shape
        
        results = scenery_model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())

        if not results.boxes:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
            return jsonify({
                "score": 0, 
                "missing": base_required, 
                "loi_khuyen_giao_vien": ["Tranh trống quá, em thử vẽ thêm nhà và cây đi cục dàng!"],
                "detected": [], 
                "nhan_xet_bo_cuc": ["Tranh trống hoặc nét mờ quá."],
                "nhan_xet_mau_sac": "", 
                "nhan_xet_nghe_thuat": []
            })

        cls_ids = [int(cls) for cls in results.boxes.cls.cpu().numpy()]
        boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
        
        boxes_dict = {name: [] for name in base_required}
        for cid, box in zip(cls_ids, boxes_xyxy):
            raw_name = str(results.names[cid]).strip().lower()
            for req in base_required:
                if req == raw_name: 
                    boxes_dict[req].append(box)

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [v for v in base_required if v not in detected]
        
        rule_errors = []
        rule_success = []

        for rule in rules:
            ok = check_rule(rule, boxes_dict)
            obj1_vi = rule.get('object1_vi', SCENERY_OBJECT_VI.get(rule['object1'], rule['object1']))
            obj2_vi = rule.get('object2_vi', SCENERY_OBJECT_VI.get(rule['object2'], rule['object2']))
            relation_vi = rule.get('relation_vi', RELATION_VI.get(rule['relation'], rule['relation']))
            
            if ok:
                rule_success.append(f"{obj1_vi} {relation_vi} {obj2_vi}")
            else:
                rule_errors.append(f"{obj1_vi} không {relation_vi} {obj2_vi}")
        
        loi_khuyen = []
        if "house" not in detected:
            loi_khuyen.append("Em thiếu mất ngôi nhà rồi huhu, đây là điểm nhấn quan trọng nhất của tranh phong cảnh đó.")
        if "tree" not in detected:
            loi_khuyen.append("Thêm một vài bóng cây xanh sẽ giúp bức tranh có sức sống hơn rất nhiều.")
        if "sun" not in detected:
            loi_khuyen.append("Bầu trời hơi trống, em thử vẽ thêm ông mặt trời, mây và chim xem sao nha cục dàng.")
        
        for noun in missing:
            if noun not in SCENERY_REQUIRED:
                loi_khuyen.append(f"Em còn thiếu {noun} trong bức tranh, hãy thêm vào nhé!")
        
        if len(detected) == len(base_required):
            loi_khuyen.append("Tranh của em rất đầy đủ chi tiết! Nếu muốn xuất sắc hơn, có thể điểm thêm bãi cỏ hoặc đàn chim trôi nhé.")

        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        nhan_xet_nghe_thuat_list = phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h)
        nhan_xet_mau_sac_str = phan_tich_mau_sac(img_cv)

        trong_so_phong_canh = {"house": 2.5, "tree": 2.0, "sun": 1.5}
        for noun in base_required:
            if noun not in trong_so_phong_canh:
                trong_so_phong_canh[noun] = 1.0
        
        diem_thanh_phan = sum([trong_so_phong_canh.get(obj, 1.0) for obj in detected])
        diem_toi_da = sum([trong_so_phong_canh.get(obj, 1.0) for obj in base_required])

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, 2.0 - so_loi_bo_cuc * 0.5)

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
        elif "rất tốt" in nhan_xet_mau_sac_str or "rực rỡ" in nhan_xet_mau_sac_str:
            diem_mau_sac += 0.5

        bonus_rules = min(len(rule_success) * 0.3, 1.0)
        penalt_rules = len(rule_errors) * 0.2

        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * 5.0 if diem_toi_da > 0 else 0
        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac + bonus_rules - penalt_rules
        
        so_vat_thieu = len(missing)
        muc_phat = (so_loi_bo_cuc * 0.5 + so_vat_thieu * 0.8) * (penalty - 1)
        score = score_base - muc_phat
        score = max(0, min(10, round(score * 1.25, 1)))

        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            
        return jsonify({
            "score": score,
            "detected": detected,
            "missing": missing,
            "rule_errors": rule_errors,
            "rule_success": rule_success,
            "total_required": len(base_required),
            "required_list": base_required,
            "nouns_from_settings": nouns_from_settings,
            "nhan_xet_bo_cuc": loi_bo_cuc,
            "nhan_xet_mau_sac": nhan_xet_mau_sac_str,
            "nhan_xet_nghe_thuat": nhan_xet_nghe_thuat_list,
            "loi_khuyen_giao_vien": loi_khuyen,
            "boxed_image": f"/static/results/{boxed_name}"
        })
        
    except Exception as e:
        print(f"Lỗi predict_scenery: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        
        return jsonify({
            "score": 0,
            "detected": [],
            "missing": SCENERY_REQUIRED,
            "rule_errors": [],
            "rule_success": [],
            "total_required": len(SCENERY_REQUIRED),
            "required_list": SCENERY_REQUIRED,
            "nouns_from_settings": [],
            "nhan_xet_bo_cuc": ["Có lỗi xảy ra"],
            "nhan_xet_mau_sac": "",
            "nhan_xet_nghe_thuat": [],
            "loi_khuyen_giao_vien": ["Có lỗi xảy ra khi xử lý ảnh!"],
            "boxed_image": ""
        })

if __name__ == "__main__":
    app.run(debug=True)