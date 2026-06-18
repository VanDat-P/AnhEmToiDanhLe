def template_0(rule, boxes_dict): # V + N
	text = rule["rule"].split()
	if text[0] == "have":
		return text[1] in boxes_dict
	elif text[0] == "not":
		return text[1] not in boxes_dict

def template_1(rule, boxes_dict): # V + N + C + N
	text = rule["rule"].split()
	if text[0] == "have":
		if text[2] == "and":
			return text[1] in boxes_dict and text[3] in boxes_dict
		if text[2] == "or":
			return text[1] in boxes_dict or text[3] in boxes_dict
	elif text[0] == "not":
		if text[2] == "and":
			return text[1] not in boxes_dict and text[3] not in boxes_dict
		if text[2] == "or":
			return text[1] not in boxes_dict or text[3] not in boxes_dict

def template_2(rule, boxes_dict):
	text = rule["rule"].split()
	