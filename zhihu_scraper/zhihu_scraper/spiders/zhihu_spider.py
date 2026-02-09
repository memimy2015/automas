import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import json
import time

class ZhihuArticleSpider(scrapy.Spider):
    name = 'zhihu_article'
    allowed_domains = ['zhuanlan.zhihu.com', 'www.zhihu.com']
    
    def start_requests(self):
        # 先访问知乎首页
        yield SeleniumRequest(
            url='https://www.zhihu.com/',
            callback=self.parse_homepage,
            wait_time=5,
            script='window.scrollTo(0, document.body.scrollHeight);'
        )
    
    def parse_homepage(self, response):
        # 等待首页加载完成
        driver = response.meta['driver']
        time.sleep(2)
        
        # 访问目标文章
        yield SeleniumRequest(
            url='https://zhuanlan.zhihu.com/p/1999034708332405397',
            callback=self.parse_article,
            wait_time=10,
            script='window.scrollTo(0, document.body.scrollHeight);'
        )
    
    def parse_article(self, response):
        driver = response.meta['driver']
        
        # 等待标题元素出现
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Post-Title'))
        )
        
        # 滚动页面加载更多内容
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        
        # 获取页面源代码
        page_source = driver.page_source
        
        # 提取标题
        title = driver.find_element(By.CLASS_NAME, 'Post-Title').text if driver.find_elements(By.CLASS_NAME, 'Post-Title') else '无标题'
        
        # 提取副标题
        subtitle = ''
        if driver.find_elements(By.CLASS_NAME, 'Post-Subtitle'):
            subtitle = driver.find_element(By.CLASS_NAME, 'Post-Subtitle').text
        else:
            subtitle = '无副标题'
        
        # 提取作者信息
        author = '未知作者'
        if driver.find_elements(By.CLASS_NAME, 'UserLink-link'):
            author = driver.find_element(By.CLASS_NAME, 'UserLink-link').text
        
        # 提取发布时间
        publish_time = '未知时间'
        if driver.find_elements(By.CLASS_NAME, 'Post-Meta-Item'):
            time_elements = driver.find_elements(By.CLASS_NAME, 'Post-Meta-Item')
            for element in time_elements:
                if '发布于' in element.text:
                    publish_time = element.text
                    break
        
        # 提取正文内容
        content_paragraphs = []
        if driver.find_elements(By.CLASS_NAME, 'Post-RichText'):
            content_div = driver.find_element(By.CLASS_NAME, 'Post-RichText')
            elements = content_div.find_elements(By.XPATH, './/*[self::p or self::blockquote or self::pre or self::h2 or self::h3 or self::h4 or self::ul or self::ol]')
            
            for element in elements:
                tag_name = element.tag_name
                text = element.text.strip()
                
                if not text:
                    continue
                    
                if tag_name == 'p':
                    content_paragraphs.append({
                        'type': 'paragraph',
                        'content': text
                    })
                elif tag_name == 'blockquote':
                    content_paragraphs.append({
                        'type': 'quote',
                        'content': text
                    })
                elif tag_name == 'pre':
                    content_paragraphs.append({
                        'type': 'code',
                        'content': text
                    })
                elif tag_name in ['h2', 'h3', 'h4']:
                    content_paragraphs.append({
                        'type': 'heading',
                        'level': tag_name,
                        'content': text
                    })
                elif tag_name in ['ul', 'ol']:
                    list_items = []
                    li_elements = element.find_elements(By.TAG_NAME, 'li')
                    for li in li_elements:
                        li_text = li.text.strip()
                        if li_text:
                            list_items.append(li_text)
                    if list_items:
                        content_paragraphs.append({
                            'type': 'list',
                            'content': list_items
                        })
        
        # 提取统计数据
        stats = {}
        
        # 点赞数
        if driver.find_elements(By.CLASS_NAME, 'VoteButton--up'):
            vote_count = driver.find_element(By.CLASS_NAME, 'VoteButton--up').text.strip()
            if vote_count:
                stats['vote_count'] = vote_count
        
        # 评论数
        if driver.find_elements(By.CLASS_NAME, 'CommentCount'):
            comment_count = driver.find_element(By.CLASS_NAME, 'CommentCount').text.strip()
            if comment_count:
                stats['comment_count'] = comment_count
        
        # 收藏数
        if driver.find_elements(By.CLASS_NAME, 'BookmarkButton'):
            collect_count = driver.find_element(By.CLASS_NAME, 'BookmarkButton').text.strip()
            if collect_count:
                stats['collect_count'] = collect_count
        
        # 提取专栏信息
        column_info = {}
        if driver.find_elements(By.CLASS_NAME, 'Post-Meta-Column'):
            column_element = driver.find_element(By.CLASS_NAME, 'Post-Meta-Column')
            column_info['name'] = column_element.text.strip()
            column_info['url'] = column_element.get_attribute('href')
        
        # 整理结果
        result = {
            'title': title,
            'subtitle': subtitle,
            'author': author,
            'publish_time': publish_time,
            'column_info': column_info,
            'stats': stats,
            'content': content_paragraphs
        }
        
        # 保存结果
        output_dir = '/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/output/'
        
        # 保存为JSON
        json_file = output_dir + 'zhihu_article_scrapy.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 保存为文本
        text_file = output_dir + 'zhihu_article_scrapy.txt'
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"标题: {title}\n\n")
            if subtitle != '无副标题':
                f.write(f"副标题: {subtitle}\n\n")
            f.write(f"作者: {author}\n")
            f.write(f"发布时间: {publish_time}\n")
            if column_info:
                f.write(f"专栏: {column_info['name']} ({column_info['url']})\n\n")
            
            if stats:
                f.write("文章数据:\n")
                for key, value in stats.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            f.write("正文内容:\n")
            f.write("-" * 50 + "\n")
            for item in content_paragraphs:
                if item['type'] == 'paragraph':
                    f.write(f"{item['content']}\n\n")
                elif item['type'] == 'quote':
                    f.write(f"【引用】{item['content']}\n\n")
                elif item['type'] == 'code':
                    f.write(f"【代码】\n{item['content']}\n\n")
                elif item['type'] == 'heading':
                    f.write(f"\n{item['content']}\n")
                    f.write("=" * len(item['content']) + "\n")
                elif item['type'] == 'list':
                    f.write("\n【列表】\n")
                    for i, item_text in enumerate(item['content'], 1):
                        f.write(f"  {i}. {item_text}\n")
                    f.write("\n")
        
        self.logger.info(f"爬取完成！结果已保存到:\n{json_file}\n{text_file}")
        yield result