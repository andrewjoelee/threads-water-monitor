import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
import json
import time
import re

# 🔐 設定你的 Supabase 連線資訊
SUPABASE_URL = "https://azezhxlatzfgltzqguoa.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_FPMDx4PO77A99RzoVbs3XQ_P9R5aOFP"

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def parse_followers_to_int(val):
    """
    將爬到的字串（例如 '1.2K', '552', '2,500'）安全轉換為純整數
    """
    if not val:
        return 0
    str_val = str(val).upper().strip()
    try:
        if 'K' in str_val:
            return int(float(str_val.replace('K', '').strip()) * 1000)
        if 'M' in str_val:
            return int(float(str_val.replace('M', '').strip()) * 1000000)
        return int(str_val.replace(',', '').strip())
    except Exception as e:
        print(f"⚠️ 數字轉換失敗 ({val}): {e}")
        return 0

def fetch_threads_followers(threads_id):
    url = f"https://www.threads.net/@{threads_id}"
    # 模擬極度真實的現代瀏覽器 Header，防止被 Threads 阻擋
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 策略 1：先抓常規的 og:description
            meta_tag = soup.find('meta', property='og:description')
            if meta_tag:
                desc = meta_tag.get('content', '')
                # 用正則表達式把「數字+粉絲/followers」直接撈出來
                match = re.search(r'([0-9\.,KkMm]+)\s*(?:followers|名粉絲|位粉絲|follower)', desc)
                if match:
                    return match.group(1).strip()
            
            # 策略 2：如果被改版擋掉，直接大範圍搜尋整個網頁原始碼裡的「粉絲」關鍵字欄位
            html_str = response.text
            match_fallback = re.search(r'"follower_count":\s*([0-9]+)', html_str)
            if match_fallback:
                return match_fallback.group(1).strip()
                
            # 策略 3：針對中文網頁的強硬比對
            match_zh = re.search(r'([0-9\.,KkMm]+)(?:名粉絲|位粉絲)', html_str)
            if match_zh:
                return match_zh.group(1).strip()
                
        return None
    except Exception as e:
        print(f"💥 爬取 @{threads_id} 出錯: {e}")
        return None

def main():
    print("🔄 開始自 Supabase 讀取目前飲水機清單...")
    response = supabase.table("water_dispensers").select("id, threads_id").execute()
    items = response.data
    
    if not items:
        print("📭 資料庫內沒有資料！")
        return

    for item in items:
        record_id = item['id']
        # 如果欄位裡沒有特別寫 threads_id，就拿原本的 id 當作帳號
        threads_id = item['threads_id'] if item.get('threads_id') else record_id
        
        print(f"🔎 正在爬取 @{threads_id} 的最新 Threads 數據...")
        raw_followers = fetch_threads_followers(threads_id)
        
        if raw_followers is not None:
            int_followers = parse_followers_to_int(raw_followers)
            print(f"✨ 成功抓取！原始資料: {raw_followers} -> 轉為整數: {int_followers}")
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # 🚀 寫入 Supabase
            supabase.table("water_dispensers") \
                .update({
                    "followers": int_followers, 
                    "last_updated_time": current_time
                }) \
                .eq("id", record_id) \
                .execute()
            print(f"✅ @{threads_id} 雲端數據同步成功！")
        else:
            print(f"⚠️ 無法取得 @{threads_id} 數據，跳過不更新")
            
        time.sleep(5) # 稍微拉長間隔，防止被連鎖封鎖

if __name__ == "__main__":
    main()
