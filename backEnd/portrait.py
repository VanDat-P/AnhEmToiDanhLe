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

app = Flask(__name__)

# === CORS phải được khởi tạo NGAY sau app ===
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5000", "http://127.0.0.1:5000"])

# === Khởi tạo translator ===
translator = GoogleTranslator(source='vi', target='en')

print("=" * 60)
print("🚀 KHỞI ĐỘNG SERVER AI ART GRADER")
print("=" * 60)

# === ROUTE TRANG CHỦ ===
@app.route('/')
def home():
    print("📄 [ROUTE] Truy cập trang chủ")
    return render_template('portrait.html')

@app.route('/adjustment')
def adjustment():
    print("📄 [ROUTE] Truy cập trang điều chỉnh")
    return render_template('adjustment.html')

@app.route('/about_us')
def aboutus():
    print("📄 [ROUTE] Truy cập trang giới thiệu")
    return render_template('about_us.html')

@app.route('/guide')
def guide():
    print("📄 [ROUTE] Truy cập trang hướng dẫn")
    return render_template('guide.html')

# === API LƯU CÀI ĐẶT TỪ ADJUSTMENT ===
@app.route("/save_settings", methods=["POST"])
def save_settings():
    print("\n" + "=" * 60)
    print("💾 [API] NHẬN REQUEST LƯU CÀI ĐẶT")
    print("=" * 60)
    
    try:
        data = request.get_json()
        print(f"📥 Dữ liệu nhận được: {data}")
        
        user_text = data.get("text", "")
        penalty = float(data.get("penalty", 1.5))
        art_type = data.get("art_type", "")  # Lấy loại tranh từ request
        
        print(f"📝 Nội dung text: {user_text}")
        print(f"⚙️ Hệ số phạt: {penalty}")
        print(f"🎨 Loại tranh: {art_type if art_type else 'Chưa chọn'}")
        
        # === TẠO 2 MẢNG ĐỂ LƯU VERBS VÀ NOUNS ===
        verbs_list = []
        nouns_list = []
        verbs_en_list = []
        nouns_en_list = []
        
        # Lưu vào file JSON trên server
        settings_file = "user_settings.json"
        
        # Đọc file cũ nếu có
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            print(f"📂 Đã đọc file settings cũ: {settings_file}")
        else:
            settings = {}
            print(f"📂 Tạo mới file settings")
        
        # === EXTRACT VERB & NOUN BẰNG UNDERTHESEA ===
        if user_text and user_text.strip():
            print("\n🔍 BẮT ĐẦU EXTRACT VERBS & NOUNS...")
            try:
                # Xử lý POS tagging bằng underthesea
                pos_tags = pos_tag(user_text)
                print(f"🏷️ POS Tags: {pos_tags}")
                
                # Lọc verbs và nouns vào 2 mảng
                for word, tag in pos_tags:
                    if tag.startswith('V'):  # Verbs in Vietnamese
                        verbs_list.append(word)
                        print(f"   ✅ Tìm thấy VERB: {word} ({tag})")
                    elif tag.startswith('N'):  # Nouns in Vietnamese
                        nouns_list.append(word)
                        print(f"   ✅ Tìm thấy NOUN: {word} ({tag})")
                
                # Loại bỏ trùng lặp
                verbs_list = list(set(verbs_list))
                nouns_list = list(set(nouns_list))
                
                print(f"\n📊 Thống kê trước khi dịch:")
                print(f"   - Verbs (VI): {verbs_list if verbs_list else 'Không có'}")
                print(f"   - Nouns (VI): {nouns_list if nouns_list else 'Không có'}")
                
                # === DỊCH SANG TIẾNG ANH BẰNG DEEP-TRANSLATOR ===
                print("\n🌐 BẮT ĐẦU DỊCH SANG TIẾNG ANH...")
                
                if verbs_list:
                    print(f"   🔄 Đang dịch {len(verbs_list)} verbs...")
                    for verb in verbs_list:
                        try:
                            translated = translator.translate(verb)
                            verbs_en_list.append(translated)
                            print(f"      • {verb} → {translated}")
                        except Exception as e:
                            print(f"      ❌ Lỗi dịch từ '{verb}': {e}")
                            verbs_en_list.append(verb)
                
                if nouns_list:
                    print(f"   🔄 Đang dịch {len(nouns_list)} nouns...")
                    for noun in nouns_list:
                        try:
                            translated = translator.translate(noun)
                            nouns_en_list.append(translated)
                            print(f"      • {noun} → {translated}")
                        except Exception as e:
                            print(f"      ❌ Lỗi dịch từ '{noun}': {e}")
                            nouns_en_list.append(noun)
                
                # In kết quả extract
                print("\n" + "-" * 50)
                print("📊 KẾT QUẢ EXTRACT CUỐI CÙNG:")
                print("-" * 50)
                print("🔤 VERBS (Vietnamese):", verbs_list if verbs_list else "Không tìm thấy")
                print("🔤 VERBS (English):", verbs_en_list if verbs_en_list else "Không tìm thấy")
                print("📚 NOUNS (Vietnamese):", nouns_list if nouns_list else "Không tìm thấy")
                print("📚 NOUNS (English):", nouns_en_list if nouns_en_list else "Không tìm thấy")
                print("-" * 50)
                
            except Exception as e:
                print(f"❌ Lỗi extract POS: {e}")
        else:
            print("⚠️ Không có text để extract")
        
        # Cập nhật settings với cả 4 mảng và art_type
        settings['text'] = user_text
        settings['penalty'] = penalty
        settings['art_type'] = art_type
        settings['verbs_vi'] = verbs_list
        settings['nouns_vi'] = nouns_list
        settings['verbs_en'] = verbs_en_list
        settings['nouns_en'] = nouns_en_list
        settings['last_updated'] = str(datetime.now())
        
        # Ghi vào file
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Đã lưu settings vào file: {settings_file}")
        
        print("\n" + "=" * 60)
        print("📦 THÔNG TIN ĐÃ LƯU:")
        print("=" * 60)
        print(f"📝 Text: {user_text}")
        print(f"⚙️ Penalty: {penalty}x")
        print(f"🎨 Art Type: {art_type if art_type else 'Chưa chọn'}")
        print(f"🔤 Verbs (VI): {verbs_list}")
        print(f"🔤 Verbs (EN): {verbs_en_list}")
        print(f"📚 Nouns (VI): {nouns_list}")
        print(f"📚 Nouns (EN): {nouns_en_list}")
        print(f"⏰ Last updated: {settings['last_updated']}")
        print("=" * 60 + "\n")
        
        return jsonify({
            "success": True,
            "message": "Đã lưu cài đặt lên server!",
            "art_type": art_type,
            "verbs_vi": verbs_list,
            "nouns_vi": nouns_list,
            "verbs_en": verbs_en_list,
            "nouns_en": nouns_en_list
        })
        
    except Exception as e:
        print(f"\n❌ LỖI KHI LƯU SETTINGS: {str(e)}")
        print("=" * 60 + "\n")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === API LẤY CÀI ĐẶT ĐÃ LƯU ===
@app.route("/get_settings", methods=["GET"])
def get_settings():
    print("\n" + "=" * 60)
    print("📥 [API] NHẬN REQUEST LẤY CÀI ĐẶT")
    print("=" * 60)
    
    try:
        settings_file = "user_settings.json"
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            print(f"✅ Đã đọc settings từ file: {settings_file}")
            print(f"📝 Text: {settings.get('text', '')}")
            print(f"⚙️ Penalty: {settings.get('penalty', 1.5)}")
            print(f"🎨 Art Type: {settings.get('art_type', 'Chưa chọn')}")
            print(f"🔤 Verbs VI: {settings.get('verbs_vi', [])}")
            print(f"🔤 Verbs EN: {settings.get('verbs_en', [])}")
            print(f"📚 Nouns VI: {settings.get('nouns_vi', [])}")
            print(f"📚 Nouns EN: {settings.get('nouns_en', [])}")
            
            return jsonify({
                "success": True,
                "text": settings.get("text", ""),
                "penalty": settings.get("penalty", 1.5),
                "art_type": settings.get("art_type", ""),
                "verbs_vi": settings.get("verbs_vi", []),
                "nouns_vi": settings.get("nouns_vi", []),
                "verbs_en": settings.get("verbs_en", []),
                "nouns_en": settings.get("nouns_en", [])
            })
        else:
            print("⚠️ File settings chưa tồn tại, trả về dữ liệu mặc định")
            return jsonify({
                "success": True,
                "text": "",
                "penalty": 1.5,
                "art_type": "",
                "verbs_vi": [],
                "nouns_vi": [],
                "verbs_en": [],
                "nouns_en": []
            })
    except Exception as e:
        print(f"❌ LỖI KHI ĐỌC SETTINGS: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === CÁC HẰNG SỐ ===
REQUIRED = ["eye", "eyebrow", "nose", "mouth", "face", "ear", "hair"]
SCENERY_REQUIRED = ["house", "tree", "sun"]

print("📦 Đang tải models...")

# === LOAD MODELS ===
model = YOLO("portraityolo12n.pt")
print("✅ Đã tải model chân dung")

scenery_model = YOLO("landscape.pt")
print("✅ Đã tải model phong cảnh")

clf_model = load_model("phanLoaiAnh.h5")
print("✅ Đã tải model phân loại ảnh")

CLASSES = ["ChanDung", "PhongCanh"]
print(f"📊 Các lớp phân loại: {CLASSES}")

# === TẠO THƯ MỤC ===
RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Thư mục kết quả: {RESULT_FOLDER}")
print(f"📁 Thư mục upload: {UPLOAD_FOLDER}")

print("\n" + "=" * 60)
print("✅ SERVER ĐÃ SẴN SÀNG!")
print("🌐 Địa chỉ: http://localhost:5000")
print("=" * 60 + "\n")

# === PHÂN LOẠI ẢNH ===
def classify_image(img_path):
    print(f"🔍 Đang phân loại ảnh: {img_path}")
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    size = clf_model.input_shape[1]
    img = cv2.resize(img, (size, size))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    pred = clf_model.predict(img, verbose=0)[0]
    class_id = np.argmax(pred)
    result = CLASSES[class_id]
    print(f"📊 Kết quả phân loại: {result} (confidence: {pred[class_id]:.2f})")
    return result

# === CÁC HÀM TIỆN ÍCH ===
def get_center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

def get_bottom(box):
    return box[3]

def get_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])

def phan_tich_mau_sac(img_cv):
    print("🎨 Đang phân tích màu sắc...")
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
    
    result = " ".join(nhan_xet) if nhan_xet else "Màu sắc kết hợp rất hài hòa và dịu mắt."
    print(f"🎨 Nhận xét màu sắc: {result}")
    return result

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
    
    print(f"📐 Nhận xét bố cục: {loi if loi else ['Tốt']}")
    return loi if loi else ["Tuyệt vời! Bố cục cân đối, nằm ngay ngắn, amazing good job em!"]

def luat_ty_le_chan_dung(boxes_dict):
    print("📏 Đang phân tích tỷ lệ chân dung...")
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
        if abs(get_center(noses[0])[0] - get_center(mouths[0])[0]) > (mouths[0][2] - mouths[0][0]) * 0.2:
            nhan_xet.append("Mũi và miệng chưa thẳng hàng dọc em nha!")
            
    eb, ey = boxes_dict.get("eyebrow", []), boxes_dict.get("eye", [])
    if eb and ey:
        if (get_center(ey[0])[1] - get_center(eb[0])[1]) > (ey[0][3] - ey[0][1]) * 2.5:
            nhan_xet.append("Lông mày em vẽ cao quá, nhìn nhân vật như đang giật mình vậy.")
            
    ears = boxes_dict.get("ear", [])
    if ears and ey:
        ear_y = get_center(ears[0])[1]
        eye_y = get_center(ey[0])[1]
        if abs(ear_y - eye_y) > (ey[0][3] - ey[0][1]) * 1.5:
            nhan_xet.append("Vị trí tai đang bị vẽ lệch lên quá cao hoặc thấp hơn so với mắt khá nhiều.")
    
    print(f"📏 Nhận xét tỷ lệ: {nhan_xet if nhan_xet else ['Tốt']}")
    return nhan_xet

def phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h):
    print("🎨 Đang phân tích nghệ thuật phong cảnh...")
    nhan_xet = []
    h, t, s = boxes_dict.get("house", []), boxes_dict.get("tree", []), boxes_dict.get("sun", [])
    
    if h and t:
        if get_bottom(h[0]) < get_bottom(t[0]): 
            nhan_xet.append("Lưu ý luật xa gần: Nhà ở gần nên vẽ thấp hơn cây ở xa em nha!")
        else: 
            nhan_xet.append("Em đã áp dụng rất tốt quy luật xa gần, amazing good job!")
        
    if h:
        hx = get_center(h[0])[0]
        if (img_w * 0.25) < hx < (img_w * 0.75): 
            nhan_xet.append("Nhà đặt ở trung tâm làm điểm nhấn rất tốt!")
        else: 
            nhan_xet.append("Ngôi nhà đặt lệch tạo quy tắc 1/3 rất nghệ thuật, đáng khen đó bảo bối.")
        
    if h and s:
        sun_area = get_area(s[0])
        house_area = get_area(h[0])
        if sun_area > house_area:
            nhan_xet.append("Ông mặt trời em vẽ to hơn cả ngôi nhà kìa, thử vẽ nhỏ lại chút xíu cho cảnh vật thật hơn nhé!")
    
    print(f"🎨 Nhận xét nghệ thuật: {nhan_xet if nhan_xet else ['Tốt']}")
    return nhan_xet

# === API ENDPOINTS ===
@app.route("/classify", methods=["POST"])
def classify():
    print("\n" + "=" * 60)
    print("🔍 [API] NHẬN REQUEST PHÂN LOẠI ẢNH")
    print("=" * 60)
    
    if "image" not in request.files: 
        print("❌ Không có file ảnh")
        return jsonify({"error": "Không có ảnh"}), 400
    
    img_path = None
    try:
        img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.jpg")
        request.files["image"].save(img_path)
        print(f"📁 Đã lưu ảnh: {img_path}")
        
        loai_anh = classify_image(img_path)
        
        if loai_anh == "Unknown":
            print("⚠️ Không xác định được loại ảnh")
            return jsonify({
                "type": "Unknown",
                "message": "Ảnh của em không phải chân dung hoặc phong cảnh rõ ràng. Em hãy chụp lại bài vẽ của mình nhé!"
            }), 200
        
        if loai_anh == "ChanDung":
            print("🖼️ Xử lý ảnh chân dung...")
            results = model(img_path, verbose=False)[0]
            detected_objects = []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                raw_name = str(results.names[cls_id]).strip().lower()
                for req in REQUIRED:
                    if req in raw_name:
                        detected_objects.append(req)
            
            unique_detected = list(set(detected_objects))
            total_detected = len(unique_detected)
            print(f"📊 Số chi tiết phát hiện: {total_detected}")
            
            if total_detected < 2:
                print("⚠️ Phát hiện quá ít chi tiết")
                return jsonify({
                    "type": "Unknown",
                    "message": f"Ảnh có vẻ là chân dung nhưng chỉ thấy {total_detected} chi tiết. Em hãy vẽ thêm mắt, mũi, miệng, tai, tóc cho rõ nét nhé!"
                }), 200
                
        else:
            print("🏞️ Xử lý ảnh phong cảnh...")
            results = scenery_model(img_path, verbose=False)[0]
            boxes_dict = {name: [] for name in SCENERY_REQUIRED}
            for box in results.boxes:
                cls_id = int(box.cls[0])
                raw_name = str(results.names[cls_id]).strip().lower()
                for req in SCENERY_REQUIRED:
                    if req in raw_name:
                        boxes_dict[req].append(box)
            
            detected = [k for k, v in boxes_dict.items() if len(v) > 0]
            print(f"📊 Số chi tiết phát hiện: {len(detected)}")
            
            if len(detected) < 2:
                print("⚠️ Phát hiện quá ít chi tiết")
                return jsonify({
                    "type": "Unknown",
                    "message": "Ảnh có vẻ là phong cảnh nhưng các chi tiết chưa rõ. Em hãy vẽ thêm nhà, cây hoặc ông mặt trời nhé!"
                }), 200
        
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            print(f"🗑️ Đã xóa ảnh tạm: {img_path}")
        
        print(f"✅ Kết quả phân loại: {loai_anh}")
        print("=" * 60 + "\n")
        return jsonify({"type": loai_anh})
        
    except Exception as e:
        print(f"❌ Lỗi classify: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        return jsonify({"type": "Unknown", "message": "Có lỗi xảy ra khi xử lý ảnh. Vui lòng thử lại!"}), 200

@app.route("/predict", methods=["POST"])
def predict():
    print("\n" + "=" * 60)
    print("🎯 [API] NHẬN REQUEST DỰ ĐOÁN CHÂN DUNG")
    print("=" * 60)
    
    if "image" not in request.files: 
        print("❌ Không có file ảnh")
        return jsonify({"error": "Không có ảnh"}), 400
    
    filename = None
    img_path = None
    
    try:
        filename = f"{uuid.uuid4().hex}.jpg"
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        request.files["image"].save(img_path)
        penalty = float(request.form.get("penalty", 1))
        
        print(f"📁 Ảnh đã lưu: {img_path}")
        print(f"⚙️ Hệ số phạt: {penalty}")
        
        img_cv = cv2.imread(img_path)
        if img_cv is None:
            raise Exception("Không thể đọc ảnh")
            
        img_h, img_w, _ = img_cv.shape
        print(f"📐 Kích thước ảnh: {img_w}x{img_h}")
        
        results = model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())
        print(f"💾 Đã lưu ảnh kết quả: {boxed_name}")

        if not results.boxes:
            print("⚠️ Không phát hiện object nào")
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
                if req in raw_name:
                    boxes_dict[req].append(box)

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [k for k in REQUIRED if k not in detected]
        
        print(f"✅ Phát hiện: {detected}")
        print(f"❌ Thiếu: {missing}")
        
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

        score_base = diem_thanh_phan + diem_bo_cuc + diem_ty_le
        muc_phat = (so_loi_bo_cuc + so_loi_ty_le + len(missing) * 0.5) * (penalty - 1)
        score = score_base - muc_phat
        score = max(0, min(10, round(score, 1)))

        print(f"📊 Điểm số: {score}/10")

        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            print(f"🗑️ Đã xóa ảnh tạm: {img_path}")
        
        print("=" * 60 + "\n")
            
        return jsonify({
            "score": score,
            "detected": detected,
            "missing": missing,
            "nhan_xet_bo_cuc": loi_bo_cuc,
            "nhan_xet_ty_le": loi_ty_le,
            "loi_khuyen_giao_vien": loi_khuyen if loi_khuyen else ["Tranh em vẽ rất tốt, không có gì để chê!"],
            "boxed_image": f"/static/results/{boxed_name}"
        })
        
    except Exception as e:
        print(f"❌ Lỗi predict: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        return jsonify({
            "score": 0, "detected": [], "missing": REQUIRED,
            "nhan_xet_bo_cuc": ["Có lỗi xảy ra khi xử lý ảnh."], "nhan_xet_ty_le": [],
            "loi_khuyen_giao_vien": ["Xin lỗi, đã có lỗi xảy ra. Em vui lòng thử lại với ảnh khác nhé!"]
        }), 200

@app.route("/predict_scenery", methods=["POST"])
@app.route("/predict_scenery", methods=["POST"])
def predict_scenery():
    print("\n" + "=" * 60)
    print("🎯 [API] NHẬN REQUEST DỰ ĐOÁN PHONG CẢNH")
    print("=" * 60)
    
    if "image" not in request.files: 
        print("❌ Không có file ảnh")
        return jsonify({"error": "Không có ảnh"}), 400
    
    filename = None
    img_path = None
    
    try:
        filename = f"{uuid.uuid4().hex}.jpg"
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        request.files["image"].save(img_path)
        penalty = float(request.form.get("penalty", 1))
        
        print(f"📁 Ảnh đã lưu: {img_path}")
        print(f"⚙️ Hệ số phạt: {penalty}")
        
        # === LẤY DANH SÁCH NOUNS TỪ FILE SETTINGS ===
        settings_file = "user_settings.json"
        nouns_from_settings = []
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    nouns_from_settings = settings.get("nouns_en", [])  # Lấy nouns tiếng Anh
                    print(f"📚 NOUNS từ settings: {nouns_from_settings}")
            except Exception as e:
                print(f"⚠️ Không đọc được nouns từ settings: {e}")
        
        # === TẠO DANH SÁCH VẬT CẦN CÓ ===
        # Gộp danh sách cố định + nouns từ settings
        base_required = SCENERY_REQUIRED.copy()  # ["house", "tree", "sun"]
        
        # Thêm các nouns từ settings vào danh sách (loại bỏ trùng)
        for noun in nouns_from_settings:
            noun_lower = noun.lower().strip()
            if noun_lower not in base_required and noun_lower not in ["house", "tree", "sun"]:
                base_required.append(noun_lower)
        
        print(f"📋 DANH SÁCH VẬT CẦN CÓ: {base_required}")
        print(f"   - Cơ bản: {SCENERY_REQUIRED}")
        print(f"   - Thêm từ settings: {nouns_from_settings}")
        
        img_cv = cv2.imread(img_path)
        if img_cv is None:
            raise Exception("Không thể đọc ảnh")
            
        img_h, img_w, _ = img_cv.shape
        print(f"📐 Kích thước ảnh: {img_w}x{img_h}")
        
        results = scenery_model(img_path, verbose=False)[0]
        boxed_name = f"boxed_{filename}"
        cv2.imwrite(os.path.join(RESULT_FOLDER, boxed_name), results.plot())
        print(f"💾 Đã lưu ảnh kết quả: {boxed_name}")

        if not results.boxes:
            print("⚠️ Không phát hiện object nào")
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
        
        # Tạo dict cho tất cả vật cần có
        boxes_dict = {name: [] for name in base_required}
        for cid, box in zip(cls_ids, boxes_xyxy):
            raw_name = str(results.names[cid]).strip().lower()
            for req in base_required:
                if req in raw_name:
                    boxes_dict[req].append(box)
                    print(f"   ✅ Phát hiện: {req}")

        detected = [k for k, v in boxes_dict.items() if len(v) > 0]
        missing = [v for v in base_required if v not in detected]
        
        print(f"✅ Phát hiện: {detected}")
        print(f"❌ Thiếu: {missing}")
        print(f"📊 Tỷ lệ hoàn thành: {len(detected)}/{len(base_required)}")
        
        # === TẠO LỜI KHUYÊN DỰA TRÊN DANH SÁCH ===
        loi_khuyen = []
        
        # Lời khuyên cho các vật cơ bản
        if "house" not in detected:
            loi_khuyen.append("Em thiếu mất ngôi nhà rồi huhu, đây là điểm nhấn quan trọng nhất của tranh phong cảnh đó.")
        if "tree" not in detected:
            loi_khuyen.append("Thêm một vài bóng cây xanh sẽ giúp bức tranh có sức sống hơn rất nhiều.")
        if "sun" not in detected:
            loi_khuyen.append("Bầu trời hơi trống, em thử vẽ thêm ông mặt trời, mây và chim xem sao nha cục dàng.")
        
        # Lời khuyên cho các nouns từ settings bị thiếu
        for noun in missing:
            if noun not in SCENERY_REQUIRED:  # Nếu là noun từ settings
                loi_khuyen.append(f"Em còn thiếu {noun} trong bức tranh, hãy thêm vào nhé!")
        
        if len(detected) == len(base_required):
            loi_khuyen.append("Tranh của em rất đầy đủ chi tiết! Nếu muốn xuất sắc hơn, có thể điểm thêm bãi cỏ hoặc đàn chim trôi nhé.")

        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        nhan_xet_nghe_thuat_list = phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h)
        nhan_xet_mau_sac_str = phan_tich_mau_sac(img_cv)

        # === TÍNH ĐIỂM DỰA TRÊN DANH SÁCH ĐỘNG ===
        # Trọng số: các vật cơ bản có trọng số cao hơn
        trong_so_phong_canh = {
            "house": 2.5, 
            "tree": 2.0, 
            "sun": 1.5
        }
        
        # Thêm trọng số cho các noun từ settings (trọng số mặc định 1.0)
        for noun in base_required:
            if noun not in trong_so_phong_canh:
                trong_so_phong_canh[noun] = 1.0
        
        # Tính điểm thành phần
        diem_thanh_phan = 0
        for obj in detected:
            diem_thanh_phan += trong_so_phong_canh.get(obj, 1.0)
        
        # Điểm tối đa có thể đạt được
        diem_toi_da = sum([trong_so_phong_canh.get(obj, 1.0) for obj in base_required])
        
        print(f"📊 Điểm thành phần: {diem_thanh_phan}/{diem_toi_da}")
        print(f"📊 Tỷ lệ hoàn thành: {len(detected)}/{len(base_required)}")

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

        # === CÔNG THỨC TÍNH ĐIỂM MỚI ===
        # Chuẩn hóa điểm thành phần về thang 5 điểm
        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * 5.0 if diem_toi_da > 0 else 0
        
        # Tổng điểm cơ bản
        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac
        
        # Tính điểm phạt dựa trên số lượng thiếu và penalty
        so_vat_thieu = len(missing)
        muc_phat = (so_loi_bo_cuc * 0.5 + so_vat_thieu * 0.8) * (penalty - 1)
        score = score_base - muc_phat
        
        # Chuẩn hóa về thang 10
        score = score * 1.25  # Nhân với 1.25 để đưa về thang 10 (vì max base là 8)
        score = max(0, min(10, round(score, 1)))

        print(f"📊 Chi tiết điểm:")
        print(f"   - Điểm thành phần (chuẩn hóa): {diem_thanh_phan_chuan:.2f}/5")
        print(f"   - Điểm bố cục: {diem_bo_cuc:.2f}/2")
        print(f"   - Điểm nghệ thuật: {diem_nghe_thuat:.2f}/2")
        print(f"   - Điểm màu sắc: {diem_mau_sac:.2f}/1")
        print(f"   - Phạt: {muc_phat:.2f}")
        print(f"📊 Điểm tổng: {score}/10")

        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            print(f"🗑️ Đã xóa ảnh tạm: {img_path}")
        
        print("=" * 60 + "\n")
            
        return jsonify({
            "score": score,
            "detected": detected,
            "missing": missing,
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
        print(f"❌ Lỗi predict_scenery: {str(e)}")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        return jsonify({
            "score": 0, 
            "detected": [], 
            "missing": SCENERY_REQUIRED,
            "total_required": len(SCENERY_REQUIRED),
            "required_list": SCENERY_REQUIRED,
            "nouns_from_settings": [],
            "nhan_xet_bo_cuc": ["Có lỗi xảy ra khi xử lý ảnh."], 
            "nhan_xet_mau_sac": "",
            "nhan_xet_nghe_thuat": [], 
            "loi_khuyen_giao_vien": ["Xin lỗi, đã có lỗi xảy ra. Em vui lòng thử lại!"]
        }), 200

if __name__ == "__main__":
    app.run(debug=True)