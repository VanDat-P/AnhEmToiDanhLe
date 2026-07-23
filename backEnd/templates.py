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

# ==========================================
# 3. TEMPLATE THUỘC TÍNH ĐƠN LẺ
# ==========================================

def template_4(rule, boxes_dict): # thành công rồi

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
        "reason": f"Kích thước {obj_vi} gần mức {size_vi}."
    }
    # return {
    #     "score": final_score,
    #     "reason": f"Kích thước {obj} gần mức {target_size}."    
    # }
# def template_11(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj=text[1]
#     target_attr=text[2]

#     if obj not in boxes_dict or len(boxes_dict[obj])==0:
#         return{
#             "score":0.0,
#             "reason":f"Không có {obj}."
#         }

#     matched=sum(
#         1
#         for item in boxes_dict[obj]
#         if target_attr in item.get("attributes",[])
#     )

#     score=matched/len(boxes_dict[obj])

#     return{
#         "score":score,
#         "reason":f"Có {matched}/{len(boxes_dict[obj])} {obj} mang thuộc tính {target_attr}."
#     }

# # ==========================================
# # 4. TEMPLATE HÌNH HỌC KHÔNG GIAN
# # ==========================================
# def template_5(rule, boxes_dict):

#     text = rule["rule"].split()

#     obj = text[1]
#     location = text[2]

#     if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
#         return {
#             "score": 0.0,
#             "reason": f"Không có {obj}."
#         }

#     scores = []

#     for item in boxes_dict[obj]:

#         cx, cy = get_center(item["box"])

#         if location == "top":
#             scores.append(max(0.0, 1.0 - cy / 0.4))

#         elif location == "bottom":
#             scores.append(
#                 max(0.0, (cy - 0.6) / 0.4)
#                 if cy >= 0.6 else 0.0
#             )

#         elif location == "left":
#             scores.append(max(0.0, 1.0 - cx / 0.4))

#         elif location == "right":
#             scores.append(
#                 max(0.0, (cx - 0.6) / 0.4)
#                 if cx >= 0.6 else 0.0
#             )

#         elif location == "center":
#             scores.append(
#                 max(
#                     0.0,
#                     1.0 - math.sqrt((cx-0.5)**2 + (cy-0.5)**2)/0.5
#                 )
#             )

#     final_score = sum(scores) / len(scores)

#     return {
#         "score": final_score,
#         "reason": f"{obj} nằm ở vị trí {location}."
#     }
def template_6(rule, boxes_dict): #tạm ổn trước tiên

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
# def template_7(rule, boxes_dict):

#     text = rule["rule"].split()

#     obj = text[1]
#     target_ratio = text[2]

#     if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
#         return {
#             "score":0.0,
#             "reason":f"Không có {obj}."
#         }

#     scores=[]

#     for item in boxes_dict[obj]:

#         box=item["box"]

#         w=box[2]-box[0]
#         h=box[3]-box[1]

#         if h<=0:
#             continue

#         ratio=w/h

#         if target_ratio=="tall":
#             scores.append(
#                 1.0 if ratio<0.9
#                 else max(0.0,1-(ratio-0.9)/0.5)
#             )

#         elif target_ratio=="wide":
#             scores.append(
#                 1.0 if ratio>1.1
#                 else max(0.0,1-(1.1-ratio)/0.5)
#             )

#         elif target_ratio=="square":
#             scores.append(
#                 max(0.0,1-abs(1-ratio)/0.3)
#             )

#     final_score=sum(scores)/len(scores) if scores else 0

#     return {
#         "score":final_score,
#         "reason":f"Tỉ lệ của {obj} gần với {target_ratio}."
#     }
# def template_8(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj1=text[1]
#     obj2=text[2]
#     target_dist=text[3]

#     if (
#         obj1 not in boxes_dict
#         or obj2 not in boxes_dict
#         or len(boxes_dict[obj1])==0
#         or len(boxes_dict[obj2])==0
#     ):
#         return {
#             "score":0.0,
#             "reason":"Thiếu đối tượng."
#         }

#     cx1,cy1=get_center(boxes_dict[obj1][0]["box"])
#     cx2,cy2=get_center(boxes_dict[obj2][0]["box"])

#     dist=math.hypot(cx1-cx2,cy1-cy2)

#     if target_dist=="close":
#         score=max(0.0,1-dist/0.3)

#     elif target_dist=="far":
#         score=min(1.0,dist/0.7)

#     else:
#         score=0.0

#     return {
#         "score":score,
#         "reason":f"Khoảng cách giữa {obj1} và {obj2} là {round(dist,3)}."
#     }
# def template_9(rule, boxes_dict):
#     """
#     align:
#     Các vật phải nằm trên cùng một hàng ngang hoặc cột dọc.
#     """

#     objects = rule.get("objects", [])

#     if len(objects) < 2:
#         return {
#             "status": "Không đạt",
#             "score": 0,
#             "message": "Thiếu đối tượng."
#         }

#     boxes = []

#     for obj in objects:
#         if obj not in boxes_dict or len(boxes_dict[obj]) == 0:
#             return {
#                 "status": "Không đạt",
#                 "score": 0,
#                 "message": f"Không tìm thấy {obj}."
#             }

#         boxes.append(boxes_dict[obj][0]["box"])

#     centers = []

#     for box in boxes:
#         x1, y1, x2, y2 = box
#         centers.append(((x1 + x2) / 2, (y1 + y2) / 2))

#     xs = [c[0] for c in centers]
#     ys = [c[1] for c in centers]

#     tolerance = rule.get("tolerance", 40)

#     horizontal = max(ys) - min(ys) <= tolerance
#     vertical = max(xs) - min(xs) <= tolerance

#     if horizontal or vertical:
#         return {
#             "status": "Đạt",
#             "score": 100,
#             "message": "Các đối tượng được căn thẳng hàng."
#         }

#     return {
#         "status": "Không đạt",
#         "score": 0,
#         "message": "Các đối tượng không thẳng hàng."
#     }
# def template_10(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj=text[1]
#     op=text[2]
#     target_pct=float(text[3])/100

#     if obj not in boxes_dict or len(boxes_dict[obj])==0:
#         return{
#             "score":0.0,
#             "reason":f"Không có {obj}."
#         }

#     total_area=min(
#         1.0,
#         sum(get_area(i["box"]) for i in boxes_dict[obj])
#     )

#     if op=="==":

#         score=max(
#             0.0,
#             1-abs(total_area-target_pct)/0.2
#         )

#     elif op==">=":

#         score=1.0 if total_area>=target_pct else (
#             total_area/target_pct if target_pct>0 else 1.0
#         )

#     elif op=="<=":

#         score=1.0 if total_area<=target_pct else max(
#             0.0,
#             1-(total_area-target_pct)/0.2
#         )

#     else:
#         score=0.0

#     return{
#         "score":score,
#         "reason":f"{obj} chiếm {round(total_area*100,1)}% diện tích."
#     }
# ==========================================
# 5. TEMPLATE TƯƠNG TÁC V+N NÂNG CAO
# ==========================================
# def template_18(rule, boxes_dict):

#     text = rule["rule"].split()

#     op = text[0]
#     obj1 = text[1]
#     obj2 = text[2]

#     if (
#         obj1 not in boxes_dict
#         or obj2 not in boxes_dict
#         or len(boxes_dict[obj1]) == 0
#         or len(boxes_dict[obj2]) == 0
#     ):
#         return {
#             "score":0.0,
#             "reason":"Thiếu đối tượng."
#         }

#     scores=[]

#     for item1 in boxes_dict[obj1]:
#         for item2 in boxes_dict[obj2]:

#             inter=get_intersection_area(item1["box"],item2["box"])

#             if op=="overlap":
#                 scores.append(1.0 if inter>0 else 0.0)

#             elif op=="contain":

#                 area2=get_area(item2["box"])

#                 if area2>0:
#                     scores.append(inter/area2)

#     score=max(scores) if scores else 0.0

#     return{
#         "score":score,
#         "reason":f"{obj1} {op} {obj2}."
#     }
# def template_19(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj=text[1]
#     condition=text[2]
#     op=text[3]
#     target=int(text[4])

#     if obj not in boxes_dict or len(boxes_dict[obj])==0:
#         return{
#             "score":0.0,
#             "reason":f"Không có {obj}."
#         }

#     valid=sum(
#         1
#         for item in boxes_dict[obj]
#         if condition==item.get("color","")
#         or condition in item.get("attributes",[])
#     )

#     if op=="==":

#         score=1.0 if valid==target else max(
#             0.0,
#             1-abs(valid-target)/max(target,1)
#         )

#     elif op==">=":

#         if target==0:
#             score=1.0
#         else:
#             score=1.0 if valid>=target else valid/target

#     elif op=="<=":

#         score=1.0 if valid<=target else max(
#             0.0,
#             1-(valid-target)/max(target,1)
#         )

#     else:
#         score=0.0

#     return{
#         "score":score,
#         "reason":f"Có {valid} {obj} thỏa điều kiện {condition}."
#     }

# def template_20(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj1=text[1]
#     obj2=text[2]
#     op=text[3]
#     target=float(text[4])

#     if (
#         obj1 not in boxes_dict
#         or obj2 not in boxes_dict
#         or len(boxes_dict[obj1])==0
#         or len(boxes_dict[obj2])==0
#     ):
#         return{
#             "score":0.0,
#             "reason":"Thiếu đối tượng."
#         }

#     mindist=float("inf")

#     for a in boxes_dict[obj1]:
#         for b in boxes_dict[obj2]:

#             c1=get_center(a["box"])
#             c2=get_center(b["box"])

#             d=math.hypot(c1[0]-c2[0],c1[1]-c2[1])

#             mindist=min(mindist,d)

#     if op=="<=":

#         score=1.0 if mindist<=target else max(
#             0.0,
#             1-(mindist-target)/0.5
#         )

#     elif op==">=":

#         score=1.0 if mindist>=target else (
#             mindist/target if target>0 else 1.0
#         )

#     else:
#         score=0.0

#     return{
#         "score":score,
#         "reason":f"Khoảng cách nhỏ nhất = {round(mindist,3)}."
#     }

# def template_21(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj=text[1]
#     state=text[2]

#     items=boxes_dict.get(obj,[])

#     if len(items)<2:
#         return{
#             "score":1.0,
#             "reason":"Không đủ đối tượng để đánh giá."
#         }

#     total=0
#     pairs=0

#     for i in range(len(items)):
#         for j in range(i+1,len(items)):

#             c1=get_center(items[i]["box"])
#             c2=get_center(items[j]["box"])

#             total+=math.hypot(c1[0]-c2[0],c1[1]-c2[1])
#             pairs+=1

#     avg=total/pairs

#     if state=="clustered":

#         score=1.0 if avg<0.25 else max(
#             0.0,
#             1-(avg-0.25)/0.5
#         )

#     elif state=="scattered":

#         score=1.0 if avg>0.5 else max(
#             0.0,
#             avg/0.5
#         )

#     else:
#         score=0.0

#     return{
#         "score":score,
#         "reason":f"Khoảng cách trung bình = {round(avg,3)}."
#     }

# def template_22(rule, boxes_dict):

#     text=rule["rule"].split()

#     obj1=text[1]
#     obj2=text[2]
#     obj3=text[3]
#     direction=text[4]

#     if (
#         obj1 not in boxes_dict
#         or obj2 not in boxes_dict
#         or obj3 not in boxes_dict
#         or len(boxes_dict[obj1])==0
#         or len(boxes_dict[obj2])==0
#         or len(boxes_dict[obj3])==0
#     ):
#         return{
#             "score":0.0,
#             "reason":"Thiếu đối tượng."
#         }

#     c1=get_center(boxes_dict[obj1][0]["box"])
#     c2=get_center(boxes_dict[obj2][0]["box"])
#     c3=get_center(boxes_dict[obj3][0]["box"])

#     if direction=="ltr":

#         if c1[0]<c2[0]<c3[0]:
#             score=1.0
#         else:
#             score=max(
#                 0.0,
#                 1
#                 -(0.5 if c1[0]>=c2[0] else 0)
#                 -(0.5 if c2[0]>=c3[0] else 0)
#             )

#     elif direction=="ttb":

#         if c1[1]<c2[1]<c3[1]:
#             score=1.0
#         else:
#             score=max(
#                 0.0,
#                 1
#                 -(0.5 if c1[1]>=c2[1] else 0)
#                 -(0.5 if c2[1]>=c3[1] else 0)
#             )

#     else:
#         score=0.0

#     return{
#         "score":score,
#         "reason":f"Thứ tự {obj1} → {obj2} → {obj3}."
#     }
# ==========================================
# 6. TEMPLATE LOGIC SUY DIỄN (KIỂM SOÁT LUẬT)
# ==========================================
def template_12(rule, boxes_dict): #tạm oke

    text = rule["rule"].split()

    obj_if = text[2]
    obj_then = text[5]
    obj_if_vi = SCENERY_OBJECT_VI.get(obj_if, obj_if)
    obj_then_vi = SCENERY_OBJECT_VI.get(obj_then, obj_then)     
    has_if = obj_if in boxes_dict and len(boxes_dict[obj_if]) > 0
    has_then = obj_then in boxes_dict and len(boxes_dict[obj_then]) > 0

    # if not has_if:
    #     return {
    #         "score": 1.0,
    #         "reason": f"Không có {obj_if}, luật không áp dụng."
    #     }

    # if has_then:
    #     return {
    #         "score": 1.0,
    #         "reason": f"Có {obj_if} và cũng có {obj_then}."
    #     }

    # return {
    #     "score": 0.0,
    #     "reason": f"Có {obj_if} nhưng thiếu {obj_then}."
    # }
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

# def template_13(rule, boxes_dict):

#     text = rule["rule"].split()

#     modality = text[0]
#     obj = text[2]

#     has_obj = obj in boxes_dict and len(boxes_dict[obj]) > 0

#     if modality == "must":

#         if has_obj:
#             score = 1.0
#             reason = f"Đã phát hiện {obj}."
#         else:
#             score = 0.0
#             reason = f"Thiếu {obj}."

#     elif modality == "may":

#         if has_obj:
#             score = 1.0
#             reason = f"Có thêm {obj} (điểm thưởng)."
#         else:
#             score = -1.0
#             reason = f"Không có {obj} nhưng không bị trừ điểm."

#     else:
#         score = 0.0
#         reason = "Luật không hợp lệ."

#     return {
#         "score": score,
#         "reason": reason
#     }

# def template_14(rule, boxes_dict):

#     text = rule["rule"].split()

#     obj1 = text[1]
#     obj2 = text[2]

#     has1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
#     has2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0

#     if has1 and has2:
#         score = 0.0
#         reason = f"Có cả {obj1} và {obj2}."

#     elif has1 or has2:
#         score = 1.0
#         reason = "Chỉ có một trong hai đối tượng."

#     else:
#         score = 0.0
#         reason = f"Không có {obj1} và {obj2}."

#     return {
#         "score": score,
#         "reason": reason
#     }
# def template_15(rule, boxes_dict):

#     text = rule["rule"].split()

#     obj1 = text[1]
#     obj2 = text[2]

#     has1 = obj1 in boxes_dict and len(boxes_dict[obj1]) > 0
#     has2 = obj2 in boxes_dict and len(boxes_dict[obj2]) > 0

#     score = 1.0 if has1 == has2 else 0.0

#     if score:
#         reason = f"{obj1} và {obj2} đồng thời xuất hiện hoặc đồng thời vắng mặt."
#     else:
#         reason = f"{obj1} và {obj2} không đồng hành."

#     return {
#         "score": score,
#         "reason": reason
#     }
def template_16(rule, boxes_dict): # thanh công phân nữa
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
def template_17(rule, boxes_dict):

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
        "size": template_4,
        # "pos_abs": template_5,
        "pos_rel": template_6,
        # "ratio": template_7,
        # "distance": template_8,
        # "align": template_9,
        # "coverage": template_10,
        # "attribute": template_11,
        "if_then": template_12,
        # "priority": template_13,
        # "xor": template_14,
        # "together": template_15,
        "count_comp": template_16,
        "size_comp": template_17,
    #     "interaction": template_18,
    #     "qty_cond": template_19,
    #     "dist_exact": template_20,
    #     "distribution": template_21,
    #     "sequence": template_22
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