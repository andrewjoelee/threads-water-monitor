import os
import re
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright

# === Supabase 設定區 ===
# 建議將這些敏感資訊設定在 GitHub Actions的 Secrets 中，透過 os.environ 讀取
# 如果想先在本機測試，可以直接把引號內換成你的 Supabase 網址與 anon key
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://azezhxlatzfgltzqguoa.supabase.co/rest/v1/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_FPMDx4PO77A99RzoVbs3XQ_P9R5aOFP")

# 你的資料表名稱（假設叫做 water_dispensers）
TABLE_NAME = "water_dispensers"


def get_accounts_from_supabase():
    """從 Supabase 撈取所有需要爬取的飲水機帳號資料"""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=id,threads_id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # 過濾掉沒有填寫 threads_id 的資料，並整理成清單
            valid_accounts = [item for item in data if item.get("threads_id")]
            return valid_accounts
    except Exception as e:
        print(f"❌ 從 Supabase 讀取帳號清單失敗: {e}")
        return []


def update_supabase_followers(record_id, followers):
    """將抓到的粉絲數，透過 API 更新回 Supabase 對應的 ID 欄位"""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?id=eq.{record_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"  # 告訴 Supabase 不需要回傳更新後的整筆資料，省流量
    }
    
    # 準備更新的欄位資料
    payload = json.dumps({
        "followers": followers,
        "updated_at": datetime.utcnow().isoformat()  # 有需要的話也可以順便紀錄更新時間
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req, timeout=15) as response:
            return "更新成功"
    except Exception as e:
        return f"更新失敗: {e}"


def get_threads_follower(page, username):
    """抓取單一 Threads 帳號的粉絲數（保持你最穩定的方案 A & B）"""
    target_url = f"https://www.threads.net/@{username}"
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000) 

        # 方案 A：從 meta description 撈
        meta_desc = page.locator('meta[name="description"]').get_attribute("content")
        if meta_desc:
            meta_match = re.search(r"([\d\.,\s]+[M|K|萬|億]?)\s*(followers|位粉絲)", meta_desc, re.IGNORECASE)
            if meta_match:
                return meta_match.group(1).strip()

        # 方案 B：暴力搜網頁原始碼
        page_content = page.content()
        match = re.search(r"([\d\.,\s]+[M|K|萬]?)\s*(followers|位粉絲)", page_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return "未公開/格式變更"
    except Exception as e:
        print(f"❌ 抓取 @{username} 失敗: {e}")
        return "抓取錯誤"


def main():
    print("📡 正在連線至 Supabase 獲取飲水機清單...")
    accounts = get_accounts_from_supabase()
    
    if not accounts:
        print("⚠️ 未在本台發現任何有效的 threads_id，程式結束。")
        return

    print(f"📋 偵測到共有 {len(accounts)} 個飲水機帳號準備從 Threads 更新...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for idx, account in enumerate(accounts, start=1):
            record_id = account["id"]
            username = account["threads_id"]

            print(f"🔎 [{idx}/{len(accounts)}] 正在網頁讀取 @{username}")
            followers = get_threads_follower(page, username)
            print(f"-> 粉絲數: {followers}")

            print(f"💾 正在同步更新至 Supabase (ID: {record_id})...")
            api_result = update_supabase_followers(record_id, followers)
            print(f"-> Supabase 後台回應: {api_result}")

            time.sleep(3)

        browser.close()

    print("\n🎉 Supabase 資料庫更新程序完全執行完畢！")


if __name__ == "__main__":
    main()
