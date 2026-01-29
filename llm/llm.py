from volcenginesdkarkruntime import Ark
import os


api_key = os.environ.get("ARK_API_KEY")
model = os.environ.get("MODEL")

client = Ark(   
    base_url="https://ark.cn-beijing.volces.com/api/v3",  
    # base_url="https://api.deepseek.com/v1", 
    # 环境变量中配置您的API Key 
    api_key=api_key, 
)

def llm_call(messages: list, tools: list):
    """
    调用模型，返回模型的回复
    """
    resp = client.chat.completions.create(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model=model,
        stream=False,
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        },
        messages=messages,
        tools=tools,
    )
    return resp.choices[0].finish_reason, resp.choices[0].message