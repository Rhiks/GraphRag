import cv2
import pdb
import time
import re

def is_all_chinese_no_punctuation(text):
    pattern = re.compile(r'^[\u4e00-\u9fff]+$')
    return bool(pattern.fullmatch(text.replace(" ", "")))  # 忽略空格

def rm_duplicate_chi_chars(text):
    if is_all_chinese_no_punctuation(text):
        """
        去除字符串中连续重复的汉字字符
        示例：
            "甲申甲" -> "甲申甲"（不变）
            "家家神" -> "家神"
            "好好好" -> "好"
        """
        # 使用正则表达式匹配连续重复的汉字并替换为单个字符
        # [\u4e00-\u9fa5] 匹配所有中文字符
        # ([\u4e00-\u9fa5])\1+ 匹配连续重复的中文字符
        return re.sub(r'([\u4e00-\u9fa5])\1+', r'\1', text)
    return text

#print(rm_duplicate_chi_chars("甲申甲甲"))


def remove_duplicate_chinese_chars(content, input_string):
    """
    去除输入字符串中的重复汉字字符，然后与content比较
    
    参数:
        content (str): 用于比较的目标字符串
        input_string (str): 需要处理的输入字符串
    
    返回:
        str: 如果去重后与content相同则返回去重结果，否则返回原字符串
    """
    # 检查输入是否已经是content，如果是直接返回
    if input_string == content:
        return input_string
    
    # 提取所有汉字字符
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', input_string)
    
    # 去除重复汉字（保留顺序）
    seen = set()
    unique_chinese = []
    for char in chinese_chars:
        if char not in seen:
            seen.add(char)
            unique_chinese.append(char)
    
    # 重建字符串（保留非汉字字符和顺序）
    result = []
    chinese_iter = iter(unique_chinese)
    current_chinese = next(chinese_iter, None)
    
    for char in input_string:
        if not re.match(r'[\u4e00-\u9fa5]', char):
            # 非汉字字符直接保留
            result.append(char)
        else:
            if current_chinese is not None and char == current_chinese:
                result.append(char)
                current_chinese = next(chinese_iter, None)
    
    deduplicated_str = ''.join(result)
    
    # 比较去重后的字符串与content
    return deduplicated_str if deduplicated_str == content else input_string

def collected_near_words():
    similar_zx= {"摩":["麻", "鹰","廖"],
                 "匀":["勾","句","今"],
                 "速":["进"],
                 "直":["真","百","白"],
                 "线":["或"],
                 "成":["或"],
                 "或":["战","我"],
                 "止":["山"],
                 "等":["箭","熊", "寺"],
                 "增":["王曾", "土曾"],
                 "大":["十", "t", "火","士"],
                 "小":["卜", "仁", "卜","g"],
                 "于":["二","干","千","云","子","丁","尹"],
                 "天":["夫"],
                 "衡":["街"],
                 "减":["城"],
                 "上":["土"],
                 "升":["井", "4","开", "并", "41"],
                 "高":["亮"],
                 "低":["俗"],
                 "不":["T"],
                 "定":["宋"],
                 "变":["受", "董","恋", "艾", "弯","交", "友","辛"],
                 "甲":["军", "申","用","田"],
                 "丁":["了"],
                 "乙":["万","2"],
                 "丙":["西", "雨"],
                 "右":["石", "古","万"],
                 "无":["天", "石"],
                 "外":["夕"],
                 "关":["吴"],
                 "偏":["依"],
                 "度":["彦"],
                 "负":["员"],
                 "合":["台"],
                 "全":["住"],
                 "方":["台"],
                 "向":["何","句"],
                 "漂":["谭","漯"],
                 "浮":["源"],
                 "动":["纷"],
                 "阻":["阳"],
                 "部":["郭"],
                 "差":["美"],
                 "积":["和"],
                 "可":["才"],
                 "电":["由"],
                 "流":["污"],
                 "不":["石"],
                 "需":["富"],
                 "要":["安"],
                 "零":["露"],
                 "杯":["标"],
                 "互":["万"],
                 "吹":["欢"],
                 "气":["瓦"],
                 "音":["窗"],
                 "色":["包"],
                 "响":["白"],
                 "亮":["房"],
                 "放":["纹"],
                 "一":["-"],
                 "二":["="],
                 "五":["万"]
                }
    return similar_zx 

def find_best_replacement_optimized(recognized_word, standard_options, similarity_map):
    """
    优化版的相似词替换搜索，适用于大型similarity_map
    
    :param recognized_word: 识别结果，如"土4"
    :param standard_options: 标准答案可选项，如["上升", "下降", "不变"]
    :param similarity_map: 相似字映射，如{"上": ["土"], "升": ["井", "4", "开", "并"]}
    :return: 最佳匹配结果或原识别结果
    """
    # 预处理：构建反向映射 {相似字符: [标准字符1, 标准字符2]}
    reverse_map = {}
    for standard_char, similar_chars in similarity_map.items():
        for char in similar_chars:
            if char not in reverse_map:
                reverse_map[char] = []
            reverse_map[char].append(standard_char)
    #print ("reverse_map: ", reverse_map)
    
    #print ("reverse_map:", reverse_map)
    # 将标准答案转为集合加速查找
    standard_set = set(standard_options)
    
    # 检查原始词是否已经在标准答案中
    if recognized_word in standard_set:
        return recognized_word
    
    # 生成所有可能的单字符替换
    for i in range(len(recognized_word)):
        current_char = recognized_word[i]
        if current_char not in reverse_map:
            continue
        
        # 获取所有可以替换当前字符的标准字符
        for standard_char in reverse_map[current_char]:
            # 生成替换后的新词
            new_word = recognized_word[:i] + standard_char + recognized_word[i+1:]
            
            # 如果新词在标准答案中，立即返回
            if new_word in standard_set:
                return new_word
            if rm_duplicate_chi_chars(new_word) in standard_set:
                return rm_duplicate_chi_chars(new_word)
    
    # 如果没有单字符替换匹配，尝试双字符替换（可选）
    # 这可以根据需要开启，但会增加时间复杂度
    if len(recognized_word) >= 2:
        for i in range(len(recognized_word)):
            current_char1 = recognized_word[i]
            if current_char1 not in reverse_map:
                continue
                
            for j in range(i+1, len(recognized_word)):
                current_char2 = recognized_word[j]
                if current_char2 not in reverse_map:
                    continue
                
                # 双重替换
                for std_char1 in reverse_map[current_char1]:
                    for std_char2 in reverse_map[current_char2]:
                        new_word = (recognized_word[:i] + std_char1 + 
                                  recognized_word[i+1:j] + std_char2 + 
                                  recognized_word[j+1:])
                        
                        if new_word in standard_set:
                            return new_word
                        if rm_duplicate_chi_chars(new_word) in standard_set:
                            return rm_duplicate_chi_chars(new_word)
        # 连续双字符替换（检查当前字符和下一个字符）
        max_len = max(len(key) for key in reverse_map.keys()) if reverse_map else 0
        #print ("max_len: ", max_len)
        if max_len==2:
            candidates = set()
            for i in range(len(recognized_word)):
                current_char = recognized_word[i]
                if i < len(recognized_word) - 1:
                    next_char = recognized_word[i+1]
                    compound_key = current_char+next_char
                    if compound_key in reverse_map:
                        for replacement in reverse_map[compound_key]:
                            candidate = recognized_word[:i] + replacement + recognized_word[i+2:]
                            candidates.add(candidate)
            # 检查候选词中是否有直接匹配的标准答案
            for candidate in candidates:
                if candidate in standard_set:
                    return candidate
                if rm_duplicate_chi_chars(candidate) in standard_set:
                    return rm_duplicate_chi_chars(candidate)
 
    # 如果没有任何替换匹配，返回原始词
    return recognized_word

def collected_pair_options():
    pairs = [["需要","不需要"],
             ["变大","变小","不变"],
             ["升高","降低","不变"],
             ["大于","等于","小于"],
             ["低于","高于","等于"],
             ["甲","乙","丙","丁"], 
             ["减小","增大"], 
             ["上升","下降","不变"],
             ["右","左"], 
             ["偏大","偏小"], 
             ["有","无"],
             ["无关","有关"],
             ["成","不成"],
             ["升华","汽化","液化"],
             ["竖直向下","竖直向上"], 
             ["一","二","三","四","五","六","日"]]
    return pairs

def find_standard_options(word, pairs):
    if pairs is None:
        return [word]
    containing_lists = [lst for lst in pairs if word in lst]
    if containing_lists==[]:
        return [word]
    else:
    
    # 合并这些列表并去除重复项
        unique_elements = []
        seen = set()
        
        for lst in containing_lists:
            for item in lst:
                if item not in seen:
                    seen.add(item)
                    unique_elements.append(item)
    
    return unique_elements

def find_best_replacement_optimized_pipe(content, sting, similarity_map, pair_options):
    standard_options = find_standard_options(content, pair_options)
    if similarity_map == {}:
        return sting    
    #print (standard_options)
    optimized_string = find_best_replacement_optimized(sting, standard_options, similarity_map)
    return optimized_string           

if __name__=="__main__":
    # 示例使用
    #standard_options = ["上升", "下降", "不变"]
    #recognized_word = "土4"
    #recognized_word = "大尹"
    #print(find_standard_options("等于"))
    #similarity_map = collected_near_words()
    similarity_map = {}
    tt_options = None
    #tt_options = collected_pair_options()
    #pdb.set_trace()
    #t0 = time.time()
    #best_match = find_best_replacement_optimized(recognized_word, standard_options, similarity_map)
    #t1 = time.time()
    content = "下降"
    sting = "上移"
    best_match=find_best_replacement_optimized_pipe(content, sting, similarity_map, tt_options)
    #print (f"similarity_map: {t1-t0}s")
    #print(f"原始识别: {recognized_word}, 最佳匹配: {best_match}")
    print(f"原始识别: {sting}, 最佳匹配: {best_match}")
