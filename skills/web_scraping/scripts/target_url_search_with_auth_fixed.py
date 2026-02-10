from playwright.sync_api import sync_playwright
import html2text
import sys
import time


def scrape_webpage(url):
    """
    Fetches the content of a webpage using Playwright (to handle JS/Anti-bot)
    and converts it to readable text, including authentication headers.
    """
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Set cookies and headers
            cookies = [
                {
                    'name': 'bd_sso_3b6da9',
                    'value': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzEzMTcyNDksImlhdCI6MTc3MDcxMjQ0OSwiaXNzIjoic3NvLmJ5dGVkYW5jZS5jb20iLCJzdWIiOiJxZDFscXF2ZjVvdzIwcGEwc3p4ZCIsInRlbmFudF9pZCI6ImhncTN0Y2NwM2kxc2pqbjU4emlrIn0.T0Z5xgfkXa3tzr1ACaR1qU2RdY-Wc1_Do65EKsnMbG3y_BJ_DE8uxg5SuTFc8qKm1nnOrmWXnFUADc3DrNUU_GB-uKN2WBa0hISr7UJMQA2wejXa5AW3nm2nDjfoiKkNa2oKzfYZwTyjM33rakjewyvQ0oW24DcrFrSQdlpUOJi3jGYRWz-QyeWvkoLXkSOMMrzaIl3izHewLTq9W3EkMFygNuCHDYyHCvbSxj3NiEpTKhop3umnIuk9Catx_7G5jB-U4QuV4erUl5yq8woG7CDd9bv92NyGLKwBgjSACJMY6gxchNw44M_cOwpaTd_mT0b1p32cVGrxcSsAyJ7XKA',
                    'domain': '.bytedance.net',
                    'path': '/'
                },
                {
                    'name': 'gd_random',
                    'value': 'eyJtYXRjaCI6dHJ1ZSwicGVyY2VudCI6MC41NjE3MjE3MTI2MzI5ODc0fQ==.lhOYLExcTouxFR2aSvESQZg5RIG5kIr0SMZjqIxjkF8=',
                    'domain': '.bytedance.net',
                    'path': '/'
                }
            ]
            
            # Create a context with authentication
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                extra_http_headers={
                    'Authorization': 'Byte-Cloud-JWT eyJhbGciOiJSUzI1NiIsImtpZCI6IiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJwYWFzLnBhc3Nwb3J0LmF1dGgiLCJleHAiOjE3NzA3MTYwNTAsImlhdCI6MTc3MDcxMjM5MCwidXNlcm5hbWUiOiJoYW50b25nLjkxNCIsInR5cGUiOiJwZXJzb25fYWNjb3VudCIsInJlZ2lvbiI6ImNuIiwidHJ1c3RlZCI6dHJ1ZSwidXVpZCI6ImJlNTBjZjVhLTEwZmQtNGJmMS04MjBiLWE4ZGNlZjkzYTZhMiIsInNpdGUiOiJvbmxpbmUiLCJieXRlY2xvdWRfdGVuYW50X2lkIjoiYnl0ZWRhbmNlIiwiYnl0ZWNsb3VkX3RlbmFudF9pZF9vcmciOiJieXRlZGFuY2UiLCJzY29wZSI6ImJ5dGVkYW5jZSIsInNlcXVlbmNlIjoiRW50ZXJwcmlzZSBTb2x1dGlvbnMiLCJvcmdhbml6YXRpb24iOiJEYXRhLUFNTC3kvIHkuJrmnI3liqEtQUkgRm91bmRhdGlvbi3kuqflk4Hop6PlhrPmlrnmoYgiLCJ3b3JrX2NvdW50cnkiOiJDSE4iLCJhdmF0YXJfdXJsIjoiaHR0cHM6Ly9zMS1pbWZpbGUuZmVpc2h1Y2RuLmNvbS9zdGF0aWMtcmVzb3VyY2UvdjEvdjNfMDB1Z18yODgyMTk0Zi04NTdlLTQ4MTYtYWI1Yi1iY2EwNzc0ZmU0ZGd-P2ltYWdlX3NpemU9bm9vcFx1MDAyNmN1dF90eXBlPVx1MDAyNnF1YWxpdHk9XHUwMDI2Zm9ybWF0PXBuZ1x1MDAyNnN0aWNrZXJfZm9ybWF0PS53ZWJwIiwiZW1haWwiOiJoYW50b25nLjkxNEBieXRlZGFuY2UuY29tIiwiZW1wbG95ZWVfaWQiOjI2ODcwODUsIm5ld19lbXBsb3llZV9pZCI6MjY4NzA4NX0.BU05-DQHPhsoKTIm-tDZWdGQbqUJEOAhVyjx_JCEDA9vG3JsHlZZce8sHZelgtAPWp4ccb3vp_6w6RRjhBxyoltI7Rgph1B7Az9gkNx4aqg_sfQce-R1weIaCmv1Yn1TO7poVMkkTuFhDFsQCdiU8XA1iY3dCv2q0IZfI5gkrIo'
                }
            )
            
            # Add cookies to context
            context.add_cookies(cookies)
            
            page = context.new_page()
            
            # Add init script to mask webdriver property
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Go to URL and wait for load
            print(f"Navigating to: {url}")
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Wait for page to fully render
            print("Waiting for page to render...")
            page.wait_for_timeout(10000)
            
            # Wait for specific element that indicates the page is loaded
            try:
                # Wait for any template item or content area
                page.wait_for_selector('div[class*="template"], div[class*="content"]', timeout=30000)
                print("Page content loaded successfully!")
            except Exception as e:
                print(f"Waiting for specific elements failed: {e}")
                print("Continuing with page content...")
            
            # Get HTML content
            html_content = page.content()
            print(f"Page content length: {len(html_content)} characters")
            
            browser.close()
        
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False  # Keep images
        h.ignore_emphasis = False
        h.body_width = 0  # Disable line wrapping
        
        # Convert to text
        text_content = h.handle(html_content)
        
        # Save content to file
        output_dir = '/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/output'
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, 'webpage_content.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"Content saved to: {output_file}")
        
        return text_content.strip()
        
    except Exception as e:
        error_msg = f"Error processing webpage: {e}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    # If no argument is provided, use the test URL
    if len(sys.argv) < 2:
        print("Error: Please provide a URL as an argument.")
    else:
        url = sys.argv[1]
        result = scrape_webpage(url)
        print(f"\nFirst 500 characters of content:\n{result[:500]}...")