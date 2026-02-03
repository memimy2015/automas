from playwright.sync_api import sync_playwright
import html2text
import sys


def scrape_webpage(url):
    """
    Fetches the content of a webpage using Playwright (to handle JS/Anti-bot)
    and converts it to readable text.
    """
    try:
        with sync_playwright() as p:
            # Launch browser
            # headless=True is default, but sometimes False helps with extreme anti-bot
            # For now, keep it headless but add arguments to look more "human"
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ]
            )
            
            # Create a context with a real user agent and viewport
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            
            page = context.new_page()
            
            # Add init script to mask webdriver property
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Go to URL and wait for load
            # 'domcontentloaded' is faster than 'networkidle' but might miss some dynamic content
            # For articles, domcontentloaded is usually enough to get the text
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait a bit for any dynamic content/redirects
            # time.sleep(2) 
            
            # Get HTML content
            html_content = page.content()
            
            browser.close()
        
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False  # Keep images
        h.ignore_emphasis = False
        h.body_width = 0  # Disable line wrapping
        
        # Convert to text
        text_content = h.handle(html_content)
        
        return text_content.strip()
        
    except Exception as e:
        return f"Error processing webpage: {e}"

if __name__ == "__main__":
    # If no argument is provided, use the test URL
    if len(sys.argv) < 2:
        print("Error: Please provide a URL as an argument.")
    else:
        url = sys.argv[1]
    print(scrape_webpage(url))
