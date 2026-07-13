import math

# ==========================================
# 1. CÁC HÀM BỔ TRỢ HÌNH HỌC (HELPER FUNCTIONS)
# ==========================================
def get_center(box):
    """Tính tọa độ tâm của bounding box [xmin, ymin, xmax, ymax]"""
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

def get_area(box):
    """Tính diện tích của bounding box"""
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])

def get_intersection_area(box1, box2):
    """Tính diện tích phần giao nhau giữa 2 bounding box"""
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)

# ==========================================
# 2. TEMPLATE CƠ BẢN & LOGIC (Theo thiết kế gốc)
# ==========================================
def template_0(rule, boxes_dict): # Sự tồn tại (V + N)
    text = rule["rule"].split()
    op, obj = text[0], text[1]
    if op == "have": return 1.0 if obj in boxes_dict and len(boxes_dict[obj]) > 0 else 0.0
    elif op == "not": return 1.0 if obj not in boxes_dict or len(boxes_dict[obj]) == 0 else 0.0
    return 0.0

def template_1(rule, boxes_dict): # Logic kết hợp (V + N + C + N)
    text = rule["rule"].split()
    op, obj1, cond, obj2 = text[0], text[1], text[2], text[3]
    has_obj1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
    has_obj2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0
    
    if op == "have":
        if cond == "and": return 1.0 if has_obj1 and has_obj2 else 0.0
        elif cond == "or": return 1.0 if has_obj1 or has_obj2 else 0.0
    elif op == "not":
        if cond == "and": return 1.0 if not has_obj1 and not has_obj2 else 0.0
        elif cond == "or": return 1.0 if not has_obj1 or not has_obj2 else 0.0
    return 0.0

def template_2(rule, boxes_dict): # Số lượng (V + N + Op + Num)
    text = rule["rule"].split()
    obj, op, target_count = text[1], text[2], int(text[3])
    current_count = len(boxes_dict.get(obj, []))
    
    if op == "==":
        if current_count == target_count: return 1.0
        return max(0.0, 1.0 - abs(current_count - target_count) / max(1, target_count))
    elif op == ">=": return 1.0 if current_count >= target_count else (current_count / target_count if target_count > 0 else 1.0)
    elif op == "<=": return 1.0 if current_count <= target_count else max(0.0, 1.0 - (current_count - target_count) / max(1, target_count))
    return 0.0

# ==========================================
# 3. TEMPLATE THUỘC TÍNH ĐƠN LẺ
# ==========================================
def template_3(rule, boxes_dict): # Màu sắc (color N C)
    text = rule["rule"].split()
    obj, target_color = text[1], text[2]
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0
    matched = sum(1 for item in boxes_dict[obj] if item.get("color") == target_color)
    return matched / len(boxes_dict[obj])

def template_4(rule, boxes_dict): # Kích thước tuyệt đối (size N S)
    text = rule["rule"].split()
    obj, target_size = text[1], text[2]
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0
    scores = []
    for item in boxes_dict[obj]:
        area = get_area(item["box"])
        if target_size == "small": scores.append(max(0.0, 1.0 - area / 0.1))
        elif target_size == "medium": scores.append(1.0 if 0.1 <= area <= 0.3 else max(0.0, 1.0 - min(abs(area - 0.1), abs(area - 0.3)) / 0.2))
        elif target_size == "large": scores.append(min(1.0, area / 0.3))
    return sum(scores) / len(scores) if scores else 0.0

def template_11(rule, boxes_dict): # Thuộc tính biểu cảm (attribute N Attr)
    text = rule["rule"].split()
    obj, target_attr = text[1], text[2]
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0
    matched = sum(1 for item in boxes_dict[obj] if target_attr in item.get("attributes", []))
    return matched / len(boxes_dict[obj])

# ==========================================
# 4. TEMPLATE HÌNH HỌC KHÔNG GIAN
# ==========================================
def template_5(rule, boxes_dict): # Vị trí tuyệt đối (position_abs N Loc)
    text = rule["rule"].split()
    obj, location = text[1], text[2]
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0
    scores = []
    for item in boxes_dict[obj]:
        cx, cy = get_center(item["box"])
        if location == "top": scores.append(max(0.0, 1.0 - cy / 0.4))
        elif location == "bottom": scores.append(max(0.0, (cy - 0.6) / 0.4) if cy >= 0.6 else 0.0)
        elif location == "left": scores.append(max(0.0, 1.0 - cx / 0.4))
        elif location == "right": scores.append(max(0.0, (cx - 0.6) / 0.4) if cx >= 0.6 else 0.0)
        elif location == "center": scores.append(max(0.0, 1.0 - math.sqrt((cx - 0.5)**2 + (cy - 0.5)**2) / 0.5))
    return sum(scores) / len(scores) if scores else 0.0

def template_6(rule, boxes_dict): # Vị trí tương đối (position_rel N1 Rel N2)
    text = rule["rule"].split()
    obj1, relation, obj2 = text[1], text[2], text[3]
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    box1, box2 = boxes_dict[obj1][0]["box"], boxes_dict[obj2][0]["box"]
    cx1, cy1 = get_center(box1)
    cx2, cy2 = get_center(box2)
    if relation == "left_of": return 1.0 if cx1 < cx2 else max(0.0, 1.0 - (cx1 - cx2) / 0.2)
    elif relation == "right_of": return 1.0 if cx1 > cx2 else max(0.0, 1.0 - (cx2 - cx1) / 0.2)
    elif relation == "above": return 1.0 if cy1 < cy2 else max(0.0, 1.0 - (cy1 - cy2) / 0.2)
    elif relation == "below": return 1.0 if cy1 > cy2 else max(0.0, 1.0 - (cy2 - cy1) / 0.2)
    elif relation == "inside":
        return 1.0 if (box1[0] >= box2[0] and box1[2] <= box2[2] and box1[1] >= box2[1] and box1[3] <= box2[3]) else 0.2 
    return 0.0

def template_7(rule, boxes_dict): # Tỷ lệ khung hình (ratio N Ratio)
    text = rule["rule"].split()
    obj, target_ratio = text[1], text[2] 
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0
    scores = []
    for item in boxes_dict[obj]:
        box = item["box"]
        w, h = box[2] - box[0], box[3] - box[1]
        if h == 0: continue
        r = w / h
        if target_ratio == "tall": scores.append(1.0 if r < 0.9 else max(0.0, 1.0 - (r - 0.9) / 0.5))
        elif target_ratio == "wide": scores.append(1.0 if r > 1.1 else max(0.0, 1.0 - (1.1 - r) / 0.5))
        elif target_ratio == "square": scores.append(max(0.0, 1.0 - abs(1.0 - r) / 0.3))
    return sum(scores) / len(scores) if scores else 0.0

def template_8(rule, boxes_dict): # Khoảng cách xa/gần (distance N1 N2 Dist)
    text = rule["rule"].split()
    obj1, obj2, target_dist = text[1], text[2], text[3]
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    cx1, cy1 = get_center(boxes_dict[obj1][0]["box"])
    cx2, cy2 = get_center(boxes_dict[obj2][0]["box"])
    dist = math.hypot(cx1 - cx2, cy1 - cy2) 
    if target_dist == "close": return max(0.0, 1.0 - dist / 0.3)
    elif target_dist == "far": return min(1.0, dist / 0.7)
    return 0.0

def template_9(rule, boxes_dict): # Căn gióng (align N1 N2 Align)
    text = rule["rule"].split()
    obj1, obj2, alignment = text[1], text[2], text[3]
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    cx1, cy1 = get_center(boxes_dict[obj1][0]["box"])
    cx2, cy2 = get_center(boxes_dict[obj2][0]["box"])
    if alignment == "horizontal": return max(0.0, 1.0 - abs(cy1 - cy2) / 0.1)
    elif alignment == "vertical": return max(0.0, 1.0 - abs(cx1 - cx2) / 0.1)
    return 0.0

def template_10(rule, boxes_dict): # Độ phủ diện tích (coverage N Op Pct)
    text = rule["rule"].split()
    obj, op, target_pct = text[1], text[2], float(text[3]) / 100.0
    if obj not in boxes_dict or not boxes_dict[obj]: return 0.0 if op in [">=", "=="] else 1.0
    total_area = min(1.0, sum(get_area(item["box"]) for item in boxes_dict[obj]))
    if op == "==": return max(0.0, 1.0 - abs(total_area - target_pct) / 0.2)
    elif op == ">=": return 1.0 if total_area >= target_pct else total_area / target_pct
    elif op == "<=": return 1.0 if total_area <= target_pct else max(0.0, 1.0 - (total_area - target_pct) / 0.2)
    return 0.0

# ==========================================
# 5. TEMPLATE TƯƠNG TÁC V+N NÂNG CAO
# ==========================================
def template_18(rule, boxes_dict): # Tương tác đè/chứa (V + N1 + N2)
    # overlap cloud sun | contain house dog
    text = rule["rule"].split()
    op, obj1, obj2 = text[0], text[1], text[2]
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    scores = []
    for item1 in boxes_dict[obj1]:
        for item2 in boxes_dict[obj2]:
            inter_area = get_intersection_area(item1["box"], item2["box"])
            if op == "overlap": scores.append(1.0 if inter_area > 0 else 0.0)
            elif op == "contain":
                area2 = get_area(item2["box"])
                if area2 > 0: scores.append(inter_area / area2)
    return max(scores) if scores else 0.0

def template_19(rule, boxes_dict): # Đếm có điều kiện (count N Attr Op Num)
    # count apple red >= 2
    text = rule["rule"].split()
    obj, condition, op_math, target_num = text[1], text[2], text[3], int(text[4])
    if obj not in boxes_dict: return 0.0 if op_math in [">=", "=="] else 1.0
    valid_count = sum(1 for item in boxes_dict[obj] if condition == item.get("color", "") or condition in item.get("attributes", []))
    
    if op_math == "==": return 1.0 if valid_count == target_num else max(0.0, 1.0 - abs(valid_count - target_num) / max(1, target_num))
    elif op_math == ">=": return 1.0 if valid_count >= target_num else (valid_count / target_num if target_num > 0 else 1.0)
    elif op_math == "<=": return 1.0 if valid_count <= target_num else max(0.0, 1.0 - (valid_count - target_num) / max(1, target_num))
    return 0.0

def template_20(rule, boxes_dict): # Khoảng cách chính xác (distance_exact N1 N2 Op Num)
    # distance_exact person tree <= 0.3
    text = rule["rule"].split()
    obj1, obj2, op_math, target_dist = text[1], text[2], text[3], float(text[4])
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    min_dist = float('inf')
    for item1 in boxes_dict[obj1]:
        for item2 in boxes_dict[obj2]:
            cx1, cy1 = get_center(item1["box"])
            cx2, cy2 = get_center(item2["box"])
            min_dist = min(min_dist, math.hypot(cx1 - cx2, cy1 - cy2))
    
    if min_dist == float('inf'): return 0.0
    if op_math == "<=": return 1.0 if min_dist <= target_dist else max(0.0, 1.0 - (min_dist - target_dist) / 0.5)
    elif op_math == ">=": return 1.0 if min_dist >= target_dist else min_dist / target_dist
    return 0.0

def template_21(rule, boxes_dict): # Trạng thái phân bố (distribute N State)
    # distribute bird scattered / clustered
    text = rule["rule"].split()
    obj, state = text[1], text[2]
    items = boxes_dict.get(obj, [])
    if len(items) < 2: return 1.0 
    
    total_dist, pairs = 0, 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            cx1, cy1 = get_center(items[i]["box"])
            cx2, cy2 = get_center(items[j]["box"])
            total_dist += math.hypot(cx1 - cx2, cy1 - cy2)
            pairs += 1
            
    avg_dist = total_dist / pairs
    if state == "clustered": return 1.0 if avg_dist < 0.25 else max(0.0, 1.0 - (avg_dist - 0.25) / 0.5)
    elif state == "scattered": return 1.0 if avg_dist > 0.5 else max(0.0, avg_dist / 0.5)
    return 0.0

def template_22(rule, boxes_dict): # Chuỗi thứ tự (sequence N1 N2 N3 Dir)
    # sequence house tree sun ltr (left-to-right)
    text = rule["rule"].split()
    obj1, obj2, obj3, direction = text[1], text[2], text[3], text[4]
    if not all(obj in boxes_dict for obj in [obj1, obj2, obj3]): return 0.0
        
    c1 = get_center(boxes_dict[obj1][0]["box"])
    c2 = get_center(boxes_dict[obj2][0]["box"])
    c3 = get_center(boxes_dict[obj3][0]["box"])
    
    if direction == "ltr":
        if c1[0] < c2[0] < c3[0]: return 1.0
        score = 1.0 - (0.5 if c1[0] >= c2[0] else 0) - (0.5 if c2[0] >= c3[0] else 0)
        return max(0.0, score)
    elif direction == "ttb":
        if c1[1] < c2[1] < c3[1]: return 1.0
        score = 1.0 - (0.5 if c1[1] >= c2[1] else 0) - (0.5 if c2[1] >= c3[1] else 0)
        return max(0.0, score)
    return 0.0

# ==========================================
# 6. TEMPLATE LOGIC SUY DIỄN (KIỂM SOÁT LUẬT)
# ==========================================
def template_12(rule, boxes_dict): # Kéo theo (if have N1 then have N2)
    text = rule["rule"].split()
    obj_if, obj_then = text[2], text[5]
    has_if = obj_if in boxes_dict and len(boxes_dict[obj_if]) > 0
    has_then = obj_then in boxes_dict and len(boxes_dict[obj_then]) > 0
    if not has_if: return 1.0 
    return 1.0 if has_then else 0.0

def template_13(rule, boxes_dict): # Ưu tiên (must/may have N)
    text = rule["rule"].split()
    modality, obj = text[0], text[2]
    has_obj = obj in boxes_dict and len(boxes_dict[obj]) > 0
    if modality == "must": return 1.0 if has_obj else 0.0
    elif modality == "may": return 1.0 if has_obj else -1.0 # Cờ -1.0 báo hiệu bỏ qua điểm trừ
    return 0.0

def template_14(rule, boxes_dict): # XOR (only_one N1 N2)
    text = rule["rule"].split()
    obj1, obj2 = text[1], text[2]
    has1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
    has2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0
    if has1 and has2: return 0.0
    if has1 or has2: return 1.0 
    return 0.0

def template_15(rule, boxes_dict): # Đồng hành (together N1 N2)
    text = rule["rule"].split()
    obj1, obj2 = text[1], text[2]
    has1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
    has2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0
    return 1.0 if has1 == has2 else 0.0

def template_16(rule, boxes_dict): # So sánh số lượng (count_compare N1 Op N2)
    text = rule["rule"].split()
    obj1, op, obj2 = text[1], text[2], text[3]
    count1 = len(boxes_dict.get(obj1, []))
    count2 = len(boxes_dict.get(obj2, []))
    if op == ">": return 1.0 if count1 > count2 else 0.0
    elif op == "<": return 1.0 if count1 < count2 else 0.0
    elif op == "==": return 1.0 if count1 == count2 else 0.0
    return 0.0

def template_17(rule, boxes_dict): # So sánh kích thước (size_compare N1 Op N2)
    text = rule["rule"].split()
    obj1, op, obj2 = text[1], text[2], text[3]
    if obj1 not in boxes_dict or obj2 not in boxes_dict: return 0.0
    avg_area1 = sum(get_area(i["box"]) for i in boxes_dict[obj1]) / len(boxes_dict[obj1])
    avg_area2 = sum(get_area(i["box"]) for i in boxes_dict[obj2]) / len(boxes_dict[obj2])
    if op == ">": return 1.0 if avg_area1 > avg_area2 else (avg_area1 / avg_area2)
    elif op == "<": return 1.0 if avg_area1 < avg_area2 else (avg_area2 / avg_area1)
    return 0.0


# ==========================================
# 7. ENGINE TỔNG HỢP (SCORING ENGINE)
# ==========================================
def evaluate_drawing(user_rules, boxes_dict):
    """Engine xử lý toàn bộ 23 template và cơ chế thưởng phạt"""
    template_map = {
        "exist": template_0, "logic": template_1, "qty": template_2, "color": template_3, "size": template_4,
        "pos_abs": template_5, "pos_rel": template_6, "ratio": template_7, "distance": template_8, "align": template_9,
        "coverage": template_10, "attribute": template_11, "if_then": template_12, "priority": template_13,
        "xor": template_14, "together": template_15, "count_comp": template_16, "size_comp": template_17,
        "interaction": template_18, "qty_cond": template_19, "dist_exact": template_20, "distribution": template_21, 
        "sequence": template_22
    }
    
    total_score, total_weight = 0.0, 0.0
    detailed_scores = {}
    
    for rule in user_rules:
        rule_type = rule["type"]
        weight = rule.get("weight", 1.0)
        rule_text = rule["rule"]
        
        if rule_type in template_map:
            rule_score = template_map[rule_type](rule, boxes_dict)
            
            # Xử lý cơ chế Bonus (May have)
            if rule_type == "priority" and rule_text.startswith("may"):
                if rule_score == -1.0:
                    detailed_scores[rule_text] = "Bonus: Bỏ qua (Không trừ)"
                else:
                    total_score += 1.0 * weight
                    total_weight += weight
                    detailed_scores[rule_text] = "Bonus: Đạt (100.0)"
                continue
                
            # Xử lý cơ chế Bắt buộc (Must have)
            if rule_type == "priority" and rule_text.startswith("must") and rule_score == 0.0:
                total_weight += weight * 2 # Phạt nặng
                detailed_scores[rule_text] = 0.0
                continue
            
            # Tính điểm bình thường
            total_score += rule_score * weight
            total_weight += weight
            detailed_scores[rule_text] = round(rule_score * 100, 2)
            
    if total_weight == 0: return 0.0, detailed_scores
    return round((total_score / total_weight) * 100, 2), detailed_scores


# ==========================================
# 8. KỊCH BẢN CHẠY THỬ TOÀN DIỆN (FULL TEST CASE)
# ==========================================
if __name__ == "__main__":
    # Dữ liệu mô phỏng một bức tranh (Ảnh 1.0 x 1.0)
    detected_boxes = {
        "house": [{"box": [0.1, 0.3, 0.4, 0.7]}],
        "door": [{"box": [0.2, 0.5, 0.3, 0.7]}], # Cửa nằm trong nhà
        "person": [
            {"box": [0.5, 0.6, 0.55, 0.8], "color": "red", "attributes": ["smiling"]},
            {"box": [0.6, 0.6, 0.65, 0.8], "color": "blue"}
        ],
        "bird": [
            {"box": [0.1, 0.1, 0.15, 0.15]},
            {"box": [0.2, 0.1, 0.25, 0.15]},
            {"box": [0.3, 0.1, 0.35, 0.15]} # Bầy chim rải rác trên trời
        ],
        "sun": [{"box": [0.8, 0.0, 1.0, 0.2]}]
    }

    # Tổng hợp các bộ luật từ dễ đến khó
    rules = [
        {"type": "priority", "rule": "must have house", "weight": 2.0},
        {"type": "priority", "rule": "may have cloud", "weight": 1.0}, # Sẽ bỏ qua vì ko vẽ
        {"type": "interaction", "rule": "contain house door", "weight": 1.5},
        {"type": "qty_cond", "rule": "count person red >= 1", "weight": 1.0},
        {"type": "distribution", "rule": "distribute bird scattered", "weight": 1.0},
        {"type": "sequence", "rule": "sequence house person sun ltr", "weight": 1.5},
        {"type": "dist_exact", "rule": "distance_exact house sun >= 0.4", "weight": 1.0},
        {"type": "logic", "rule": "have person and sun", "weight": 1.0}
    ]

    final_score, details = evaluate_drawing(rules, detected_boxes)

    print("="*55)
    print(" HỆ THỐNG AI CHẤM ĐIỂM TRANH VẼ (MASTER V1.0)")
    print("="*55)
    print(f">> ĐIỂM TỔNG HỢP: {final_score}/100\n")
    print(">> BẢNG ĐIỂM CHI TIẾT TỪNG TIÊU CHÍ:")
    for rule_str, score in details.items():
        print(f"   [+] {rule_str.ljust(40)} : {score}")
    print("="*55)