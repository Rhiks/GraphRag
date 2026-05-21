from skimage.feature import hog
from skimage import exposure
import cv2
def extract_hog_features(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (128, 128))  # 标准化大小
    features, _ = hog(img, orientations=8, pixels_per_cell=(16,16),
                     cells_per_block=(1,1), visualize=True)
    return features

# 计算两个手写字符的HOG特征余弦相似度
features1 = extract_hog_features("handwritten_s.jpg")
features2 = extract_hog_features("handwritten_5.jpg")
similarity = np.dot(features1, features2) / (np.linalg.norm(features1) * np.linalg.norm(features2))
print(f"HOG特征相似度: {similarity:.2f}")
