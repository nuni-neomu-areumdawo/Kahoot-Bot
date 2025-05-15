import asyncio
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from os import cpu_count

KAHOOT_URL = "https://kahoot.it/"
DEFAULT_BOT_COUNT = cpu_count() * 2
MAX_BOT_NAME_SUFFIX = 1048576
CONCURRENT_BOTS = cpu_count()
PAGE_LOAD_TIMEOUT = 16
ELEMENT_INTERACTION_TIMEOUT = 8
GAMEPLAY_WAIT_TIMEOUT = 64

def generate_bot_name(base_name: str, bot_number: int) -> str:
    return f"{base_name}-{bot_number}-{random.randint(0, MAX_BOT_NAME_SUFFIX)}"

def create_webdriver_options() -> Options:
    #Creates Chrome options for the WebDriver.
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
    return chrome_options

def join_kahoot_instance_sync(game_pin: str, bot_true_name: str, bot_display_number: int, total_bots: int):
    bot_label = f"[Bot {bot_display_number}/{total_bots} - {bot_true_name}]"
    driver = None
    try:
        driver = webdriver.Chrome(options=create_webdriver_options())

        print(f"{bot_label}: Navigating to {KAHOOT_URL}...\n")
        driver.get(KAHOOT_URL)

        wait = WebDriverWait(driver, ELEMENT_INTERACTION_TIMEOUT)

        pin_input_locator = (By.ID, "game-input")
        pin_submit_button_locator = (By.CSS_SELECTOR, "button[data-functional-selector='join-game-pin']")
        pin_input_element = wait.until(EC.element_to_be_clickable(pin_input_locator))
        print(f"{bot_label}: Entering PIN '{game_pin}'...\n")
        pin_input_element.send_keys(game_pin)
        pin_submit_button = wait.until(EC.element_to_be_clickable(pin_submit_button_locator))
        pin_submit_button.click()

        username_input_locator = (By.ID, "nickname")
        username_submit_button_locator = (By.CSS_SELECTOR, "button[data-functional-selector='join-button-username']")
        username_input_element = wait.until(EC.element_to_be_clickable(username_input_locator))
        print(f"{bot_label}: Entering name '{bot_true_name}'...\n")
        username_input_element.send_keys(bot_true_name)
        username_submit_button = wait.until(EC.element_to_be_clickable(username_submit_button_locator))
        username_submit_button.click()

        wait.until(EC.staleness_of(username_input_element))
        print(f"SUCCESS: {bot_label} has joined the game!\n")

        answer_buttons_locator = (By.XPATH, "//button[starts-with(@data-functional-selector, 'answer-button-')]")
        POST_ANSWER_STATE_INDICATOR = (By.CSS_SELECTOR, "[data-testid='next-question-countdown'], [data-testid='feedback-block']")
        
        game_wait = WebDriverWait(driver, GAMEPLAY_WAIT_TIMEOUT)
        short_game_wait = WebDriverWait(driver, ELEMENT_INTERACTION_TIMEOUT)

        question_count = 0
        while True:
            try:
                clickable_answer_buttons = game_wait.until(
                    EC.presence_of_all_elements_located(answer_buttons_locator)
                )
                
                visible_clickable_buttons = [
                    btn for btn in clickable_answer_buttons if btn.is_displayed() and btn.is_enabled()
                ]

                time_spent = 0
                while not visible_clickable_buttons and time_spent < 3:
                    visible_clickable_buttons = [
                        btn for btn in clickable_answer_buttons if btn.is_displayed() and btn.is_enabled()
                    ]
                    time_spent += 0.5
                    time.sleep(0.5)
                    
                question_count += 1
                time.sleep(random.random())

                chosen_button = random.choice(visible_clickable_buttons)
                button_info = chosen_button.get_attribute('data-functional-selector') or "Unknown Selector"
                
                chosen_button.click()
                print(f"{bot_label}: Answer submitted for question {question_count}.")

                print(f"{bot_label}: Waiting for question {question_count} to end...")
                try:
                    short_game_wait.until(EC.staleness_of(chosen_button))
                    print(f"{bot_label}: Answer buttons went stale (question ended).")
                except TimeoutException:
                    try:
                        game_wait.until(EC.presence_of_element_located(POST_ANSWER_STATE_INDICATOR))
                        print(f"{bot_label}: Post-answer state detected.")
                    except TimeoutException:
                        print(f"{bot_label}: Did not detect end of question {question_count} clearly. Game might be stuck or ended. Will try to continue.")
    
            except Exception as e:
                print(f"Caught: {e}")
                time.sleep(random.random() * 10)
    except Exception as e:
        print(f"Caught: {e}")
        time.sleep(random.random() * 10)
    finally:
        print(f"{bot_label}: Task processing finished.")
        if driver:
            pass


async def launch_bot_task(semaphore, game_pin, base_bot_name, bot_number, total_bots):
    async with semaphore:
        bot_name = generate_bot_name(base_bot_name, bot_number)
        print(f"Preparing Bot {bot_number}/{total_bots} ({bot_name})...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            join_kahoot_instance_sync,
            game_pin,
            bot_name,
            bot_number,
            total_bots
        )

async def main():
    done = False
    while not done:
        try:
            game_pin = int(input("Enter the pin of the game: "))
            done = True
        except Exception as e:
            print(f"Ensure you enter an integer. {e}")
            pass
    base_bot_name = input("Enter the name of the bot: ")
    
    done = False
    while not done:
        try:
            num_bots = int(input(f"Enter the number of bots in total, note ({cpu_count()} will join at once): "))
            done = True
        except Exception as e:
            print(f"Ensure you enter an integer. {e}")
            pass
    
    semaphore = asyncio.Semaphore(CONCURRENT_BOTS)
    tasks = []

    print(f"\nAttempting to launch {num_bots} bot(s) with base name '{base_bot_name}' for PIN '{game_pin}'...")

    start_time = time.time()
    for i in range(1, num_bots + 1):
        task = launch_bot_task(semaphore, game_pin, base_bot_name, i, num_bots)
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    print(f"\n\nAll {num_bots} bot tasks have been initiated/completed in {end_time - start_time:.2f} seconds.")
    print("Bots that successfully joined should attempt to play by randomly answering.")
    print("Press Ctrl+C to exit all bots (this will close their browsers).\n\n")
    
    try:
        while True:
            await asyncio.sleep(3600) 
    except KeyboardInterrupt:
        print("\nExiting script and closing any remaining browser instances...")
    finally:
        print("Script finished.")

if __name__ == "__main__":
    print("Consider starring this on GitHub and checking out my other projects! https://github.com/nuni-neomu-areumdawo/Kahoot-Bot")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Shutting down.")
    except Exception as e_main:
        print(f"Unhandled exception in main execution: {e_main}")
