
import time
import logging
import traceback
from threading import Lock

# TELEGRAM LIB
import telebot
from telebot.types import Message

# SELENIUM LIBS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================ CONFIG ================
# Put your bot token here
BOT_TOKEN = "your bot token"

# Admin Telegram IDs allowed to use commands
ADMIN_IDS = [your admin id]

# Panel configuration (unchanged from user)
PANEL_CONFIG = {
    6: {
        "name": "Senior Panel",
        "url": "https://sm.bet555mix.com/",
        "user": "00000",
        "pass": "00000",
        "menu": "Master"
    },
    9: {
        "name": "Master Panel",
        "url": "https://ms.bet555mix.com/",
        "user": "00000",
        "pass": "00000",
        "menu": "Agents"
    },
    12: {
        "name": "Agent Panel",
        "url": "https://ag.bet555mix.com/",
        "user": "00000",
        "pass": "00000",
        "menu": "Members"
    }
}

# Selenium options
HEADLESS = True  # set False for visible browser (debug)

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================ AUTOMATION CLASS ================
class AgentAutomation:
    def __init__(self, headless=True):
        self.driver = None
        self.wait = None
        self.current_role = None
        self.headless = headless
        self.last_error = None
        self.start_driver()

    def start_driver(self):
        """Start or restart Chrome driver"""
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass

            logging.info("Starting Chrome Driver...")
            chrome_options = Options()
            if self.headless:
                # Headless new mode recommended
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self.current_role = None
            logging.info("✅ Chrome Driver started")
        except Exception as e:
            self.last_error = traceback.format_exc()
            logging.error(f"Failed to start driver: {e}")
            raise

    def check_browser(self):
        try:
            _ = self.driver.current_url
        except Exception as e:
            logging.warning("Browser not reachable, restarting driver...")
            logging.debug(str(e))
            try:
                self.start_driver()
            except Exception as exc:
                logging.error("Driver restart failed.")
                self.last_error = traceback.format_exc()

    def safe_click(self, element):
        try:
            ActionChains(self.driver).move_to_element(element).pause(0.2).click().perform()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass

    def clean_aria_hidden(self):
        try:
            self.driver.execute_script("""
                document.body.removeAttribute('aria-hidden');
                document.querySelectorAll('[aria-hidden="true"]').forEach(el => el.removeAttribute('aria-hidden'));
            """)
        except Exception:
            pass

    def login(self, role_length):
        """Dynamic Login based on username length (6/9/12)"""
        try:
            self.check_browser()
            config = PANEL_CONFIG.get(role_length)
            if not config:
                return False, "Invalid Username Length (Must be 6, 9, or 12)"

            # If already logged-in with same role and in list page, skip
            if self.current_role == role_length:
                try:
                    if "list" in self.driver.current_url:
                        return True, "Already Logged In"
                except Exception:
                    pass

            logging.info(f"Switching to {config['name']} ({config['url']})")
            self.driver.get(config['url'])
            time.sleep(1)

            # Logout if switching roles
            if self.current_role is not None and self.current_role != role_length:
                try:
                    logout_btn = self.driver.find_element(By.CLASS_NAME, "anticon-logout")
                    self.safe_click(logout_btn)
                    time.sleep(1)
                    confirm = self.driver.find_element(By.XPATH, "//button[contains(., 'OK') or contains(., 'Yes')]")
                    self.safe_click(confirm)
                    time.sleep(2)
                except Exception:
                    pass

            # Wait for username field or treat as session active
            try:
                username_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
            except Exception:
                # If cannot find login fields, maybe already session active
                self.current_role = role_length
                logging.info("Session seems active.")
                return True, "Session Active"

            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")

            username_field.clear()
            username_field.send_keys(config['user'])
            password_field.clear()
            password_field.send_keys(config['pass'])
            password_field.send_keys(Keys.RETURN)

            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "ant-layout-content")))

            # Close common popups
            try:
                time.sleep(2)
                popups = self.driver.find_elements(By.XPATH, "//button[contains(., 'Agree') or contains(., 'AGREE') or contains(@class, 'ant-modal-close')]")
                for p in popups:
                    if p.is_displayed():
                        self.safe_click(p)
            except Exception:
                pass

            self.current_role = role_length
            logging.info("Login success")
            return True, "Login Success"
        except Exception as e:
            logging.error(f"Login Error: {e}")
            self.last_error = traceback.format_exc()
            return False, str(e)

    def navigate_to_list(self, role_len):
        """Navigate to the target 'List' page depending on panel"""
        try:
            config = PANEL_CONFIG[role_len]
            menu_name = config['menu']

            # Senior Panel (6) force URL jump
            if role_len == 6:
                target_url = "https://sm.bet555mix.com/masters"
                if target_url not in self.driver.current_url:
                    logging.info(f"Force jumping to {target_url}")
                    self.driver.get(target_url)
                    try:
                        WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.ant-table-row")))
                    except Exception:
                        logging.warning("Table wait timeout (continuing...)")
                return True

            # For Master & Agent -> click menu -> List
            if f"{menu_name.lower()}/list" in self.driver.current_url:
                return True

            logging.info(f"Navigating to {menu_name} > List...")
            menu_item = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{menu_name}')]")))
            try:
                parent_li = menu_item.find_element(By.XPATH, "./ancestor::li")
                if "ant-menu-submenu-open" not in parent_li.get_attribute("class"):
                    self.safe_click(menu_item)
            except Exception:
                self.safe_click(menu_item)

            time.sleep(1)
            list_menu = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li//span[text()='List'] | //a[contains(text(),'List')]")))
            self.safe_click(list_menu)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.ant-table-row")))
            return True
        except Exception as e:
            logging.error(f"Navigation Error: {e}")
            self.last_error = traceback.format_exc()
            return False

    def manage_balance(self, target_username, amount, action_type="add"):
        """
        Core function which:
         - determines panel by username length
         - logs in/switches
         - searches for user
         - opens Manage Balance modal, fills amount and saves
        Returns string: "SUCCESS|..." or "ERROR|..."
        """
        try:
            u_len = len(target_username)
            if u_len not in PANEL_CONFIG:
                return f"ERROR|Invalid Username Length: {u_len} (Must be 6, 9, or 12)"

            success, msg = self.login(u_len)
            if not success:
                return f"ERROR|Login Failed: {msg}"

            # ensure we are on expected window
            try:
                self.driver.switch_to.window(self.driver.current_window_handle)
            except Exception:
                pass

            if not self.navigate_to_list(u_len):
                return "ERROR|Navigation Failed"

            # Search user
            logging.info(f"Searching for user: {target_username}")
            try:
                search_input = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.ant-input")))
                # clear
                self.driver.execute_script("arguments[0].value = '';", search_input)
                search_input.send_keys(target_username)
                search_input.send_keys(Keys.RETURN)
                time.sleep(2)
            except Exception:
                return "ERROR|Search Box Issue"

            # Find user row
            target_xpath = f"//tr[contains(., '{target_username}')]"
            try:
                user_row = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, target_xpath)))
            except Exception:
                return f"ERROR|User {target_username} Not Found"

            # Click eye icon or last button
            try:
                eye_icon = user_row.find_element(By.CSS_SELECTOR, ".anticon-eye")
                self.safe_click(eye_icon)
            except Exception:
                try:
                    btns = user_row.find_elements(By.TAG_NAME, "button")
                    if btns:
                        self.safe_click(btns[-1])
                except Exception:
                    pass

            time.sleep(1)

            # Click Manage Balance button
            try:
                manage_btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Manage Balance')]")))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", manage_btn)
                self.safe_click(manage_btn)
            except Exception:
                return "ERROR|Manage Balance Btn Missing"

            # Amount input
            try:
                amount_box = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input.ant-input-number-input"))
                )
            except Exception:
                try:
                    amount_box = self.driver.find_element(By.ID, "basic_amount")
                except Exception:
                    return "ERROR|Amount Input Missing"

            self.clean_aria_hidden()

            # Select add/remove radio if available
            try:
                cmd_text = "add" if action_type == "add" else "remove"
                radio = self.driver.find_element(By.XPATH, f"//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{cmd_text}')]")
                self.safe_click(radio)
            except Exception:
                pass

            # Fill amount
            try:
                self.driver.execute_script("arguments[0].value = '';", amount_box)
                amount_box.send_keys(str(amount))
                # force react update attribute
                try:
                    self.driver.execute_script("arguments[0].setAttribute('value', arguments[1])", amount_box, str(amount))
                except Exception:
                    pass
            except Exception:
                pass

            time.sleep(0.5)

            # Save/Confirm
            try:
                save_btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'ant-modal-footer')]//button[contains(@class, 'ant-btn-primary')]")
                self.safe_click(save_btn)
            except Exception:
                try:
                    amount_box.send_keys(Keys.ENTER)
                except Exception:
                    pass

            time.sleep(3)
            try:
                self.driver.refresh()
            except Exception:
                pass

            return f"SUCCESS|Amount {amount} {action_type}ed to {target_username}"
        except Exception as e:
            logging.error(f"Automation Failed: {e}")
            tb = traceback.format_exc()
            self.last_error = tb
            # If driver crashed, attempt restart so subsequent commands work
            if "invalid session" in str(e).lower() or "chrome not reachable" in str(e).lower():
                try:
                    self.start_driver()
                    self.current_role = None
                except Exception:
                    pass
            return f"ERROR|{str(e)}"

# ================ TELEGRAM BOT HANDLERS ================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
agent_lock = Lock()
bot_agent = AgentAutomation(headless=HEADLESS)

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['help'])
def cmd_help(message: Message):
    text = (
        "Commands (Admin only):\n"
        "/add USERNAME AMOUNT    - add balance\n"
        "/remove USERNAME AMOUNT - remove balance\n"
        "/restart                - restart chrome driver\n"
        "/status                 - show driver status\n"
        "/log                    - show last error\n"
        "/help                   - this message\n"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['status'])
def cmd_status(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Permission Denied")
        return
    try:
        agent = bot_agent
        status = "Driver: up" if agent.driver else "Driver: down"
        role = agent.current_role if agent.current_role else "None"
        bot.reply_to(message, f"{status}\nCurrent Role Length: {role}")
    except Exception as e:
        bot.reply_to(message, f"Error retrieving status: {e}")

@bot.message_handler(commands=['restart'])
def cmd_restart(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Permission Denied")
        return
    bot.reply_to(message, "🔄 Restarting driver...")
    try:
        with agent_lock:
            bot_agent.start_driver()
            bot.reply_to(message, "✅ Driver restarted")
    except Exception as e:
        bot.reply_to(message, f"❌ Restart failed: {e}")

@bot.message_handler(commands=['log'])
def cmd_log(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Permission Denied")
        return
    le = bot_agent.last_error
    if not le:
        bot.reply_to(message, "No recent errors logged.")
    else:
        # Telegram messages have length limits; split if big
        for i in range(0, len(le), 3800):
            bot.send_message(message.chat.id, f"```\n{le[i:i+3800]}\n```", parse_mode='Markdown')

def _parse_two_args(text):
    # returns (username, amount) or (None, None)
    parts = text.strip().split()
    if len(parts) < 3:
        return None, None
    # parts[0] is command
    username = parts[1].strip()
    try:
        amount = int(parts[2])
    except Exception:
        return username, None
    return username, amount

@bot.message_handler(commands=['add'])
def cmd_add(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Permission Denied")
        return

    username, amount = _parse_two_args(message.text)
    if not username or amount is None:
        bot.reply_to(message, "⚠️ Usage:\n/add USERNAME AMOUNT")
        return

    bot.reply_to(message, f"🚀 Processing add: {username} +{amount}")
    with agent_lock:
        res = bot_agent.manage_balance(username, amount, "add")
    if res.startswith("SUCCESS"):
        bot.reply_to(message, f"✅ {res}")
    else:
        bot.reply_to(message, f"❌ {res}")

@bot.message_handler(commands=['remove'])
def cmd_remove(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Permission Denied")
        return

    username, amount = _parse_two_args(message.text)
    if not username or amount is None:
        bot.reply_to(message, "⚠️ Usage:\n/remove USERNAME AMOUNT")
        return

    bot.reply_to(message, f"🚀 Processing remove: {username} -{amount}")
    with agent_lock:
        res = bot_agent.manage_balance(username, amount, "remove")
    if res.startswith("SUCCESS"):
        bot.reply_to(message, f"✅ {res}")
    else:
        bot.reply_to(message, f"❌ {res}")

# ================ MAIN RUN ================
if __name__ == "__main__":
    try:
        logging.info("Bot starting...")
        print("Bot running. Press Ctrl+C to exit.")
        bot.infinity_polling(timeout=60, long_polling_timeout = 60)
    except KeyboardInterrupt:
        print("Interrupted by user - exiting.")
    except Exception as e:
        logging.error("Bot crashed: " + str(e))
        traceback.print_exc()
    finally:
        try:
            if bot_agent and bot_agent.driver:
                bot_agent.driver.quit()
        except Exception:
            pass
