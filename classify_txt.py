import os
import csv
import time
from openai import OpenAI, RateLimitError, APIError

# =========================================================
# ⚠️ 사용자 설정 영역 (이 부분은 반드시 수정해야 합니다)
# =========================================================

# 1. OpenAI API Key 설정
# 환경 변수에 설정된 경우 자동으로 로드되지만, 여기에 직접 입력할 수도 있습니다.
# API_KEY = "여기에_당신의_API_KEY를_입력하세요"
# API_KEY를 설정하지 않으면 환경 변수(OPENAI_API_KEY)를 사용합니다.
# client = OpenAI(api_key=API_KEY)

# 환경 변수 사용을 권장합니다. (터미널에서 export OPENAI_API_KEY='your-key-here' 설정)
client = OpenAI() 

# 2. 로컬 입력 파일 및 출력 파일 경로 설정
INPUT_FILE_PATH = "collected_drive_lines.txt"
OUTPUT_FILE_PATH = "classified_results.csv"

# 3. 분류에 사용할 레이블 목록
LABELS = [
    "여성/가족",
    "남성",
    "성소수자",
    "인종/국적",
    "연령",
    "지역",
    "종교",
    "기타 혐오",
    "악플/욕설",
    "clean"
]

# 4. 사용할 GPT 모델 설정
MODEL_NAME = "gpt-5.1"

# =========================================================
# ⚙️ 함수 정의
# =========================================================

def classify_text_with_gpt(sentence: str, labels: list) -> str:
    """
    주어진 문장을 OpenAI API를 사용하여 분류하고 레이블을 반환합니다.
    """
    label_list_str = ", ".join(labels)
    
    # 혐오 표현 분류에 최적화된 프롬프트 구성
    system_prompt = (
        f"당신은 혐오 표현 분류기입니다. 다음 목록의 10가지 레이블 중 하나로 문장을 분류하고, "
        f"가장 적합한 **하나의 레이블**만을 응답하세요. 다른 설명이나 추가 텍스트는 일절 포함하지 마세요. "
        f"문장을 분류할 때 각 단어별로 혐오 표현이 있는지 확인하고 혐오 표현이 있다면 가장 부합하는 레이블을 선택하세요."
        f"최근 인터넷 커뮤니티에서 떠도는 밈과 같은 부분도 체크하여 반영해야 합니다."
        f"레이블 목록: [{label_list_str}]"
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"분류할 문장: {sentence.strip()}"}
            ],
            temperature=0.0 # 분류 작업에는 낮은 온도(결정적)를 사용합니다.
        )
        
        # 모델의 응답에서 분류된 텍스트(레이블)를 추출
        classified_label = response.choices[0].message.content.strip()
        
        # 분류된 레이블이 우리가 정의한 목록에 없는 경우 '분류_오류'로 표시
        if classified_label not in labels:
            return f"응답_오류: {classified_label}"
            
        return classified_label

    except RateLimitError:
        print("❗️ Rate Limit 초과: 잠시 대기 후 재시도합니다.")
        time.sleep(20) # 20초 대기 후 다시 시도할 수 있도록 처리
        return "Rate_Limit_Error"
    except APIError as e:
        print(f"❗️ API 오류 발생: {e}")
        return "API_Error"
    except Exception as e:
        print(f"❗️ 예기치 않은 오류 발생: {e}")
        return "Unknown_Error"


def process_local_file():
    """
    로컬 TXT 파일을 읽고, 각 줄을 GPT로 분류한 후 CSV 파일로 저장합니다.
    """
    if not os.path.exists(INPUT_FILE_PATH):
        print(f"⚠️ 오류: 입력 파일 '{INPUT_FILE_PATH}'을 찾을 수 없습니다.")
        print("파일 경로를 확인하거나, 해당 경로에 파일을 생성해주세요.")
        return

    results = []
    print(f"파일 '{INPUT_FILE_PATH}'에서 문장을 읽고 분류를 시작합니다...")

    # CSV 파일 쓰기 설정
    with open(OUTPUT_FILE_PATH, 'w', newline='', encoding='utf-8') as outfile:
        csv_writer = csv.writer(outfile)
        # 헤더 작성
        csv_writer.writerow(["Original_Sentence", "Classified_Label"])
        
        # 입력 TXT 파일 읽기
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
            total_lines = len(lines)

            for i, line in enumerate(lines):
                sentence = line.strip()
                if not sentence:
                    continue # 빈 줄 건너뛰기

                # GPT API 호출
                label = classify_text_with_gpt(sentence, LABELS)
                
                # 결과를 CSV 파일에 즉시 기록
                csv_writer.writerow([sentence, label])
                
                print(f"[{i + 1}/{total_lines}] 문장: '{sentence[:30]}...' -> 레이블: {label}")
                
                # API 호출 간격 설정 (rate limit 방지를 위해 중요)
                time.sleep(0.5) 
                
    print("\n")
    print("=" * 50)
    print(f"✅ 작업 완료! 총 {total_lines}개의 문장 처리 완료.")
    print(f"결과는 '{OUTPUT_FILE_PATH}' 파일에 저장되었습니다.")
    print("=" * 50)


if __name__ == '__main__':
    process_local_file()