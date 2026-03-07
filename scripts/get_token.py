from playwright.sync_api import sync_playwright
import time

def save_login_state():
    with sync_playwright() as p:
        print("Starting Edge browser...")
        
        # Force use of Windows built-in Edge browser
        browser = p.chromium.launch(headless=False, channel="msedge") 
        
        context = browser.new_context()
        page = context.new_page()

        print("Please scan QR code with Xianyu App in the opened browser.")
        # Go to Xianyu homepage for login
        page.goto("https://www.goofish.com/") 

        print("You have 60 seconds to complete login, please scan QR code...")
        time.sleep(60) 

        # Save login state to local file
        context.storage_state(path="state.json")
        print("Success! Login state saved as 'state.json' in current directory.")
        
        browser.close()

if __name__ == "__main__":
    save_login_state()