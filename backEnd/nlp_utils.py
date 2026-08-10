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
    "eyes", "eyebrows", "ears", "hair", "head"
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
    "bông hoa": "flower", "khóm hoa": "flower", "hoa": "flower","tranh":"picture","bức tranh":"picture",
    "người":"person"
}

PORTRAIT_OBJECT_MAPPING = {
    "khuôn mặt": "face", "gương mặt": "face", "mặt": "face",
    "lông mày": "eyebrow", "chân mày": "eyebrow", "mày": "eyebrow",
    "mái tóc": "hair", "tóc": "hair",
    "đôi mắt": "eye", "mắt": "eye",
    "cái mũi": "nose", "mũi": "nose",
    "cái miệng": "mouth", "miệng": "mouth",
    "cái tai": "ear", "đôi tai": "ear", "tai": "ear","tranh":"picture","bức tranh":"picture"
}

PORTRAIT_OBJECT_VI = {
    "eye": "mắt", "nose": "mũi", "mouth": "miệng",
    "ear": "tai", "eyebrow": "lông mày", "hair": "tóc", "face": "khuôn mặt"
}

SCENERY_OBJECT_VI = {
    "tree": "cây", "house": "nhà", "sun": "mặt trời", 
    "moon": "mặt trăng", "cloud": "mây", "mountain": "núi", 
    "river": "sông", "bird": "chim", "flower": "hoa",
    "person":"người","people": "người"
    
}

# RELATION_MAPPING = {
#     "phía trên": "above", "ở trên": "above", "bên trên": "above", "trên": "above",
#     "phía dưới": "below", "ở dưới": "below", "bên dưới": "below", "dưới": "below",
#     "bên trái": "left_of", "phía trái": "left_of", "trái": "left_of",
#     "bên phải": "right_of", "phía phải": "right_of", "phải": "right_of",
#     "cao hơn": "higher_than", "to hơn": "higher_than", "lớn hơn": "higher_than",
#     "thấp hơn": "lower_than", "nhỏ hơn": "lower_than", "bé hơn": "lower_than",
#     "có": "have","và": "and",
#     "to": "large",
#     "lớn": "large",
#     "nhỏ": "small",
#     "bé": "small"
# }
# ===============================
# QUAN HỆ VỊ TRÍ
# ===============================
POSITION_MAPPING = {
    "phía trên": "above",
    "ở trên": "above",
    "bên trên": "above",
    "trên": "above",

    "phía dưới": "below",
    "ở dưới": "below",
    "bên dưới": "below",
    "dưới": "below",

    "bên trái": "left_of",
    "phía trái": "left_of",
    "trái": "left_of",

    "bên phải": "right_of",
    "phía phải": "right_of",
    "phải": "right_of"
}


# ===============================
# QUAN HỆ SO SÁNH KÍCH THƯỚC
# ===============================
SIZE_MAPPING = {
    "cao hơn": "higher_than",
    "to hơn": "higher_than",
    "lớn hơn": "higher_than",

    "thấp hơn": "lower_than",
    "nhỏ hơn": "lower_than",
    "bé hơn": "lower_than"
}


# ===============================
# KÍCH THƯỚC TUYỆT ĐỐI
# ===============================
SIZE_VALUE_MAPPING = {
    "to": "large",
    "lớn": "large",

    "nhỏ": "small",
    "bé": "small",
    "vừa": "A",
    "nhiều hơn": "more_than",
    "ít hơn": "less_than",
    "vừa": "medium" 
}


# ===============================
# LOGIC
# ===============================
OTHER_MAPPING = {
    "có": "have",
    "và": "and"
}

RELATION_VI = {
    "higher_than": "cao hơn", "lower_than": "thấp hơn",
    "left_of": "bên trái", "right_of": "bên phải",
    "above": "ở trên", "below": "ở dưới"
}
QUANTITY_MAPPING = {
    "đúng": "==",
    "ít nhất": ">=",
    "không quá": "<="

}
LOGIC_MAPPING = {
    "và":"AND",
    "hoặc":"OR"
}
RELATION_MAPPING = (
    POSITION_MAPPING |
    SIZE_MAPPING |
    SIZE_VALUE_MAPPING |
    OTHER_MAPPING |
    LOGIC_MAPPING
)
#
MAPPING = (
    SCENERY_OBJECT_MAPPING |
    PORTRAIT_OBJECT_MAPPING |
    POSITION_MAPPING |
    SIZE_MAPPING |
    SIZE_VALUE_MAPPING |
    OTHER_MAPPING |
    QUANTITY_MAPPING |
    LOGIC_MAPPING
)

# CUSTOM_POS_MAPPING = {
#     "nhiều hơn": "COMPARE",
#     "ít hơn": "COMPARE",
#     "bên trái": "C", "phía trái": "C", "trái": "C",
#     "bên phải": "C", "phía phải": "C", "phải": "C",
#     "phía trên": "REL", "ở trên": "REL", "bên trên": "REL", "trên": "REL",
#     "phía dưới": "C", "ở dưới": "C", "bên dưới": "C", "dưới": "C",
#     "cao hơn": "C", "to hơn": "C", "lớn hơn": "C",
#     "thấp hơn": "C", "nhỏ hơn": "C", "bé hơn": "C",
#     "và": "C", "hoặc": "C", "với": "C",
#     "ông mặt trời": "N", "mặt trời": "N", "vầng thái dương": "N",
#     "ngôi nhà": "N", "căn nhà": "N", "mái nhà": "N",
#     "cái cây": "N", "bóng cây": "N", "ngọn cây": "N",
#     "đám mây": "N", "ngọn núi": "N", "dãy núi": "N","bức tranh":"N","tranh":"N",
#     "cây":"N",
#     "nhà":"N",
#     "mặt trời":"N",
#     "mây":"N",
#     "núi":"N",
#     "hoa":"N",
#     "dòng sông": "N", "con sông": "N", "con chim": "N", "đàn chim": "N",
#     "bông hoa": "N", "khóm hoa": "N",
#     "khuôn mặt": "N", "gương mặt": "N", "lông mày": "N", "chân mày": "N",
#     "mái tóc": "N", "đôi mắt": "N", "cái mũi": "N", "cái miệng": "N",
#     "cái tai": "N", "đôi tai": "N",
#     "phải có": "V", "bắt buộc có": "V", "yêu cầu có": "V", "bao gồm": "V",
#     "đúng": "A",
#     "không": "R",
#     "quá": "R",
#     "ít nhất": "X",
#     "to": "A",
#     "lớn": "A",
#     "nhỏ": "A",
#     "bé": "A",
#     "nếu": "L",
#     "thì": "L",
#     "vừa": "A",
#     # logic
#     "và": "C",
#     "hoặc": "C",

#     # vị trí
#     "trái": "REL",
#     "bên trái": "REL",
#     "phải": "REL",
#     "bên phải": "REL",
#     "trên": "REL",
#     "dưới": "REL",

#     # so sánh
#     "cao hơn": "COMPARE",
#     "thấp hơn": "COMPARE",
#     "to hơn": "COMPARE",
#     "lớn hơn": "COMPARE",
#     "nhỏ hơn": "COMPARE",
#     "bé hơn": "COMPARE",
# }
CUSTOM_POS_MAPPING = {
    # ==========================================================
    # ĐỘNG TỪ (Verb)
    # ==========================================================
    "phải có": "V",
    "bắt buộc có": "V",
    "yêu cầu có": "V",
    "bao gồm": "V",

    # ==========================================================
    # DANH TỪ (Noun)
    # ==========================================================

    # Cảnh vật
    "bức tranh": "N",
    "tranh": "N",

    "ông mặt trời": "N",
    "mặt trời": "N",
    "vầng thái dương": "N",

    "ngôi nhà": "N",
    "căn nhà": "N",
    "mái nhà": "N",
    "nhà": "N",

    "cái cây": "N",
    "bóng cây": "N",
    "ngọn cây": "N",
    "cây": "N",

    "đám mây": "N",
    "mây": "N",

    "ngọn núi": "N",
    "dãy núi": "N",
    "núi": "N",

    "bông hoa": "N",
    "khóm hoa": "N",
    "hoa": "N",

    "dòng sông": "N",
    "con sông": "N",

    "con chim": "N",
    "đàn chim": "N",

    # Chân dung
    "khuôn mặt": "N",
    "gương mặt": "N",

    "lông mày": "N",
    "chân mày": "N",

    "mái tóc": "N",

    "đôi mắt": "N",

    "cái mũi": "N",

    "cái miệng": "N",

    "cái tai": "N",
    "đôi tai": "N",

    # ==========================================================
    # TÍNH TỪ (Adjective)
    # ==========================================================
    "đúng": "A",
    "to": "A",
    "lớn": "A",
    "nhỏ": "A",
    "bé": "A",
    "vừa": "A",

    # ==========================================================
    # TRẠNG TỪ (Adverb)
    # ==========================================================
    "không": "R",
    "quá": "R",

    # ==========================================================
    # TỪ ĐỊNH LƯỢNG
    # ==========================================================
    "ít nhất": "X",

    # ==========================================================
    # TỪ ĐIỀU KIỆN (Logic)
    # ==========================================================
    "nếu": "L",
    "thì": "L",
    "vừa": "A",
    "đủ": "A",
    "và": "C",
    "hoặc": "C",
    "với": "C",

    # ==========================================================
    # QUAN HỆ VỊ TRÍ
    # ==========================================================
    "trái": "REL",
    "bên trái": "REL",
    "phía trái": "C",

    "phải": "REL",
    "bên phải": "REL",
    "phía phải": "C",

    "trên": "REL",
    "ở trên": "REL",
    "bên trên": "REL",
    "phía trên": "REL",

    "dưới": "REL",
    "ở dưới": "C",
    "bên dưới": "C",
    "phía dưới": "C",

    # ==========================================================
    # SO SÁNH
    # ==========================================================
    "nhiều hơn": "COMPARE",
    "ít hơn": "COMPARE",

    "cao hơn": "COMPARE",
    "thấp hơn": "COMPARE",

    "to hơn": "COMPARE",
    "lớn hơn": "COMPARE",

    "nhỏ hơn": "COMPARE",
    "bé hơn": "COMPARE",
}
templates = [
    # nếu có A thì có B
    ["L","V","N","L","V","N"],

    # không quá
    ["V","R","R","M","N"],

     # đúng 3 chim
    ["V","A","M","N"],

    # có A và B
    ["V","N","C","N"],

    # ít nhất
    ["V","X","M","N"],

    # có A
    ["V","N"],

    # cây bên trái nhà
    ["N","REL","N"],

    # cây to
    ["N","A"],

  
     # A nhiều hơn B
    ["N","COMPARE","N"],

    # A đi cùng B
    ["N","C","N"],   
]

# ==========================================
# 3. CÁC HÀM XỬ LÝ (NẰM DƯỚI CÙNG ĐỂ ĐỌC ĐƯỢC BIẾN)
# ==========================================
def rule_to_vietnamese(rule):
    replace = {
        "exist": "có",
        "sun": "mặt trời",
        "tree": "cây",
        "house": "nhà",
        "cloud": "mây",
        "mountain": "núi",
        "river": "sông",
        "bird": "chim",
        "flower": "hoa",
        "above": "ở trên",
        "below": "ở dưới",
        "left_of": "bên trái",
        "right_of": "bên phải",
        "higher_than": "cao hơn",
        "lower_than": "thấp hơn"
    }

    for k, v in replace.items():
        rule = rule.replace(k, v)

    return rule
def custom_pos_tag(text):
    if not text:
        return []

    temp_text = text
    placeholder_map = {}
    counter = 0

    sorted_keys = sorted(CUSTOM_POS_MAPPING.keys(), key=len, reverse=True)

    for key in sorted_keys:
        pattern = rf'(?<!\S){re.escape(key)}(?!\S)'
        while re.search(pattern, temp_text):
            # placeholder = f"TOKENX{counter}X"
            placeholder = f"__P{counter}__"
            placeholder_map[placeholder] = {
                "word": key,
                "tag": CUSTOM_POS_MAPPING[key]
            }
            # temp_text = re.sub(pattern, placeholder, temp_text, count=1)
            temp_text = re.sub(
                pattern,
                f" {placeholder} ",
                temp_text,
                count=1
            )
            counter += 1


    temp_text = re.sub(r"\s+", " ", temp_text).strip()
    print("TEMP TEXT:", temp_text)
    raw_tags = pos_tag(temp_text)
    print(raw_tags)
    final_tags = []

    for word, tag in raw_tags:
        word_clean = word.strip()

        # Nếu là số
        if word_clean.isdigit():
            final_tags.append([word_clean, "M"])

        # Nếu là placeholder
        # elif word_clean in placeholder_map:
        #     final_tags.append([
        #         placeholder_map[word_clean]["word"],
        #         placeholder_map[word_clean]["tag"]
        #     ])
        elif any(p in word_clean for p in placeholder_map):

            parts = word_clean.split()

            for p in parts:
                if p in placeholder_map:
                    final_tags.append([
                        placeholder_map[p]["word"],
                        placeholder_map[p]["tag"]
                    ])

        # Các từ bình thường
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
    return weights

def parse_rulesv2(tokens, sentence):
    print("======== DEBUG PARSE ========")
    print(tokens)
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
                        if (
                            pos.startswith(word_type)
                            or 
                            (word_type=="C" and pos in ["AND","OR"])
                        ):
                            found = True
                            break
                        current_idx += 1
                    
                    if not found or current_idx >= len(valid_tokens):
                        is_match = False
                        break
                    
                    if word in MAPPING:
                        en_word = MAPPING[word]
                    else:
                        en_word = translator.translate(word).lower()
            
            if is_match:
                print("MATCH TEMPLATE:", template)
                print(valid_tokens)
                if template == ["V","A","M","N"]:

                    quantity = QUANTITY_MAPPING[valid_tokens[1][0].lower()]
                    number = valid_tokens[2][0]
                    obj = MAPPING[valid_tokens[3][0].lower()]
                    
                    return {
                        "type": "qty",
                        "weight": 1.0,
                        "rule": f"count {obj} {quantity} {number}"
                    }
                if template == ["V","X","M","N"]:

                    quantity = QUANTITY_MAPPING[valid_tokens[1][0].lower()]
                    number = valid_tokens[2][0]
                    obj = MAPPING[valid_tokens[3][0].lower()]

                    return {
                        "type": "qty",
                        "weight": 1.0,
                        "rule": f"count {obj} {quantity} {number}"
                    }
                if template == ["V","R","R","M","N"]:

                    quantity = QUANTITY_MAPPING["không quá"]
                    number = valid_tokens[3][0]
                    obj = MAPPING[valid_tokens[4][0].lower()]

                    return {
                        "type": "qty",
                        "weight": 1.0,
                        "rule": f"count {obj} {quantity} {number}"
                    }

                if template == ["N","REL","N"]:

                    obj1 = MAPPING[valid_tokens[0][0].lower()]
                    relation = MAPPING[valid_tokens[1][0].lower()]
                    obj2 = MAPPING[valid_tokens[2][0].lower()]

                    return {
                        "type": "pos_rel",
                        "weight": 1.0,
                        "rule": f"position {obj1} {relation} {obj2}"
                    }
                if template == ["N","OR","N"]:

                    obj1 = MAPPING[valid_tokens[0][0].lower()]
                    obj2 = MAPPING[valid_tokens[2][0].lower()]

                    return {
                        "type": "xor",
                        "weight": 1.0,
                        "rule": f"xor {obj1} {obj2}"
                    }
                if template == ["N","COMPARE","N"]:

                    obj1 = MAPPING[valid_tokens[0][0].lower()]
                    relation = MAPPING[valid_tokens[1][0].lower()]
                    obj2 = MAPPING[valid_tokens[2][0].lower()]

                    # So sánh kích thước
                    if relation == "higher_than":
                        return {
                            "type": "size_comp",
                            "weight": 1.0,
                            "rule": f"compare {obj1} > {obj2}"
                        }

                    elif relation == "lower_than":
                        return {
                            "type": "size_comp",
                            "weight": 1.0,
                            "rule": f"compare {obj1} < {obj2}"
                        }

                    # So sánh số lượng
                    elif relation == "more_than":
                        return {
                            "type": "count_comp",
                            "weight": 1.0,
                            "rule": f"count {obj1} > {obj2}"
                        }

                    elif relation == "less_than":
                        return {
                            "type": "count_comp",
                            "weight": 1.0,
                            "rule": f"count {obj1} < {obj2}"
                        }
                if template == ["N","V","C"]:

                    obj = MAPPING[valid_tokens[0][0].lower()]
                    position = MAPPING[valid_tokens[2][0].lower()]

                    return {
                        "type": "absolute_position",
                        "weight": 1.0,
                        "rule": f"position {obj} {position}"
                    }
                if template == ["N","A"]:

                    obj = MAPPING[valid_tokens[0][0].lower()]
                    size = MAPPING[valid_tokens[1][0].lower()]

                    return {
                        "type": "size",
                        "weight": 1.0,
                        "rule": f"size {obj} {size}"
                    }   
                if template == ["L","V","N","L","V","N"]:

                    obj1 = MAPPING[valid_tokens[2][0].lower()]
                    obj2 = MAPPING[valid_tokens[5][0].lower()]

                    return {
                        "type": "if_then",
                        "weight": 1.0,
                        "rule": f"if have {obj1} then have {obj2}"
                    }
                if template == ["N","C","N","C","N"]:

                    obj1 = MAPPING[valid_tokens[0][0].lower()]
                    relation1 = MAPPING[valid_tokens[1][0].lower()]
                    obj2 = MAPPING[valid_tokens[2][0].lower()]
                    relation2 = MAPPING[valid_tokens[3][0].lower()]
                    obj3 = MAPPING[valid_tokens[4][0].lower()]

                    return {
                        "type": "relation3",
                        "weight": 1.0,
                        "rule": f"{obj1} {relation1} {obj2} {relation2} {obj3}"
                    }
     
                if template == ["V","N"]:

                    obj = MAPPING[valid_tokens[1][0].lower()]

                    return {
                        "type": "exist",
                        "weight": 1.0,
                        "rule": f"have {obj}"
                    }

                if template == ["V","Ns"]:

                    objects = []

                    for token in valid_tokens[1:]:
                        if token[1].startswith("N"):
                            objects.append(MAPPING[token[0].lower()])

                    return {
                        "type": "exist_multi",
                        "weight": 1.0,
                        "rule": [f"exist {obj}" for obj in objects]
                    }

                if template == ["V","N","C","N"]:

                    obj1 = MAPPING.get(valid_tokens[1][0].lower())
                    obj2 = MAPPING.get(valid_tokens[3][0].lower())

                    logic_word = valid_tokens[2][0].lower()

                    if logic_word == "và":
                        logic = "and"
                    elif logic_word == "hoặc":
                        logic = "or"
                    else:
                        logic = MAPPING.get(logic_word, "and")

                    return {
                        "type": "logic",
                        "weight": 1.0,
                        "rule": f"have {obj1} {logic} {obj2}"
                    }


                if template == ["N","C","N"]:

                    if valid_tokens[1][0].lower() == "và":

                        obj1 = MAPPING[valid_tokens[0][0].lower()]
                        obj2 = MAPPING[valid_tokens[2][0].lower()]

                        return {
                            "type": "together",
                            "weight": 1.0,
                            "rule": f"together {obj1} {obj2}"
                        }
                return {
                    "rule": rule_to_vietnamese(rule_en.strip()),
                    "rule_en": rule_en.strip(),
                    "template": template,
                    "raw_text": str(sentence),
                    "tokens": valid_tokens
                }
        return None
    except Exception as e:
        print(f"❌ Lỗi parse_rulesv2: {e}")
        return None