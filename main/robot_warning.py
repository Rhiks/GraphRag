import requests
import json

# 使用示例
webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=52e245f5-0d50-408f-afff-519e644066a6' 

def send_wechat_message(message, webhook_url=webhook_url):
    """
    发送微信消息到指定的Webhook URL

    :param webhook_url: 微信Webhook URL
    :param message: 要发送的消息内容
    """
    # Headers
    headers = {
        'Content-Type': 'application/json'
    }

    # Payload
    payload = {
        "msgtype": "text",
        "text": {
            "content": message,
            "mentioned_mobile_list":["15210960775"]
	
    		
        }
    }

    # Send the request
    response = requests.post(webhook_url, headers=headers, data=json.dumps(payload))

    # Check the response
    if response.status_code == 200:
        print('Message sent successfully')
    else:
        print(f'Failed to send message: {response.status_code}')
        print(response.text)


if __name__=="__main__":
    message = 'test'
    send_wechat_message(message)
    #send_ans_wechat_message(message)
