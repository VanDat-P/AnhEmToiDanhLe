from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import uuid
import json
from datetime import datetime
import cv2
import re

from nlp_utils import *
from models import *
from vision_utils import *

# IMPORT MASTER ENGINE
from templates import evaluate_drawing

app = Flask(__name__)
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5000", "http://127.0.0.1:5000"])

REQUIRED = ["eye", "nose", "mouth"]
SCENERY_REQUIRED = ["tree", "sun","house"]
detected_object_scenery =[]

RESULT_FOLDER = "static/results"
os.makedirs(RESULT_FOLDER, exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

print("\n✅ SERVER ĐÃ SẴN SÀNG!\n")

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
            clauses = [c.strip() for c in user_text.split('.') if c.strip()]
            obj_dict = PORTRAIT_OBJECT_MAPPING if art_type == "portrait" else SCENERY_OBJECT_MAPPING
            
            for clause in clauses:
                try:
                    clause = clause.lower()
                    pos_tags = custom_pos_tag(clause)
                    
                    if 'parse_rulesv2' in globals():
                        rule_v2 = parse_rulesv2(pos_tags, clause)

                        if rule_v2:
                            possible_rules.append(rule_v2)
                            all_rules.append(rule_v2)

                            # Đã parse được bằng parser mới thì bỏ qua parser cũ
                            continue
                    
                    raw_verbs_vi = [word for word, tag in pos_tags if tag.startswith('V')]
                    raw_nouns_vi = [word for word, tag in pos_tags if tag.startswith('N')]
                    
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
                    
                    has_co = any(v.lower() in ["có", "phải", "cần", "vẽ", "bắt buộc"] for v in raw_verbs_vi) or "có" in clause.lower()
                    
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
                        "pos_tags": pos_tags
                    })
                    
                    verbs_list.extend(raw_verbs_vi)
                    nouns_list.extend(raw_nouns_vi)
                    verbs_en_list.extend(clause_verbs_en)
                    nouns_en_list.extend(clause_nouns_en)
                    
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
        settings[f"{art_type}_rules"] = all_rules
        settings["rules"] = all_rules   # nếu vẫn muốn giữ
        
        if art_type:
            settings[f"{art_type}_text"] = user_text
            settings[f"{art_type}_sentences_data"] = sentences_data
            settings[f"{art_type}_last_updated"] = str(datetime.now())
            
        settings['last_updated'] = str(datetime.now())
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        with open ("rules.json","w", encoding = "utf-8") as f:
            json.dump(possible_rules, f, ensure_ascii=False, indent=4)
            
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

@app.route("/classify", methods=["POST"])
def classify():
    if "image" not in request.files:
        return jsonify({"error": "Không có ảnh"}), 400
    
    img_path = None
    try:
        img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.jpg")
        request.files["image"].save(img_path)
        
        loai_anh = classify_image(img_path)
        print("====== CLASSIFY ======")
        print(loai_anh)
        print("======================")
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
                detected_objects.append(raw_name)
            
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


            detected_objects = []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                raw_name = str(results.names[cls_id]).strip().lower()
                detected_objects.append(raw_name)


            unique_detected = list(set(detected_objects))
            total_detected = len(unique_detected)
            unique_detected = list(set(detected_objects))
            detected_object_scenery = unique_detected.copy()
            total_detected = len(unique_detected)
            

            if total_detected < 2:
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
                print("SETTINGS KEYS:", settings.keys())
                rules = settings.get("portrait_rules", [])

        print("RULES LOAD =", rules)
        
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
        
        # ĐÂY LÀ BOXES DICT GỐC (Cho hàm vision_utils cũ của bạn)
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
        
        # BỌC DỮ LIỆU ĐỂ TÍCH HỢP MASTER ENGINE 
        boxes_dict_template = {k: [{"box": b} for b in v] for k, v in boxes_dict.items()}
        _, rule_details = evaluate_drawing(rules, boxes_dict_template)
       
        
        for rule in rules:
            rule_str = rule.get("rule", "")
            detail = rule_details.get(rule_str)

            if detail is None:
                ok = False
            else:
                score = detail.get("score", 0)
                ok = score >= 50

            obj1_vi = rule.get('object1_vi', PORTRAIT_OBJECT_VI.get(rule.get('object1', ''), rule.get('object1', '')))
            obj2_vi = rule.get('object2_vi', PORTRAIT_OBJECT_VI.get(rule.get('object2', ''), rule.get('object2', '')))
            relation_vi = rule.get('relation_vi', RELATION_VI.get(rule.get('relation', ''), rule.get('relation', '')))
            chuoi_hien_thi = f"{obj1_vi} {relation_vi} {obj2_vi}".strip()
            if not chuoi_hien_thi:
                chuoi_hien_thi = rule_str
            
            if ok:
                rule_success.append(f"{chuoi_hien_thi}")
            else:
                rule_errors.append(f"{relation_vi} {obj1_vi} ,{obj2_vi}" if relation_vi else f"Vi phạm: {chuoi_hien_thi}")

        print("RULES =", rules)
        print("RULE DETAILS =", rule_details)
        print("SUCCESS =", rule_success)
        print("ERROR =", rule_errors)
        loi_bo_cuc = kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h)
        loi_ty_le = luat_ty_le_chan_dung(boxes_dict_template)        
        loi_khuyen = []
        if "hair" not in detected and "ear" not in detected:
            loi_khuyen.append("Gợi ý: Khuôn mặt sẽ hoàn hảo hơn nếu em vẽ thêm phần viền khuôn mặt, tóc vành tai.")
        if missing:
            loi_khuyen.append(f"Em nhớ bổ sung các bộ phận còn thiếu nhé: {', '.join(missing)}.")
        
        # --- CƠ CHẾ ĐIỂM ĐỘNG CHÂN DUNG ---
        user_text = settings.get("portrait_text", "")
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)
        trong_so_chan_dung = {"eye": 1.5, "nose": 1.0, "mouth": 1.0}
        diem_toi_da = sum(trong_so_chan_dung.values())
        for obj in detected:
            if obj not in trong_so_chan_dung.keys():
                trong_so_chan_dung[obj] = 0.5
                diem_toi_da += 0.5
        diem_thanh_phan = sum([trong_so_chan_dung.get(obj, 0) for obj in detected])
        diem_thanh_phan_chuan = (float(diem_thanh_phan) / float(diem_toi_da)) * float(dynamic_weights.get("objects", 5.0)) if diem_toi_da > 0 else 0

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        diem_bo_cuc = max(0, dynamic_weights.get("layout", 2.0) - (so_loi_bo_cuc * (dynamic_weights.get("layout", 2.0) / 2))) 

        so_loi_ty_le = len(loi_ty_le)
        diem_ty_le = max(0, dynamic_weights.get("art_proportion", 2.0) - (so_loi_ty_le * (dynamic_weights.get("art_proportion", 2.0) / 3))) 

        diem_mau_sac = dynamic_weights.get("color", 1.0)

        bonus_rules = min(len(rule_success) * 0.15, 0.6)
        penalt_rules = len(rule_errors) * 1

        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_ty_le + diem_mau_sac + bonus_rules - penalt_rules
        so_vat_thieu = len(missing)
        muc_phat_do_kho = (so_loi_bo_cuc + so_loi_ty_le + so_vat_thieu * 0.5) * (penalty - 1)

        # --- CƠ CHẾ ĐIỂM ĐỘNG VÀ ĐIỂM TUYỆT ĐỐI ---
        tru_diem_tuyet_doi = 0.0
        cong_diem_tuyet_doi = 0.0
        so_vat_thieu_tu_nhien = len(missing)
        danh_sach_cau = []
        if user_text:
            text_lower = user_text.lower()
            tat_ca_vat_the = detected + missing  
            vat_bi_phat = []
            
            danh_sach_cau = [c.strip() for c in text_lower.split('.') if c.strip()] or []
            
            for cau in danh_sach_cau:
                # 1. QUÉT LỆNH THƯỞNG
                for match in re.finditer(r'(?:cộng|thưởng|thêm)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_cong = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    for rs in rule_success:
                        if rs.lower() in cau:
                            cong_diem_tuyet_doi += diem_cong
                            loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì vẽ đúng luật '{rs}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue
                    
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
                    
                    for re_err in rule_errors:
                        if re_err.lower() in cau:
                            tru_diem_tuyet_doi += diem_tru
                            loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do vi phạm luật: '{re_err}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue

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

        score_tinh_toan = score_base - muc_phat_do_kho - tru_diem_tuyet_doi + cong_diem_tuyet_doi
        score = max(0, min(10, round(score_tinh_toan, 1)))
        score_breakdown = {
            
                            "details":[
                        {
                            "title":"Chi tiết đối tượng",
                            "score":round(diem_thanh_phan_chuan,2),
                            "max":dynamic_weights.get("objects",5),
                            "description":"Đánh giá số lượng bộ phận AI phát hiện được.",
                            "formula":f"{len(detected)}/{len(REQUIRED)} đối tượng",
                            "detected":detected,
                            "missing":missing
                        },
                        {
                            "title":"Bố cục",
                            "score":round(diem_bo_cuc,2),
                            "max":dynamic_weights.get("layout",2),
                            "description":"Đánh giá vị trí các bộ phận trên khuôn mặt.",
                            "formula":"Kiểm tra khoảng cách và vị trí bằng luật hình học",
                            "result":loi_bo_cuc
                        },
                        {
                            "title":"Tỷ lệ khuôn mặt",
                            "score":round(diem_ty_le,2),
                            "max":dynamic_weights.get("art_proportion",2),
                            "description":"Đánh giá tỷ lệ giữa mắt, mũi, miệng.",
                            "formula":"Rule-based",
                            "result": loi_ty_le
                        },
                        {
                            "title":"Màu sắc",
                            "score":round(diem_mau_sac,2),
                            "max":dynamic_weights.get("color",1),
                            "description":"Đánh giá mức độ hài hòa màu sắc.",
                            "formula":"OpenCV Color Analysis"
                        }
                        ],
                            

                            "bonus": [
                                {
                                    "reason": r,
                                    "point":0.5
                                }
                                for r in rule_success
                            ],

                            "penalty": [
                                {
                                    "reason": r,
                                    "point": 0.5
                                }
                                for r in rule_errors
                            ],

                            "template_rules": {
                                "user_text": danh_sach_cau,
                                "success": rule_success,
                                "error": rule_errors
                            },
                            "formula": {
                                "base": round(score_base,2),
                                "bonus": round(bonus_rules + cong_diem_tuyet_doi,2),
                                "penalty": round(penalt_rules + tru_diem_tuyet_doi,2),
                                "difficulty": round(muc_phat_do_kho,2),
                                "final": score
                            }
                        }
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
            "boxed_image": f"/static/results/{boxed_name}",
            "score_breakdown": score_breakdown
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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
                rules = settings.get("scenery_rules", [])
                print("===== SCENERY DEBUG =====")
                print("ART TYPE:", settings.get("art_type"))
                print("ALL KEYS:", settings.keys())
                print("SCENERY RULES:", rules)
                print("=========================")
        
        base_required = SCENERY_REQUIRED.copy()
        
        for noun in nouns_from_settings:
            noun_lower = noun.lower().strip()
            if noun_lower not in base_required and noun_lower not in ["tree", "sun"]:
                base_required.append(noun_lower)
        
        img_cv = cv2.imread(img_path)
        img_h, img_w, _ = img_cv.shape
        
        results = scenery_model(img_path, verbose=False)[0]



        boxes_dict = {}
        for box in results.boxes:

            cls_id = int(box.cls[0])
            obj = str(results.names[cls_id]).strip().lower()

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            if obj not in boxes_dict:
                boxes_dict[obj] = []

            boxes_dict[obj].append({
                "box": [x1, y1, x2, y2]
            })
        boxes_xyxy = results.boxes.xyxy.cpu().numpy().tolist()
        print(boxes_dict)

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

        detected = list(boxes_dict.keys())

        missing = [
            obj for obj in base_required
            if obj not in boxes_dict
        ]
        
        rule_errors = []
        rule_success = []

        boxes_dict_template = boxes_dict
        _, rule_details = evaluate_drawing(rules, boxes_dict_template)
        print("=" * 60)
        print("RULES =", rules)
        print("RULE DETAILS =", rule_details)
        print("=" * 60)
        for rule in rules:
            rule_str = rule.get("rule", "")
            detail = rule_details.get(rule_str)

            if detail is None:
                ok = False
                score = 0
            else:
                if isinstance(detail, dict):
                    score = detail.get("score", 0)
                else:
                    score = detail

                ok = score >= 50

            print(rule_str, score, ok)
               
            obj1_vi = rule.get('object1_vi', SCENERY_OBJECT_VI.get(rule.get('object1', ''), rule.get('object1', '')))
            obj2_vi = rule.get('object2_vi', SCENERY_OBJECT_VI.get(rule.get('object2', ''), rule.get('object2', '')))
            relation_vi = rule.get('relation_vi', RELATION_VI.get(rule.get('relation', ''), rule.get('relation', '')))
            if relation_vi == "có":
                chuoi_hien_thi = f"{relation_vi} {obj1_vi}  và {obj2_vi}".strip()
            else:    
                chuoi_hien_thi = f"{obj1_vi} {relation_vi}   {obj2_vi}".strip()
            if not chuoi_hien_thi:
                chuoi_hien_thi = rule_str
            reason = detail.get("reason", "") if isinstance(detail, dict) else ""
            if ok:
                rule_success.append(reason if reason else chuoi_hien_thi)
            else:
                rule_errors.append(reason if reason else f"Vi phạm: {chuoi_hien_thi}")

            if rule.get("type") == "size":
                text = rule["rule"].split()

                obj = SCENERY_OBJECT_VI.get(text[1], text[1])

                size_vi = {
                    "large": "to",
                    "small": "nhỏ",
                    "medium": "vừa"
                }.get(text[2], text[2])

                chuoi_hien_thi = f"{obj} {size_vi}"

            else:
                obj1_vi = rule.get(
                    "object1_vi",
                    SCENERY_OBJECT_VI.get(rule.get("object1", ""), rule.get("object1", ""))
                )

                obj2_vi = rule.get(
                    "object2_vi",
                    SCENERY_OBJECT_VI.get(rule.get("object2", ""), rule.get("object2", ""))
                )

                relation_vi = rule.get(
                    "relation_vi",
                    RELATION_VI.get(rule.get("relation", ""), rule.get("relation", ""))
                )

                if relation_vi == "có":
                    chuoi_hien_thi = f"{relation_vi} {obj1_vi} và {obj2_vi}"
                else:
                    chuoi_hien_thi = f"{obj1_vi} {relation_vi} {obj2_vi}"
        print("SUCCESS =", rule_success)
        print("ERROR =", rule_errors)
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
        nhan_xet_nghe_thuat_list = phan_tich_nghe_thuat_phong_canh(
            boxes_dict_template,
            img_w,
            img_h
        )        
        # SỬ DỤNG HÀM MÀU SẮC GỐC CỦA BẠN (TRÊN TOÀN BỘ ẢNH)
        nhan_xet_mau_sac_str = phan_tich_mau_sac(img_cv)
        print('nhan xet mau sech: ', nhan_xet_mau_sac_str)
        # TÍNH ĐIỂM
        user_text = settings.get("scenery_text", "")
        dynamic_weights = phan_tich_trong_so_tieu_chi(user_text)

        trong_so_phong_canh = {"house": 2.5, "tree": 2.0, "sun": 1.5}
        for noun in base_required:
            if noun not in trong_so_phong_canh: trong_so_phong_canh[noun] = 0.5
            
        diem_thanh_phan = sum([trong_so_phong_canh.get(obj, 0.25) for obj in detected]) 
        diem_toi_da = sum([trong_so_phong_canh.get(obj, 1.0) for obj in base_required])
        
        # Đảm bảo điểm max không chia cho 0
        diem_thanh_phan_chuan = (float(diem_thanh_phan) / float(diem_toi_da)) * float(dynamic_weights.get("objects", 3.0)) if diem_toi_da > 0 else 0

        so_loi_bo_cuc = sum(1 for l in loi_bo_cuc if "Lỗi" in l)
        # diem_bo_cuc = max(0, dynamic_weights.get("layout", 1.0) - (so_loi_bo_cuc * (dynamic_weights.get("layout", 2.0) / 3)))

        diem_bo_cuc = max(
            0,
            dynamic_weights["layout"] -
            so_loi_bo_cuc * 1
        )
        # diem_nghe_thuat = dynamic_weights.get("art_proportion", 1.0) * 0.5
        diem_nghe_thuat = 0
        for nx in nhan_xet_nghe_thuat_list:
            if "tốt" in nx.lower() or "đẹp" in nx.lower():
                diem_nghe_thuat += 0.5
            elif "lưu ý" in nx.lower() or "to hơn" in nx.lower():
                diem_nghe_thuat -= 0.3

        diem_nghe_thuat = max(
            0,
            min(dynamic_weights["art_proportion"], diem_nghe_thuat)
        )
        #
        for nx in nhan_xet_nghe_thuat_list:
            if "tốt" in nx or "nghệ thuật" in nx or "amazing" in nx:
                diem_nghe_thuat += (dynamic_weights.get("art_proportion", 1.0) * 0.25)
            elif "to hơn" in nx or "lưu ý" in nx.lower():
                diem_nghe_thuat -= (dynamic_weights.get("art_proportion", 1.0) * 0.25)
        diem_nghe_thuat = max(0, min(dynamic_weights.get("art_proportion", 1.0), diem_nghe_thuat))

        # diem_mau_sac = dynamic_weights.get("color", 1.0) * 0.6 
        diem_mau_sac = 0
     
        if "rực rỡ" in nhan_xet_mau_sac_str: 
            print("RỰC RỠ")
            diem_mau_sac += dynamic_weights["color"]*0.6

        elif "rất tốt" in nhan_xet_mau_sac_str:
            diem_mau_sac += dynamic_weights["color"]*0.8
            print("RẤT TỐT")

        elif "nhạt nhòa" in nhan_xet_mau_sac_str:
            diem_mau_sac += dynamic_weights["color"]*0.2
            print("NHẠT NHÒA")
        elif "hài hòa" in nhan_xet_mau_sac_str:
            diem_mau_sac += dynamic_weights["color"]*0.8
            print("HÀI HÒA")
        elif "trong trẻo" in nhan_xet_mau_sac_str:
            diem_mau_sac += dynamic_weights["color"]*0.8
        bonus_rules = min(len(rule_success) * 0.5, 1.5)
        penalt_rules = len(rule_errors) * 0.5

        score_base = diem_thanh_phan_chuan + diem_bo_cuc + diem_nghe_thuat + diem_mau_sac + bonus_rules - penalt_rules
        # Giới hạn điểm nếu thiếu nhiều vật
        if len(missing) >= 5:
            score_base = min(score_base, 6)

        elif len(missing) >= 3:
            score_base = min(score_base, 8)
        # CƠ CHẾ ĐIỂM ĐỘNG VÀ ĐIỂM TUYỆT ĐỐI BẰNG REGEX
        tru_diem_tuyet_doi = 0.0
        cong_diem_tuyet_doi = 0.0
        so_vat_thieu_tu_nhien = len(missing)
        danh_sach_cau = []
        if user_text:
            text_lower = user_text.lower()
            tat_ca_vat_the = detected + missing  
            vat_bi_phat = []
            
            danh_sach_cau = [c.strip() for c in text_lower.split('.') if c.strip()]
            
            for cau in danh_sach_cau:
                # 1. QUÉT LỆNH THƯỞNG
                for match in re.finditer(r'(?:cộng|thưởng|thêm)\s*(\d+(?:\.\d+)?)\s*điểm', cau):
                    diem_cong = float(match.group(1))
                    da_xu_ly_luat = False
                    
                    for rs in rule_success:
                        if rs.lower() in cau:
                            cong_diem_tuyet_doi += diem_cong
                            loi_khuyen.append(f"🌟 Lời khen: Cộng {diem_cong} điểm vì vẽ đúng luật '{rs}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue
                    
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
                    
                    for re_err in rule_errors:
                        if re_err.lower() in cau:
                            tru_diem_tuyet_doi += diem_tru
                            loi_khuyen.append(f"⚠️ Cảnh báo: Trừ thẳng {diem_tru} điểm do vi phạm luật: '{re_err}'!")
                            da_xu_ly_luat = True
                            break
                    if da_xu_ly_luat: continue

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

        muc_phat_do_kho = (so_loi_bo_cuc * 0.5 + so_vat_thieu_tu_nhien * 0.8) * (penalty - 1)

        score_tinh_toan = score_base - muc_phat_do_kho - tru_diem_tuyet_doi + cong_diem_tuyet_doi
        score = max(0, min(10, round(score_tinh_toan, 1)))
        score_breakdown = {
            "details":[
            {
                "title":"Chi tiết đối tượng",
                "score":round(diem_thanh_phan_chuan,2),
                "max":dynamic_weights.get("objects",5),
                "description":"Đánh giá số lượng bộ phận AI phát hiện được.",
                "formula": f"{len(detected)}/{len(base_required)} đối tượng",
                "detected":detected,
                "missing":missing
            },
            {
                "title":"Bố cục",
                "score":round(diem_bo_cuc,2),
                "max":dynamic_weights.get("layout",2),
                "description":"Đánh giá bố cục của tranh phong cảnh.",
                "formula":"Kiểm tra khoảng cách và vị trí bằng luật hình học",
                "result":loi_bo_cuc
            },
           {
                "title":"Nghệ thuật",
                "score": round(diem_nghe_thuat,2),
                "max": dynamic_weights.get("art_proportion",2),
                "description":"Đánh giá bố cục nghệ thuật của tranh phong cảnh.",
                "formula":"Rule-based",
                "result":
                    nhan_xet_nghe_thuat_list
            },
            {
                "title":"Màu sắc",
                "score":round(diem_mau_sac,2),
                "max":dynamic_weights.get("color",1),
                "description":"Đánh giá mức độ hài hòa màu sắc.",
                "formula":"OpenCV Color Analysis"
            }
            ],

            "bonus": [
                {
                    "reason": r,
                    "point": 0.5
                }
                for r in rule_success
            ],

            "penalty": [
                {
                    "reason": r,
                    "point": 0.5
                }
                for r in rule_errors
            ],
            "template_rules": {
                "user_text": danh_sach_cau,
                "success": rule_success,
                "error": rule_errors
            },
            "formula": {
                "base": round(score_base,2),
                "bonus": round(bonus_rules + cong_diem_tuyet_doi,2),
                "penalty": round(penalt_rules + tru_diem_tuyet_doi,2),
                "difficulty": round(muc_phat_do_kho,2),
                "final": score
            }
        }
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
            "boxed_image": f"/static/results/{boxed_name}",
            "score_breakdown": score_breakdown,
        })
        
    except Exception as e:
        print("Lỗi ở đây", e)
        import traceback
        traceback.print_exc()
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