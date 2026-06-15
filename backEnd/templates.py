def template_0(rule, boxes_dict): # V + N
	text = rule["rule"].split()
	if text[0] == "có":
		return text[1] in boxes_dict
	elif text[0] == "không":
		return text[1] not in boxes_dict

def template_1(rule, boxes_dict): # V + N + C + N
	text = rule["rule"].split()
	if text[0] == "có":
		if text[2] == "và":
			return text[1] in boxes_dict and text[3] in boxes_dict
		if text[2] == "hoặc":
			return text[1] in boxes_dict or text[3] in boxes_dict
	elif text[0] == "không":
		if text[2] == "và":
			return text[1] not in boxes_dict and text[3] not in boxes_dict
		if text[2] == "hoặc":
			return text[1] not in boxes_dict or text[3] not in boxes_dict