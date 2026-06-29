import os
import re
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
from supabase import create_client, Client

# 🔐 設定你的 Supabase 連線資訊
SUPABASE_URL = "https://azezhxlatzfgltzqguoa.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_FPMDx4PO77A99RzoVbs3XQ_P9R5aOFP"

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_threads_follower(page, username):
    """【完全保留你原本的爬蟲原理】使用 Playwright 模擬真人載入網頁撈取粉絲數"""
    target_url = f"https://www.threads.net/@{username}"
    try:
        # 模擬真人正常滾動載入
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000) 

        # 方案 A：直接從網頁的 meta description 撈
        meta_desc = page.locator('meta[name="description"]').get_attribute("content")
        if meta_desc:
            meta_match = re.search(r"([\d\.,\s]+[M|K|萬|億]?)\s*(followers|位粉絲)", meta_desc, re.IGNORECASE)
            if meta_match:
                return meta_match.group(1).strip()

        # 方案 B：如果 meta 沒撈到，直接搜尋網頁原始碼
        page_content = page.content()
        match = re.search(r"([\d\.,\s]+[M|K|萬]?)\s*(followers|位粉絲)", page_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return "未公開/格式變更"
    except Exception as e:
        print(f"❌ 抓取 @{username} 失敗: {e}")
        return "抓取錯誤"


def main():
    print("🔄 [開始] 自 Supabase 讀取目前排整齊的飲水機清單...")
    
    # 撈取你最新的 threads_id 欄位（英文帳號）
    response = supabase.table("water_dispensers").select("threads_id").execute()
    items = response.data
    
    if not items:
        print("📭 資料庫內沒有資料！")
        return
        
    threads_accounts = [item['threads_id'] for item in items if item.get('threads_id')]
    print(f"📋 偵測到共有 {len(threads_accounts)} 個飲水機帳號準備更新...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for idx, username in enumerate(threads_accounts, start=1):
            print(f"🔎 [{idx}/{len(threads_accounts)}] 正在透過 Playwright 讀取網頁 @{username}")
            followers = get_threads_follower(page, username)
            print(f"-> 粉絲數結果: {followers}")

            if followers not in ["抓取錯誤", "未公開/格式變更"]:
                # 🎯 核心修正：強制轉換為台灣時區 (UTC+8)
                tz_taiwan = timezone(timedelta(hours=8))
                current_time = datetime.now(tz_taiwan).strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"💾 [同步] 正在安全覆寫更新數據回 Supabase (台灣時間: {current_time})...")
                
                # 使用 upsert 對齊主鍵 threads_id，直接覆寫更新
                supabase.table("water_dispensers") \
                    .upsert({
                        "threads_id": username,
                        "followers": followers, 
                        "last_updated_time": current_time
                    }, on_conflict="threads_id") \
                    .execute()
                    
                print(f"✅ @{username} 資料庫數據同步成功！")
            else:
                print(f"⚠️ @{username} 抓取數值異常 ({followers})，跳過不更新資料庫")

            time.sleep(4)

        browser.close()

    print("\n🎉 全數飲水機 Playwright 爬取與 Supabase 同步程序順利完成！")


if __name__ == "__main__":
    main()
