from contextlib import contextmanager
import logging
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from decouple import config

import time

from CSV import CSV
from JSON import JSON
from NFT import NFT

EXTENSION_PATH = config("EXTENSION_PATH")

RECOVERY_CODE = config("RECOVERY_CODE")

PASSWORD = config("PASSWORD")

CHROME_DRIVER_PATH = config("CHROME_DRIVER_PATH")

DEFAULT_TIMEOUT = 30

_logger = logging.getLogger()
_logger.setLevel(logging.INFO)

@contextmanager
def wait_for_new_window(driver, timeout=DEFAULT_TIMEOUT):
    try:
        handles_before = len(driver.window_handles)
        yield
    finally:
        _logger.info('waiting new window to open...')
        WebDriverWait(driver, timeout).until(
            lambda driver: handles_before < len(driver.window_handles))

def find_window_by_title(driver: webdriver.Chrome, title: str, raise_not_found=False):
    for window_handle in driver.window_handles:
        driver.switch_to.window(window_handle)
        if driver.title == title:
            return True
    if raise_not_found:
        raise Exception('Window not found')
    return False


def _wait_for_element(d: webdriver.Chrome, query:str, select_by=By.XPATH, wait_second:int=DEFAULT_TIMEOUT):
    _logger.info(f"waiting for element to present ({select_by}): {query}...")
    element = WebDriverWait(d, wait_second).until(
        EC.presence_of_element_located((select_by, query))
    )
    return element

def _wait_until_clickable(d:webdriver.Chrome, query: str, select_by=By.XPATH,  wait_second:int=DEFAULT_TIMEOUT):
    _logger.info(f"waiting for element to be clickable ({select_by}): {query}...")
    return WebDriverWait(d, wait_second).until(
        EC.element_to_be_clickable((select_by, query))
    )



def setup_metamask_wallet(d: webdriver.Chrome):
    d.switch_to.window(d.window_handles[0])  # focus on metamask tab

    _wait_until_clickable(d, '//button[text()="Get Started"]').click()

    _wait_until_clickable(d, '//button[text()="Import wallet"]').click()

    _wait_until_clickable(d, '//button[text()="No Thanks"]').click()

    _wait_for_element(d, '//input[@placeholder="Paste Secret Recovery Phrase from clipboard"]').send_keys(RECOVERY_CODE)
    _wait_for_element(d, 'password', By.ID).send_keys(PASSWORD)
    _wait_for_element(d, 'confirm-password', By.ID).send_keys(PASSWORD)

    _wait_until_clickable(d, ".first-time-flow__terms", By.CSS_SELECTOR).click()
    _wait_until_clickable(d, '//button[text()="Import"]').click()


def move_to_opensea(d: webdriver.Chrome):
    with wait_for_new_window(d):
        d.execute_script('''window.open("https://opensea.io","_blank")''')
    
    d.switch_to.window(d.window_handles[2])
    # manually click the 'profile' button to go to login page
    element = _wait_until_clickable(d, '//a[@href="/account"][text()="Profile"]')
    d.execute_script("arguments[0].scrollIntoView();", element)
    # d.implicitly_wait(10) # wait for scroll
    time.sleep(3)
    element.click()


def signin_to_opensea(d: webdriver.Chrome):
    # first time click, a new pop-up opens and close and then the metamask tab open
    # click again and the 'Connect with MetaMask' pop up window should open
    # the following code retries 5 times until the desired popup shows
    for i in range(5):
        # switch back to opensea.io
        d.switch_to.window(d.window_handles[2])
        with wait_for_new_window(d):
            _wait_until_clickable(d, '//button//span[text()="MetaMask"]').click()
            time.sleep(5) # wait for the popup to dispear... if it is going to disappear
        
        if find_window_by_title(d, 'MetaMask Notification'):
            break
        else:
            # close the new tab 
            d.close()

    _wait_until_clickable(d, '//button[text()="Next"]').click()

    _wait_until_clickable(d, '//button[text()="Connect"]').click()


def fillMetadata(d: webdriver.Chrome, metadataMap: dict):
    _wait_until_clickable(d, '//div[@class="AssetFormTraitSection--side"]/button').click()
    for index, value in enumerate(metadataMap):
        input1 = d.find_element_by_xpath('//tbody[@class="AssetTraitsForm--body"]/tr[last()]/td[1]/div/div/input')
        input2 = d.find_element_by_xpath('//tbody[@class="AssetTraitsForm--body"]/tr[last()]/td[2]/div/div/input')

        input1.send_keys(str(value))
        input2.send_keys(str(metadataMap[value]))
        if index != len(metadataMap) - 1:
            d.find_element_by_xpath('//button[text()="Add more"]').click()

    time.sleep(1)
    d.find_element_by_xpath('//button[text()="Save"]').click()


def upload(d: webdriver.Chrome, nft: NFT):
    d.switch_to.window(driver.window_handles[-1])
    time.sleep(3)
    d.find_element_by_id("media").send_keys(nft.file)
    d.find_element_by_id("name").send_keys(nft.name)
    d.find_element_by_id("description").send_keys(nft.description)

    time.sleep(3)

    fillMetadata(d, nft.metadata)

    time.sleep(2)
    d.find_element_by_xpath('//button[text()="Create"]').click()
    time.sleep(5)
    d.execute_script('''location.href="https://opensea.io/asset/create"''')


if __name__ == '__main__':
    # setup metamask
    opt = webdriver.ChromeOptions()
    opt.add_extension(EXTENSION_PATH)

    driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, chrome_options=opt)
    
    setup_metamask_wallet(driver)

    move_to_opensea(driver)

    signin_to_opensea(driver)
    
    with wait_for_new_window(driver):
        driver.execute_script('''window.open("https://opensea.io/asset/create","_blank")''')
    driver.switch_to.window(driver.window_handles[-1])

    # wait for the page to load 
    element = _wait_until_clickable(driver, '//button//span[text()="MetaMask"]')

    with wait_for_new_window(driver):
        element.click()

    find_window_by_title(driver, 'MetaMask Notification', True)
    _wait_until_clickable(driver, '//button[text()="Sign"]').click()
    
    data = JSON(os.getcwd() + "/data/metadata.json").readFromFile()
    for key in data:
        name = "#"+key # NAME OF YOUR FILE
        description = name + " from DemonQueenNFT" #NOTE: YOU NEED TO UPDATE THIS ACCORDINGLY
        file = key+".png"
        metadata = data[key]
        upload(driver, NFT(name, description, metadata, os.getcwd() + "/data/" + file))
    print("DONE!!")
