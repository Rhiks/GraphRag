import cv2
import numpy as np
import re


def filter_colors_by_hsv(image):
    """
    根据指定的HSV色域范围过滤图像，只保留蓝色、绿色和黑色
    在统计非白色像素之前对图像进行预处理

    Args:
        image: BGR格式的输入图像

    Returns:
        filtered_image: 过滤后的BGR图像，非指定颜色的像素变为白色
    """
    # 定义颜色范围 (HSV格式)
    color_ranges = {
        "blue": ((100, 50, 50), (130, 255, 255)),
        "green": ((35, 50, 50), (85, 255, 255)),
        "black": ((0, 0, 0), (180, 255, 30)),
    }

    # 转换为HSV颜色空间
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 创建掩码，初始化为全False
    combined_mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)

    # 为每种颜色创建掩码并合并
    for color_name, (lower, upper) in color_ranges.items():
        lower_bound = np.array(lower)
        upper_bound = np.array(upper)
        mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # 创建结果图像，非指定颜色的像素设为白色
    result_image = image.copy()
    result_image[combined_mask == 0] = [255, 255, 255]  # 将非指定颜色设为白色

    return result_image


def split_lines_and_draw(color_image):
    sorted_line_images = {}
    sorted_line_coords = {}
    original_color_image = color_image
    image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = np.ones((9, 175), np.uint8)
    dilated = cv2.dilate(binary, kernel)

    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    line_images = []
    line_coords = []
    areas = [cv2.contourArea(contour) for contour in contours]
    if areas:
        max_area = max(areas)
        min_area_threshold = max_area / 25

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area_threshold:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if h > 15 and h / w < 1:
                line_image = original_color_image[y : y + h, x : x + w]
                line_images.append(line_image)
                line_coords.append((x, y, w, h))
    # line_coords = sorted(line_coords, key=lambda coord: coord[1])
    # 替换原有的 refine_large_boxes 调用
    line_coords = refine_abnormal_boxes(line_coords, original_color_image)
    while True:
        has_merged = False
        new_boxes = []
        used_indices = set()

        for i, (x1, y1, w1, h1) in enumerate(line_coords):
            if i in used_indices:
                continue
            base_box = (x1, y1, w1, h1)

            for j, (x2, y2, w2, h2) in enumerate(line_coords):
                if i == j or j in used_indices:
                    continue

                xi1 = max(x1, x2)
                yi1 = max(y1, y2)
                xi2 = min(x1 + w1, x2 + w2)
                yi2 = min(y1 + h1, y2 + h2)
                overlap_width = max(0, xi2 - xi1)
                overlap_height = max(0, yi2 - yi1)
                overlap_area = overlap_width * overlap_height

                area1 = w1 * h1
                area2 = w2 * h2

                min_area = min(area1, area2)
                max_area = max(area1, area2)
                # 计算面积比
                area_ratio = min_area / max_area if max_area > 0 else 0

                # 按面积比动态调整重叠阈值
                if abs(y1 - y2) < 100:
                    overlap_thresh = 0.1
                else:
                    if area_ratio > 0.2:
                        overlap_thresh = 0.8
                    else:
                        overlap_thresh = 0.1

                if overlap_area > overlap_thresh * min(area1, area2):
                    base_box = (
                        min(x1, x2),
                        min(y1, y2),
                        max(x1 + w1, x2 + w2) - min(x1, x2),
                        max(y1 + h1, y2 + h2) - min(y1, y2),
                    )
                    used_indices.add(j)
                    has_merged = True

            new_boxes.append(base_box)
            used_indices.add(i)

        line_coords = new_boxes
        if not has_merged:
            break

    origin_image_width = original_color_image.shape[1]
    line_coords = group_by_column(line_coords, origin_image_width)
    # print("line_coords =", line_coords)
    for line_idx, (x, y, w, h) in enumerate(line_coords):
        # 计算外扩5%的像素数
        expand_w = int(w * 0.1)
        expand_h = int(h * 0.1)
        # 计算新的坐标，确保不超出原图边界
        x1 = max(0, x - expand_w)
        y1 = max(0, y - expand_h)
        x2 = min(original_color_image.shape[1], x + w + expand_w)
        y2 = min(original_color_image.shape[0], y + h + expand_h)
        sorted_line_images[line_idx] = original_color_image[y1:y2, x1:x2]
    sorted_line_coords["0"] = line_coords
    return sorted_line_images, sorted_line_coords


def group_by_column(coords, origin_image_width, x_threshold=450):
    if not coords:
        return []
    # 先按x从小到大排序
    coords = sorted(coords, key=lambda c: c[0])
    columns = []
    column_idx = 0
    temp_columns = []
    for coord in coords:
        x, y, w, h = coord
        if w > origin_image_width * 0.7 or (x < 200 and y < 400):
            # print("origin_coord =", coord)
            if not temp_columns:
                temp_columns.append([coord])
            else:
                temp_columns[0].append(coord)
            continue  # 跳过后续分列逻辑

        placed = False
        for col in columns:
            # 判断是否属于当前列
            # if abs((col[0][0]+col[0][2]/2) - (x+w/2)) < x_threshold:
            if abs(col[0][0] - x) < x_threshold:
                # print("col =", col)
                col.append(coord)
                placed = True
                break
        if not placed:
            columns.append([coord])
            column_idx += 1
    # 每列内按y排序
    # print("temp_columns =", temp_columns)
    # print("columns =", columns)
    if temp_columns != [] and columns != []:
        columns[0] = temp_columns[0] + columns[0]
    elif temp_columns != [] and columns == []:
        columns = temp_columns
    # print("columns =", columns)
    for col in columns:
        col.sort(key=lambda c: c[1])
    # 所有列按x排序
    columns.sort(key=lambda col: col[0][0])
    # 拼接所有列
    sorted_coords = []
    for col in columns:
        sorted_coords.extend(col)
    return sorted_coords


# 检查是否有高度异常的框，递归细分
def refine_abnormal_boxes(line_coords, original_color_image):
    refined_coords = list(line_coords)
    max_iter = 10
    iter_cnt = 0
    # while True:
    iter_cnt += 1
    if len(refined_coords) <= 1:
        return line_coords
    heights = [h for (x, y, w, h) in refined_coords]
    abnormal_indices = []
    for idx, (x, y, w, h) in enumerate(refined_coords):
        other_heights = heights[:idx] + heights[idx + 1 :]
        if not other_heights:
            continue
        avg_other_h = sum(other_heights) / len(other_heights)
        if h > 2 * avg_other_h:
            abnormal_indices.append((idx, (x, y, w, h)))
            new_coords = [
                box for i, box in enumerate(refined_coords) if i not in abnormal_indices
            ]
            refined_coords = new_coords
    # print("abnormal_indices =", abnormal_indices)
    if not abnormal_indices:
        return line_coords
    new_coords = []
    last_idx = 0
    any_found_new = False
    for idx, (x, y, w, h) in abnormal_indices:
        new_coords.extend(refined_coords[last_idx:idx])
        sub_img = original_color_image[y : y + h, x : x + w]
        sub_gray = cv2.cvtColor(sub_img, cv2.COLOR_BGR2GRAY)
        _, sub_binary = cv2.threshold(
            sub_gray, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        kernels = [(2, 70)]
        prev_boxes = [(0, 0, w, h)]
        found_new = False
        for kernel_size in kernels:
            kernel = np.ones(kernel_size, np.uint8)
            sub_dilated = cv2.dilate(sub_binary, kernel)
            sub_contours, _ = cv2.findContours(
                sub_dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
            )
            sub_boxes = []
            for contour in sub_contours:
                sx, sy, sw, sh = cv2.boundingRect(contour)
                if sh > 15 and sh / sw < 1:
                    sub_boxes.append((sx, sy, sw, sh))
            sub_boxes_offset = [
                (x + sx, y + sy, sw, sh) for (sx, sy, sw, sh) in sub_boxes
            ]
            # 如果细分结果和原框一致，继续下一个kernel
            if (
                len(sub_boxes_offset) == 1
                and sub_boxes_offset[0][2:] == prev_boxes[0][2:]
            ):
                prev_boxes = sub_boxes_offset
                continue
            elif len(sub_boxes_offset) > 1 or (
                len(sub_boxes_offset) == 1
                and sub_boxes_offset[0][2:] != prev_boxes[0][2:]
            ):
                new_coords.extend(sub_boxes_offset)
                found_new = True
                any_found_new = True
                # print("new_coords =", new_coords)
        if not found_new:
            new_coords.append((x, y, w, h))
        last_idx = idx + 1
    new_coords.extend(refined_coords[last_idx:])
    # if not any_found_new:
    #     break
    refined_coords = new_coords
    # print("refined_coords =", refined_coords)
    return refined_coords


def extract_main_model_result(raw_result):
    # 匹配包含“结果:”的那一行，并取冒号后面的内容
    match = re.search(r"结果[：:]\s*(.*)", raw_result)
    if not match:
        return raw_result
    result_str = match.group(1).strip()
    return result_str
