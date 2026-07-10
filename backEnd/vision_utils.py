import numpy as np
import math
import cv2

def get_center_abs(box):
    """Lấy tâm của bounding box [xmin, ymin, xmax, ymax]"""
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

def get_area_abs(box):
    """Tính diện tích bounding box"""
    return (box[2] - box[0]) * (box[3] - box[1])


def phan_tich_mau_sac(img_cv):
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
    
    return " ".join(nhan_xet) if nhan_xet else "Màu sắc kết hợp rất hài hòa và dịu mắt."

def kiem_tra_bo_cuc_tong_the(boxes_xyxy, img_w, img_h):
    if not boxes_xyxy:
        return ["Tranh trống hoặc nét mờ quá, thầy/cô không chấm được bố cục."]
    min_x, min_y = min([b[0] for b in boxes_xyxy]), min([b[1] for b in boxes_xyxy])
    max_x, max_y = max([b[2] for b in boxes_xyxy]), max([b[3] for b in boxes_xyxy])
    ty_le = ((max_x - min_x) * (max_y - min_y)) / (img_w * img_h)
    
    loi = []
    if ty_le < 0.05:
        loi.append("Lỗi tỷ lệ: Hình vẽ bị quá nhỏ và lọt thỏm giữa tờ giấy. Hãy vẽ to và tự tự lên cục dàng!")
    elif ty_le > 0.85:
        loi.append("Lỗi lề: Em vẽ hình to quá bị chạm vào sát mép giấy, bức tranh nhìn hơi chật chội rồi cưng ơi.")
    if abs(((min_x + max_x) / 2) - (img_w / 2)) > (img_w * 0.15):
        loi.append("Lỗi xô lệch: Trọng tâm hình vẽ đang bị lệch hẳn sang một bên, chưa căn giữa.")
    
    return loi if loi else ["Tuyệt vời! Bố cục cân đối, nằm ngay ngắn, amazing good job em!"]

def luat_ty_le_chan_dung(boxes_dict):
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
        if abs(((noses[0][0] + noses[0][2]) / 2) - ((mouths[0][0] + mouths[0][2]) / 2)) > (mouths[0][2] - mouths[0][0]) * 0.2:
            nhan_xet.append("Mũi và miệng chưa thẳng hàng dọc em nha!")
            
    eb, ey = boxes_dict.get("eyebrow", []), boxes_dict.get("eye", [])
    if eb and ey:
        if (((ey[0][1] + ey[0][3]) / 2) - ((eb[0][1] + eb[0][3]) / 2)) > (ey[0][3] - ey[0][1]) * 2.5:
            nhan_xet.append("Lông mày em vẽ cao quá, nhìn nhân vật như đang giật mình vậy.")
            
    ears = boxes_dict.get("ear", [])
    if ears and ey:
        ear_y = (ears[0][1] + ears[0][3]) / 2
        eye_y = (ey[0][1] + ey[0][3]) / 2
        if abs(ear_y - eye_y) > (ey[0][3] - ey[0][1]) * 1.5:
            nhan_xet.append("Vị trí tai đang bị vẽ lệch lên quá cao hoặc thấp hơn so với mắt khá nhiều.")
    
    return nhan_xet if nhan_xet else ["Tỷ lệ tốt!"]

def phan_tich_nghe_thuat_phong_canh(boxes_dict, img_w, img_h):
    nhan_xet = []
    h, t, s = boxes_dict.get("house", []), boxes_dict.get("tree", []), boxes_dict.get("sun", [])
    
    if h and t:
        if h[0][3] < t[0][3]:
            nhan_xet.append("Lưu ý luật xa gần: Nhà ở gần nên vẽ thấp hơn cây ở xa em nha!")
        else:
            nhan_xet.append("Em đã áp dụng rất tốt quy luật xa gần, amazing good job!")
        
    if h:
        hx = (h[0][0] + h[0][2]) / 2
        if (img_w * 0.25) < hx < (img_w * 0.75):
            nhan_xet.append("Nhà đặt ở trung tâm làm điểm nhấn rất tốt!")
        else:
            nhan_xet.append("Ngôi nhà đặt lệch tạo quy tắc 1/3 rất nghệ thuật, đáng khen đó bảo bối.")
        
    if h and s:
        sun_area = (s[0][2] - s[0][0]) * (s[0][3] - s[0][1])
        house_area = (h[0][2] - h[0][0]) * (h[0][3] - h[0][1])
        if sun_area > house_area:
            nhan_xet.append("Ông mặt trời em vẽ to hơn cả ngôi nhà kìa, thử vẽ nhỏ lại chút xíu cho cảnh vật thật hơn nhé!")
    
    return nhan_xet if nhan_xet else ["Bố cục nghệ thuật tốt!"]