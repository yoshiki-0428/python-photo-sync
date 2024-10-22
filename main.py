import os
import asyncio
import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 認証スコープ
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# 認証を行い、Google Photos APIにアクセスできるようにする
def authenticate_google_photos():
    print("Authenticating with Google Photos API...")
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("Token loaded from token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("Token refreshed.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            print("New token created.")
        # トークンを保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Token saved to token.json.")
    return creds

# 非同期ダウンロード処理
async def download_video(session, media_item, download_path):
    file_name = os.path.join(download_path, media_item['filename'])

    # ファイルがすでに存在している場合はスキップ
    if os.path.exists(file_name):
        print(f"File already exists, skipping: {media_item['filename']}")
        return False  # ダウンロードしなかったことを示す

    # 動画のURLを取得してダウンロード
    download_url = media_item['baseUrl'] + "=dv"
    try:
        async with session.get(download_url) as response:
            with open(file_name, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
        print(f"Downloaded: {media_item['filename']}")
        return True  # ダウンロードが成功したことを示す
    except Exception as e:
        print(f"Failed to download {media_item['filename']}: {e}")
        return False  # ダウンロードが失敗したことを示す

# メイン処理の非同期版
async def process_videos(service, download_path):
    os.makedirs(download_path, exist_ok=True)

    next_page_token = None
    total_downloaded = 0
    skipped_files = 0

    async with aiohttp.ClientSession() as session:
        print("Starting video download...")

        # 動画の取得とダウンロードの繰り返し
        while True:
            # APIリクエストを送信して動画を取得
            results = service.mediaItems().search(
                body={"pageSize": 100, "pageToken": next_page_token, "filters": {"mediaTypeFilter": {"mediaTypes": ["VIDEO"]}}}
            ).execute()

            items = results.get('mediaItems', [])
            if not items:
                print("No more videos found.")
                break

            # 10個ずつ非同期で並列ダウンロードを実行
            for i in range(0, len(items), 10):
                batch = items[i:i + 10]
                tasks = [download_video(session, item, download_path) for item in batch]
                batch_results = await asyncio.gather(*tasks)

                for result in batch_results:
                    if result:
                        total_downloaded += 1
                    else:
                        skipped_files += 1
                print(f"Progress: {total_downloaded} videos downloaded, {skipped_files} files skipped")

            # 次のページに移動
            next_page_token = results.get('nextPageToken')
            if not next_page_token:
                break

    print(f"Process completed. Total videos downloaded: {total_downloaded}, Files skipped: {skipped_files}")

def main():
    creds = authenticate_google_photos()
    service = build('photoslibrary', 'v1', static_discovery=False, credentials=creds)

    download_path = './downloaded_videos'

    # 非同期処理の開始
    asyncio.run(process_videos(service, download_path))


if __name__ == '__main__':
    main()
