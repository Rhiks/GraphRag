import os, sys
import oss2
#from video import config_loader
#import config_loader
import cv2
import io
import numpy as np
import time

#region = config_loader.region
#endpoint = config_loader.endpoint
#bucket_name = config_loader.bucket_name
#access_key_id = config_loader.access_key_id
#access_key_secret = config_loader.access_key_secret

region="cn-beijing"
bucket_name="aixuexi-sjyy"
endpoint="oss-cn-beijing.aliyuncs.com"
access_key_id=os.environ.get("ALIYUN_ACCESS_KEY_ID", "")
access_key_secret=os.environ.get("ALIYUN_ACCESS_KEY_SECRET", "")

#app_key=APP_KEY_REPLACE_ME
#file_link_pre=https://aixuexi-sjyy.oss-cn-beijing.aliyuncs.com/

# 使用获取的RAM用户的访问密钥配置访问凭证
auth = oss2.AuthV4(access_key_id, access_key_secret)
# 填写Bucket名称。
bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)

def put_object(audio_file_path, audio_oss_path):
    # logger.info(f"put_object start {audio_file_path}")
    # 必须以二进制的方式打开文件。
    # 填写本地文件的完整路径。如果未指定本地路径，则默认从示例程序所属项目对应本地路径中上传文件。
    with open(audio_file_path, 'rb') as file_obj:
        # 填写Object完整路径。Object完整路径中不能包含Bucket名称。
        bucket.put_object(audio_oss_path, file_obj)
    # logger.info(f"put_object end {audio_file_path}")


def put_object_cv(bgr_im, audio_oss_path):

    # 必须以二进制的方式打开文件。
    # 填写本地文件的完整路径。如果未指定本地路径，则默认从示例程序所属项目对应本地路径中上传文件。
    #with open(audio_file_path, 'rb') as file_obj:
        # 填写Object完整路径。Object完整路径中不能包含Bucket名称。
    try:
        bgr_data = bgr_im.astype(np.uint8)
        _, buffer = cv2.imencode('.jpg', bgr_data)

        #image_stream = io.BytesIO(buffer)
        with io.BytesIO(buffer) as image_stream:

            result = bucket.put_object(audio_oss_path, image_stream.getvalue())
        del bgr_data
        if result.status == 200:
            return True
        else:
            return False
    except Exception as e:
        print (f"上传图片超时:{e}")
        return False
    

if __name__ == "__main__":
    # 使用示例
    #file_path = 'file/segment_000.mp3'
    #oss_path = "attention/mp3/" + file_path
    file_path = '/data/shell/reserve_imgs/0_3525974.0_8654209.0_50201788.0.jpg'
    bgr_im = cv2.imread(file_path)
    #pdb.set_trace()
    t0 = time.time()
    #oss_path = "attention_cv/1719/1720/check/" + os.path.basename(file_path)
    oss_path = "blanks_recog/1719/1720/check/" + os.path.basename(file_path)
    #res_logic = put_object_cv(bgr_im, oss_path)
    put_object_cv(bgr_im, oss_path)
    #print ("result: res_logic: ", res_logic)
    t1 = time.time()
    print (f"use time: {np.round(t1-t0, 4)}s")
