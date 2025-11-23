import time
import logging
import traceback
import asyncio
from threading import Lock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================= CONFIGURATION =================
# ⚠️ Replace the values below with your actual data
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ALLOWED_USER_IDS = [123456789]  # Replace with your Telegram User ID (Integer)

# Web URLs
LOGIN_URL = "https://ag.sportsxzone.com/"      # Replace with actual Login URL
PAYMENT_URL = "https://ag.sportsxzone.com/payment/deposit-withdrawl"  # Replace with actual Payment URL

# Login Credentials
ADMIN_USER = "YOUR_USERNAME_HERE"
ADMIN_PASS = "YOUR_PASSWORD_HERE"
# =================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class BrowserBot:
    def __init__(self):
        self.lock = Lock()
        self.driver = None
        self.wait = None
        self.start_browser()

    def start_browser(self):
        """VPS/Server Browser Setup"""
        if self.driver:
            try: self.driver.quit()
            except: pass

        print("🚀 Starting Chrome Browser on VPS...")
        options = Options()
        
        # ================= VPS Settings =================
        options.add_argument("--headless=new")  # Must be headless for VPS
        options.add_argument("--no-sandbox")    
        options.add_argument("--disable-dev-shm-usage") 
        options.add_argument("--disable-gpu")   
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--remote-allow-origins=*")
        # ============================================
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Browser Opened Successfully!")
        except Exception as e:
            print(f"❌ Browser Start Error: {e}")

    def safe_click(self, element):
        try:
            ActionChains(self.driver).move_to_element(element).pause(0.2).click().perform()
        except:
            self.driver.execute_script("arguments[0].click();", element)

    def login(self):
        print("🔄 Logging in...")
        try:
            self.driver.get(LOGIN_URL)
            time.sleep(2)

            if "payment" in self.driver.current_url:
                print("✅ Already Logged In")
                return True

            # Note: You may need to adjust these XPaths to match your specific website
            try:
                # Example: Selecting a specific tab if needed
                # senior_tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Senior']")))
                # self.safe_click(senior_tab)
                pass 
            except:
                pass

            # Input Username
            try:
                user_in = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Username'] | //input[@type='text']")))
                user_in.clear()
                user_in.send_keys(ADMIN_USER)
            except:
                print("⚠️ Username Input not found")

            # Input Password
            try:
                pass_in = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                pass_in.clear()
                pass_in.send_keys(ADMIN_PASS)
            except:
                print("⚠️ Password Input not found")

            # Click Login
            try:
                login_btn = self.driver.find_element(By.CSS_SELECTOR, "button.ant-btn-block")
                self.safe_click(login_btn)
                print("🖱️ Clicked Sign In...")
            except:
                print("⚠️ Login Button not found")

            time.sleep(5)
            return True

        except Exception as e:
            print(f"❌ Login Error: {e}")
            return False

    def process_transaction(self, target_user, amount, type="deposit"):
        with self.lock:
            # Check Login
            if "payment" not in self.driver.current_url:
                if not self.login(): return "❌ Login Failed"

            try:
                if self.driver.current_url != PAYMENT_URL:
                    self.driver.get(PAYMENT_URL)
                    time.sleep(2)

                print(f"🔍 Searching: {target_user}")
                try:
                    # Update ID based on your website's HTML
                    search_input = self.wait.until(EC.element_to_be_clickable((By.ID, "advanced_search_userId")))
                    self.safe_click(search_input)
                    self.driver.execute_script("arguments[0].value = '';", search_input)
                    search_input.send_keys(target_user)
                    time.sleep(1)
                    search_input.send_keys(Keys.RETURN)
                    
                    try:
                        first_option = self.driver.find_element(By.CSS_SELECTOR, ".ant-select-item-option-content")
                        first_option.click()
                    except: pass

                except Exception as e:
                    return "❌ Search Box not found"

                time.sleep(2) 

                final_amount = str(amount)
                action_text = "Deposited"
                if type == "withdraw":
                    final_amount = f"-{amount}"
                    action_text = "Withdrawn"

                try:
                    amount_box = self.wait.until(EC.presence_of_element_located((By.ID, "amount")))
                    self.safe_click(amount_box)
                    self.driver.execute_script("arguments[0].value = '';", amount_box)
                    amount_box.send_keys(final_amount)
                except Exception as e:
                    return "❌ Amount Box not found"

                time.sleep(1)

                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button.w-100[type='submit']")
                    self.safe_click(submit_btn)
                    
                    time.sleep(2)

                    # Confirm Modal Step
                    try:
                        confirm_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm")))
                        self.safe_click(confirm_btn)
                    except Exception as e:
                        return "⚠️ Error: Confirm Popup not found"
                    
                    time.sleep(3)
                    return f"✅ {action_text} Successfully.\n👤 User: {target_user}\n💰 Amount: {amount}"

                except Exception as e:
                    return f"❌ Submit Failed: {e}"

            except Exception as e:
                traceback.print_exc()
                self.start_browser()
                return f"❌ System Error: {str(e)}"

bot_agent = BrowserBot()

def restricted(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text(f"⛔ Unauthorized. ID: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 **Bot Ready on VPS!**", parse_mode="Markdown")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, bot_agent.login)

@restricted
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/deposit username amount`", parse_mode="Markdown")
        return
    username = context.args[0]
    amount = context.args[1]
    await update.message.reply_text(f"⏳ Depositing {amount} to {username}...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, bot_agent.process_transaction, username, amount, "deposit")
    await update.message.reply_text(result)

@restricted
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/withdraw username amount`", parse_mode="Markdown")
        return
    username = context.args[0]
    amount = context.args[1]
    await update.message.reply_text(f"⏳ Withdrawing {amount} from {username}...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, bot_agent.process_transaction, username, amount, "withdraw")
    await update.message.reply_text(result)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.run_polling()

if __name__ == "__main__":
    main()
