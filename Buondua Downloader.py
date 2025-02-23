import os
import re
import sys
import concurrent.futures
from urllib.parse import urljoin, urlsplit, unquote
import requests
import random
import threading
import yaml
import time
from bs4 import BeautifulSoup

base_url = "https://buondua.us"
# 配置路径
SETTING_PATH = "setting.yml"

# 定义User-Agent池
USER_AGENTS = [
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
]

# 全局变量
err_images = []
counter = 0  # 计数器，用于记录已下载的图片数量
max_counter = 50
wait = 10
lock = threading.Lock()  # 创建一个线程锁对象


class Console:
    """控制台输出类，用于美化输出"""
    def __init__(self):
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.BLUE = '\033[94m'
        self.RESET = '\033[0m'
    
    def reset(self, color, mes, end='\n', flush=False):
        print(color + mes + self.RESET, end=end, flush=flush)

    def add(self, mes, end='\n', flush=False):
        self.reset(self.BLUE, f"[+] {mes}", end=end, flush=flush)

    def err(self, mes, end='\n', flush=False):
        self.reset(self.YELLOW, f"[-] {mes}", end=end, flush=flush)
    
    def info(self, mes, end='\n', flush=False):
        self.reset(self.GREEN, f"[#] {mes}", end=end, flush=flush)
    
    def warn(self, mes, end='\n', flush=False):
        self.reset(self.RED, f"[!] {mes}", end=end, flush=flush)


console = Console()


def get_system_proxy():
    """获取并过滤系统代理设置，仅保留 HTTP 和 HTTPS 代理"""
    from urllib.request import getproxies
    proxies = getproxies()
    filtered_proxies = {k: v.replace('https', 'http') if k == 'https' else v for k, v in proxies.items() if k in ['http', 'https']}
    
    if filtered_proxies:
        console.info(f"检测到系统代理配置：{filtered_proxies}")
    else:
        console.info("未检测到系统代理配置。")
    
    return filtered_proxies


def save_image(image_data, save_path):
    """保存图片数据到指定路径，确保文件夹存在并正确保存图片"""
    try:
        # 去除文件夹和文件名称中的非法字符
        folder_name = re.sub(r' ', "_", os.path.dirname(save_path))
        file_name = re.sub(r'[\\/:\*\?"<>\|]', "-", os.path.basename(save_path))
        save_path = os.path.join(folder_name, file_name)

        # 确保文件夹存在，如果不存在就创建
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 保存图片到文件
        with open(save_path, 'wb') as file:
            file.write(image_data)

        console.info(f"图片已保存: {save_path}")

    except Exception as e:
        console.err(f"保存图片失败: {save_path}")
        print(e)


def get_extension_from_url(url):
    """从图片URL中提取扩展名，不包括点号，并转换为小写"""
    path = urlsplit(url).path
    base = os.path.basename(unquote(path))
    _, ext = os.path.splitext(base)
    return ext.lstrip('.').lower()


def format_filename(page, index, ext):
    """格式化文件名称，页码采用三位数字，图片序号采用两位数字"""
    try:
        page_num = int(page)
        page_str = f"{page_num:03d}"
    except ValueError:
        page_str = str(page)
    image_str = f"{index+1:02d}"
    return f"{page_str}-{image_str}.{ext}"


def is_url(string):
    """判断是否为有效URL"""
    url_pattern = re.compile(r'^https?://\S+$', re.IGNORECASE)
    return bool(re.match(url_pattern, string))


def get_settings():
    """获取或创建配置文件"""
    global base_url, max_counter, wait
    
    default_settings = {
        'save_path': "downloads",
        'num_threads': 5,
        'max_counter': 50,
        'wait': 10,
        'base_url': "https://buondua.com"
    }

    if not os.path.exists(SETTING_PATH):
        with open(SETTING_PATH, 'w') as f:
            yaml.dump(default_settings, f)
        return default_settings['save_path'], default_settings['num_threads']

    with open(SETTING_PATH, 'r') as f:
        settings = yaml.safe_load(f)
        save_dir = settings.get('save_path', default_settings['save_path'])
        num_threads = settings.get('num_threads', default_settings['num_threads'])
        base_url = settings.get('base_url', default_settings['base_url'])
        max_counter = settings.get('max_counter', default_settings['max_counter'])
        wait = settings.get('wait', default_settings['wait'])
        return save_dir, num_threads


def download_image(url, save_path, max_counter, wait):
    """下载图片并保存"""
    global counter
    try:
        with lock:
            response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, proxies=proxies)
            if response.status_code == 200:
                counter += 1
                save_image(response.content, save_path)
                if counter % max_counter == 0:
                    console.warn(f"下载了{max_counter}张图片，暂停{wait}秒...")
                    time.sleep(wait)
            else:
                console.err(f"[code: {response.status_code}] Failed to download image: {url}")
    except Exception as e:
        console.err(f"Failed to download image: {url}")
        err_images.append({"url": url, "save": save_path})
        print(e)


def start_download_image_thread(url, page, save_dir, max_counter, wait):
    """启动下载图片的线程"""
    try:
        response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, proxies=proxies)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            img_urls = soup.find(class_='article-fulltext').find_all('img')
            for i, img_url in enumerate(img_urls):
                image_url = img_url['src']
                ext = get_extension_from_url(image_url)
                save_path = os.path.join(save_dir, format_filename(page, i, ext))
                if os.path.exists(save_path):
                    console.warn(f"图片已存在: {save_path}")
                else:
                    download_image(image_url, save_path, max_counter, wait)
        else:
            console.err(f"[code: {response.status_code}] Failed to start download thread: {url}")
    except Exception as e:
        console.err(f"[Error] Failed to start download thread: {url}")
        print(e)


def start_download_buondua(url, save_dir, max_counter, wait):
    """启动下载buondua的线程"""
    try:
        response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, proxies=proxies)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                # 图集
                page_urls = soup.find(class_='pagination-list').select('span > a')
                page_title = soup.find(class_="article-header").find("h1").text
                folder_name = re.sub(r'[\\/:\*\?"<>\|]', "-", page_title)
                if page_urls:
                    for i, page_url in enumerate(page_urls):
                        image_url = urljoin(base_url, page_url['href'])
                        console.add(f"添加线程URL: {image_url}")
                        save_path = os.path.join(save_dir, folder_name)
                        start_download_image_thread(image_url, i + 1, save_path, max_counter, wait)
                else:
                    console.info(f"没有找到图集: {url}")
            except Exception as e:
                # 图集列表
                album_urls = soup.select('a.item-link.popunder')
                if album_urls:
                    for album_url in album_urls:
                        album_title = album_url.select_one('img').get('alt')
                        album_url = urljoin(base_url, album_url['href'])
                        console.info(f"开始图集: {console.BLUE}《{album_title}》")
                        start_download_buondua(album_url, save_dir, max_counter, wait)
                else:
                    console.warn(f"没有从图集列表中找到图集: {url}")
        else:
            console.err(f"[code: {response.status_code}] Failed to start download buondua: {url}")
    except Exception as e:
        console.err(f"[Error] Failed to start download buondua: {url}")
        print(e)


def main():
    save_dir, num_threads = get_settings()
    os.makedirs(save_dir, exist_ok=True)

    console.reset(console.BLUE, "\nBuondua Downloader\n")
    console.reset(console.RESET, f"支持如下Key: \n1. 图集ID: 31465\n2. 链接Pathname: pure-media-vol-232-onix-오닉스-hot-debut-99-photos-30151、hot\n3. 完整链接: https://buondua.com/?start=1\n")

    keys = input("输入关键信息(图集ID、链接Pathname、以及完整链接，用空格分隔): ").split()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for key in keys:
            if key.startswith(base_url):
                executor.submit(start_download_buondua, key, save_dir, max_counter, wait)
            else:
                album_url = urljoin(base_url, key) if not is_url(key) else key
                executor.submit(start_download_buondua, album_url, save_dir, max_counter, wait)

        executor.shutdown(wait=True)
    
    if err_images:
        console.warn(f"尝试重新下载 {len(err_images)} 张失败的图片...")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for image in err_images:
                executor.submit(download_image, image["url"], image["save"], max_counter, wait)


if __name__ == '__main__':
    proxies = get_system_proxy()
    main()
