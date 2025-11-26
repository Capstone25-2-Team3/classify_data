from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import time

# =========================================================
# ⚠️ 1. 이 경로를 다운로드한 JSON 키 파일의 경로로 변경해야 합니다.
SERVICE_ACCOUNT_FILE = 'drive_access.json' 

# ⚠️ 2. 검색을 원하는 특정 Google Drive 폴더의 ID를 여기에 입력하세요.
# 폴더 ID는 해당 폴더의 Drive URL에서 'folders/' 뒤에 나오는 긴 문자열입니다.
# 예: '1aBcDeFgHiJkLmNoPqRsTuVwXyZ0'
TARGET_FOLDER_ID = '1_Txqyp9l0Mx7tZrEBAoGX_bfXjiD6459' 
# =========================================================

# Google Drive 파일의 읽기 전용 권한 설정
SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] 

def get_drive_service():
    """Google Drive API 서비스 객체를 반환합니다."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"서비스 계정 인증 오류: {e}")
        print(f"'{SERVICE_ACCOUNT_FILE}' 파일이 올바른 경로에 있는지 확인하고, Drive API가 활성화되었는지 확인하세요.")
        exit()

def process_drive_files():
    """
    특정 폴더 내의 파일(TXT 파일로 가정)을 읽어 모든 줄을 수집하고 
    로컬 파일에 저장합니다.
    """

    service = get_drive_service()
    all_lines = []
    local_output_filename = "collected_drive_lines.txt"

    # 특정 폴더 ID 내에 있고, 휴지통에 없는 파일만 검색하는 쿼리
    search_query = f"'{TARGET_FOLDER_ID}' in parents and trashed = false"

    print(f"대상 폴더 ID '{TARGET_FOLDER_ID}' 내의 파일 목록을 가져오는 중...")
    
    try:
        results = service.files().list(
            pageSize=1000, 
            q=search_query, # 👈 여기가 수정된 핵심 부분입니다.
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
    except Exception as e:
        print(f"파일 목록 조회 오류: {e}")
        return

    if not items:
        print(f"대상 폴더에서 접근 가능한 파일을 찾을 수 없습니다.")
        print("서비스 계정의 이메일 주소가 해당 폴더에 '뷰어' 권한 이상으로 공유되었는지 다시 한번 확인하세요.")
        return

    print(f"총 {len(items)}개의 파일을 찾았습니다. 내용을 처리하는 중...")

    for i, item in enumerate(items):
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        
        # Google Docs, Sheets 등의 마임타입은 건너뜁니다.
        if mime_type.startswith('application/vnd.google-apps.'):
            print(f"[{i+1}/{len(items)}] 파일 '{file_name}' ({mime_type})은 Google Workspace 문서이므로 건너뜁니다.")
            continue

        print(f"[{i+1}/{len(items)}] 파일 '{file_name}' 처리 중...")

        try:
            # 파일 내용 다운로드
            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # 다운로드된 내용을 문자열로 디코딩하고 각 줄을 리스트에 저장
            file_content_string = file_content.getvalue().decode('utf-8')
            
            lines = file_content_string.splitlines()
            all_lines.extend(lines)
            print(f"  -> {len(lines)} 줄 수집 완료.")

        except Exception as e:
            print(f"  -> 오류 발생: 파일 '{file_name}'를 처리할 수 없습니다. (오류: {e})")
            continue
        
        time.sleep(0.1)
    
    # 수집된 모든 줄을 하나의 로컬 TXT 파일에 저장
    print(f"\n총 {len(all_lines)}개의 줄을 수집했습니다. 로컬 파일 '{local_output_filename}'에 저장하는 중...")
    with open(local_output_filename, 'w', encoding='utf-8') as f:
        for line in all_lines:
            f.write(line + '\n')
            
    print(f"\n✅ 작업 완료! 모든 줄이 '{local_output_filename}' 파일에 성공적으로 저장되었습니다.")

if __name__ == '__main__':
    process_drive_files()