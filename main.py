import os
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# 認証スコープ
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly',
          'https://www.googleapis.com/auth.photoslibrary']

# 認証を行い、Google Photos APIにアクセスできるようにする
def authenticate_google_photos():
    print("Authenticating with Google Photos API...")
    creds = None
    # トークンが既にある場合は読み込む
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("Token loaded from token.json")
    # トークンがないか期限が切れている場合は再認証
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


def download_video(media_item, download_path):
    # 動画のURLを取得しダウンロード
    download_url = media_item['baseUrl'] + "=dv"
    response = requests.get(download_url, stream=True)

    # ファイルの保存
    file_name = os.path.join(download_path, media_item['filename'])
    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {media_item['filename']}")



def main():
    creds = authenticate_google_photos()
    service = build('photoslibrary', 'v1', static_discovery=False, credentials=creds)

    download_path = './downloaded_videos'
    os.makedirs(download_path, exist_ok=True)

    next_page_token = None
    total_downloaded = 0
    total_deleted = 0

    print("Starting video download...")

    # 動画の取得とダウンロード、削除の繰り返し
    while True:
        results = service.mediaItems().search(
            body={"pageSize": 100, "pageToken": next_page_token, "filters": {"mediaTypeFilter": {"mediaTypes": ["VIDEO"]}}}
        ).execute()

        items = results.get('mediaItems', [])
        if not items:
            print("No more videos found.")
            break

        for item in items:
            download_video(item, download_path)
            total_downloaded += 1
            print(f"Progress: {total_downloaded} videos downloaded")

        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break

    print(f"Process completed. Total videos downloaded: {total_downloaded}, Total videos deleted: {total_deleted}")


if __name__ == '__main__':
    main()
