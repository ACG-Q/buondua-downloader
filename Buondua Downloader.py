import os
import re
import sys
import concurrent.futures
from urllib.parse import urljoin

import requests
import random
import threading
import yaml
import time
from bs4 import BeautifulSoup

base_url = 'https://buondua.com/'
setting_path = "setting.yml"

BLACKLIST = [
	'https://buondua.com/',
	'https://buondua.com/hot',
	'https://buondua.com/collection',
]

# 定义User-Agent池
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"
    # 可以根据需要添加更多的 User-Agent
]

err_images = []
counter = 0  # 计数器，用于记录已下载的图片数量
max_counter = 50 # 下载多少就等待
wait = 10 # 等待多久
lock = threading.Lock()  # 创建一个线程锁对象

class Console:

    def __init__(self):
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.RESET = '\033[0m'
    
    def reset(self, color, mes, end='\n', flush=False):
        print(color + mes + self.RESET, end=end, flush=flush)

    def add(self, mes, end='\n', flush=False):
        self.reset(self.BLUE,  f"[+] {mes}", end=end, flush=flush)

    def err(self, mes, end='\n', flush=False):
        self.reset(self.YELLOW, f"[-] {mes}", end=end, flush=flush)
    
    def info(self, mes, end='\n', flush=False):
        self.reset(self.GREEN, f"[#] {mes}", end=end, flush=flush)
    
    def warn(self, mes, end='\n', flush=False):
        self.reset(self.RED, f"[!] {mes}", end=end, flush=flush)

console = Console()

def is_url(string):
    url_pattern = re.compile(r'^https?://\S+$', re.IGNORECASE)
    return bool(re.match(url_pattern, string))

def get_settings():
    global max_counter, wait
    default_save_dir = "downloads"
    default_num_threads = 5
    default_max_counter = 50
    default_wait = 10

    if os.path.exists(setting_path):
        with open(setting_path, 'r') as f:
            settings = yaml.safe_load(f)
            save_dir = settings.get('save_path', default_save_dir)
            num_threads = settings.get('num_threads', default_num_threads)
            max_counter = settings.get('max_counter', default_max_counter)
            wait = settings.get('wait', default_wait)
    else:
        save_dir = default_save_dir
        num_threads = default_num_threads
        max_counter = default_max_counter
        wait = default_wait

    return save_dir, num_threads

def download_err_images():
    err_len = len(err_images)
    if err_len > 0:
        console.warn(f"download image err length {err_len}")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for image in err_images:
                executor.submit(download_image, image["url"], image["save"])
        
def download_image(url, save_path):
    global counter
    try:
        # 使用线程锁来保证计数器的安全访问
        with lock:
            response = requests.get(url, headers={'User-Agent': random.choice(user_agents)})
            if response.status_code == 200:
                counter += 1  # 每成功下载一张图片，计数器加1
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                if counter % max_counter == 0:  # 当下载完成 max_counter 张图片时
                    console.warn(f"下载了{max_counter}张图片，暂停{wait}秒...")
                    time.sleep(wait)  # 暂停 wait 秒
        
    except Exception as e:
        console.err(f"Failed to download image: {url}")
        err_images.append({
            "url": url,
            "save": save_path
        })
        print(e)

def start_download_image_thread(url, page, save_dir):
    try:
        response = requests.get(url, headers={'User-Agent': random.choice(user_agents)})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            img_urls = soup.find(class_='article-fulltext').find_all('img')
            for i, img_url in enumerate(img_urls):
                image_url = img_url['src']
                exts = image_url.split("/")
                ext = exts[-1].split("?")[0]
                save_path = os.path.join(save_dir, f"{page}-{i}.{ext}")
                info = f"save image path: {save_path}"
                console.info(info, end='\r')
                if os.path.exists(save_path):
                    print('\r' +' '*(len(info) + 3), end='\r')
                    console.warn(f"this image path exist: {save_path}")
                else:
                    print("")
                    download_image(image_url, save_path)
    except Exception as e:
        console.err(f"Failed to start download thread: {url}")
        print(e)

def start_download_buondua(url, save_dir):
    try:
        response = requests.get(url, headers={'User-Agent': random.choice(user_agents)})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            try:
                # 图集
                page_urls = soup.find(class_='pagination-list').select('span > a')
                page_title = soup.find(class_="article-header").find("h1").text
                folder_name = re.sub(r'[\\/:\*\?"<>\|]', "-", page_title)
                if len(page_urls) > 0:# 如果是图集
                    for i, page_url in enumerate(page_urls):
                        image_url = urljoin(base_url, page_url['href'])
                        console.add(f"add threading url: {image_url}")
                        save_path = os.path.join(save_dir, folder_name)
                        console.info(f"save dir: {save_path}")
                        if not os.path.exists(save_path): os.makedirs(save_path)
                        start_download_image_thread(image_url, i + 1, save_path)
                else:
                    console.warn(f"Not find page by album : {url}")
            except Exception as e:
                console.info(f"This {url} is not {console.YELLOW} Album {console.GREEN}, it should be an {console.BLUE} Albums")

                # 图集列表
                album_urls = soup.select('.view-list .page-header a')
                if len(album_urls) > 0:# 如果是图集
                    for i, album_url in enumerate(album_urls):
                        album_title = album_url.text.split("\n")[1]
                        album_url = urljoin(base_url, album_url['href'])
                        console.info(f"start album: {console.BLUE}《{album_title}》")
                        console.add(f"add threading url: {album_url}")
                        start_download_buondua(album_url, save_dir)
                else:
                    console.warn(f"Not find album by albums: {url}")

    except Exception as e:
        console.err(f"Failed to start download buondua: {url}")
        print(e)

def just(url, save_dir, executor):
    # 如果是https://buondua.com/开头，那么就
    if url.startswith('https://buondua.com/'):
        #执行
        executor.submit(start_download_buondua, url, save_dir)
    else:
        # todo： 如果url不是链接，那么就认为是链接的部分
        # 或者 是开头的https://buondua.com/
        if not is_url(url):
            album_url = f'{base_url}{url}'
            executor.submit(start_download_buondua, album_url, save_dir)
        else:
            console.err(f"unkown url: {url}")

def main():
    save_dir, num_threads = get_settings()

    os.makedirs(save_dir, exist_ok=True)

    console.reset(console.BLUE, "\nBuondua Downloader\n")
    console.reset(console.RESET, f"支持如下Key: \n1. 图集ID: 31465\n2. 链接Pathname: pure-media-vol-232-onix-오닉스-hot-debut-99-photos-30151、hot\n3. 完整链接: https://buondua.com/?start=1\n")

    console.info(f"保存目录: {console.BLUE}{save_dir}")
    console.info(f"线程数: {console.BLUE}{num_threads}")

    keys = input("输入关键信息(图集ID、链接Pathname、以及完整链接，用空格分隔): ").split()
    # keys = ['31465', 'pure-media-vol-232-onix-오닉스-hot-debut-99-photos-30151', "https://buondua.com/?start=1", "https://buondua.com/tag/pure-media-10876"]  # 示例，可以根据你的需求修改

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for key in keys:
            just(key, save_dir, executor)

        # 等待线程池中的所有线程执行完毕
        executor.shutdown(wait=True)
    download_err_images()

if __name__ == '__main__':
    main()


    # 31465 pure-media-vol-232-onix-오닉스-hot-debut-99-photos-30151 https://buondua.com/?start=1 https://buondua.com/tag/pure-media-10876