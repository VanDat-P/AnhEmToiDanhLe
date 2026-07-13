import cv2
from sentence_transformers import SentenceTransformer, util
from deep_translator import GoogleTranslator
from underthesea import pos_tag
import re

# ==========================================
# 1. KHỞI TẠO CÁC CÔNG CỤ NLP
# ==========================================
translator = GoogleTranslator(source='vi', target='en')
embed_model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")

# ==========================================
# 2. KHAI BÁO TỪ ĐIỂN VÀ MAPPING (ĐẶT LÊN ĐẦU ĐỂ KHÔNG LỖI)
# ==========================================
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
    "bên trái": "C", "phía trái": "C", "trái": "C",
    "bên phải": "C", "phía phải": "C", "phải": "C",
    "phía trên": "C", "ở trên": "C", "bên trên": "C", "trên": "C",
    "phía dưới": "C", "ở dưới": "C", "bên dưới": "C", "dưới": "C",
    "cao hơn": "C", "to hơn": "C", "lớn hơn": "C",
    "thấp hơn": "C", "nhỏ hơn": "C", "bé hơn": "C",
    "và": "C", "hoặc": "C", "với": "C",
    "ông mặt trời": "N", "mặt trời": "N", "vầng thái dương": "N",
    "ngôi nhà": "N", "căn nhà": "N", "mái nhà": "N",
    "cái cây": "N", "bóng cây": "N", "ngọn cây": "N",
    "đám mây": "N", "ngọn núi": "N", "dãy núi": "N",
    "dòng sông": "N", "con sông": "N", "con chim": "N", "đàn chim": "N",
    "bông hoa": "N", "khóm hoa": "N",
    "khuôn mặt": "N", "gương mặt": "N", "lông mày": "N", "chân mày": "N",
    "mái tóc": "N", "đôi mắt": "N", "cái mũi": "N", "cái miệng": "N",
    "cái tai": "N", "đôi tai": "N",
    "phải có": "V", "bắt buộc có": "V", "yêu cầu có": "V", "bao gồm": "V"
}

templates = [
    ["V", "N", "C", "N"], 
    ["N", "C", "N"],
    ["V", "Ns"]
]

# ==========================================
# 3. CÁC HÀM XỬ LÝ (NẰM DƯỚI CÙNG ĐỂ ĐỌC ĐƯỢC BIẾN)
# ==========================================

def custom_pos_tag(text):
    if not text: return []
    temp_text = text
    placeholder_map = {}
    counter = 0
    sorted_keys = sorted(CUSTOM_POS_MAPPING.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        pattern = rf'(?<!\S){key}(?!\S)'
        while re.search(pattern, temp_text):
            placeholder = f"TOKENX{counter}X"
            placeholder_map[placeholder] = {"word": key, "tag": CUSTOM_POS_MAPPING[key]}
            temp_text = re.sub(pattern, placeholder, temp_text, count=1)
            counter += 1
            
    raw_tags = pos_tag(temp_text)
    final_tags = []
    for word, tag in raw_tags:
        if word in placeholder_map:
            final_tags.append([placeholder_map[word]["word"], placeholder_map[word]["tag"]])
        else:
            final_tags.append([word, tag])
    return final_tags

def filter_valid_nouns_en(nouns_list, art_type="portrait"):
    valid_nouns = []
    allowed_nouns = VALID_PORTRAIT_NOUNS if art_type == "portrait" else VALID_SCENERY_NOUNS
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
    weights = {"objects": 5.0, "layout": 2.0, "art_proportion": 2.0, "color": 1.0}
    if not user_text or not user_text.strip(): return weights
        
    text = user_text.lower()
    if any(kw in text for kw in ["phải có", "bắt buộc", "thiếu", "không có", "trừ điểm"]):
        weights["objects"] += 4.0; weights["layout"] -= 1.0; weights["art_proportion"] -= 1.0; weights["color"] -= 0.5
    if any(kw in text for kw in ["màu", "màu sắc", "tô màu", "rực rỡ", "tươi sáng", "đậm"]):
        weights["color"] += 3.0; weights["objects"] -= 1.0 
    if any(kw in text for kw in ["bố cục", "căn giữa", "vị trí", "bên trái", "bên phải", "ở trên", "ở dưới", "to hơn", "nhỏ hơn"]):
        weights["layout"] += 2.0; weights["objects"] -= 1.0
    if any(kw in text for kw in ["tỷ lệ", "xa gần", "nghệ thuật", "hài hòa", "cân đối", "sáng tạo"]):
        weights["art_proportion"] += 2.0; weights["objects"] -= 1.0
        
    for k in weights: weights[k] = max(0.1, weights[k])
    total = sum(weights.values())
    for key in weights: weights[key] = round((weights[key] / total) * 10.0, 2)
    return weights

def parse_rulesv2(tokens, sentence):
    try:
        if not tokens or not sentence or len(tokens) == 0: return None
        
        valid_tokens = []
        for token in tokens:
            if isinstance(token, (list, tuple)) and len(token) >= 2:
                word, tag = str(token[0]).strip(), str(token[1]).strip()
                if word and tag: valid_tokens.append([word, tag])
        
        if not valid_tokens: return None
        
        for template in templates:
            rule_vi, rule_en = "", ""
            current_idx, is_match = 0, True
            
            for word_type in template:
                if word_type == "Ns":
                    found_nouns = 0
                    while current_idx < len(valid_tokens):
                        word = str(valid_tokens[current_idx][0]).lower()
                        pos = valid_tokens[current_idx][1]
                        
                        if pos.startswith('N'):
                            found_nouns += 1
                            rule_vi += f" {word}"
                            en_word = MAPPING.get(word, translator.translate(word).lower())
                            rule_en += f" {en_word}"
                        elif word in [",", "và", "hoặc"] or pos == "C":
                            rule_vi += f" {word}"
                            rule_en += f" {word}"
                        elif pos.startswith('V'):
                            break
                        current_idx += 1
                    if found_nouns == 0:
                        is_match = False
                        break
                else:
                    found = False
                    while current_idx < len(valid_tokens):
                        word = str(valid_tokens[current_idx][0]).lower()
                        pos = valid_tokens[current_idx][1]
                        if pos.startswith(word_type[0]):
                            found = True
                            break
                        current_idx += 1
                    
                    if not found or current_idx >= len(valid_tokens):
                        is_match = False
                        break
                    
                    word = str(valid_tokens[current_idx][0]).lower()
                    rule_vi += f" {word}"
                    en_word = MAPPING.get(word, translator.translate(word).lower())
                    rule_en += f" {en_word}"
                    current_idx += 1
            
            if is_match and rule_vi.strip():
                return {
                    "rule": rule_vi.strip(), "rule_en": rule_en.strip(),
                    "template": template, "raw_text": str(sentence), "tokens": valid_tokens
                }
        return None
    except Exception as e:
        print(f"❌ Lỗi parse_rulesv2: {e}")
        return None

def parse_rules(user_text, art_type="scenery"):
    rules = []
    if not user_text or not user_text.strip(): return rules
    
    clauses = [c.strip() for c in user_text.lower().split('.') if c.strip()]
    obj_dict = PORTRAIT_OBJECT_MAPPING if art_type == "portrait" else SCENERY_OBJECT_MAPPING
    vi_dict = PORTRAIT_OBJECT_VI if art_type == "portrait" else SCENERY_OBJECT_VI
    
    for clause in clauses:
        if len(clause) < 3: continue
        found_objects, found_relations = [], []
        
        clause_temp = clause
        for vi_word, en_key in obj_dict.items():
            for match in re.finditer(rf"(?:\b|\s|^){vi_word}(?:\b|\s|$)", clause_temp):
                found_objects.append({"vi": vi_word, "en": en_key, "pos": match.start()})
                clause_temp = clause_temp[:match.start()] + " " * len(match.group()) + clause_temp[match.end():]
                
        clause_temp_rel = clause
        for vi_word, en_key in RELATION_MAPPING.items():
            for match in re.finditer(rf"(?:\b|\s|^){vi_word}(?:\b|\s|$)", clause_temp_rel):
                found_relations.append({"vi": vi_word, "en": en_key, "pos": match.start()})
                clause_temp_rel = clause_temp_rel[:match.start()] + " " * len(match.group()) + clause_temp_rel[match.end():]

        found_objects = sorted(found_objects, key=lambda x: x['pos'])
        found_relations = sorted(found_relations, key=lambda x: x['pos'])

        if len(found_objects) >= 2 and len(found_relations) >= 1:
            obj_A, obj_B, rel = found_objects[0], found_objects[1], found_relations[0]
            if rel['pos'] < obj_A['pos']: obj_A, obj_B = obj_B, obj_A
                
            en_rel = rel['en']
            rule_data = {
                "weight": 1.0,
                "object1": obj_A['en'], "object2": obj_B['en'], "relation": rel['en'],
                "object1_vi": vi_dict.get(obj_A['en'], obj_A['vi']), 
                "object2_vi": vi_dict.get(obj_B['en'], obj_B['vi']), 
                "relation_vi": rel['vi']
            }
            
            if en_rel in ["higher_than", "lower_than"]:
                rule_data["type"] = "size_comp"
                op = ">" if en_rel == "higher_than" else "<"
                rule_data["rule"] = f"size_compare {obj_A['en']} {op} {obj_B['en']}"
            else:
                rule_data["type"] = "pos_rel"
                rule_data["rule"] = f"position_rel {obj_A['en']} {en_rel} {obj_B['en']}"
                
            rules.append(rule_data)
    return rules