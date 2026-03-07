from playwright.sync_api import sync_playwright
import time

def run_agent():
    with sync_playwright() as p:
        print("Agent starting: verifying identity token (state.json)...")
        
        # 继续强行调用 Edge 浏览器。为了让你看清它的动作，我们先保持 headless=False (有界面)
        browser = p.chromium.launch(headless=False, channel="msedge") 
        
        # Warning 核心装甲：注入我们刚刚拿到的 state.json！
        context = browser.new_context(storage_state="state.json")
        page = context.new_page()

        # 锁定我们的测试猎物：Switch Lite
        target_keyword = "Switch Lite"
        target_url = f"https://www.goofish.com/search?q={target_keyword}"
        
        print(f"Carrying token to infiltrate target waters：{target_url}")
        page.goto(target_url)

        # 给闲鱼服务器一点反应时间，让商品列表完全加载出来
        print("Waiting for product data to render (5秒)...")
        page.wait_for_timeout(5000) 

        # 战术留痕：拍下一张网页截图，证明我们成功潜入了！
        page.screenshot(path="sniper_proof.png")
        print("Click! Scene photo taken，保存为同目录下的 'sniper_proof.png'。")
        
        # 尝试提取网页的标题，确认我们在哪
        page_title = page.title()
        print(f"Successfully breached! Current page title is: {page_title}")
        
        # 停留 10 秒让你欣赏一下它的全自动操作，然后撤退
        time.sleep(10)
        browser.close()
        print("Patrol ended, Agent safely evacuated。")

if __name__ == "__main__":
    run_agent()