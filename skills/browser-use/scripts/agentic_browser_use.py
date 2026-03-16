from browser_use.llm import ChatOpenAI
from browser_use import Agent, Browser, ChatBrowserUse
import asyncio
import os
import sys

import logging

# logging.getLogger("browser_use").setLevel(logging.WARNING)
# logging.getLogger("playwright").setLevel(logging.WARNING)
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("openai").setLevel(logging.WARNING)
# logging.getLogger("browser_use.browser").setLevel(logging.WARNING)
# logging.getLogger("bubus").disabled = True
# logging.getLogger("cdp_use.client").disabled = True

db = ChatOpenAI(
    model=os.getenv("MODEL"),
    api_key=os.getenv("ARK_API_KEY"),
    base_url=os.getenv("ARK_BASE_URL"),
)


async def main(task: str):
    browser = Browser(
        # use_cloud=True,  # Use a stealth browser on Browser Use Cloud
    )

    agent = Agent(
        task=task,
        llm=db,
        browser=browser,
        use_vision=True,
        # use_thinking=True,
    )
    output = await agent.run()
    print(f"Task: {task}\nFinal Results: {output.model_actions()[-1]}")
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide a task as an argument.")
    else:
        task = sys.argv[1]
    asyncio.run(main(task))

# task: 访问bilibili，搜索jnu，告诉我播放量最高的视频是什么  
# AgentHistoryList(all_results=[ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory='Navigated to https://www.bilibili.com/', extracted_content='🔗 Navigated to https://www.bilibili.com/', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory="Typed 'jnu'", extracted_content="Typed 'jnu'", include_extracted_content_only_once=False, metadata={'input_x': 941.0, 'input_y': 33.0}, include_in_memory=False), ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory='Sent keys: Enter', extracted_content='Sent keys: Enter', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory=None, extracted_content='Clicked svg. Note: This opened a new tab (tab_id: 1745) - switch to it if you need to interact with the new page.', include_extracted_content_only_once=False, metadata={'click_x': 1197.0, 'click_y': 33.0}, include_in_memory=False), ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory='Switched to tab #DD1A', extracted_content='Switched to tab #DD1A', include_extracted_content_only_once=False, metadata=None, include_in_memory=False), ActionResult(is_done=False, success=None, judgement=None, error=None, attachments=None, images=None, long_term_memory=None, extracted_content='Clicked button "最多播放"', include_extracted_content_only_once=False, metadata={'click_x': 256.0, 'click_y': 263.0}, include_in_memory=False), ActionResult(is_done=True, success=True, judgement=JudgementResult(reasoning='用户任务的关键要点为：1. 访问B站官网；2. 在搜索框输入“jnu”并执行搜索；3. 筛选出播放量最多的视频并获取其信息。agent成功导航到B站首页，在搜索框输入“jnu”并提交搜索，切换到搜索结果页面后，点击“最多播放”排序选项，成功获取到播放量最高的视频的标题、播放量、发布者和发布时间信息。工具使用方面，导航、输入、点击、切换标签页等操作均有效执行，无工具失败情况。输出结果完整准确，匹配用户需求，所有任务要点均完成，用户需求得到满足。', verdict=True, failure_reason='', impossible_task=False, reached_captcha=False), error=None, attachments=[], images=None, long_term_memory='Task completed: True - 在B站搜索jnu后，找到播放量最高的视频为：\n标题：Win11升级后连不上校园网？快看这里！（暨南大学校园网 JNU-Secure）\n播放量：9.9万\n发布者：DoodleHimi\n发布时间：2021 - 6 more characters', extracted_content='在B站搜索jnu后，找到播放量最高的视频为：\n标题：Win11升级后连不上校园网？快看这里！（暨南大学校园网 JNU-Secure）\n播放量：9.9万\n发布者：DoodleHimi\n发布时间：2021-11-06', include_extracted_content_only_once=False, metadata=None, include_in_memory=False)], all_model_outputs=[{'navigate': {'url': 'https://www.bilibili.com/', 'new_tab': False}, 'interacted_element': None}, {'input': {'index': 52, 'text': 'jnu', 'clear': True}, 'interacted_element': DOMInteractedElement(node_id=162, backend_node_id=52, frame_id=None, node_type=<NodeType.ELEMENT_NODE: 1>, node_value='', node_name='INPUT', attributes={'class': 'nav-search-input', 'type': 'text', 'autocomplete': 'off', 'accesskey': 's', 'maxlength': '100', 'x-webkit-speech': '', 'x-webkit-grammar': 'builtin:translate', 'value': '', 'placeholder': '姜姜安徽找磊哥复合', 'title': '姜姜安徽找磊哥复合'}, bounds=DOMRect(x=736.0, y=23.0, width=410.0, height=20.0), x_path='html/body/div[2]/div[2]/div[1]/div[1]/div/div/form/div[1]/input', element_hash=8037800593336365097, stable_hash=8037800593336365097, ax_name='姜姜安徽找磊哥复合')}, {'send_keys': {'keys': 'Enter'}, 'interacted_element': None}, {'click': {'index': 10}, 'interacted_element': DOMInteractedElement(node_id=4822, backend_node_id=10, frame_id=None, node_type=<NodeType.ELEMENT_NODE: 1>, node_value='', node_name='svg', attributes={'width': '17', 'height': '17', 'viewBox': '0 0 17 17', 'fill': 'none', 'xmlns': 'http://www.w3.org/2000/svg'}, bounds=DOMRect(x=1188.5, y=24.5, width=17.0, height=17.0), x_path='html/body/div[2]/div[2]/div[1]/div[1]/div/div/form/div[2]/svg', element_hash=761130674863377905, stable_hash=14596188730145541611, ax_name=None)}, {'switch': {'tab_id': 'DD1A'}, 'interacted_element': None}, {'click': {'index': 3410}, 'interacted_element': DOMInteractedElement(node_id=462, backend_node_id=3410, frame_id=None, node_type=<NodeType.ELEMENT_NODE: 1>, node_value='', node_name='BUTTON', attributes={'class': 'vui_button vui_button--tab mr_sm', 'data-v-33652d7a': ''}, bounds=DOMRect(x=206.0, y=247.0, width=100.0, height=32.0), x_path='html/body/div[3]/div/div[2]/div[1]/div[3]/div/div[1]/div/button[2]', element_hash=599235992144769002, stable_hash=12977109875429752365, ax_name='最多播放')}, {'done': {'text': '在B站搜索jnu后，找到播放量最高的视频为：\n标题：Win11升级后连不上校园网？快看这里！（暨南大学校园网 JNU-Secure）\n播放量：9.9万\n发布者：DoodleHimi\n发布时间：2021-11-06', 'success': True, 'files_to_display': []}, 'interacted_element': None}])