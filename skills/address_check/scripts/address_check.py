import os
from openai import OpenAI
import sys

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
# 初始化Ark客户端，从环境变量中读取您的API Key
client = OpenAI(
    # 此为默认路径，您可根据业务所在地域进行配置
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
    api_key=os.environ.get("ARK_API_KEY"),
)

def guess_city(image_url):
    response = client.chat.completions.create(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model="doubao-seed-1-6-vision-250815",
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        },
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "阅读图片，猜测图片中的风景所属的城市，仅返回城市名称，不要有解释信息。"},
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        },
                    }
                ],
            }
        ],
    )
    return response.choices[0].message.content


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("错误：请提供一个图片地址")
        print("示例: python address.py https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg")
        sys.exit(1)
    
    date_str = sys.argv[1]
    address = guess_city(date_str)
    print(address)


if __name__ == "__main__":
    main()
