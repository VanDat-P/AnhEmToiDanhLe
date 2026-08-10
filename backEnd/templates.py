import math
from nlp_utils import SCENERY_OBJECT_VI
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

# 
def template_0(rule, boxes_dict):
    text = rule["rule"].split()
    op, obj = text[0], text[1]
    obj_vi = SCENERY_OBJECT_VI.get(obj, obj)
    has_obj = obj in boxes_dict and len(boxes_dict[obj]) > 0

    if op == "have":
        if has_obj:
            return {
                "score": 1.0,
                "reason": f"Đã phát hiện {obj_vi}."
            }
        return {
            "score": 0.0,
            "reason": f"Thiếu {obj_vi}."
        }

    elif op == "not":
        if not has_obj:
            return {
                "score": 1.0,
                "reason": f"Không xuất hiện {obj_vi}."
            }
        return {
            "score": 0.0,
            "reason": f"Có xuất hiện {obj_vi}."
        }

    return {
        "score": 0.0,
        "reason": "Luật không hợp lệ."
    }
# def template_1(rule, boxes_dict): #hoàn thành rồi ní ơi

#     text = rule["rule"].split()

#     op = text[0]
#     obj1 = text[1]
#     logic = text[2]
#     obj2 = text[3]
    
#     has1 = len(boxes_dict.get(obj1, [])) > 0
#     has2 = len(boxes_dict.get(obj2, [])) > 0

#     # Tên tiếng Việt (nếu có)
#     name1 = rule.get("SCENERY_OBJECT_VI", obj1)
#     name2 = rule.get("SCENERY_OBJECT_VI", obj2)

#     if logic == "and":

#         score = 1.0 if (has1 and has2) else 0.0

#     elif logic == "or":

#         score = 1.0 if (has1 or has2) else 0.0

#     else:
#         return {
#             "score": 0.0,
#             "reason": f"Cả {obj1} và {obj2}: logic không hợp lệ."
#         }

#     # Tạo nội dung hiển thị cho từng đối tượng
#     result = []

#     result.append(f"{'có' if has1 else 'nhưng không có'} {name1}")
#     result.append(f"{'có' if has2 else 'nhưng không có'} {name2}")

#     return {
#         "score": score,
#         "reason": ", ".join(result)
#     }
def template_1(rule, boxes_dict):

    text = rule["rule"].split()

    op = text[0]
    obj1 = text[1]
    logic = text[2]
    obj2 = text[3]

    # Đổi tên object sang tiếng Việt
    obj1_vi = SCENERY_OBJECT_VI.get(obj1, obj1)
    obj2_vi = SCENERY_OBJECT_VI.get(obj2, obj2)

    has1 = len(boxes_dict.get(obj1, [])) > 0
    has2 = len(boxes_dict.get(obj2, [])) > 0

    if logic == "and":
        score = 1.0 if (has1 and has2) else 0.0

    elif logic == "or":
        score = 1.0 if (has1 or has2) else 0.0

    else:
        return {
            "score": 0.0,
            # "reason": f"Điều kiện giữa {obj1_vi} và {obj2_vi} không hợp lệ."
            "reason": "sai điều kiện template 1 "
        }

    result = []

    result.append(f"{'Có' if has1 else 'Không có'} {obj1_vi}")
    result.append(f"{'Có' if has2 else 'Không có'} {obj2_vi}")

    return {
        "score": score,
        "status": "Đạt" if score == 1.0 else "Không đạt",
        "reason": ", ".join(result)
    }
def template_2(rule, boxes_dict):#chạy được rồi

    text = rule["rule"].split()

    obj = text[1]
    op = text[2]
    
    
    target_count = int(text[3])
    obj_vi = SCENERY_OBJECT_VI.get(obj, obj)
    current_count = len(boxes_dict.get(obj, []))

    if op == "==":
        score = 1.0 if current_count == target_count else 0.0

    elif op == ">=":
        score = 1.0 if current_count >= target_count else 0.0

    elif op == "<=":
        score = 1.0 if current_count <= target_count else 0.0

    else:
        score = 0.0


    return {
        "score": score,
        "status": "Đạt" if score == 1.0 else "Không đạt",
        "reason": f"Phát hiện {current_count}/{target_count} {obj_vi}."
    }


def template_3(rule, boxes_dict): # thành công rồi

    text = rule["rule"].split()
    SIZE_VI = {
        "large": "to",
        "medium": "vừa",
        "small": "nhỏ"
    }

    obj = text[1]
    target_size = text[2]

    if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
        return {
            "score": 0.0,
            "reason": f"Không có {obj}."
        }

    scores = []

    for item in boxes_dict[obj]:

        area = get_area(item["box"])

        if target_size == "small":
            scores.append(max(0.0, 1.0 - area / 0.1))

        elif target_size == "medium":
            scores.append(
                1.0 if 0.1 <= area <= 0.3
                else max(0.0, 1.0 - min(abs(area-0.1), abs(area-0.3))/0.2)
            )

        elif target_size == "large":
            scores.append(min(1.0, area / 0.3))

    final_score = sum(scores) / len(scores)
    obj_vi = SCENERY_OBJECT_VI.get(obj, obj)
    size_vi = SIZE_VI.get(target_size, target_size)

    return {
        "score": final_score,
        "reason": f"Kích thước {obj_vi} không đạt mức {size_vi}."
    }

def template_4(rule, boxes_dict): #tạm ổn trước tiên

    text = rule["rule"].split()

    obj1 = text[1]
    relation = text[2]
    obj2 = text[3]
    obj1_vi = SCENERY_OBJECT_VI.get(obj1, obj1)
    obj2_vi = SCENERY_OBJECT_VI.get(obj2, obj2)
    print("========== DEBUG TEMPLATE 6 ==========")
    print("Boxes:", boxes_dict.keys())
    print("obj1 =", obj1)
    print("obj2 =", obj2)
    print("boxes obj1 =", boxes_dict.get(obj1))
    print("boxes obj2 =", boxes_dict.get(obj2))
    print("======================================")
    RELATION_VI1 = {
                "left_of": "nằm bên trái",
                "right_of": "nằm bên phải",
                "above": "nằm phía trên",
                "below": "nằm phía dưới",
                "inside": "nằm bên trong"
            }
    relation_vi1= RELATION_VI1.get(relation, relation)
    if obj1 not in boxes_dict or len(boxes_dict.get(obj1, [])) == 0:
        return {
            "score": 0.0,
            "reason": f"Thiếu {obj1_vi} nên không đạt điều kiện {relation_vi1}."
        }

    if obj2 not in boxes_dict or len(boxes_dict.get(obj2, [])) == 0:
        return {
            "score": 0.0,
            "reason": f"Thiếu {obj2_vi} nên không đạt điều kiện {relation_vi1}."
        }

    best_score = 0.0

    for item1 in boxes_dict[obj1]:
        for item2 in boxes_dict[obj2]:

            box1 = item1["box"]
            box2 = item2["box"]

            cx1, cy1 = get_center(box1)
            cx2, cy2 = get_center(box2)

            # -------------------------
            # LEFT OF
            # -------------------------
            if relation == "left_of":

                if cx1 < cx2:
                    score = 1.0
                else:
                    score = max(0.0, 1 - (cx1 - cx2) / 0.3)

            # -------------------------
            # RIGHT OF
            # -------------------------
            elif relation == "right_of":

                if cx1 > cx2:
                    score = 1.0
                else:
                    score = max(0.0, 1 - (cx2 - cx1) / 0.3)

            # -------------------------
            # ABOVE
            # -------------------------
            elif relation == "above":

                if cy1 < cy2:
                    score = 1.0
                else:
                    score = max(0.0, 1 - (cy1 - cy2) / 0.3)

            # -------------------------
            # BELOW
            # -------------------------
            elif relation == "below":

                if cy1 > cy2:
                    score = 1.0
                else:
                    score = max(0.0, 1 - (cy2 - cy1) / 0.3)

            # -------------------------
            # INSIDE
            # -------------------------
            elif relation == "inside":

                inter = get_intersection_area(box1, box2)
                area = get_area(box1)

                score = inter / area if area > 0 else 0.0

            else:
                score = 0.0

            best_score = max(best_score, score)
    RELATION_VI = {
            "left_of": "nằm bên trái",
            "right_of": "nằm bên phải",
            "above": "nằm phía trên",
            "below": "nằm phía dưới",
            "inside": "nằm bên trong"
        }
    relation_vi = RELATION_VI.get(relation, relation)
    return {
        "score": round(best_score, 3),
        "reason": f"{obj1_vi} {relation_vi} {obj2_vi}"
    }


def template_5(rule, boxes_dict): #tạm oke

    text = rule["rule"].split()

    obj_if = text[2]
    obj_then = text[5]
    obj_if_vi = SCENERY_OBJECT_VI.get(obj_if, obj_if)
    obj_then_vi = SCENERY_OBJECT_VI.get(obj_then, obj_then)     
    has_if = obj_if in boxes_dict and len(boxes_dict[obj_if]) > 0
    has_then = obj_then in boxes_dict and len(boxes_dict[obj_then]) > 0

    if not has_if:
        return {
            "score": 1.0,
            "reason": f"Không có {obj_if_vi}, luật không áp dụng."
        }

    if has_then:
        return {
            "score": 1.0,
            "reason": f"Có {obj_if_vi} và cũng có {obj_then_vi}."
        }

    return {
        "score": 0.0,
        "reason": f"Có {obj_if_vi} nhưng thiếu {obj_then_vi}."
}   

def template_6(rule, boxes_dict): # thanh công phân nữa
    print("================================")
    print(boxes_dict)
    print("tree =", boxes_dict.get("tree"))
    print("cloud =", boxes_dict.get("cloud"))
    print("================================")
    text = rule["rule"].split()

    obj1 = text[1]
    op = text[2]
    obj2 = text[3]
    obj1_vi = SCENERY_OBJECT_VI.get(obj1, obj1)
    obj2_vi = SCENERY_OBJECT_VI.get(obj2, obj2)
    count1 = len(boxes_dict.get(obj1, []))
    count2 = len(boxes_dict.get(obj2, []))

    if op == ">":
        if count1 > count2:
            score = 1.0
            reason = f"Số lượng {obj1_vi} ({count1}) nhiều hơn {obj2_vi} ({count2})."
        else:
            score = 0.0
            reason = f"Số lượng {obj1_vi} ({count1}) không nhiều hơn {obj2_vi} ({count2})."

    elif op == "<":
        if count1 < count2:
            score = 1.0
            reason = f"Số lượng {obj1_vi} ({count1}) ít hơn {obj2_vi} ({count2})."
        else:
            score = 0.0
            reason = f"Số lượng {obj1_vi} ({count1}) không ít hơn {obj2_vi} ({count2})."

    elif op == "==":
        if count1 == count2:
            score = 1.0
            reason = f"Số lượng {obj1_vi} ({count1}) bằng {obj2_vi} ({count2})."
        else:
            score = 0.0
            reason = f"Số lượng {obj1_vi} ({count1}) không bằng {obj2_vi} ({count2})."

    else:
        score = 0.0
        reason = "Phép so sánh không hợp lệ."

    return {
        "score": score,
        "status": "Đạt" if score == 1.0 else "Không đạt",
        "reason": reason
    }
def template_7(rule, boxes_dict):

    text = rule["rule"].split()

    obj1 = text[1]
    op = text[2]
    obj2 = text[3]
    obj1_vi = SCENERY_OBJECT_VI.get(obj1, obj1)
    obj2_vi = SCENERY_OBJECT_VI.get(obj2, obj2)
    if (
        obj1 not in boxes_dict
        or obj2 not in boxes_dict
        or len(boxes_dict[obj1]) == 0
        or len(boxes_dict[obj2]) == 0
    ):
        return {
            "score": 0.0,
            "reason": "Thiếu đối tượng để so sánh."
        }

    avg1 = sum(get_area(i["box"]) for i in boxes_dict[obj1]) / len(boxes_dict[obj1])
    avg2 = sum(get_area(i["box"]) for i in boxes_dict[obj2]) / len(boxes_dict[obj2])

    if op == ">":

        if avg1 > avg2:
            score = 1.0
        else:
            score = avg1 / avg2 if avg2 > 0 else 0.0

    elif op == "<":

        if avg1 < avg2:
            score = 1.0
        else:
            score = avg2 / avg1 if avg1 > 0 else 0.0

    else:
        score = 0.0

    if score == 1.0:
        reason = f"{obj1_vi} to hơn {obj2_vi}."
    else:
        reason = f"{obj1_vi} không to hơn {obj2_vi}."

    return {
        "score": score,
        "status": "Đạt" if score == 1.0 else "Không đạt",
        "reason": reason
    }
# ==========================================
# 7. ENGINE TỔNG HỢP (SCORING ENGINE)
# ==========================================
def evaluate_drawing(user_rules, boxes_dict):
    template_map = {
        "exist": template_0,
        "logic": template_1,
        "qty": template_2,
        "size": template_3,
        "pos_rel": template_4,
        "if_then": template_5,
        "count_comp": template_6,
        "size_comp": template_7,
    }

    total_score = 0.0
    total_weight = 0.0

    detailed_scores = {}

    for rule in user_rules:

        rule_type = rule["type"]
        weight = rule.get("weight", 1.0)
        rule_text = rule["rule"]

        if rule_type not in template_map:
            continue

        result = template_map[rule_type](rule, boxes_dict)

        rule_score = result["score"]
        reason = result["reason"]

        # ===============================
        # MAY HAVE (Bonus)
        # ===============================
        if rule_type == "priority" and rule_text.startswith("may"):

            if rule_score == -1:

                detailed_scores[rule_text] = {
                    "score": "Bonus",
                    "reason": reason
                }

            else:

                total_score += weight
                total_weight += weight

                detailed_scores[rule_text] = {
                    "score": 100,
                    "reason": reason
                }

            continue

        # ===============================
        # MUST HAVE
        # ===============================
        if (
            rule_type == "priority"
            and rule_text.startswith("must")
            and rule_score == 0
        ):

            total_weight += weight * 2

            detailed_scores[rule_text] = {
                "score": 0,
                "reason": reason
            }

            continue

        # ===============================
        # NORMAL RULE
        # ===============================
        total_score += rule_score * weight
        total_weight += weight

        detailed_scores[rule_text] = {
            "score": round(rule_score * 100, 2),
            "status": result.get("status"),
            "reason": reason
        }

    if total_weight == 0:
        return 0.0, detailed_scores

    final_score = round(total_score / total_weight * 100, 2)

    return final_score, detailed_scores


# # ==========================================
# # 8. KỊCH BẢN CHẠY THỬ TOÀN DIỆN (FULL TEST CASE)
# # ==========================================
# if __name__ == "__main__":
#     # Dữ liệu mô phỏng một bức tranh (Ảnh 1.0 x 1.0)
#     detected_boxes = {
#         "house": [{"box": [0.1, 0.3, 0.4, 0.7]}],
#         "door": [{"box": [0.2, 0.5, 0.3, 0.7]}], # Cửa nằm trong nhà
#         "person": [
#             {"box": [0.5, 0.6, 0.55, 0.8], "color": "red", "attributes": ["smiling"]},
#             {"box": [0.6, 0.6, 0.65, 0.8], "color": "blue"}
#         ],
#         "bird": [
#             {"box": [0.1, 0.1, 0.15, 0.15]},
#             {"box": [0.2, 0.1, 0.25, 0.15]},
#             {"box": [0.3, 0.1, 0.35, 0.15]} # Bầy chim rải rác trên trời
#         ],
#         "sun": [{"box": [0.8, 0.0, 1.0, 0.2]}]
#     }

#     # Tổng hợp các bộ luật từ dễ đến khó
#     rules = [
#         {"type": "priority", "rule": "must have house", "weight": 2.0},
#         {"type": "priority", "rule": "may have cloud", "weight": 1.0}, # Sẽ bỏ qua vì ko vẽ
#         {"type": "interaction", "rule": "contain house door", "weight": 1.5},
#         {"type": "qty_cond", "rule": "count person red >= 1", "weight": 1.0},
#         {"type": "distribution", "rule": "distribute bird scattered", "weight": 1.0},
#         {"type": "sequence", "rule": "sequence house person sun ltr", "weight": 1.5},
#         {"type": "dist_exact", "rule": "distance_exact house sun >= 0.4", "weight": 1.0},
#         {"type": "logic", "rule": "have person and sun", "weight": 1.0}
#     ]

#     final_score, details = evaluate_drawing(rules, detected_boxes)

#     print("="*55)
#     print(" HỆ THỐNG AI CHẤM ĐIỂM TRANH VẼ (MASTER V1.0)")
#     print("="*55)
#     print(f">> ĐIỂM TỔNG HỢP: {final_score}/100\n")
#     print(">> BẢNG ĐIỂM CHI TIẾT TỪNG TIÊU CHÍ:")
#     for rule_str, score in details.items():
#         print(f"   [+] {rule_str.ljust(40)} : {score}")
#     print("="*55)