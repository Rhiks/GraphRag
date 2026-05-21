import base64

# 原始数据
data = b"Hello, World!"

# 使用 urlsafe_b64encode 直接获取 URL-safe 编码
url_safe_encoded_data = base64.urlsafe_b64encode(data)

# 转换为字符串
url_safe_str = url_safe_encoded_data.decode('utf-8')

print(url_safe_str)



### 
import base64

# 读取文件并进行 Base64 编码
with open('your_image.jpg', 'rb') as f:
    img_data = base64.b64encode(f.read())

# 转换为 URL-safe Base64 编码
url_safe_img_data = base64.urlsafe_b64encode(f.read())
url_safe_str = url_safe_img_data.decode('utf-8')

print(url_safe_str)


import urllib.parse

# 假设这是经过 URL 编码的字符串
encoded_str = 'TWFu%20aW5nIGlzIG5vdCBoZXJlLgo%3D'

# 使用 urllib.parse.unquote() 进行解码
decoded_str = urllib.parse.unquote(encoded_str)

print(decoded_str)


