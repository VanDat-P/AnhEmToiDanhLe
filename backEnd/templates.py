import math

# ==========================================
# 1. CÁC HÀM BỔ TRỢ (HELPER FUNCTIONS)
# ==========================================
def get_center(box):
    """Tính tọa độ tâm của bounding box [xmin, ymin, xmax, ymax]"""
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

def get_area(box):
    """Tính diện tích của bounding box"""
    return (box[2] - box[0]) * (box[3] - box[1])

# ==========================================
# 2. HỆ THỐNG TEMPLATE (SOFT RULES: 0.0 -> 1.0)
# ==========================================

def template_0(rule, boxes_dict): # Sự tồn tại (V + N)
    
    text = rule["rule"].split()
    op = text[0]
    obj = text[1]
    
    if op == "have":
        return 1.0 if obj in boxes_dict and len(boxes_dict[obj]) > 0 else 0.0
    elif op == "not":
        return 1.0 if obj not in boxes_dict or len(boxes_dict[obj]) == 0 else 0.0
    return 0.0

def template_1(rule, boxes_dict): # Logic kết hợp (V + N + C + N)
    # Cú pháp: "have apple and banana" hoặc "not apple or banana"
    text = rule["rule"].split()
    op = text[0]
    obj1 = text[1]
    cond = text[2]
    obj2 = text[3]
    
    has_obj1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
    has_obj2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0
    
    if op == "have":
        if cond == "and":
            return 1.0 if has_obj1 and has_obj2 else 0.0
        elif cond == "or":
            return 1.0 if has_obj1 or has_obj2 else 0.0
            
    elif op == "not":
        if cond == "and":
            return 1.0 if not has_obj1 and not has_obj2 else 0.0
        elif cond == "or":
            return 1.0 if not has_obj1 or not has_obj2 else 0.0
    return 0.0

def template_2(rule, boxes_dict): # Số lượng (Quantity)
    # Cú pháp: "count apple >= 3"
    text = rule["rule"].split()
    obj = text[1]
    op = text[2]
    target_count = int(text[3])
    
    current_count = len(boxes_dict.get(obj, []))
    
    if op == "==":
        if current_count == target_count: return 1.0
        return max(0.0, 1.0 - abs(current_count - target_count) / max(1, target_count))
    elif op == ">=":
        if current_count >= target_count: return 1.0
        return current_count / target_count if target_count > 0 else 1.0
    elif op == "<=":
        if current_count <= target_count: return 1.0
        return max(0.0, 1.0 - (current_count - target_count) / max(1, target_count))
    return 0.0

def template_3(rule, boxes_dict): # Màu sắc (Color)
    # Cú pháp: "color apple red"
    text = rule["rule"].split()
    obj = text[1]
    target_color = text[2]
    
    if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
        return 0.0
        
    matched_color_count = sum(1 for item in boxes_dict[obj] if item.get("color") == target_color)
    return matched_color_count / len(boxes_dict[obj])

def template_4(rule, boxes_dict): # Kích thước (Size)
    # Cú pháp: "size apple small"
    text = rule["rule"].split()
    obj = text[1]
    target_size = text[2] # large, medium, small
    
    if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
        return 0.0
        
    scores = []
    for item in boxes_dict[obj]:
        area = get_area(item["box"])
        if target_size == "small":
            scores.append(max(0.0, 1.0 - area / 0.1))
        elif target_size == "medium":
            if 0.1 <= area <= 0.3: scores.append(1.0)
            else: scores.append(max(0.0, 1.0 - min(abs(area - 0.1), abs(area - 0.3)) / 0.2))
        elif target_size == "large":
            scores.append(min(1.0, area / 0.3))
            
    return sum(scores) / len(scores) if scores else 0.0

def template_5(rule, boxes_dict): # Vị trí tuyệt đối (Absolute Position)
    # Cú pháp: "position_abs sun top"
    text = rule["rule"].split()
    obj = text[1]
    location = text[2]
    
    if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
        return 0.0
        
    scores = []
    for item in boxes_dict[obj]:
        cx, cy = get_center(item["box"])
        if location == "top":
            scores.append(max(0.0, 1.0 - cy / 0.4))
        elif location == "bottom":
            scores.append(max(0.0, (cy - 0.6) / 0.4) if cy >= 0.6 else 0.0)
        elif location == "left":
            scores.append(max(0.0, 1.0 - cx / 0.4))
        elif location == "right":
            scores.append(max(0.0, (cx - 0.6) / 0.4) if cx >= 0.6 else 0.0)
        elif location == "center":
            dist_to_center = math.sqrt((cx - 0.5)**2 + (cy - 0.5)**2)
            scores.append(max(0.0, 1.0 - dist_to_center / 0.5))
            
    return sum(scores) / len(scores) if scores else 0.0

def template_6(rule, boxes_dict): # Vị trí tương đối (Relative Position)
    # Cú pháp: "position_rel apple left_of banana"
    text = rule["rule"].split()
    obj1 = text[1]
    relation = text[2]
    obj2 = text[3]
    
    if obj1 not in boxes_dict or obj2 not in boxes_dict:
        return 0.0
        
    box1 = boxes_dict[obj1][0]["box"]
    box2 = boxes_dict[obj2][0]["box"]
    
    cx1, cy1 = get_center(box1)
    cx2, cy2 = get_center(box2)
    
    if relation == "left_of":
        return 1.0 if cx1 < cx2 else max(0.0, 1.0 - (cx1 - cx2) / 0.2)
    elif relation == "right_of":
        return 1.0 if cx1 > cx2 else max(0.0, 1.0 - (cx2 - cx1) / 0.2)
    elif relation == "above":
        return 1.0 if cy1 < cy2 else max(0.0, 1.0 - (cy1 - cy2) / 0.2)
    elif relation == "below":
        return 1.0 if cy1 > cy2 else max(0.0, 1.0 - (cy2 - cy1) / 0.2)
    elif relation == "inside":
        inside_x = box1[0] >= box2[0] and box1[2] <= box2[2]
        inside_y = box1[1] >= box2[1] and box1[3] <= box2[3]
        return 1.0 if (inside_x and inside_y) else 0.2 
        
    return 0.0

# ==========================================
# 3. ENGINE TỔNG HỢP (SCORING ENGINE)
# ==========================================

def evaluate_drawing(user_rules, boxes_dict):
    """Hàm chạy qua tất cả các luật và tổng hợp điểm"""
    template_map = {
        "exist": template_0,
        "logic": template_1,
        "qty": template_2,
        "color": template_3,
        "size": template_4,
        "pos_abs": template_5,
        "pos_rel": template_6
    }
    
    total_score = 0.0
    total_weight = 0.0
    detailed_scores = {}
    
    for rule in user_rules:
        rule_type = rule["type"]
        weight = rule.get("weight", 1.0)
        
        if rule_type in template_map:
            rule_score = template_map[rule_type](rule, boxes_dict)
            total_score += rule_score * weight
            total_weight += weight
            detailed_scores[rule["rule"]] = round(rule_score * 100, 2)
            
    if total_weight == 0: 
        return 0.0, detailed_scores
    
    final_score = (total_score / total_weight) * 100
    return round(final_score, 2), detailed_scores

# ==========================================
# 4. KỊCH BẢN CHẠY THỬ (TEST CASE)
# ==========================================
if __name__ == "__main__":
    # Mock data: Đầu ra từ mô hình AI nhận diện vật thể trong ảnh
    # Tọa độ: [xmin, ymin, xmax, ymax] đã chuẩn hóa 0-1
    detected_boxes = {
        "apple": [
            {"box": [0.1, 0.2, 0.3, 0.4], "color": "red"},  # Tâm: (0.2, 0.3), Diện tích: 0.04
            {"box": [0.5, 0.6, 0.6, 0.7], "color": "green"} # Tâm: (0.55, 0.65), Diện tích: 0.01
        ],
        "banana": [
            {"box": [0.7, 0.2, 0.9, 0.5], "color": "yellow"} # Tâm: (0.8, 0.35), Diện tích: 0.06
        ],
        "sun": [
            {"box": [0.8, 0.0, 1.0, 0.2], "color": "yellow"} # Tâm: (0.9, 0.1), Diện tích: 0.04 (Ở góc trên phải)
        ]
    }

    # Mock rules: Các luật được tạo ra từ việc parse text đầu vào của người dùng
    rules = [
        {"type": "exist", "rule": "have apple", "weight": 1.0},
        {"type": "qty", "rule": "count apple == 2", "weight": 1.5},
        {"type": "color", "rule": "color apple red", "weight": 1.0}, # Mong đợi 50% vì có 1 đỏ, 1 xanh
        {"type": "pos_abs", "rule": "position_abs sun top", "weight": 1.0},
        {"type": "pos_rel", "rule": "position_rel apple left_of banana", "weight": 2.0}
    ]

    # Thực thi quá trình chấm điểm
    final_score, details = evaluate_drawing(rules, detected_boxes)

    # In kết quả
    print("--- KẾT QUẢ CHẤM ĐIỂM TRANH VẼ ---")
    print(f"Điểm tổng hợp: {final_score}/100")
    print("Điểm chi tiết từng tiêu chí (thang 100):")
    for rule_str, score in details.items():
        print(f"  * {rule_str}: {score}")