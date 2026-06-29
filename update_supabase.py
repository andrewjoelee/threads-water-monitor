import requests
from supabase import create_client, Client
import time

# 🔐 設定你的 Supabase 連線資訊
SUPABASE_URL = "https://azezhxlatzfgltzqguoa.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_FPMDx4PO77A99RzoVbs3XQ_P9R5aOFP"

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def fetch_threads_followers_via_api(threads_username):
    """
    透過公共 API 接口直接撈取 JSON 數據，避免 GitHub Actions 的 IP 被 Threads 網頁阻擋。
    """
    url = f"https://ungh.cc/users/{threads_username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "followers" in data["user"]:
                return int(data["user"]["followers"])
        return None
    except Exception as e:
        print(f"💥 使用 API 讀取 @{threads_username} 出錯: {e}")
        return None

def main():
    print("🔄 開始自 Supabase 讀取目前飲水機清單...")
    # 🎯 這裡撈取「id」，因為你目前的資料表裡，id 欄位放的是英文帳號（例如 fhsh_waterdispenser）
    response = supabase.table("water_dispensers").select("id").execute()
    items = response.data
    
    if not items:
        print("📭 資料庫內沒有資料！")
        return

    for item in items:
        # 💡 真正的英文 Username 在 id 欄位裡
        threads_username = item['id']
        
        print(f"🔎 正在透過 API 撈取真正帳號 @{threads_username} 的最新數據...")
        followers_count = fetch_threads_followers_via_api(threads_username)
        
        if followers_count is not None:
            print(f"✨ 成功抓取！粉絲數: {followers_count}")
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # 🚀 依據你現有的「id」欄位進行更新
            supabase.table("water_dispensers") \
                .update({
                    "followers": str(followers_count), # 配合你資料庫的 text 格式
                    "last_updated_time": current_time
                }) \
                .eq("id", threads_username) \
                .execute()
            print(f"✅ @{threads_username} 雲端數據同步成功！")
        else:
            print(f"⚠️ API 無法取得 @{threads_username} 數據，跳過不更新")
            
        time.sleep(3)

if __name__ == "__main__":
    main()
