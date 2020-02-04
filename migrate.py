# -*- coding: utf-8 -*-

"""
@author: hsowan <hsowan.me@gmail.com>
@date: 2020/2/4

"""
import json
import time

from bs4.element import Tag
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


cookies_file = 'cookies.json'
articles_file = 'articles.json'


def crawl_articles():
    """
    抓取所有博客信息

    :return:
    """

    try:

        csdn_blog_url = 'https://blog.csdn.net/ken1583096683/article/list/'

        # 生成博客对应的图片（数量人工判断，对应文章的数量）
        thumbnails = []
        for i in range(2, 7):
            r = requests.get(f'https://picsum.photos/v2/list?page={str(i)}&limit=50')
            if r.status_code == 200:
                items = r.json()
                for item in items:
                    thumbnails.append(item.get('url'))

        with open(cookies_file, 'r') as f:
            cookies = json.loads(f.read())

        # 设置cookies
        jar = requests.cookies.RequestsCookieJar()
        for cookie in cookies:
            jar.set(cookie['name'], cookie['value'])
        # 设置头信息
        headers = {
            'referer': 'https://www.csdn.net/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
            'authority': 'blog.csdn.net',
        }

        articles = []
        # 页数人工判断
        for i in range(1, 8):
            r = requests.get(csdn_blog_url + str(i), headers=headers, cookies=jar)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                items = soup.find_all('div', attrs={'class': 'article-item-box csdn-tracking-statistics'})
                for item in items:
                    # 原创/转载
                    tag = item.select('h4 a')[0].contents[1].string
                    url = item.select('h4 a')[0]['href']
                    id_ = url.split('https://blog.csdn.net/ken1583096683/article/details/')[1]
                    title = item.select('h4 a')[0].contents[2].strip()
                    date = item.find('span', attrs={'class': 'date'}).string.strip()
                    content = item.find('p', attrs={'class': 'content'}).a.string.strip()
                    articles.append({
                        'id_': id_,
                        'title': title,
                        'content': content,
                        'tag': tag,
                        'url': url,
                        'date': date,
                        'thumbnail': thumbnails[len(articles)]
                    })

        with open(articles_file, 'w') as f:
            f.write(json.dumps(articles))

    except Exception as e:
        print(str(e))
        exit(1)


def dump_articles():
    with open(cookies_file, 'r') as f:
        cookies = json.loads(f.read())

    with open(articles_file, 'r') as f:
        articles = json.loads(f.read())

    success = 0
    failed = 0
    count = len(articles)
    for index, article in enumerate(articles):
        try:
            start = time.time()

            options = webdriver.ChromeOptions()
            prefs = {
                'profile.default_content_setting_values.images': 2,  # 禁止图片加载
            }
            options.add_experimental_option('prefs', prefs)
            driver = webdriver.Chrome(options=options)
            # driver = webdriver.Remote(command_executor='http://localhost:4444/wd/hub', options=options)

            driver.get('https://blog.csdn.net/ken1583096683')
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)
            try:
                with open('blog/csdn_' + str(index) + '.md', 'w') as f:
                    f.write('---\n')
                    f.write('title: \'' + article.get('title').replace('\'', '"') + '\'\n')
                    f.write('comments: true\n')
                    f.write('date: ' + article.get('date') + '\n')
                    f.write("thumbnail: '" + article.get('thumbnail') + "'\n")

                    driver.get('https://editor.csdn.net/md/?articleId=' + article.get('id_'))
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//div[@class='cledit-section']"))
                    )

                    # 点击发布按钮才能显示文章的标签、分类信息
                    publish_button = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[@class='btn btn-publish']"))
                    )
                    publish_button.click()

                    # 获取文章标签、分类信息
                    try:
                        tags = WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, "//div[@class='mark_selection_title_el_tag']/span/span"))
                        )
                        f.write('tags:\n')
                        for tag in tags:
                            f.write('  - ' + tag.text.strip() + '\n')
                    except TimeoutException:
                        pass

                    try:
                        categories = WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, "//div[@class='tag__item-box']/span"))
                        )
                        f.write('categories:\n')
                        for category in categories:
                            f.write('  - ' + category.text.strip() + '\n')
                    except TimeoutException:
                        pass

                    f.write('---\n\n')
                    f.write(article.get('content') + '\n\n')
                    f.write('<!-- more -->\n\n')

                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    sections = soup.find_all('div', attrs={'class': 'cledit-section'})

                    for section in sections:
                        # 调用tag的 find_all() 方法时,Beautiful Soup会检索当前tag的所有子孙节点,如果只想搜索tag的直接子节点,可以使用参数 recursive=False
                        tags = section.find_all('span', recursive=False)
                        for tag in tags:
                            classes = tag.get('class', [])
                            # 直接打印的元素
                            if 'p' in classes or 'comment' in classes or 'cl' in classes or 'csdnvideo' in classes or 'entity' in classes:
                                if tag.string:
                                    f.write(tag.string)
                            # 换行
                            elif 'lf' in classes:
                                f.write('\n')
                            # 链接
                            elif 'link' in classes:
                                tag_contents = tag.contents
                                f.write(tag_contents[0])
                                if tag_contents[1].string:
                                    f.write(tag_contents[1].string)
                                f.write(tag_contents[2])
                            # 代码/加粗/斜体
                            elif 'code' in classes or 'strong' in classes or 'em' in classes:
                                tag_contents = tag.contents
                                for tag_content in tag_contents:
                                    if isinstance(tag_content, Tag):
                                        classes = tag_content.get('class', [])
                                        if 'lf' in classes:
                                            f.write('\n')
                                        elif 'cl' in classes:
                                            f.write(tag_content.string)
                                    elif isinstance(tag_content, str):
                                        f.write(tag_content)
                            # 代码
                            elif 'pre' in classes and 'gfm' in classes:
                                if len(tag.find_all('span', recursive=False)) == 1:
                                    tag_contents = tag.find_all('span', recursive=False)[0].contents
                                else:
                                    tag_contents = tag.contents

                                for tag_content in tag_contents:
                                    if isinstance(tag_content, str):
                                        f.write(tag_content)
                                        continue

                                    classes = tag_content.get('class', [])
                                    if 'lf' in classes:
                                        f.write('\n')
                                    elif 'tag' in classes:
                                        for tag_content_ in tag_content.contents:
                                            if isinstance(tag_content_, str):
                                                f.write(tag_content_)
                                                continue

                                            classes = tag_content_.get('class', [])
                                            if 'attr-name' in classes or 'punctuation' in classes:
                                                f.write(tag_content_.string)
                                            elif 'tag' in classes:
                                                f.write(tag_content_.contents[0].string + tag_content_.contents[1])
                                            elif 'attr-value' in classes:
                                                if len(tag_content_.contents) == 4:
                                                    f.write('="' + tag_content_.contents[2].string + '"')
                                                else:
                                                    f.write('=""')
                                    else:
                                        if tag_content.string:
                                            f.write(tag_content.string)
                            # 图片
                            elif 'img-wrapper' in classes:
                                for tag_content in tag.contents[1].contents:
                                    if isinstance(tag_content, str):
                                        f.write(tag_content)
                                    else:
                                        if tag_content.string:
                                            f.write(tag_content.string)
                            # 标题/引用/删除
                            elif 'h1' in classes or 'h2' in classes or 'h3' in classes or 'h4' in classes or 'h5' in classes or 'h6' in classes or 'blockquote' in classes or 'del' in classes:
                                for tag_content in tag.contents:
                                    if tag_content.string:
                                        f.write(tag_content.string)
                            # 任务
                            elif 'task' in classes:
                                if len(tag.contents) == 2:
                                    f.write('[ ]')
                                else:
                                    f.write('[x]')
                            # 网页元素
                            elif 'tag' in classes:
                                for tag_content in tag.contents:
                                    if isinstance(tag_content, str):
                                        f.write(tag_content)
                                        continue

                                    classes = tag_content.get('class', [])
                                    if 'attr-name' in classes or 'punctuation' in classes:
                                        f.write(tag_content.string)
                                    elif 'tag' in classes:
                                        f.write(tag_content.contents[0].string + tag_content.contents[1])
                                    elif 'attr-value' in classes:
                                        if len(tag_content.contents) == 4:
                                            f.write('="' + tag_content.contents[2].string + '"')
                                        else:
                                            f.write('=""')
                            # 表格
                            elif 'table' in classes:
                                # 表格内部可以插入图片和链接等其他格式的内容，待完善
                                for tag_content in tag.contents:
                                    classes = tag_content.get('class', [])
                                    if 'lf' in classes:
                                        f.write('\n')
                                    elif 'link' in classes:
                                        tag_contents = tag_content.contents
                                        f.write(tag_contents[0])
                                        if tag_contents[1].string:
                                            f.write(tag_contents[1].string)
                                        f.write(tag_contents[2])
                                    elif 'img-wrapper' in classes:
                                        for tag_content_ in tag_content.contents[1].contents:
                                            if isinstance(tag_content_, str):
                                                f.write(tag_content_)
                                            else:
                                                if tag_content_.string:
                                                    f.write(tag_content_.string)
                                    elif 'code' in classes or 'strong' in classes or 'em' in classes:
                                        tag_contents = tag_content.contents
                                        if len(tag_contents) == 3:
                                            f.write(tag_contents[0].string)
                                            f.write(tag_contents[1])
                                            f.write(tag_contents[2].string)
                                        else:
                                            f.write(tag_contents[0].string * 2)
                                    elif 'del' in classes:
                                        for tag_content_ in tag_content.contents:
                                            f.write(tag_content_.string)
                                    else:
                                        f.write(tag_content.string)

            finally:
                driver.quit()

            spend_time = round(time.time() - start, 2)
            success += 1
            print('成功转换文章: ' + article.get('title') + ', 耗时' + str(spend_time) + '秒, 已完成' + str(round((success+failed)/count*100)) + '%')
        except Exception as e:
            print(str(e))
            print(article.get('url'))
            failed += 1
            continue

        print('成功转换' + str(success) + '篇文章, 失败' + str(failed) + '篇')


if __name__ == '__main__':
    has_crawl_articles = input('是否已经爬取所有文章的基本信息？(y/n)')
    if has_crawl_articles.lower() == 'y':
        print('开始转换为md文件')
        dump_articles()
    elif has_crawl_articles.lower() == 'n':
        print('开始爬取文章基本信息')
        crawl_articles()
    else:
        print('请输入y/n')

