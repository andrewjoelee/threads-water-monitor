import requests
from supabase import create_client, Client
import time
import json
import re

# 🔐 設定你的 Supabase 連線資訊
SUPABASE_URL = "https://azezhxlatzfgltzqguoa.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_FPMDx4PO77A99RzoVbs3XQ_P9R5aOFP"

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def fetch_followers(threads_id):
    """
    雙保險機制抓取 Threads 粉絲數
    """
    # ------------------ 🚀 第一條路：透過 Allorigins 開源網頁代理 ------------------
    proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(f'https://www.threads.net/@{threads_id}')}"
    try:
        response = requests.get(proxy_url, timeout=15)
        if response.status_code == 200:
            html_content = response.json().get('contents', '')
            
            # 嘗試 1：抓取網頁底層的真實數字變數
            match_num = re.search(r'"follower_count":\s*([0-9]+)', html_content)
            if match_num:
                return int(match_num.group(1))
                
            # 嘗試 2：抓取 meta description 裡面的文字
            match_meta = re.search(r'([0-9\.,KkMm]+)\s*(?:followers|名粉絲|位粉絲)', html_content)
            if match_meta:
                val = match_meta.group(1).upper()
                if 'K' in val:
                    return int(float(val.replace('K', '')) * 1000)
                if 'M' in val:
                    return int(float(val.replace('M', '')) * 1000000)
                return int(val.replace(',', ''))
    except Exception as e:
        print(f"ℹ️ 主要代理管道嘗試未果，準備切換備用管道...")

    # ------------------ 🚀 第二條路：切換公共 API 備用鏡像 ------------------
    fallback_url = f"https://ungh.cc/users/{threads_id}"
    try:
        fb_res = requests.get(fallback_url, timeout=10)
        if fb_res.status_code == 200:
            fb_data = fb_res.json()
            if "user" in fb_data and "followers" in fb_data["user"]:
                return int(fb_data["user"]["followers"])
    except Exception as e:
        print(f"💥 備用管道亦發生異常: {e}")

    return None

def main():
    print("🔄 開始自 Supabase 讀取目前飲水機清單...")
    
    # 🎯 核心修正：完全捨棄舊的 id，改為撈取你全新改好的 threads_id 欄位！
    response = supabase.table("water_dispensers").select("threads_id").execute()
    items = response.data
    
    if not items:
        print("📭 資料庫內沒有資料！")
        return

    for item in items:
        threads_id = item['threads_id']
        
        print(f"🔎 正在爬取真正的 Threads 帳號 @{threads_id} 的最新數據...")
        followers_count = fetch_followers(threads_id)
        
        if followers_count is not None:
            followers_str = str(followers_count)
            print(f"✨ 成功抓取！粉絲數: {followers_str}")
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # 🚀 核心修正：更新條件完全對準 threads_id 欄位
            supabase.table("water_dispensers") \
                .update({
                    "followers": followers_str, 
                    "last_updated_time": current_time
                }) \
                .eq("threads_id", threads_id) \
                .execute()
            print(f"✅ @{threads_id} 雲端數據同步成功！")
        else:
            print(f"⚠️ 無法取得 @{threads_id} 數據，跳過不更新")
            
        time.sleep(5)

if __name__ == "__main__":
    main()
