# coding: utf8
from iris import ChatContext
import json
import sqlite3
import os
import re

DB_PATH = "iris.db"

FIELD_LABELS = {
    'nickname_age_location': '닉네임/나이/상세지역',
    'mbti_height': 'MBTI/키',
    'married_children': '기미돌/자녀',
    'ideal_type': '썸상형',
    'charm_point': '나의 매력 포인트',
    'day_night': '낮프밤프',
    'mobility': '기동성',
    'join_date': '입방날짜'
}

def init_db():
    """자소서 테이블 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cover_letters (
            user_id TEXT PRIMARY KEY,
            user_name TEXT,
            nickname_age_location TEXT,
            mbti_height TEXT,
            married_children TEXT,
            ideal_type TEXT,
            charm_point TEXT,
            day_night TEXT,
            mobility TEXT,
            join_date TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def parse_cover_letter(msg):
    """자소서 메시지에서 각 항목 파싱"""
    data = {}
    
    # 각 항목 파싱 (더 유연한 패턴)
    patterns = {
        'nickname_age_location': r'💟닉네임/나이/(?:상세)?지역\s*[-:–]\s*(.+)',
        'mbti_height': r'💟MBTI/키\s*[-:–]\s*(.+)',
        'married_children': r'💟기미돌/자녀\s*[-:–]\s*(.+)',
        'ideal_type': r'💟썸상형\s*[-:–]\s*(.+)',
        'charm_point': r'💟나의\s*매력\s*포인트\s*[-:–]\s*(.+)',
        'day_night': r'💟낮프밤프\s*[-:–]\s*(.+)',
        'mobility': r'💟기동성[^-:–]*[-:–]\s*(.+)',
        'join_date': r'💥입방날짜\s*[:：]\s*(.+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            # 값 추출 및 정리 (다음 줄이나 이모지 전까지)
            value = match.group(1).strip()
            # 다음 이모지나 특수 기호 전까지만 추출
            value = re.split(r'\n|💟|💥|🔆', value)[0].strip()
            data[key] = value
        else:
            data[key] = ""
    
    return data

def handle_cover_letter(chat: ChatContext):
    """자소서 관련 기능 처리"""
    # !자소서 명령어 처리
    if chat.message.command == "!자소서":
        show_cover_letter(chat)
        return
    
    # !자소서삭제 명령어 처리
    if chat.message.command == "!자소서삭제":
        delete_cover_letter(chat)
        return
    
    # BOT이 보낸 메시지는 무시
    if chat.sender.type == "BOT":
        return
    
    # 자소서 템플릿이 포함된 메시지 자동 저장
    if "🦋자소서🦋" in chat.message.msg:
        save_cover_letter(chat)

def save_cover_letter(chat: ChatContext):
    """자소서를 SQLite DB에 저장"""
    try:
        msg = chat.message.msg
        user_id = str(chat.sender.id)
        user_name = chat.sender.name
        
        # 자소서 파싱
        parsed_data = parse_cover_letter(msg)
        
        # 디버깅: 파싱된 데이터 출력
        print(f"[DEBUG] 파싱된 데이터 - 유저: {user_name}")
        for key, value in parsed_data.items():
            print(f"  {key}: '{value}' (비어있음: {not value.strip()})")
        
        # 빈 항목 확인
        empty_fields = [FIELD_LABELS[key] for key, value in parsed_data.items() if not value.strip()]
        
        # 전부 비어있으면 아무 멘트 없이 무시
        if len(empty_fields) == len(FIELD_LABELS):
            print(f"[DEBUG] 모든 항목이 비어있어 무시됨")
            return
        
        # 일부 비어있으면 어떤 항목인지 알려주고 저장 거부
        if empty_fields:
            missing = ', '.join(empty_fields)
            print(f"[DEBUG] 비어있는 항목: {missing}")
            chat.reply(f"아래 항목이 비어있어요! 채우고 다시 보내주세요 🥲\n\n📋 {missing}")
            return
        
        # DB 초기화
        init_db()
        
        # 자소서 저장 (있으면 업데이트, 없으면 삽입)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cover_letters 
            (user_id, user_name, nickname_age_location, mbti_height, married_children, 
             ideal_type, charm_point, day_night, mobility, join_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id, 
            user_name,
            parsed_data.get('nickname_age_location', ''),
            parsed_data.get('mbti_height', ''),
            parsed_data.get('married_children', ''),
            parsed_data.get('ideal_type', ''),
            parsed_data.get('charm_point', ''),
            parsed_data.get('day_night', ''),
            parsed_data.get('mobility', ''),
            parsed_data.get('join_date', '')
        ))
        conn.commit()
        conn.close()
        
        chat.reply(f"{chat.sender.name} 님의 자소서가 등록되었습니다!")
        print(f"[INFO] 자소서 저장 완료 - 유저: {user_name}")
    except Exception as e:
        print(f"[ERROR] 자소서 저장 실패 - 유저: {chat.sender.name}, 오류: {e}")
        import traceback
        traceback.print_exc()
        chat.reply("자소서 등록 중 오류가 발생했습니다.")

def show_cover_letter(chat: ChatContext):
    """자소서 조회 - 멘션된 유저 또는 본인의 자소서 표시"""
    target_user_id = None
    
    # 멘션 확인
    if chat.message.attachment:
        try:
            # attachment가 이미 dict인지 string인지 확인
            if isinstance(chat.message.attachment, str):
                attachment = json.loads(chat.message.attachment)
            else:
                attachment = chat.message.attachment
            
            mentions = attachment.get('mentions', [])
            if mentions:
                target_user_id = str(mentions[0]['user_id'])
        except Exception as e:
            print(f"[WARN] 멘션 파싱 실패: {e}")
    
    # 멘션이 없으면 본인 자소서
    if not target_user_id:
        target_user_id = str(chat.sender.id)
    
    # DB에서 자소서 조회
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nickname_age_location, mbti_height, married_children, 
                   ideal_type, charm_point, day_night, mobility, join_date
            FROM cover_letters 
            WHERE user_id = ?
        ''', (target_user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # 자소서 포맷팅 (들여쓰기 제거)
            response = f"""🦋자소서🦋
💟닉네임/나이/상세지역- {result[0]}
💟MBTI/키- {result[1]}
💟기미돌/자녀 - {result[2]}
💟썸상형 - {result[3]}
💟나의 매력 포인트 - {result[4]}
💟낮프밤프- {result[5]}
💟기동성(이동할수있는)- {result[6]}
💥입방날짜: {result[7]}
🔆지우지말고 복붙"""
            
            chat.reply(response)
        else:
            if target_user_id == str(chat.sender.id):
                chat.reply("등록된 자소서가 없습니다.\n자소서 템플릿을 채워서 보내주세요!")
            else:
                chat.reply("해당 유저의 자소서가 등록되지 않았습니다.")
    except Exception as e:
        print(f"[ERROR] 자소서 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        chat.reply("자소서 조회 중 오류가 발생했습니다.")

def delete_cover_letter(chat: ChatContext):
    """자소서 삭제 - 본인의 자소서만 삭제 가능"""
    try:
        user_id = str(chat.sender.id)
        user_name = chat.sender.name
        
        # DB에서 자소서 존재 확인
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM cover_letters WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            chat.reply("삭제할 자소서가 없습니다.")
            conn.close()
            return
        
        # 자소서 삭제
        cursor.execute('DELETE FROM cover_letters WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        chat.reply("자소서가 삭제되었습니다. 🗑️")
        
    except Exception as e:
        print(f"[ERROR] 자소서 삭제 실패 - 유저: {chat.sender.name}, 오류: {e}")
        import traceback
        traceback.print_exc()
        chat.reply("자소서 삭제 중 오류가 발생했습니다.")

def get_cover_letter_template(chat: ChatContext):
    """자소서 템플릿 전송"""
    template = """🦋자소서🦋
💟닉네임/나이/상세지역-
💟MBTI/키-
💟기미돌/자녀 -
💟썸상형 - 
💟나의 매력 포인트 -
💟낮프밤프- 
💟기동성(이동할수있는)-
💥입방날짜: 
🔆지우지말고 복붙"""
    
    chat.reply(template)