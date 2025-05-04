import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import subprocess
from queue import Queue


# 配置参数
index = 1
MAX_THREADS = 64
RETRIES = 3
DOWNLOAD_DIR = "res"
USER_AGENT = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"

# 创建下载目录
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# 请求队列和线程管理
request_queue = Queue()
lock = threading.Lock()
active_threads = 0

def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    filename = filename.replace('淫','')
    filename = filename.replace('白浆','')
    filename = filename.replace('自慰','思维')
    filename = filename.replace('交','')
    filename = filename.replace('飞机','')
    filename = filename.replace('撸管','梨瓜')
    filename = filename.replace('穴','')
    filename = filename.replace('裸','卤')
    filename = filename.replace('全卤','窜路')
    filename = filename.replace('鸡鸡','ch')
    filename = filename.replace('牛子','ch')
    filename = filename.replace('爆','叭')
    filename = filename.replace('吊带袜','ddw')
    filename = filename.replace('袜','w')
    filename = filename.replace('丝','s')
    filename = filename.replace('啪啪','')
    filename = filename.replace('羞辱','溴')
    filename = filename.replace('射','丢')
    filename = filename.replace('奶子','让')
    filename = filename.replace('乳','让')
    filename = filename.replace('调教','纸Fe')
    filename = filename.replace('奴','铝')
    filename = filename.replace('手撸','输了')
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in filename).replace(" ", "")

def download_video_with_ffmpeg(video_url, filename):
    global index
    """使用ffmpeg下载m3u8视频"""
    output_file = os.path.join(DOWNLOAD_DIR, f"{index}.{sanitize_filename(filename)}.mp4")
    
    index += 1
    command = [
        'ffmpeg',
        '-i', video_url,
        '-c', 'copy',
        '-threads', '64',
        output_file
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.wait()
        print(f"[✓] 下载成功: {filename}")
    except subprocess.CalledProcessError as e:
        print(f"[✗] 下载失败: {filename} - {str(e)}")

def fetch_page(url):
    """带重试机制的页面获取"""
    headers = {'User-Agent': USER_AGENT}
    for attempt in range(RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"[⚠] 第{attempt+1}次尝试失败 ({url}): {str(e)}")
            time.sleep(2 ** attempt)  # 指数退避
    return None

def process_subpage(subpage_url):
    """处理子页面，提取视频信息"""
    soup = fetch_page(subpage_url)
    if not soup:
        return
        
    # 提取视频URL
    video_wrap = soup.find('div', class_='dplayer w-full')
    if not video_wrap:
        print(f"[!] 未找到视频容器: {subpage_url}")
        return
        
        
    # 提取标题
    title_tag = soup.find('h1', class_='text-xl font-bold pl-3 text-yellow-500')
    if not title_tag:
        print(f"[!] 未找到标题: {subpage_url}")
        return
        
    video_url = video_wrap['data-url']
    if not video_url.startswith("https://"):
        # 如果不包含，则在前面加上
        video_url = "https://zkwu.lol" + video_url
    title = title_tag.get_text(strip=True)
    title = title.replace(' ','_')
    title = title + '.mp4'
    # 启动下载线程
    threading.Thread(
        target=download_video_with_ffmpeg,
        args=(video_url, title),
        daemon=True
    ).start()

def process_page(page_url):
    """处理主页面"""
    global active_threads
    
    soup = fetch_page(page_url)
    if not soup:
        return
        
    # 处理所有子页面
    for div in soup.find_all('div', class_='relative'):
        a_tag = div.find('a')
        if not a_tag or not a_tag.has_attr('href'):
            continue
            
        subpage_url = urljoin(page_url, a_tag['href'])
        process_subpage(subpage_url)
        
    # 查找下一页
    next_page = soup.find('a', rel='next')
    if next_page and next_page.has_attr('href'):
        next_url = urljoin(page_url, next_page['href'])
        request_queue.put(next_url)

def worker():
    """工作线程"""
    global active_threads
    
    while not request_queue.empty():
        try:
            page_url = request_queue.get(timeout=5)
            with lock:
                active_threads += 1
                print(f"[+] 正在处理页面: {page_url}")
                
            process_page(page_url)
            
            with lock:
                active_threads -= 1
                
        except Exception as e:
            print(f"[!] 线程错误: {str(e)}")
            with lock:
                active_threads -= 1

def main():
    """主程序入口"""
    """start_url = input("请输入起始页面地址: ").strip()"""
    start_url = "https://zkwu.lol/tags/%E9%93%83%E6%9C%A8%E7%BE%8E%E5%92%B2?page=1"
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
        
    request_queue.put(start_url)
    
    # 创建并启动线程池
    threads = []
    for _ in range(min(MAX_THREADS, 64)):  # 主页面处理线程限制为10
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)
        
    # 等待所有线程完成
    while not request_queue.empty() or active_threads > 0:
        time.sleep(1)
        
    print("[✓] 所有任务已完成")

if __name__ == "__main__":
    main()