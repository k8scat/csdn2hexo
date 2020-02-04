# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/4

"""
import json
import time

from selenium import webdriver

cookies_file = 'cookies.json'

if __name__ == '__main__':
    login_url = 'https://passport.csdn.net/login'

    driver = webdriver.Chrome()
    try:
        driver.get(login_url)

        # 扫码登录
        time.sleep(30)

        # 获取到cookies
        cookies = driver.get_cookies()
        # 判断是否登录成功
        for c in cookies:
            cookies_str = json.dumps(cookies)
            with open(cookies_file, 'w') as f:
                f.write(cookies_str)
    finally:
        driver.close()
