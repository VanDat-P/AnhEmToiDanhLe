import cv2
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from underthesea import pos_tag
import re
from templates import *
from models import clf_model, model

translator = GoogleTranslator(source='vi', target='en')
embed_model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")

from model import clf_model
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
    "ông mặt trời": "sun", "mặt trời": "sun", "vầng thái dương": "sun",
    "ngôi nhà": "house", "căn nhà": "house", "mái nhà": "house", "nhà": "house",
    "cái cây": "tree", "bóng cây": "tree", "ngọn cây": "tree", "cây": "tree",
    "đám mây": "cloud", "mây": "cloud",
    "ngọn núi": "mountain", "dãy núi": "mountain", "núi": "mountain",
    "dòng sông": "river", "con sông": "river", "sông": "river",
    "con chim": "bird", "đàn chim": "bird", "chim": "bird",
    "bông hoa": "flower", "khóm hoa": "flower", "hoa": "flower"
}



PORTRAIT_OBJECT_MAPPING = {
    "khuôn mặt": "face", "gương mặt": "face", "mặt": "face",
    "lông mày": "eyebrow", "chân mày": "eyebrow", "mày": "eyebrow",
    "mái tóc": "hair", "tóc": "hair",
    "đôi mắt": "eye", "mắt": "eye",
    "cái mũi": "nose", "mũi": "nose",
    "cái miệng": "mouth", "miệng": "mouth",
    "cái tai": "ear", "đôi tai": "ear", "tai": "ear"
}

PORTRAIT_OBJECT_VI = {
    "eye": "mắt", "nose": "mũi", "mouth": "miệng",
    "ear": "tai", "eyebrow": "lông mày", "hair": "tóc", "face": "khuôn mặt"
}

SCENERY_OBJECT_VI = {
    "tree": "cây", "house": "nhà", "sun": "mặt trời", 
    "moon": "mặt trăng", "cloud": "mây", "mountain": "núi", 
    "river": "sông", "bird": "chim", "flower": "hoa"
}

RELATION_MAPPING = {
    "phía trên": "above", "ở trên": "above", "bên trên": "above", "trên": "above",
    "phía dưới": "below", "ở dưới": "below", "bên dưới": "below", "dưới": "below",
    "bên trái": "left_of", "phía trái": "left_of", "trái": "left_of",
    "bên phải": "right_of", "phía phải": "right_of", "phải": "right_of",
    "cao hơn": "higher_than", "to hơn": "higher_than", "lớn hơn": "higher_than",
    "thấp hơn": "lower_than", "nhỏ hơn": "lower_than", "bé hơn": "lower_than",
    "có": "have","và": "and"
}

RELATION_VI = {
    "higher_than": "cao hơn", "lower_than": "thấp hơn",
    "left_of": "bên trái", "right_of": "bên phải",
    "above": "ở trên", "below": "ở dưới"
}
MAPPING = SCENERY_OBJECT_MAPPING | PORTRAIT_OBJECT_MAPPING | RELATION_MAPPING

CUSTOM_POS_MAPPING = {
    # === Từ chỉ Quan Hệ / Vị Trí (Gắn tag "C" - Condition/Comparator) ===
    "bên trái": "C", "phía trái": "C", "trái": "C",
    "bên phải": "C", "phía phải": "C", "phải": "C",
    "phía trên": "C", "ở trên": "C", "bên trên": "C", "trên": "C",
    "phía dưới": "C", "ở dưới": "C", "bên dưới": "C", "dưới": "C",
    "cao hơn": "C", "to hơn": "C", "lớn hơn": "C",
    "thấp hơn": "C", "nhỏ hơn": "C", "bé hơn": "C",
    "và": "C", "hoặc": "C", "với": "C",

    # === Danh Từ Ghép (Gắn tag "N" - Noun) ===
    "ông mặt trời": "N", "mặt trời": "N", "vầng thái dương": "N",
    "ngôi nhà": "N", "căn nhà": "N", "mái nhà": "N",
    "cái cây": "N", "bóng cây": "N", "ngọn cây": "N",
    "đám mây": "N", "ngọn núi": "N", "dãy núi": "N",
    "dòng sông": "N", "con sông": "N", "con chim": "N", "đàn chim": "N",
    "bông hoa": "N", "khóm hoa": "N",
    "khuôn mặt": "N", "gương mặt": "N", "lông mày": "N", "chân mày": "N",
    "mái tóc": "N", "đôi mắt": "N", "cái mũi": "N", "cái miệng": "N",
    "cái tai": "N", "đôi tai": "N",

    # === Động Từ (Gắn tag "V" - Verb) ===
    "phải có": "V", "bắt buộc có": "V", "yêu cầu có": "V", "bao gồm": "V"
}



def custom_pos_tag(text):
    if not text: 
        return []
        
    temp_text = text
    placeholder_map = {}
    counter = 0
    
    # Sắp xếp từ khoá theo độ dài giảm dần (để ưu tiên gom cụm "ông mặt trời" trước chữ "mặt trời")
    sorted_keys = sorted(CUSTOM_POS_MAPPING.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        # Regex an toàn cho Tiếng Việt: Bắt từ khoá có khoảng trắng/đầu câu/cuối câu bao quanh
        pattern = rf'(?<!\S){key}(?!\S)'
        
        while re.search(pattern, temp_text):
            # Mã hoá bằng một chữ không có nghĩa
            placeholder = f"TOKENX{counter}X"
            placeholder_map[placeholder] = {"word": key, "tag": CUSTOM_POS_MAPPING[key]}
            
            # Thay thế từ khoá bằng placeholder
            temp_text = re.sub(pattern, placeholder, temp_text, count=1)
            counter += 1
            
    # Gọi hàm gốc của underthesea trên câu đã mã hoá
    raw_tags = pos_tag(temp_text)
    
    # Giải mã và build mảng kết quả với format [word, tag]
    final_tags = []
    for word, tag in raw_tags:
        if word in placeholder_map:
            # Ép về list [từ_gốc, tag_tự_chế] như yêu cầu
            final_tags.append([placeholder_map[word]["word"], placeholder_map[word]["tag"]])
        else:
            # Các từ thông thường ép về list
            final_tags.append([word, tag])
            
    return final_tags

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

def phan_tich_trong_so_tieu_chi(user_text):
    # Thang điểm mặc định
    weights = {"objects": 5.0, "layout": 2.0, "art_proportion": 2.0, "color": 1.0}
    if not user_text or not user_text.strip():
        return weights
        
    text = user_text.lower()
    
    # Chỉ bắt các từ khóa mang tính NGHỆ THUẬT & PHONG CÁCH
    if any(kw in text for kw in ["màu", "sắc", "rực rỡ", "tươi sáng", "đậm"]):
        weights["color"] += 3.0
        weights["objects"] -= 1.0 
        
    if any(kw in text for kw in ["bố cục", "căn giữa", "vị trí", "trái", "phải", "trên", "dưới"]):
        weights["layout"] += 2.0
        weights["objects"] -= 1.0
        
    if any(kw in text for kw in ["tỷ lệ", "xa gần", "nghệ thuật", "hài hòa", "cân đối"]):
        weights["art_proportion"] += 2.0
        weights["objects"] -= 1.0
        
    # Chuẩn hóa về thang 10
    total = sum(weights.values())
    for key in weights:
        weights[key] = (weights[key] / total) * 10.0
        
    return weights
        
    text = user_text.lower()
    
    # 0. MỚI THÊM: Giáo viên cực kỳ gắt gao về việc PHẢI CÓ vật thể
    if any(kw in text for kw in ["phải có", "bắt buộc", "thiếu", "không có", "trừ điểm"]):
        weights["objects"] += 4.0   # Tăng vọt điểm vật thể lên
        weights["layout"] -= 1.0    # Cắt bớt điểm các phần khác
        weights["art_proportion"] -= 1.0
        weights["color"] -= 0.5
    
    # 1. Giáo viên khó tính về MÀU SẮC
    if any(kw in text for kw in ["màu", "màu sắc", "tô màu", "rực rỡ", "tươi sáng", "đậm"]):
        weights["color"] += 3.0
        weights["objects"] -= 1.0 
        
    # 2. Giáo viên khó tính về BỐ CỤC / VỊ TRÍ
    if any(kw in text for kw in ["bố cục", "căn giữa", "vị trí", "bên trái", "bên phải", "ở trên", "ở dưới", "to hơn", "nhỏ hơn"]):
        weights["layout"] += 2.0
        weights["objects"] -= 1.0
        
    # 3. Giáo viên khó tính về NGHỆ THUẬT / QUY LUẬT
    if any(kw in text for kw in ["tỷ lệ", "xa gần", "nghệ thuật", "hài hòa", "cân đối", "sáng tạo"]):
        weights["art_proportion"] += 2.0
        weights["objects"] -= 1.0
        
    # CHUẨN HÓA: Ép tổng điểm luôn luôn bằng đúng 10.0
    total = sum(weights.values())
    for key in weights:
        weights[key] = (weights[key] / total) * 10.0
        
    return weights


templates = [
    ["V", "N", "C", "N"], 
    ["V", "Ns"]
]
def parse_rulesv2(tokens, sentence):
    try:
        for template in templates:
            rule = ""
            rule_en = ""
            current_idx = 0
            is_match = True 
            
            for word_type in template:
                # ==========================================
                # Xử lý gom nhóm Danh Từ (Ns): Vét nhiều Nouns
                # ==========================================
                if word_type == "Ns":
                    found_nouns = 0
                    while current_idx < len(tokens):
                        word = str(tokens[current_idx][0]).lower()
                        pos = tokens[current_idx][1]
                        
                        if pos.startswith('N'):
                            found_nouns += 1
                            rule += f" {word}"
                            rule_en += f" {MAPPING.get(word, translator.translate(word).lower())}"
                            
                        elif word in [",", "và", "hoặc"] or pos == "C":
                            pass # Gặp dấu phẩy hoặc chữ "và" thì lướt qua đi tìm N tiếp
                            
                        elif pos.startswith('V'):
                            break # Gặp động từ mới thì ngắt cụm
                            
                        current_idx += 1
                        
                    if found_nouns == 0:
                        is_match = False
                        break

                # ==========================================
                # Xử lý V, N, C (Bắt chính xác 1 từ)
                # ==========================================
                else:
                    while current_idx < len(tokens):
                        word = str(tokens[current_idx][0]).lower() 
                        pos = tokens[current_idx][1]
                        if pos.startswith(word_type[0]):
                            break
                        current_idx += 1
                        
                    if current_idx >= len(tokens): 
                        is_match = False
                        break 
                    
                    word = str(tokens[current_idx][0]).lower()
                    rule += f" {word}"
                    rule_en += f" {MAPPING.get(word, translator.translate(word).lower())}"
                    current_idx += 1
                    
            # Nếu đã khớp khuôn mẫu -> Trả về Dictionary luôn, không cần AI chấm điểm
            if is_match and rule.strip():
                print(f"✅ Match rule: {rule.strip()} | {rule_en.strip()}")
                return {
                    "rule": rule.strip(),
                    "rule_en": rule_en.strip(),
                    "template": template,
                    "raw_text": str(sentence)
                }
                
        return None # Không khớp template nào
        
    except Exception as e:
        print(f"❌ Lỗi khi parse rule v2: {e}")
        return None

def check_rulev2(rule, boxes_dict):
    try:
        template_idx = templates.index(rule["template"])
        match template_idx:
            case 0:
                return template_1(rule, boxes_dict)  # ["V", "N", "C", "N"]
            # case 1:
            #     return template_ns(rule, boxes_dict) # ["V", "Ns"]
            case 2:
                return template_0(rule, boxes_dict)  # ["V", "N"]
                
    except Exception as e:
        print(f"Có lỗi xảy ra khi check rules. Lỗi: {e}")
        return 0.0

def parse_rules(user_text, art_type="scenery"):
    rules = []
    if not user_text or not user_text.strip():
        return rules
    
    # SỬA: Tách theo dấu chấm (.)
    clauses = [c.strip() for c in user_text.lower().split('.') if c.strip()]
    
    obj_dict = PORTRAIT_OBJECT_MAPPING if art_type == "portrait" else SCENERY_OBJECT_MAPPING
    vi_dict = PORTRAIT_OBJECT_VI if art_type == "portrait" else SCENERY_OBJECT_VI
    
    for clause in clauses:
        if not clause or len(clause.strip()) < 3:
            continue
            
        found_objects = []
        found_relations = []
        
        clause_temp = clause
        for vi_word, en_key in obj_dict.items():
            pattern = rf"(?:\b|\s|^){vi_word}(?:\b|\s|$)"
            for match in re.finditer(pattern, clause_temp):
                found_objects.append({"vi": vi_word, "en": en_key, "pos": match.start()})
                clause_temp = clause_temp[:match.start()] + " " * len(match.group()) + clause_temp[match.end():]
                
        clause_temp_rel = clause
        for vi_word, en_key in RELATION_MAPPING.items():
            pattern = rf"(?:\b|\s|^){vi_word}(?:\b|\s|$)"
            for match in re.finditer(pattern, clause_temp_rel):
                found_relations.append({"vi": vi_word, "en": en_key, "pos": match.start()})
                clause_temp_rel = clause_temp_rel[:match.start()] + " " * len(match.group()) + clause_temp_rel[match.end():]

        found_objects = sorted(found_objects, key=lambda x: x['pos'])
        found_relations = sorted(found_relations, key=lambda x: x['pos'])

        if len(found_objects) >= 2 and len(found_relations) >= 1:
            obj_A, obj_B, rel = found_objects[0], found_objects[1], found_relations[0]
            
            if obj_A['pos'] < rel['pos'] < obj_B['pos']:
                rules.append({
                    "object1": obj_A['en'], "relation": rel['en'], "object2": obj_B['en'],
                    "object1_vi": vi_dict.get(obj_A['en'], obj_A['vi']), 
                    "object2_vi": vi_dict.get(obj_B['en'], obj_B['vi']), "relation_vi": rel['vi']
                })
            elif rel['pos'] < obj_A['pos'] < obj_B['pos']:
                rules.append({
                    "object1": obj_B['en'], "relation": rel['en'], "object2": obj_A['en'],
                    "object1_vi": vi_dict.get(obj_B['en'], obj_B['vi']), 
                    "object2_vi": vi_dict.get(obj_A['en'], obj_A['vi']), "relation_vi": rel['vi']
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