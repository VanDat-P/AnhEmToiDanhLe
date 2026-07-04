from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import uuid
import json
import datetime
from nlp_utils import *

from models import *
from nlp.utils import *
from vision_utils import *

app = Flask(__name__)
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5000", "http://127.0.0.1:5000"])

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

@app.route("/save_settings", methods=["POST"])
def save_settings():
    try:
        data = request.get_json()
        user_text = data.get("text", "")
        penalty = float(data.get("penalty", 1.5))
        art_type = data.get("art_type", "")
        
        settings_file = "user_settings.json"
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
            
        verbs_list = []
        nouns_list = []
        verbs_en_list = []
        nouns_en_list = []
        all_rules = []
        sentences_data = []
        possible_rules = []
        if user_text and user_text.strip():
            # SỬA: Tách thành nhiều câu theo dấu chấm (.)
            clauses = [c.strip() for c in user_text.split('.') if c.strip()]
            obj_dict = PORTRAIT_OBJECT_MAPPING if art_type == "portrait" else SCENERY_OBJECT_MAPPING
            
            for clause in clauses:
                try:
                    clause = clause.lower()
                    pos_tags = custom_pos_tag(clause)
                    possible_rules.append(parse_rulesv2(pos_tags,clause))
                    
                    raw_verbs_vi = [word for word, tag in pos_tags if tag.startswith('V')]
                    raw_nouns_vi = [word for word, tag in pos_tags if tag.startswith('N')]
                    
                    # Bắt thêm danh từ ghép thủ công tránh underthesea tách lỗi
                    for vi_word in obj_dict.keys():
                        if re.search(rf"(?:\b|\s|^){vi_word}(?:\b|\s|$)", clause.lower()) and vi_word not in raw_nouns_vi:
                            raw_nouns_vi.append(vi_word)
                            
                    clause_verbs_en = []
                    for v in raw_verbs_vi:
                        try:
                            clause_verbs_en.append(translator.translate(v).lower())
                        except:
                            clause_verbs_en.append(v)
                            
                    clause_nouns_en = []
                    for n in raw_nouns_vi:
                        en_mapped = obj_dict.get(n.lower())
                        if en_mapped:
                            clause_nouns_en.append(en_mapped)
                        else:
                            try:
                                clause_nouns_en.append(translator.translate(n).lower())
                            except:
                                clause_nouns_en.append(n)
                                
                    clause_nouns_en = filter_valid_nouns_en(clause_nouns_en, art_type)
                    
                    # Kiểm tra tính bắt buộc
                    has_co = any(v.lower() in ["có", "phải", "cần", "vẽ", "bắt buộc"] for v in raw_verbs_vi) or "có" in clause.lower()
                    clause_rules = parse_rules(clause, art_type)
                    
                    sentences_data.append({
                        "raw_tokens" : pos_tags,
                        "sentence": clause,
                        "raw_verbs_vi": list(set(raw_verbs_vi)),
                        "raw_nouns_vi": list(set(raw_nouns_vi)),
                        "verbs_en": list(set(clause_verbs_en)),
                        "nouns_en": list(set(clause_nouns_en)),
                        "mandatory_nouns_en": list(set(clause_nouns_en)) if has_co else [],
                        "optional_nouns_en": [] if has_co else list(set(clause_nouns_en)),
                        "has_co_verb": has_co,
                        "comparison_rules": clause_rules,
                        "pos_tags": pos_tags
                    })
                    
                    verbs_list.extend(raw_verbs_vi)
                    nouns_list.extend(raw_nouns_vi)
                    verbs_en_list.extend(clause_verbs_en)
                    nouns_en_list.extend(clause_nouns_en)
                    all_rules.extend(clause_rules)
                    
                except Exception as e:
                    print(f"Lỗi extract: {e}")
            
            verbs_list = list(set(verbs_list))
            nouns_list = list(set(nouns_list))
            verbs_en_list = list(set(verbs_en_list))
            nouns_en_list = list(set(nouns_en_list))
        
        settings['text'] = user_text
        settings['penalty'] = penalty
        settings['art_type'] = art_type
        settings['verbs_vi'] = verbs_list
        settings['nouns_vi'] = nouns_list
        settings['verbs_en'] = verbs_en_list
        settings['nouns_en'] = nouns_en_list
        settings['rules'] = all_rules
        
        # SỬA: Lưu JSON theo cấu trúc mới
        if art_type:
            settings[f"{art_type}_text"] = user_text
            settings[f"{art_type}_sentences_data"] = sentences_data
            settings[f"{art_type}_last_updated"] = str(datetime.now())
            
        settings['last_updated'] = str(datetime.now())
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        with open ("rules.json","w", encoding = "utf-8") as f:
            json.dump(possible_rules, f,ensure_ascii=False ,indent = 4)
        print(f"✅ Đã lưu settings cho {art_type}")

        
        return jsonify({
            "success": True,
            "message": "Đã lưu cài đặt lên server!",
            "art_type": art_type,
            "verbs_vi": verbs_list,
            "nouns_vi": nouns_list,
            "verbs_en": verbs_en_list,
            "nouns_en": nouns_en_list,
            "rules": all_rules
        })

    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


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
    

REQUIRED = ["eye", "eyebrow", "nose", "mouth", "face", "ear", "hair"]
SCENERY_REQUIRED = ["tree", "sun"]


RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

print("\n✅ SERVER ĐÃ SẴN SÀNG!\n")


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
        
        # --- CƠ CHẾ ĐIỂM ĐỘNG CHÂN DUNG ---
        user_text = settings.get("text", "")
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)

        trong_so_chan_dung = {"face": 1.5, "eye": 1.5, "nose": 1.0, "mouth": 1.0, "hair": 1.0, "eyebrow": 0.5, "ear": 0.5}
        diem_toi_da = sum(trong_so_chan_dung.values())
        
        diem_thanh_phan = sum([trong_so_chan_dung.get(obj, 0) for obj in detected])
        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * dynamic_weights["objects"] if diem_toi_da > 0 else 0

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, dynamic_weights["layout"] - (so_loi_bo_cuc * (dynamic_weights["layout"] / 2))) 

        so_loi_ty_le = len(loi_ty_le)
        diem_ty_le = max(0, dynamic_weights["art_proportion"] - (so_loi_ty_le * (dynamic_weights["art_proportion"] / 3))) 

        # Vì ảnh chân dung chưa phân tích màu sắc, hệ thống tự động tặng full điểm màu theo trọng số
        diem_mau_sac = dynamic_weights["color"]

        bonus_rules = min(len(rule_success) * 0.5, 1.5)
        penalt_rules = len(rule_errors) * 0.5

        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_ty_le + diem_mau_sac + bonus_rules - penalt_rules
        so_vat_thieu = len(missing)
        muc_phat_do_kho = (so_loi_bo_cuc + so_loi_ty_le + so_vat_thieu * 0.5) * (penalty - 1)

        # --- CƠ CHẾ ĐIỂM ĐỘNG VÀ ĐIỂM TUYỆT ĐỐI (ĐÃ SỬA LỖI TĂNG ĐIỂM) CHO CHÂN DUNG ---
        user_text = settings.get("text", "")
        tru_diem_tuyet_doi = 0.0
        cong_diem_tuyet_doi = 0.0
        
        # Đếm số vật thiếu để tính điểm phạt độ khó tự nhiên
        so_vat_thieu_tu_nhien = len(missing)

        if user_text:
            text_lower = user_text.lower()
            tat_ca_vat_the = detected + missing  
            vat_bi_phat = []
            
            # SỬA: TÁCH VĂN BẢN THEO DẤU CHẤM
            danh_sach_cau = [c.strip() for c in text_lower.split('.') if c.strip()]
            
            for cau in danh_sach_cau:
                
                # 1. QUÉT LỆNH THƯỞNG
                for match in re.finditer(r'(?:cộng|thưởng|thêm)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_cong = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    # 1.1 Ưu tiên kiểm tra Luật Không Gian/Tỷ Lệ (Relations)
                    for rs in rule_success:
                        if rs.lower() in cau:
                            cong_diem_tuyet_doi += diem_cong
                            loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì vẽ đúng luật '{rs}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue
                    
                    # 1.2 Kiểm tra Vật Thể (Objects)
                    for obj in tat_ca_vat_the:
                        cac_cach_goi = [vi for vi, en in PORTRAIT_OBJECT_MAPPING.items() if en == obj]
                        if not cac_cach_goi: cac_cach_goi = [PORTRAIT_OBJECT_VI.get(obj, obj)]
                        matched_name = next((name for name in cac_cach_goi if name in cau), None)
                        
                        if matched_name:
                            cau_phu_dinh = any(kw in cau for kw in ["không", "chưa", "thiếu"])
                            if cau_phu_dinh and obj in missing:
                                cong_diem_tuyet_doi += diem_cong
                                loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì em đã KHÔNG VẼ '{matched_name}'!")
                                break
                            elif not cau_phu_dinh and obj in detected:
                                cong_diem_tuyet_doi += diem_cong
                                loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì em ĐÃ VẼ '{matched_name}'!")
                                break
                
                # 2. QUÉT LỆNH PHẠT
                for match in re.finditer(r'(?:trừ|phạt|bớt)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_tru = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    # 2.1 Ưu tiên kiểm tra Luật Không Gian/Tỷ Lệ bị vi phạm
                    for re_err in rule_errors:
                        if re_err.lower() in cau:
                            tru_diem_tuyet_doi += diem_tru
                            loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do vi phạm luật: '{re_err}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue

                    # 2.2 Kiểm tra Vật Thể bị sai sót
                    for obj in tat_ca_vat_the:
                        cac_cach_goi = [vi for vi, en in PORTRAIT_OBJECT_MAPPING.items() if en == obj]
                        if not cac_cach_goi: cac_cach_goi = [PORTRAIT_OBJECT_VI.get(obj, obj)]
                        matched_name = next((name for name in cac_cach_goi if name in cau), None)
                        
                        if matched_name and obj not in vat_bi_phat:
                            cau_phu_dinh = any(kw in cau for kw in ["không", "chưa", "thiếu"])
                            if cau_phu_dinh and obj in missing:
                                tru_diem_tuyet_doi += diem_tru
                                vat_bi_phat.append(obj)
                                so_vat_thieu_tu_nhien -= 1 
                                loi_khuyen = [lk for lk in loi_khuyen if matched_name not in lk]
                                loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do THIẾU '{matched_name}'!")
                                break
                            elif not cau_phu_dinh and obj in detected:
                                tru_diem_tuyet_doi += diem_tru
                                vat_bi_phat.append(obj)
                                loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm vì VẼ THỪA '{matched_name}' sai yêu cầu!")
                                break

        # 2. TÍNH ĐIỂM THÀNH PHẦN (Dựa trên danh sách detected thật 100%)
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)

        trong_so_chan_dung = {"face": 1.5, "eye": 1.5, "nose": 1.0, "mouth": 1.0, "hair": 1.0, "eyebrow": 0.5, "ear": 0.5}
        diem_toi_da = sum(trong_so_chan_dung.values())
        
        diem_thanh_phan = sum([trong_so_chan_dung.get(obj, 0) for obj in detected])
        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * dynamic_weights["objects"] if diem_toi_da > 0 else 0

        # 3. TÍNH ĐIỂM CÁC TIÊU CHÍ KHÁC
        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, dynamic_weights["layout"] - (so_loi_bo_cuc * (dynamic_weights["layout"] / 2))) 

        so_loi_ty_le = len(loi_ty_le)
        diem_ty_le = max(0, dynamic_weights["art_proportion"] - (so_loi_ty_le * (dynamic_weights["art_proportion"] / 3))) 

        diem_mau_sac = dynamic_weights["color"]

        bonus_rules = min(len(rule_success) * 0.5, 1.5)
        penalt_rules = len(rule_errors) * 0.5

        # 4. TỔNG KẾT ĐIỂM
        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_ty_le + diem_mau_sac + bonus_rules - penalt_rules
        
        # TÍNH PHẠT ĐỘ KHÓ: Sử dụng biến đã được trừ đi những vật bị phạt lệnh
        muc_phat_do_kho = (so_loi_bo_cuc + so_loi_ty_le + so_vat_thieu_tu_nhien * 0.5) * (penalty - 1)

        score_tinh_toan = score_base - muc_phat_do_kho - tru_diem_tuyet_doi + cong_diem_tuyet_doi
        score = max(0, min(10, round(score_tinh_toan, 1)))

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
            if noun_lower not in base_required and noun_lower not in ["tree", "sun"]:
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

        # --- CƠ CHẾ ĐIỂM ĐỘNG PHONG CẢNH ---
        user_text = settings.get("text", "")
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)

        trong_so_phong_canh = {"house": 2.5, "tree": 2.0, "sun": 1.5}
        for noun in base_required:
            if noun not in trong_so_phong_canh: trong_so_phong_canh[noun] = 1.0
            
        diem_thanh_phan = sum([trong_so_phong_canh.get(obj, 1.0) for obj in detected]) 
        diem_toi_da = sum([trong_so_phong_canh.get(obj, 1.0) for obj in base_required])
        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * dynamic_weights["objects"] if diem_toi_da > 0 else 0

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, dynamic_weights["layout"] - (so_loi_bo_cuc * (dynamic_weights["layout"] / 3)))

        diem_nghe_thuat = dynamic_weights["art_proportion"] * 0.5
        for nx in nhan_xet_nghe_thuat_list:
            if "tốt" in nx or "nghệ thuật" in nx or "amazing" in nx:
                diem_nghe_thuat += (dynamic_weights["art_proportion"] * 0.25)
            elif "to hơn" in nx or "lưu ý" in nx.lower():
                diem_nghe_thuat -= (dynamic_weights["art_proportion"] * 0.25)
        diem_nghe_thuat = max(0, min(dynamic_weights["art_proportion"], diem_nghe_thuat))

        diem_mau_sac = dynamic_weights["color"] * 0.6 
        if "nhạt nhòa" in nhan_xet_mau_sac_str or "hơi tối" in nhan_xet_mau_sac_str:
            diem_mau_sac -= (dynamic_weights["color"] * 0.3)
        elif "rất tốt" in nhan_xet_mau_sac_str or "rực rỡ" in nhan_xet_mau_sac_str:
            diem_mau_sac += (dynamic_weights["color"] * 0.4)
        diem_mau_sac = max(0, min(dynamic_weights["color"], diem_mau_sac))

        bonus_rules = min(len(rule_success) * 0.5, 1.5)
        penalt_rules = len(rule_errors) * 0.5

        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac + bonus_rules - penalt_rules
        so_vat_thieu = len(missing)
        muc_phat_do_kho = (so_loi_bo_cuc * 0.5 + so_vat_thieu * 0.8) * (penalty - 1)

        # --- CƠ CHẾ ĐIỂM ĐỘNG VÀ ĐIỂM TUYỆT ĐỐI (ĐÃ SỬA LỖI TĂNG ĐIỂM) ---
        user_text = settings.get("text", "")
        tru_diem_tuyet_doi = 0.0
        cong_diem_tuyet_doi = 0.0
        
        # Đếm số vật thiếu để tính điểm phạt độ khó tự nhiên
        so_vat_thieu_tu_nhien = len(missing)

        if user_text:
            text_lower = user_text.lower()
            tat_ca_vat_the = detected + missing  
            vat_bi_phat = []
            
            # SỬA: TÁCH VĂN BẢN THEO DẤU CHẤM
            danh_sach_cau = [c.strip() for c in text_lower.split('.') if c.strip()]
            
            for cau in danh_sach_cau:
                
                # 1. QUÉT LỆNH THƯỞNG
                for match in re.finditer(r'(?:cộng|thưởng|thêm)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_cong = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    # 1.1 Ưu tiên kiểm tra Luật Không Gian (Relations)
                    for rs in rule_success:
                        if rs.lower() in cau:
                            cong_diem_tuyet_doi += diem_cong
                            loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì vẽ đúng luật '{rs}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue
                    
                    # 1.2 Kiểm tra Vật Thể (Objects)
                    for obj in tat_ca_vat_the:
                        cac_cach_goi = [vi for vi, en in SCENERY_OBJECT_MAPPING.items() if en == obj]
                        if not cac_cach_goi: cac_cach_goi = [SCENERY_OBJECT_VI.get(obj, obj)]
                        matched_name = next((name for name in cac_cach_goi if name in cau), None)
                        
                        if matched_name:
                            cau_phu_dinh = any(kw in cau for kw in ["không", "chưa", "thiếu"])
                            if cau_phu_dinh and obj in missing:
                                cong_diem_tuyet_doi += diem_cong
                                loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì em đã KHÔNG VẼ '{matched_name}'!")
                                break
                            elif not cau_phu_dinh and obj in detected:
                                cong_diem_tuyet_doi += diem_cong
                                loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì em ĐÃ VẼ '{matched_name}'!")
                                break
                
                # 2. QUÉT LỆNH PHẠT
                for match in re.finditer(r'(?:trừ|phạt|bớt)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_tru = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    # 2.1 Ưu tiên kiểm tra Luật Không Gian bị vi phạm
                    for re_err in rule_errors:
                        if re_err.lower() in cau:
                            tru_diem_tuyet_doi += diem_tru
                            loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do vi phạm luật: '{re_err}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue

                    # 2.2 Kiểm tra Vật Thể bị sai sót
                    for obj in tat_ca_vat_the:
                        cac_cach_goi = [vi for vi, en in SCENERY_OBJECT_MAPPING.items() if en == obj]
                        if not cac_cach_goi: cac_cach_goi = [SCENERY_OBJECT_VI.get(obj, obj)]
                        matched_name = next((name for name in cac_cach_goi if name in cau), None)
                        
                        if matched_name and obj not in vat_bi_phat:
                            cau_phu_dinh = any(kw in cau for kw in ["không", "chưa", "thiếu"])
                            if cau_phu_dinh and obj in missing:
                                tru_diem_tuyet_doi += diem_tru
                                vat_bi_phat.append(obj)
                                so_vat_thieu_tu_nhien -= 1 
                                loi_khuyen = [lk for lk in loi_khuyen if matched_name not in lk]
                                loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do THIẾU '{matched_name}'!")
                                break
                            elif not cau_phu_dinh and obj in detected:
                                tru_diem_tuyet_doi += diem_tru
                                vat_bi_phat.append(obj)
                                loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm vì VẼ THỪA '{matched_name}' sai yêu cầu!")
                                break

        # 2. TÍNH ĐIỂM THÀNH PHẦN 
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)

        trong_so_phong_canh = {"house": 2.5, "tree": 2.0, "sun": 1.5}
        for noun in base_required:
            if noun not in trong_so_phong_canh: trong_so_phong_canh[noun] = 1.0
            
        diem_thanh_phan = sum([trong_so_phong_canh.get(obj, 1.0) for obj in detected]) 
        diem_toi_da = sum([trong_so_phong_canh.get(obj, 1.0) for obj in base_required])
        diem_thanh_phan_chuan = (diem_thanh_phan / diem_toi_da) * dynamic_weights["objects"] if diem_toi_da > 0 else 0

        # 3. TÍNH ĐIỂM CÁC TIÊU CHÍ KHÁC
        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, dynamic_weights["layout"] - (so_loi_bo_cuc * (dynamic_weights["layout"] / 3)))

        diem_nghe_thuat = dynamic_weights["art_proportion"] * 0.5
        for nx in nhan_xet_nghe_thuat_list:
            if "tốt" in nx or "nghệ thuật" in nx or "amazing" in nx:
                diem_nghe_thuat += (dynamic_weights["art_proportion"] * 0.25)
            elif "to hơn" in nx or "lưu ý" in nx.lower():
                diem_nghe_thuat -= (dynamic_weights["art_proportion"] * 0.25)
        diem_nghe_thuat = max(0, min(dynamic_weights["art_proportion"], diem_nghe_thuat))

        diem_mau_sac = dynamic_weights["color"] * 0.6 
        if "nhạt nhòa" in nhan_xet_mau_sac_str or "hơi tối" in nhan_xet_mau_sac_str:
            diem_mau_sac -= (dynamic_weights["color"] * 0.3)
        elif "rất tốt" in nhan_xet_mau_sac_str or "rực rỡ" in nhan_xet_mau_sac_str:
            diem_mau_sac += (dynamic_weights["color"] * 0.4)
        diem_mau_sac = max(0, min(dynamic_weights["color"], diem_mau_sac))

        bonus_rules = min(len(rule_success) * 0.5, 1.5)
        penalt_rules = len(rule_errors) * 0.5

        # 4. TỔNG KẾT ĐIỂM
        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac + bonus_rules - penalt_rules
        
        # TÍNH PHẠT ĐỘ KHÓ: Sử dụng biến đã được trừ đi những vật bị phạt lệnh
        muc_phat_do_kho = (so_loi_bo_cuc * 0.5 + so_vat_thieu_tu_nhien * 0.8) * (penalty - 1)

        score_tinh_toan = score_base - muc_phat_do_kho - tru_diem_tuyet_doi + cong_diem_tuyet_doi
        score = max(0, min(10, round(score_tinh_toan, 1)))

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