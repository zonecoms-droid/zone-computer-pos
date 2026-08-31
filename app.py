import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
import os
import base64
import json
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFont

# สร้างโฟลเดอร์สำหรับเก็บบันทึกไฟล์รูป/วิดีโอที่ลูกค้าอัปโหลด
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 🛠️ สร้างไฟล์โลโก้ .JPG มาตรฐานร้านอัตโนมัติ ถ้ายังไม่มี
LOGO_DEFAULT_PATH = "logo.jpg"
if not os.path.exists(LOGO_DEFAULT_PATH):
    try:
        img = Image.new('RGB', (600, 180), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 160, 160], fill=(15, 23, 42))
        draw.rectangle([35, 35, 145, 145], outline=(2, 132, 199), width=4)
        draw.text((185, 45), "ZONE COMPUTER", fill=(15, 23, 42))
        draw.text((185, 85), "& SERVICE (ช่างดิด)", fill=(2, 132, 199))
        draw.text((185, 125), "ศูนย์ซ่อมคอมพิวเตอร์และบริการไอที", fill=(100, 116, 139))
        img.save(LOGO_DEFAULT_PATH, "JPEG")
    except Exception:
        pass

# ตั้งค่าหน้าเว็บเริ่มต้น
st.set_page_config(
    page_title="ZoneOnline Service - Enterprise Edition", 
    page_icon="⚡", 
    layout="wide"
)

# 🌐 ดาวน์โหลดฟอนต์ภาษาไทยมาตรฐาน (Sarabun) จาก Google Fonts อัตโนมัติ ป้องกันปัญหาฟอนต์สี่เหลี่ยม
SARABUN_REGULAR = "Sarabun-Regular.ttf"
SARABUN_BOLD = "Sarabun-Bold.ttf"

if not os.path.exists(SARABUN_REGULAR):
    try:
        urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf", SARABUN_REGULAR)
    except Exception:
        pass

if not os.path.exists(SARABUN_BOLD):
    try:
        urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Bold.ttf", SARABUN_BOLD)
    except Exception:
        pass

# 🎁 ฟังก์ชันสุ่มคำคม (ตัวอักษรชัดเจน ขยายใหญ่ และสุ่มสีสดใส)
def get_dynamic_repair_terms():
    today = datetime.now()
    month = today.month
    day = today.day
    
    if month == 1 and day == 1:
        festival_msg = "🎉 สวัสดีปีใหม่ ขอให้มีความสุขตลอดปี!"
    elif month == 4 and (13 <= day <= 15):
        festival_msg = "💦 สุกสันต์วันสงกรานต์ เดินทางปลอดภัยนะครับ"
    elif month == 12 and (25 <= day <= 31):
        festival_msg = "🎄 Merry Christmas & Happy New Year"
    elif month == 2 and day == 14:
        festival_msg = "💖 สุขสันต์วันวาเลนไทน์ ดูแลสุขภาพด้วยนะ"
    else:
        quotes = [
            "💡 'คอมพิวเตอร์ก็เหมือนความรัก ถ้าร้อนรุ่มเดี๋ยวก็พัง'",
            "⚡ 'ข้อมูลสำคัญคือชีวิต สำรองไว้ก่อนปลอดภัยที่สุด'",
            "🔧 'ซ่อมไว ไว้ใจช่างดิด บริการด้วยใจ ใส่ใจทุกชิ้น'",
            "💻 'หน้าจอฟ้าไม่ใช่จุดจบ จุดเริ่มต้นของการซ่อม'",
            "🚀 'อัปเกรดความเร็วให้คอมพิวเตอร์ เติมพลังชีวิต'"
        ]
        festival_msg = random.choice(quotes)
    
    colors = ["#2563eb", "#16a34a", "#d97706", "#0d9488", "#4f46e5", "#e11d48", "#9333ea"]
    chosen_color = random.choice(colors)
    
    return f"<div style='font-size: 10px; font-weight: bold; color: {chosen_color}; margin-top: 2px;'>{festival_msg}</div>"

# 🔔 ฟังก์ชันส่งข้อความแจ้งเตือนผ่าน LINE Messaging API (Push Message)
def send_line_push_message(message, access_token, target_id):
    if not access_token or not target_id or not access_token.strip() or not target_id.strip():
        return
    try:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token.strip()}'
        }
        payload = {
            'to': target_id.strip(),
            'messages': [
                {
                    'type': 'text',
                    'text': message
                }
            ]
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        urllib.request.urlopen(req)
    except Exception:
        pass

# 🇹🇭 ฟังก์ชันสร้าง EMVCo PromptPay Payload QR Code ที่แอปธนาคารไทยสแกนได้จริง 100%
def generate_promptpay_payload(target, amount=None):
    target = "".join(filter(str.isdigit, str(target)))
    if len(target) == 10:
        target_value = "0066" + target[1:]
    elif len(target) == 13:
        target_value = target
    else:
        target_value = target

    tag00 = "0016A000000677010111"
    tag01_id = "01" + f"{len(target_value):02d}" + target_value
    tag29_content = tag00 + tag01_id
    tag29 = "29" + f"{len(tag29_content):02d}" + tag29_content

    poi = "010211" if amount is None else "010212"
    payload = "000201" + poi + tag29 + "5303764"
    
    if amount is not None and amount > 0:
        amt_str = f"{amount:.2f}"
        payload += "54" + f"{len(amt_str):02d}" + amt_str

    payload += "5802TH"
    payload_for_crc = payload + "6304"

    crc = 0xFFFF
    for char in payload_for_crc:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    chk = f"{crc:04X}"
    return payload_for_crc + chk

# 🛡️ ฟังก์ชันเรียกใช้งานฟอนต์ภาษาไทยที่ปลอดภัย
def get_safe_font(size=14, bold=False):
    font_path = SARABUN_BOLD if bold else SARABUN_REGULAR
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None

# 🎨 ฟังก์ชันสร้าง QR Card สำหรับดาวน์โหลด ขยายขนาด QR Code และตัวหนังสือให้ใหญ่สะใจเต็มพิกัด
def generate_downloadable_qr_card(data, store_name, store_phone, logo_path=LOGO_DEFAULT_PATH, top_label="QR CODE ติดตามสถานะงานซ่อม"):
    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=18,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path)
            img_w, img_h = img.size
            logo_size = int(img_w * 0.25)
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            box_size = logo_size + 12
            box_img = Image.new("RGB", (box_size, box_size), "white")
            box_pos = ((img_w - box_size) // 2, (img_h - box_size) // 2)
            img.paste(box_img, box_pos)
            
            logo_pos = ((img_w - logo_size) // 2, (img_h - logo_size) // 2)
            img.paste(logo, logo_pos)
        except Exception:
            pass

    font_top = get_safe_font(28, bold=True)
    font_title = get_safe_font(30, bold=True)
    font_sub = get_safe_font(24, bold=False)

    card_width = img.width + 80
    top_margin = 70
    bottom_margin = 170
    card_height = img.height + top_margin + bottom_margin
    
    card = Image.new("RGB", (card_width, card_height), "white")
    draw = ImageDraw.Draw(card)

    try:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), top_label, font=font_top)
            tw = bbox[2] - bbox[0]
        else:
            tw = 300
    except Exception:
        tw = 300
    draw.text(((card_width - tw) / 2, 18), top_label, fill="#0284c7", font=font_top)
    card.paste(img, (40, top_margin))

    box_y = top_margin + img.height + 20
    draw.rectangle([25, box_y, card_width - 25, card_height - 20], fill="#f8fafc", outline="#cbd5e1", width=2)
    
    try:
        if hasattr(draw, "textbbox"):
            bbox_title = draw.textbbox((0, 0), store_name, font=font_title)
            title_w = bbox_title[2] - bbox_title[0]
            bbox_sub = draw.textbbox((0, 0), f"โทร. {store_phone}", font=font_sub)
            sub_w = bbox_sub[2] - bbox_sub[0]
        else:
            title_w, sub_w = 250, 180
    except Exception:
        title_w, sub_w = 250, 180

    draw.text(((card_width - title_w) / 2, box_y + 18), store_name, fill="#0f172a", font=font_title)
    draw.text(((card_width - sub_w) / 2, box_y + 62), f"โทร. {store_phone}", fill="#475569", font=font_sub)

    stream = BytesIO()
    card.save(stream, format="PNG")
    stream.seek(0)
    return stream

def generate_qr_with_logo(data, logo_path=LOGO_DEFAULT_PATH, top_label="QR CODE ติดตามสถานะงานซ่อม"):
    return generate_downloadable_qr_card(data, STORE_NAME, STORE_PHONE, logo_path, top_label)

def get_img_base64(path):
    if path and isinstance(path, str) and os.path.exists(path):
        try:
            ext = path.split('.')[-1].lower()
            mime = "image/jpeg"
            if ext == "png":
                mime = "image/png"
            elif ext in ["jpg", "jpeg"]:
                mime = "image/jpeg"
            
            with open(path, "rb") as img_file:
                b64_data = base64.b64encode(img_file.read()).decode()
                return f"data:{mime};base64,{b64_data}"
        except Exception:
            return ""
    return ""

def init_connection():
    conn = sqlite3.connect('zone_online.db', check_same_thread=False)
    return conn

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            phone TEXT,
            tax_id TEXT,
            address TEXT,
            note TEXT,
            promptpay TEXT,
            line_link TEXT,
            fb_link TEXT,
            tiktok_link TEXT,
            youtube_link TEXT,
            prefix_qt TEXT DEFAULT 'QT',
            prefix_iv TEXT DEFAULT 'IV',
            prefix_tax TEXT DEFAULT 'TAX',
            prefix_rc TEXT DEFAULT 'RC',
            prefix_cn TEXT DEFAULT 'CN',
            prefix_dn TEXT DEFAULT 'DN',
            default_currency TEXT DEFAULT 'THB',
            accounting_method TEXT DEFAULT 'เกณฑ์สิทธิ์ (Accrual)',
            accounting_period TEXT DEFAULT '2026',
            lock_period TEXT DEFAULT 'ยังไม่ล็อก',
            opening_balance REAL DEFAULT 0.0,
            logo_path TEXT,
            watermark_path TEXT,
            use_logo INTEGER DEFAULT 1,
            use_watermark INTEGER DEFAULT 1,
            watermark_opacity REAL DEFAULT 0.03,
            watermark_size INTEGER DEFAULT 50,
            repair_terms TEXT,
            commercial_terms TEXT,
            line_access_token TEXT,
            line_target_id TEXT
        )
    ''')
    conn.commit()
    
    extra_cols = [
        ('prefix_qt', 'TEXT'), ('prefix_iv', 'TEXT'), ('prefix_tax', 'TEXT'),
        ('prefix_rc', 'TEXT'), ('prefix_cn', 'TEXT'), ('prefix_dn', 'TEXT'),
        ('default_currency', 'TEXT'), ('accounting_method', 'TEXT'), 
        ('accounting_period', 'TEXT'), ('lock_period', 'TEXT'), ('opening_balance', 'REAL'),
        ('logo_path', 'TEXT'), ('watermark_path', 'TEXT'),
        ('use_logo', 'INTEGER DEFAULT 1'), ('use_watermark', 'INTEGER DEFAULT 1'),
        ('watermark_opacity', 'REAL DEFAULT 0.03'), ('watermark_size', 'INTEGER DEFAULT 50'),
        ('repair_terms', 'TEXT'), ('commercial_terms', 'TEXT'), 
        ('line_access_token', 'TEXT'), ('line_target_id', 'TEXT'),
        ('youtube_link', 'TEXT')
    ]
    for col, col_type in extra_cols:
        try:
            cursor.execute(f"ALTER TABLE store_settings ADD COLUMN {col} {col_type};")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            price REAL DEFAULT 0.0,
            cost REAL DEFAULT 0.0,
            stock INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commercial_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE,
            doc_type TEXT,
            status TEXT,
            customer_name TEXT,
            customer_tax TEXT,
            customer_branch TEXT,
            customer_address TEXT,
            doc_date TEXT,
            due_date TEXT,
            salesperson TEXT,
            currency TEXT,
            items_json TEXT,
            subtotal REAL,
            discount_pct REAL,
            vat_amount REAL,
            grand_total REAL,
            ref_doc_no TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    try:
        cursor.execute("ALTER TABLE commercial_docs ADD COLUMN customer_phone TEXT;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link, youtube_link, prefix_qt, prefix_iv, prefix_tax, prefix_rc, prefix_cn, prefix_dn, default_currency, logo_path, watermark_path, use_logo, use_watermark, watermark_opacity, watermark_size, repair_terms, commercial_terms, line_access_token, line_target_id) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-026-1927', '1340700066417', '152 หมู่ 8 ต.บัวงาม อ.บุณฑริก จ.อุบลราชธานี 34230', 'ขอบคุณที่ใช้บริการครับ', '0890261927', 'https://line.me', 'https://facebook.com', 'https://tiktok.com', 'https://youtube.com', 'QT', 'IV', 'TAX', 'RC', 'CN', 'DN', 'THB', 'logo.jpg', 'logo.jpg', 1, 1, 0.03, 50, '(เงื่อนไข: ฝากซ่อมเกิน 30 วัน ทางร้านขอสงวนสิทธิ์เก็บค่าฝากรักษา)', 'รับประกันงานซ่อมและอะไหล่ตามเงื่อนไขของร้าน', '', '')
        ''')
        conn.commit()
    else:
        cursor.execute("UPDATE store_settings SET tax_id = '1340700066417', phone = '089-026-1927', address = '152 หมู่ 8 ต.บัวงาม อ.บุณฑริก จ.อุบลราชธานี 34230' WHERE id = 1;")
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'cashier', 'technician')) NOT NULL
        )
    ''')
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech1', 'ช่างดิด (มือหนึ่ง)', 'technician')")
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech2', 'ช่างเสริม', 'technician')")
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            device_name TEXT NOT NULL,
            serial_number TEXT,
            problem_description TEXT NOT NULL,
            accessories TEXT,
            estimated_cost REAL,
            technician_id INTEGER,
            status TEXT DEFAULT 'RECEIVED',
            media_file TEXT,
            need_tax INTEGER DEFAULT 0,
            tax_name TEXT,
            tax_id TEXT,
            tax_branch TEXT,
            tax_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (technician_id) REFERENCES staff(id)
        )
    ''')
    conn.commit()
    
    for col, col_type in [('need_tax', 'INTEGER DEFAULT 0'), ('tax_name', 'TEXT'), ('tax_id', 'TEXT'), ('tax_branch', 'TEXT'), ('tax_address', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE repairs ADD COLUMN {col} {col_type};")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    cursor.close()

conn = init_connection()
init_db(conn)

cursor = conn.cursor()
cursor.execute("SELECT store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link, youtube_link, prefix_qt, prefix_iv, prefix_tax, prefix_rc, prefix_cn, prefix_dn, default_currency, accounting_method, accounting_period, lock_period, opening_balance, logo_path, watermark_path, use_logo, use_watermark, watermark_opacity, watermark_size, repair_terms, commercial_terms, line_access_token, line_target_id FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()

if store_info:
    (STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY, 
     STORE_LINE, STORE_FB, STORE_TIKTOK, STORE_YOUTUBE, P_QT, P_IV, P_TAX, P_RC, P_CN, P_DN, 
     DEF_CURR, ACC_METHOD, ACC_PERIOD, LOCK_PER, OPEN_BAL, LOGO_PATH, WATERMARK_PATH, USE_LOGO, USE_WATERMARK, WM_OPACITY, WM_SIZE, REPAIR_TERMS, COMMERCIAL_TERMS, LINE_ACCESS_TOKEN, LINE_TARGET_ID) = store_info
else:
    STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY = "ร้านโซนคอมพิวเตอร์", "089-026-1927", "1340700066417", "152 หมู่ 8 ต.บัวงาม อ.บุณฑริก จ.อุบลราชธานี 34230", "ขอบคุณ", "0890261927"
    STORE_LINE, STORE_FB, STORE_TIKTOK, STORE_YOUTUBE = "", "", "", ""
    P_QT, P_IV, P_TAX, P_RC, P_CN, P_DN = "QT", "IV", "TAX", "RC", "CN", "DN"
    DEF_CURR, ACC_METHOD, ACC_PERIOD, LOCK_PER, OPEN_BAL, LOGO_PATH, WATERMARK_PATH, USE_LOGO, USE_WATERMARK, WM_OPACITY, WM_SIZE = "THB", "เกณฑ์สิทธิ์ (Accrual)", "2026", "ยังไม่ล็อก", 0.0, "logo.jpg", "logo.jpg", 1, 1, 0.03, 50
    REPAIR_TERMS, COMMERCIAL_TERMS, LINE_ACCESS_TOKEN, LINE_TARGET_ID = "(เงื่อนไข: ฝากซ่อมเกิน 30 วัน ทางร้านขอสงวนสิทธิ์เก็บค่าฝากรักษา)", "รับประกันงานซ่อมและอะไหล่ตามเงื่อนไขของร้าน", "", ""

STORE_NAME = STORE_NAME or "ร้านโซนคอมพิวเตอร์"
STORE_PHONE = STORE_PHONE or "089-026-1927"
STORE_TAX = STORE_TAX or "1340700066417"
STORE_ADDRESS = STORE_ADDRESS or "152 หมู่ 8 ต.บัวงาม อ.บุณฑริก จ.อุบลราชธานี 34230"
STORE_NOTE = STORE_NOTE or ""
STORE_PROMPTPAY = STORE_PROMPTPAY or ""
STORE_LINE = STORE_LINE or ""
STORE_FB = STORE_FB or ""
STORE_TIKTOK = STORE_TIKTOK or ""
STORE_YOUTUBE = STORE_YOUTUBE or ""
P_QT = P_QT or "QT"
P_IV = P_IV or "IV"
P_TAX = P_TAX or "TAX"
P_RC = P_RC or "RC"
P_CN = P_CN or "CN"
P_DN = P_DN or "DN"
DEF_CURR = DEF_CURR or "THB"
ACC_METHOD = ACC_METHOD or "เกณฑ์สิทธิ์ (Accrual)"
ACC_PERIOD = ACC_PERIOD or "2026"
LOCK_PER = LOCK_PER or "ยังไม่ล็อก"
OPEN_BAL = float(OPEN_BAL) if OPEN_BAL is not None else 0.0
LOGO_PATH = LOGO_PATH or "logo.jpg"
WATERMARK_PATH = WATERMARK_PATH or "logo.jpg"
USE_LOGO = int(USE_LOGO) if USE_LOGO is not None else 1
USE_WATERMARK = int(USE_WATERMARK) if USE_WATERMARK is not None else 1
WM_OPACITY = float(WM_OPACITY) if WM_OPACITY is not None else 0.03
WM_SIZE = int(WM_SIZE) if WM_SIZE is not None else 50
REPAIR_TERMS = REPAIR_TERMS or "(เงื่อนไข: ฝากซ่อมเกิน 30 วัน ทางร้านขอสงวนสิทธิ์เก็บค่าฝากรักษา)"
COMMERCIAL_TERMS = COMMERCIAL_TERMS or "รับประกันงานซ่อมและอะไหล่ตามเงื่อนไขของร้าน"
LINE_ACCESS_TOKEN = LINE_ACCESS_TOKEN or ""
LINE_TARGET_ID = LINE_TARGET_ID or ""

logo_img_header_tag = ""
if USE_LOGO and LOGO_PATH and os.path.exists(LOGO_PATH):
    logo_hdr_uri = get_img_base64(LOGO_PATH)
    if logo_hdr_uri:
        logo_img_header_tag = f'<img src="{logo_hdr_uri}" style="max-height: 45px; vertical-align: middle; margin-right: 10px;">'

watermark_html = ""
if USE_WATERMARK and WATERMARK_PATH and os.path.exists(WATERMARK_PATH):
    wm_data_uri = get_img_base64(WATERMARK_PATH)
    if wm_data_uri:
        watermark_html = f'''
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); opacity: {WM_OPACITY}; z-index: 0; pointer-events: none; text-align: center; width: {WM_SIZE}%;">
            <img src="{wm_data_uri}" style="width: 100%; height: auto;">
        </div>
        '''

query_params = st.query_params
track_code = query_params.get("track", None)
track_doc = query_params.get("track_doc", None)
page_param = query_params.get("page", None)

if track_code:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.job_code, r.device_name, r.problem_description, r.status, r.created_at, r.updated_at, c.name, r.estimated_cost, c.phone
        FROM repairs r JOIN customers c ON r.customer_id = c.id
        WHERE r.job_code = ?
    """, (track_code,))
    job_data = cursor.fetchone()
    cursor.close()
    
    if job_data:
        j_code, dev, prob, stat, d_in, d_up, c_name, cost_val, c_phone = job_data
        cost_val = float(cost_val) if cost_val is not None else 0.0
        
        status_dict = {
            "RECEIVED": ("📥 รับเครื่องเข้าศูนย์ซ่อมแล้ว", "#17a2b8", "ช่างรับเครื่องและบันทึกเข้าสู่ระบบเรียบร้อย"),
            "CHECKING": ("🔍 กำลังตรวจสอบอาการ", "#ffc107", "ช่างกำลังเช็คความผิดปกติของอุปกรณ์"),
            "WAITING_PART": ("⏳ รออะไหล่ / รออนุมัติ", "#fd7e14", "กำลังรออะไหล่หรือรอการยืนยันจากลูกค้า"),
            "REPAIRING": ("⚡ กำลังดำเนินการซ่อม", "#007bff", "ช่างกำลังปฏิบัติงานซ่อมแซมเครื่อง"),
            "COMPLETED": ("🎉 ซ่อมเสร็จสิ้น พร้อมส่งมอบ", "#28a745", "เครื่องซ่อมเสร็จสมบูรณ์ พร้อมมารับกลับได้เลย!"),
            "CANCELLED": ("❌ ยกเลิกการซ่อม", "#dc3545", "รายการซ่อมนี้ถูกยกเลิก")
        }
        
        thai_status, badge_color, status_desc = status_dict.get(stat, ("📌 กำลังดำเนินการ", "#6c757d", "สถานะกำลังอัปเดต"))
        name_parts = c_name.split()
        masked_name = f"คุณ {name_parts[0]} ({name_parts[1][0]}***)" if len(name_parts) > 1 else f"คุณ {c_name}"

        public_html = f"""
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ติดตามสถานะงานซ่อม - {STORE_NAME}</title>
            <style>
                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 10px; }}
                .card {{ background: white; padding: 25px 20px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 420px; text-align: center; }}
                h2 {{ color: #333; margin-bottom: 5px; font-size: 20px; }}
                .store-sub {{ color: #666; font-size: 12px; margin-bottom: 15px; }}
                .info-box {{ background: #f8f9fa; border-radius: 10px; padding: 12px; margin-bottom: 15px; text-align: left; font-size: 13px; border-left: 4px solid #007bff; }}
                .info-box p {{ margin: 5px 0; color: #444; }}
                .status-badge {{ background-color: {badge_color}; color: white; padding: 10px 18px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>⚡ {STORE_NAME}</h2>
                <div class="store-sub">ระบบติดตามสถานะงานซ่อมเรียลไทม์</div>
                <div class="info-box">
                    <p><b>เลขที่ใบงาน:</b> {j_code}</p>
                    <p><b>ชื่อลูกค้า:</b> {masked_name}</p>
                    <p><b>รุ่นอุปกรณ์:</b> {dev}</p>
                    <p><b>รายการซ่อม:</b> {prob}</p>
                </div>
                <div class="status-badge">{thai_status}</div>
            </div>
        </body>
        </html>
        """
        components.html(public_html, height=650, scrolling=True)
    else:
        st.error("❌ ไม่พบข้อมูลใบงานนี้ในระบบ")
    st.stop()

# ==========================================
# 🖥️ หน้าแอดมินหลัก (Enterprise Dashboard with Switcher Menu)
# ==========================================
st.title(f"⚡ {STORE_NAME} [Enterprise Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (สไตล์ Enterprise พรีเมียม)")

if 'current_job_code' not in st.session_state:
    st.session_state.current_job_code = None

# แผงควบคุมเมนูหลักแบบสวิตช์เปิด-ปิด มีไฟสีเขียวเมื่อใช้งานหน้านั้นอยู่
menu_options = [
    "📥 รับเครื่องซ่อมใหม่", 
    "🖨️ พิมพ์สติกเกอร์ติดเครื่อง",
    "📦 จัดการลูกค้า & สินค้า",
    "📱 QR โหลดหน้าลงทะเบียน",
    "🔍 ติดตามสถานะซ่อม", 
    "⚙️ ศูนย์กลางการตั้งค่า"
]

if 'current_menu' not in st.session_state:
    st.session_state.current_menu = menu_options[0]

st.markdown("##### 🎛️ แผงควบคุมสวิตช์เมนูหลักระบบ")
cols_menu = st.columns(len(menu_options))
for i, m_opt in enumerate(menu_options):
    with cols_menu[i]:
        is_active = (st.session_state.current_menu == m_opt)
        btn_label = f"🟢 ON: {m_opt}" if is_active else f"🔌 OFF: {m_opt}"
        if st.button(btn_label, use_container_width=True, key=f"sw_menu_{i}"):
            st.session_state.current_menu = m_opt
            st.rerun()

menu = st.session_state.current_menu
st.markdown("---")

# ==========================================
# 1. รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่":
    st.header("📥 บันทึกรับเครื่องซ่อมและพิมพ์ใบรับซ่อม (A4 แนวตั้ง - สไตล์โมเดิร์น)")
    
    with st.form("pro_repair_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("ข้อมูลลูกค้า")
            customer_name = st.text_input("ชื่อ-นามสกุล ลูกค้า")
            phone = st.text_input("เบอร์โทรศัพท์ (ใช้เป็น Key หลัก)")
            address = st.text_area("ที่อยู่ลูกค้า (ถ้ามี)")
        with col2:
            st.subheader("ข้อมูลอุปกรณ์ & การซ่อม")
            device_name = st.text_input("รุ่นอุปกรณ์ (เช่น Notebook ASUS ROG)")
            serial_number = st.text_input("Serial Number (สำหรับเช็คประกัน)")
            accessories = st.text_input("อุปกรณ์ที่แนบมา (เช่น สายชาร์จ, กระเป๋า)")
            
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            problem_description = st.text_area("อาการเสีย / รายละเอียดจากปากลูกค้า")
            estimated_cost = st.number_input("ประเมินราคาค่าซ่อมเบื้องต้น (บาท)", min_value=0.0, step=100.0)
        with col4:
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name FROM staff WHERE role = 'technician'")
            techs = cursor.fetchall()
            cursor.close()
            tech_dict = {t[1]: t[0] for t in techs} if techs else {"ยังไม่มีข้อมูลช่าง": 0}
                
            selected_tech_name = st.selectbox("มอบหมายให้ช่างผู้รับผิดชอบ", list(tech_dict.keys()))
            technician_id = tech_dict[selected_tech_name]
            commission = st.number_input("ค่ามือ / คอมมิชชั่นช่างงานนี้ (บาท)", min_value=0.0, step=50.0)

        submit_btn = st.form_submit_button("🚀 บันทึกรับเครื่องและสร้างใบรับซ่อม")
        
        if submit_btn:
            if customer_name and phone and device_name:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO customers (name, phone, address) 
                        VALUES (?, ?, ?) 
                        ON CONFLICT(phone) DO UPDATE SET name = excluded.name, address = excluded.address;
                    """, (customer_name, phone, address))
                    
                    cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
                    customer_id = cursor.fetchone()[0]
                    
                    job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                    
                    cursor.execute("""
                        INSERT INTO repairs (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'RECEIVED')
                    """, (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id))
                    
                    conn.commit()
                    cursor.close()
                    
                    st.session_state.current_job_code = job_code
                    st.success(f"🎉 บันทึกรับเครื่องสำเร็จ! เลขที่ใบงาน: **{job_code}** เลื่อนลงด้านล่างเพื่อกดปุ่มสั่งปริ้นได้เลยครับ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")

    st.markdown("---")
    st.subheader("🖨️ ตัวอย่างใบรับซ่อม A4 แนวตั้ง (สไตล์โมเดิร์น พรีเมียม)")
    
    cursor = conn.cursor()
    cursor.execute("SELECT job_code FROM repairs ORDER BY created_at DESC LIMIT 50")
    all_jobs = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    if all_jobs:
        default_index = 0
        if st.session_state.current_job_code in all_jobs:
            default_index = all_jobs.index(st.session_state.current_job_code)
            
        selected_job_to_print = st.selectbox("เลือกเลขใบงานที่ต้องการแสดงเอกสาร", all_jobs, index=default_index)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.job_code, c.name, c.phone, r.device_name, r.serial_number, r.problem_description, r.accessories, r.estimated_cost, r.status, r.created_at
            FROM repairs r JOIN customers c ON r.customer_id = c.id
            WHERE r.job_code = ?
        """, (selected_job_to_print,))
        print_data = cursor.fetchone()
        cursor.close()
        
        if print_data:
            j_code, c_name, c_phone, dev, sn, prob, acc, cost, stat, date_in = print_data
            cost = float(cost) if pd.notna(cost) else 0.0
            
            track_url = f"https://zone-computer-pos.streamlit.app/?track={j_code}"
            track_stream_qr = generate_qr_with_logo(track_url, LOGO_PATH)
            track_b64 = base64.b64encode(track_stream_qr.getvalue()).decode()
            qr_track_tag = f'<img src="data:image/png;base64,{track_b64}" width="100px"><br><span style="font-size:8px; font-weight:bold;">สแกนเช็คสถานะงานซ่อม</span>'
            
            def make_social_qr_inline(link, label):
                if not link: return ""
                s_stream = generate_qr_with_logo(link, LOGO_PATH)
                s_b64 = base64.b64encode(s_stream.getvalue()).decode()
                return f'<div style="text-align:center; display:inline-block; margin: 0 4px;"><img src="data:image/png;base64,{s_b64}" width="40px"><br><span style="font-size:7px;">{label}</span></div>'

            social_html = ""
            if STORE_LINE: social_html += make_social_qr_inline(STORE_LINE, "Line")
            if STORE_FB: social_html += make_social_qr_inline(STORE_FB, "Facebook")
            if STORE_TIKTOK: social_html += make_social_qr_inline(STORE_TIKTOK, "TikTok")
            if STORE_YOUTUBE: social_html += make_social_qr_inline(STORE_YOUTUBE, "YouTube")
            
            current_dynamic_terms = get_dynamic_repair_terms()
            
            portrait_a4_html = f"""
            <html>
            <head>
            <style>
                @page {{ size: A4 portrait; margin: 8mm; }}
                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                .print-btn-container {{ margin-bottom: 15px; display: flex; gap: 10px; justify-content: center; }}
                .btn-print {{ background-color: #0f172a; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                .btn-print:hover {{ background-color: #334155; }}
                .btn-print-nodate {{ background-color: #475569; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                .btn-print-nodate:hover {{ background-color: #64748b; }}
                .print-container {{ background: white; border: 1px solid #cbd5e1; padding: 12mm 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); position: relative; overflow: hidden; }}
                .section-box {{ height: 125mm; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; position: relative; z-index: 1; overflow: hidden; padding: 5px; }}
                .header-tbl {{ width: 100%; border-collapse: collapse; }}
                .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin: 8px 0; font-size: 12px; }}
                .cust-box td {{ padding: 3px 6px; word-break: break-word; }}
                .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
                .items-tbl th {{ background: #0f172a; color: white; padding: 8px 6px; text-align: left; font-weight: 600; }}
                .items-tbl td {{ padding: 8px 6px; border-bottom: 1px solid #e2e8f0; word-break: break-word; }}
                .perforation {{ border-top: 2px dashed #94a3b8; margin: 6mm 0; text-align: center; font-size: 11px; color: #64748b; font-weight: bold; position: relative; z-index: 1; }}
                .signature-row {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 11px; align-items: flex-end; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
                .nodate-field {{ display: none; }}
                @media print {{
                    body {{ background: white; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                    .print-btn-container {{ display: none !important; }}
                    .print-container {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                }}
            </style>
            <script>
                function printNoDate() {{
                    var normalDates = document.getElementsByClassName('normal-date');
                    var nodateFields = document.getElementsByClassName('nodate-field');
                    for(var i=0; i<normalDates.length; i++) {{ normalDates[i].style.display = 'none'; }}
                    for(var i=0; i<nodateFields.length; i++) {{ nodateFields[i].style.display = 'inline'; }}
                    window.print();
                    setTimeout(function() {{
                        for(var i=0; i<normalDates.length; i++) {{ normalDates[i].style.display = 'inline'; }}
                        for(var i=0; i<nodateFields.length; i++) {{ nodateFields[i].style.display = 'none'; }}
                    }}, 500);
                }}
            </script>
            </head>
            <body>
                <div class="print-btn-container">
                    <button class="btn-print" onclick="window.print()">🖨️ พิมพ์ใบรับซ่อม (ปกติ)</button>
                    <button class="btn-print-nodate" onclick="printNoDate()">🖨️ พิมพ์แบบไม่ลงวันที่</button>
                </div>
                
                <div class="print-container">
                    <!-- ส่วนที่ 1: สำหรับลูกค้า (ต้นฉบับ) -->
                    <div class="section-box">
                        {watermark_html}
                        <div class="content-wrap" style="position: relative; z-index: 1;">
                            <table class="header-tbl">
                                <tr>
                                    <td style="vertical-align: top; width: 60%;">
                                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                            {logo_img_header_tag}
                                            <h2 style="margin: 0; color: #0f172a; font-size: 20px; line-height: 1.2;">
                                                <b>ร้านโซนคอมพิวเตอร์</b><br>
                                                <span style="font-size: 15px; font-weight: bold; color: #0f172a;">แอนด์ เซอร์วิส</span>
                                            </h2>
                                        </div>
                                        <p style="font-size: 11px; margin: 4px 0; color: #475569; line-height: 1.4; word-break: break-word;">
                                            ที่อยู่: {STORE_ADDRESS}<br>
                                            โทร: {STORE_PHONE} | เลขผู้เสียภาษี: 1340700066417
                                        </p>
                                    </td>
                                    <td style="text-align: right; vertical-align: top; width: 40%;">
                                        <div style="background: #0f172a; color: white; padding: 6px 12px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 13px; margin-bottom: 6px;">
                                            ใบรับซ่อมสินค้า (CUSTOMER)
                                        </div>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>เลขที่ใบงาน:</b> {j_code}</p>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>วันที่รับเครื่อง:</b> <span class="normal-date">{date_in}</span><span class="nodate-field">....................................</span></p>
                                    </td>
                                </tr>
                            </table>

                            <table class="cust-box tbl">
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>

                            <table class="items-tbl">
                                <tr>
                                    <th>รายการอาการเสีย / อะไหล่ที่ส่งมาด้วย</th>
                                    <th style="text-align: right; width: 130px;">ประเมินราคา (บาท)</th>
                                </tr>
                                <tr>
                                    <td><b>อาการเสีย:</b> {prob}<br><span style="font-size: 11px; color: #64748b;">อุปกรณ์: {acc if acc else '-'}</span></td>
                                    <td style="text-align: right; font-weight: bold; color: #0f172a; vertical-align: middle;">{cost:,.2f}</td>
                                </tr>
                            </table>
                        </div>
                        <div class="signature-row" style="position: relative; z-index: 1;">
                            <div style="width: 55%; display: flex; align-items: flex-end; gap: 10px;">
                                <div style="text-align: center; background: #f8fafc; padding: 4px 6px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                    <div style="font-size:7px; font-weight:bold; color:#475569; margin-bottom:2px;">ติดตามโซเชียลร้าน</div>
                                    <div style="display: flex; gap: 3px;">{social_html}</div>
                                </div>
                                <div>
                                    <span>ลงชื่อลูกค้า: ......................................................</span><br>
                                    {current_dynamic_terms}
                                </div>
                            </div>
                            <div style="text-align: right; width: 42%; padding-right: 0; margin-right: 0;">
                                <div style="text-align: right;">
                                    {qr_track_tag}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- รอยฉีก -->
                    <div class="perforation">
                        ✂️ - - - - - - - - - - - - - - - - - รอยฉีกสำหรับแยกระหว่างลูกค้าและร้านค้า (Cut / Tear Here) - - - - - - - - - - - - - - - - - ✂️
                    </div>

                    <!-- ส่วนที่ 2: สำหรับร้านค้า (สำเนา) -->
                    <div class="section-box">
                        {watermark_html}
                        <div class="content-wrap" style="position: relative; z-index: 1;">
                            <table class="header-tbl">
                                <tr>
                                    <td style="vertical-align: top; width: 60%;">
                                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                            {logo_img_header_tag}
                                            <h2 style="margin: 0; color: #0f172a; font-size: 20px; line-height: 1.2;">
                                                <b>ร้านโซนคอมพิวเตอร์</b><br>
                                                <span style="font-size: 15px; font-weight: bold; color: #334155;">แอนด์ เซอร์วิส</span>
                                            </h2>
                                        </div>
                                        <p style="font-size: 11px; margin: 4px 0; color: #475569; line-height: 1.4; word-break: break-word;">
                                            ที่อยู่: {STORE_ADDRESS}<br>
                                            โทร: {STORE_PHONE} | เลขผู้เสียภาษี: 1340700066417
                                        </p>
                                    </td>
                                    <td style="text-align: right; vertical-align: top; width: 40%;">
                                        <div style="background: #334155; color: white; padding: 6px 12px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 13px; margin-bottom: 6px;">
                                            ใบรับซ่อมสินค้า (STORE COPY)
                                        </div>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>เลขที่ใบงาน:</b> {j_code}</p>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>วันที่รับเครื่อง:</b> <span class="normal-date">{date_in}</span><span class="nodate-field">....................................</span></p>
                                    </td>
                                </tr>
                            </table>

                            <table class="cust-box tbl">
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>

                            <table class="items-tbl">
                                <tr>
                                    <th>รายการอาการเสีย / อะไหล่ที่ส่งมาด้วย</th>
                                    <th style="text-align: right; width: 130px;">ประเมินราคา (บาท)</th>
                                </tr>
                                <tr>
                                    <td><b>อาการเสีย:</b> {prob}<br><span style="font-size: 11px; color: #64748b;">อุปกรณ์: {acc if acc else '-'}</span></td>
                                    <td style="text-align: right; font-weight: bold; color: #0f172a; vertical-align: middle;">{cost:,.2f}</td>
                                </tr>
                            </table>
                        </div>
                        <div class="signature-row" style="position: relative; z-index: 1;">
                            <div style="width: 55%; display: flex; align-items: flex-end; gap: 10px;">
                                <div style="text-align: center; background: #f8fafc; padding: 4px 6px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                    <div style="font-size:7px; font-weight:bold; color:#475569; margin-bottom:2px;">ติดตามโซเชียลร้าน</div>
                                    <div style="display: flex; gap: 3px;">{social_html}</div>
                                </div>
                                <div>
                                    <span>ลงชื่อลูกค้า (รับทราบเงื่อนไข): ......................................................</span><br><br>
                                    <span>ช่างผู้รับซ่อม: ......................................................</span>
                                </div>
                            </div>
                            <div style="text-align: right; width: 42%; padding-right: 0; margin-right: 0;">
                                <div style="text-align: right;">
                                    {qr_track_tag}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            components.html(portrait_a4_html, height=1050, scrolling=True)
    else:
        st.info("ยังไม่มีข้อมูลใบงานในระบบ")

# ==========================================
# 2. พิมพ์สติกเกอร์ติดเครื่องลูกค้า (3 ขนาดเลือกได้)
# ==========================================
elif menu == "🖨️ พิมพ์สติกเกอร์ติดเครื่อง":
    st.header("🖨️ ระบบพิมพ์สติกเกอร์ติดเครื่องลูกค้า")
    st.markdown("เลือกขนาดและสไตล์สติกเกอร์ที่ต้องการพิมพ์ (รองรับเครื่องพิมพ์สติกเกอร์ความร้อน)")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.job_code, c.name, c.phone, r.device_name, r.serial_number, r.problem_description, r.estimated_cost, r.status
        FROM repairs r JOIN customers c ON r.customer_id = c.id
        ORDER BY r.created_at DESC LIMIT 50
    """)
    sticker_jobs = cursor.fetchall()
    cursor.close()

    if sticker_jobs:
        job_options = [f"{j[0]} - {j[1]} ({j[2]})" for j in sticker_jobs]
        selected_sticker_job_str = st.selectbox("เลือกเลขใบงานที่ต้องการพิมพ์สติกเกอร์", job_options)
        
        selected_job_code_val = selected_sticker_job_str.split(" - ")[0]
        chosen_job_data = next(j for j in sticker_jobs if j[0] == selected_job_code_val)
        
        st.markdown("---")
        
        st.markdown("##### 📐 เลือกขนาดสติกเกอร์")
        size_choice = st.radio("ขนาดสติกเกอร์", [
            "📏 50 x 30 มม. (ยอดนิยม มาตรฐาน)", 
            "📏 40 x 30 มม. (ไซส์กะทัดรัด)", 
            "📏 40 x 25 มม. (ไซส์จิ๋วพิเศษ)"
        ], horizontal=True)

        if "50 x 30" in size_choice:
            box_width = "340px"
            box_pad = "8px 10px"
            font_content = "11px"
            font_footer = "10.5px"
            bc_height = "30"
            bc_width = "1.3"
        elif "40 x 30" in size_choice:
            box_width = "290px"
            box_pad = "6px 8px"
            font_content = "10px"
            font_footer = "9px"
            bc_height = "24"
            bc_width = "1.0"
        else:
            box_width = "270px"
            box_pad = "5px 6px"
            font_content = "9px"
            font_footer = "8px"
            bc_height = "20"
            bc_width = "0.9"

        st.markdown("##### 🎨 เลือกสไตล์สติกเกอร์ (5 สไตล์สุดพรีเมียม)")
        
        sticker_styles = [
            "1. คลาสสิกเน้นบาร์โค้ด (Blue Gradient)",
            "2. สไตล์มินิมอลตัวหนังสือใหญ่ (Indigo Banner)",
            "3. วอยด์รับประกันหลังซ่อม (Emerald Green)",
            "4. มินิบาร์โค้ดขนาดเล็กพิเศษ (Amber Orange)",
            "5. สไตล์พรีเมียมข้อมูลครบถ้วน (Rose Gradient)"
        ]
        
        if 'sticker_style_choice' not in st.session_state:
            st.session_state.sticker_style_choice = sticker_styles[0]

        cols_stk = st.columns(len(sticker_styles))
        for s_idx, s_name in enumerate(sticker_styles):
            with cols_stk[s_idx]:
                is_stk_active = (st.session_state.sticker_style_choice == s_name)
                btn_sw = "🟢 ON" if is_stk_active else "🔌 OFF"
                if st.button(f"{btn_sw}\nแบบที่ {s_idx+1}", use_container_width=True, key=f"stk_btn_{s_idx}"):
                    st.session_state.sticker_style_choice = s_name
                    st.rerun()

        chosen_style = st.session_state.sticker_style_choice
        st.markdown(f"🎯 **สไตล์สติกเกอร์ที่เลือก:** `{chosen_style}` | **ขนาด:** `{size_choice}`")

        s_code, s_name, s_phone, s_dev, s_sn, s_prob, s_cost, s_stat = chosen_job_data

        logo_sticker_tag = ""
        if USE_LOGO and LOGO_PATH and os.path.exists(LOGO_PATH):
            logo_uri = get_img_base64(LOGO_PATH)
            if logo_uri:
                logo_sticker_tag = f'<img src="{logo_uri}" style="max-height: 24px; vertical-align: middle; margin-right: 4px;">'

        wm_sticker_html = ""
        if USE_WATERMARK and WATERMARK_PATH and os.path.exists(WATERMARK_PATH):
            wm_uri = get_img_base64(WATERMARK_PATH)
            if wm_uri:
                wm_sticker_html = f'''
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-25deg); opacity: 0.05; z-index: 0; pointer-events: none; width: 60%;">
                    <img src="{wm_uri}" style="width: 100%; height: auto;">
                </div>
                '''

        if "1." in chosen_style:
            theme_bg = "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)"
            theme_header = "#2563eb"
            theme_border = "#93c5fd"
        elif "2." in chosen_style:
            theme_bg = "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)"
            theme_header = "#4f46e5"
            theme_border = "#c7d2fe"
        elif "3." in chosen_style:
            theme_bg = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)"
            theme_header = "#16a34a"
            theme_border = "#86efac"
        elif "4." in chosen_style:
            theme_bg = "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)"
            theme_header = "#d97706"
            theme_border = "#fde68a"
        else:
            theme_bg = "linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%)"
            theme_header = "#e11d48"
            theme_border = "#fda4af"

        stk_dynamic_terms = get_dynamic_repair_terms()
        barcode_elem_id = f"barcode_{s_code.replace('-', '_')}"

        sticker_html_card = f"""
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8fafc; display: flex; justify-content: center; align-items: center; padding: 10px; }}
            .sticker-box {{ background: {theme_bg}; border: 1.5px solid {theme_border}; border-radius: 8px; padding: {box_pad}; width: {box_width}; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.08); position: relative; overflow: hidden; }}
            .stk-header {{ display: flex; align-items: center; border-bottom: 1.5px solid {theme_header}; padding-bottom: 3px; margin-bottom: 3px; position: relative; z-index: 1; }}
            .stk-title {{ font-size: 11.5px; font-weight: bold; color: {theme_header}; line-height: 1.1; }}
            .stk-content {{ font-size: {font_content}; color: #1e293b; line-height: 1.25; position: relative; z-index: 1; }}
            .stk-footer {{ margin-top: 3px; display: flex; flex-direction: column; align-items: center; text-align: center; border-top: 1px dashed {theme_border}; padding-top: 3px; position: relative; z-index: 1; }}
            .print-btn {{ background-color: {theme_header}; color: white; border: none; padding: 8px 16px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; display: block; margin: 10px auto; }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .print-btn {{ display: none !important; }}
                .sticker-box {{ border: 1px solid #000; box-shadow: none; width: 100%; }}
            }}
        </style>
        </head>
        <body>
            <div>
                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์สติกเกอร์บาร์โค้ดนี้</button>
                <div class="sticker-box">
                    {wm_sticker_html}
                    <div class="stk-header">
                        {logo_sticker_tag}
                        <div class="stk-title"><b>{STORE_NAME}</b></div>
                    </div>
                    <div class="stk-content">
                        <p style="margin: 1.5px 0;"><b>📋 เลขใบงาน:</b> <span style="color:{theme_header}; font-weight:bold; font-size:11.5px;">{s_code}</span></p>
                        <p style="margin: 1.5px 0;"><b>👤 ลูกค้า:</b> {s_name} ({s_phone})</p>
                        <p style="margin: 1.5px 0;"><b>💻 อุปกรณ์:</b> {s_dev}</p>
                        <div style="margin-top: 1px; text-align: center;">
                            {stk_dynamic_terms}
                        </div>
                    </div>
                    <div class="stk-footer">
                        <div style="font-size: {font_footer}; color: #0f172a; font-weight: bold; margin-bottom: 2px;">
                            📞 โทร: {STORE_PHONE} &nbsp;|&nbsp; ⭐ ขอบคุณที่ใช้บริการครับ 🙏
                        </div>
                        <div style="text-align: center;">
                            <svg id="{barcode_elem_id}"></svg>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                try {{
                    JsBarcode("#{barcode_elem_id}", "{s_code}", {{
                        format: "CODE128",
                        width: {bc_width},
                        height: {bc_height},
                        displayValue: true,
                        fontSize: 9,
                        margin: 0
                    }});
                }} catch(e) {{
                    console.error(e);
                }}
            </script>
        </body>
        </html>
        """
        components.html(sticker_html_card, height=350, scrolling=True)
    else:
        st.info("ยังไม่มีข้อมูลใบงานสำหรับพิมพ์สติกเกอร์ในระบบ")

# ==========================================
# 3. จัดการลูกค้า & สินค้า (CRM & Inventory Management)
# ==========================================
elif menu == "📦 จัดการลูกค้า & สินค้า":
    st.header("📦 ระบบจัดการข้อมูลลูกค้าและสินค้า / อะไหล่ (CRM & Inventory)")
    st.markdown("เพิ่ม, ค้นหา, แก้ไข และลบข้อมูลลูกค้าและสินค้าในสต็อกได้อย่างสะดวกรวดเร็ว")
    
    tab_cust, tab_prod = st.tabs(["👥 จัดการข้อมูลลูกค้า (Customers)", "📦 จัดการข้อมูลสินค้า / อะไหล่ (Products)"])
    
    with tab_cust:
        st.subheader("👥 ฐานข้อมูลลูกค้า (Customer Management)")
        
        c_search = st.text_input("🔍 ค้นหาลูกค้า (ด้วยชื่อ หรือ เบอร์โทรศัพท์)")
        cursor = conn.cursor()
        c_query = "SELECT id, name, phone, address, created_at FROM customers"
        if c_search:
            c_query += f" WHERE name LIKE '%{c_search}%' OR phone LIKE '%{c_search}%'"
        c_query += " ORDER BY id DESC;"
        cust_df = pd.read_sql(c_query, conn)
        cursor.close()
        
        if not cust_df.empty:
            st.dataframe(cust_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("##### ✏️ แก้ไข หรือ 🗑️ ลบข้อมูลลูกค้า")
            selected_cust_id = st.selectbox("เลือกลูกค้าที่ต้องการจัดการ", cust_df['id'].tolist(), format_func=lambda x: f"ID: {x} - {cust_df[cust_df['id']==x]['name'].values[0]} ({cust_df[cust_df['id']==x]['phone'].values[0]})")
            
            target_cust = cust_df[cust_df['id'] == selected_cust_id].iloc[0]
            
            with st.form("edit_customer_form"):
                e_name = st.text_input("ชื่อ-นามสกุล", value=target_cust['name'])
                e_phone = st.text_input("เบอร์โทรศัพท์", value=target_cust['phone'])
                e_address = st.text_area("ที่อยู่", value=target_cust['address'] if pd.notna(target_cust['address']) else "")
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    update_cust_btn = st.form_submit_button("💾 บันทึกการแก้ไขข้อมูลลูกค้า", type="primary")
                with col_e2:
                    delete_cust_btn = st.form_submit_button("🗑️ ลบลูกค้ารายนี้")
                    
                if update_cust_btn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?", (e_name, e_phone, e_address, selected_cust_id))
                    conn.commit()
                    cursor.close()
                    st.success("อัปเดตข้อมูลลูกค้าสำเร็จ!")
                    st.rerun()
                    
                if delete_cust_btn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM customers WHERE id = ?", (selected_cust_id,))
                    conn.commit()
                    cursor.close()
                    st.success("ลบข้อมูลลูกค้าสำเร็จ!")
                    st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลลูกค้าในระบบ")

    with tab_prod:
        st.subheader("📦 ฐานข้อมูลสินค้าและอะไหล่ (Inventory Management)")
        
        with st.expander("➕ เพิ่มสินค้า / อะไหล่ใหม่เข้าสต็อก", expanded=False):
            with st.form("add_product_form"):
                p_code = st.text_input("รหัสสินค้า / Barcode (เช่น PART-001)")
                p_name = st.text_input("ชื่อสินค้า / อะไหล่ (เช่น แรม DDR4 8GB)")
                p_cat = st.text_input("หมวดหมู่สินค้า (เช่น RAM, Harddisk, อุปกรณ์เสริม)", value="อะไหล่คอมพิวเตอร์")
                p_cols = st.columns(3)
                with p_cols[0]:
                    p_price = st.number_input("ราคาขาย (บาท)", min_value=0.0, step=50.0, value=500.0)
                with p_cols[1]:
                    p_cost = st.number_input("ทุน (บาท)", min_value=0.0, step=50.0, value=300.0)
                with p_cols[2]:
                    p_stock = st.number_input("จำนวนคงเหลือ (Stock)", min_value=0, value=10)
                    
                add_prod_submit = st.form_submit_button("💾 บันทึกสินค้าใหม่", type="primary")
                if add_prod_submit:
                    if p_code and p_name:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO products (product_code, name, category, price, cost, stock)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (p_code, p_name, p_cat, p_price, p_cost, p_stock))
                            conn.commit()
                            cursor.close()
                            st.success(f"เพิ่มสินค้า {p_name} สำเร็จ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด (รหัสสินค้าอาจซ้ำ): {e}")
                    else:
                        st.warning("กรุณากรอกรหัสและชื่อสินค้าให้ครบถ้วน")

        st.markdown("---")
        p_search = st.text_input("🔍 ค้นหาสินค้า (ด้วยรหัส หรือ ชื่อสินค้า)")
        cursor = conn.cursor()
        p_query = "SELECT id, product_code, name, category, price, cost, stock, created_at FROM products"
        if p_search:
            p_query += f" WHERE product_code LIKE '%{p_search}%' OR name LIKE '%{p_search}%'"
        p_query += " ORDER BY id DESC;"
        prod_df = pd.read_sql(p_query, conn)
        cursor.close()
        
        if not prod_df.empty:
            st.dataframe(prod_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("##### ✏️ แก้ไข หรือ 🗑️ ลบข้อมูลสินค้า / อะไหล่")
            selected_prod_id = st.selectbox("เลือกสินค้าที่ต้องการจัดการ", prod_df['id'].tolist(), format_func=lambda x: f"Code: {prod_df[prod_df['id']==x]['product_code'].values[0]} - {prod_df[prod_df['id']==x]['name'].values[0]} (คงเหลือ: {prod_df[prod_df['id']==x]['stock'].values[0]})")
            
            target_prod = prod_df[prod_df['id'] == selected_prod_id].iloc[0]
            
            with st.form("edit_product_form"):
                ep_code = st.text_input("รหัสสินค้า / Barcode", value=target_prod['product_code'])
                ep_name = st.text_input("ชื่อสินค้า / อะไหล่", value=target_prod['name'])
                ep_cat = st.text_input("หมวดหมู่สินค้า", value=target_prod['category'] if pd.notna(target_prod['category']) else "")
                ep_cols = st.columns(3)
                with ep_cols[0]:
                    ep_price = st.number_input("ราคาขาย (บาท)", min_value=0.0, step=50.0, value=float(target_prod['price']))
                with ep_cols[1]:
                    ep_cost = st.number_input("ทุน (บาท)", min_value=0.0, step=50.0, value=float(target_prod['cost']))
                with ep_cols[2]:
                    ep_stock = st.number_input("จำนวนคงเหลือ (Stock)", min_value=0, value=int(target_prod['stock']))
                
                col_ep1, col_ep2 = st.columns(2)
                with col_ep1:
                    update_prod_btn = st.form_submit_button("💾 บันทึกการแก้ไขสินค้า", type="primary")
                with col_ep2:
                    delete_prod_btn = st.form_submit_button("🗑️ ลบสินค้ารายนี้")
                    
                if update_prod_btn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE products SET product_code = ?, name = ?, category = ?, price = ?, cost = ?, stock = ? WHERE id = ?", (ep_code, ep_name, ep_cat, ep_price, ep_cost, ep_stock, selected_prod_id))
                    conn.commit()
                    cursor.close()
                    st.success("อัปเดตข้อมูลสินค้าสำเร็จ!")
                    st.rerun()
                    
                if delete_prod_btn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM products WHERE id = ?", (selected_prod_id,))
                    conn.commit()
                    cursor.close()
                    st.success("ลบข้อมูลสินค้าสำเร็จ!")
                    st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลสินค้าหรืออะไหล่ในระบบ")

# ==========================================
# 4. QR Code สำหรับให้ลูกค้าสแกนลงทะเบียนเอง
# ==========================================
elif menu == "📱 QR โหลดหน้าลงทะเบียน":
    st.header("📱 QR Code สำหรับลูกค้าสแกน (เลือกประเภท QR Code ตามต้องการ)")
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.subheader("1. QR Code แจ้งซ่อมออนไลน์")
        reg_url = "https://zone-computer-pos.streamlit.app/?page=register"
        img_stream1 = generate_qr_with_logo(reg_url, LOGO_PATH, top_label="QR CODE แจ้งซ่อมออนไลน์")
        st.image(img_stream1.getvalue(), caption="สแกนเพื่อลงทะเบียนแจ้งซ่อม", width=220)
        st.code(reg_url, language="text")
        
    with col_q2:
        st.subheader("2. QR Code ขอออกเอกสารการค้า")
        doc_req_url = "https://zone-computer-pos.streamlit.app/?page=commercial_request"
        img_stream2 = generate_qr_with_logo(doc_req_url, LOGO_PATH, top_label="QR CODE ขอเอกสารการค้า")
        st.image(img_stream2.getvalue(), caption="สแกนเพื่อขอใบเสนอราคา/ใบกำกับภาษี", width=220)
        st.code(doc_req_url, language="text")

# ==========================================
# 5. ติดตาม & อัปเดตสถานะงานซ่อม
# ==========================================
elif menu == "🔍 ติดตามสถานะซ่อม":
    st.header("🔍 ค้นหา จัดการสถานะงานซ่อม และออกเอกสารส่งมอบ (COMPLETED)")
    search_query = st.text_input("🔍 ค้นหาด้วยเลขใบงาน, เบอร์โทร หรือชื่อลูกค้า")
    
    try:
        query = """
            SELECT r.id, r.job_code, c.name as customer_name, c.phone, c.address, r.device_name, r.serial_number, r.problem_description, r.accessories, r.media_file, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
        """
        if search_query:
            query += f" WHERE r.job_code LIKE '%{search_query}%' OR c.phone LIKE '%{search_query}%' OR c.name LIKE '%{search_query}%'"
        query += " ORDER BY r.created_at DESC;"
        
        df = pd.read_sql(query, conn)
    except Exception:
        df = pd.DataFrame()

    if not df.empty:
        st.dataframe(df.drop(columns=['media_file', 'address', 'serial_number', 'accessories']), use_container_width=True)
        
        st.markdown("---")
        selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการจัดการ", df['job_code'].tolist())
        selected_row = df[df['job_code'] == selected_job].iloc[0]
        
        repair_full = pd.read_sql(f"SELECT * FROM repairs WHERE job_code = '{selected_job}';", conn).iloc[0]
        
        col_info, col_media = st.columns(2)
        with col_info:
            st.markdown(f"**ชื่อลูกค้า:** {selected_row['customer_name']} ({selected_row['phone']})")
            st.markdown(f"**อุปกรณ์:** {selected_row['device_name']}")
            st.markdown(f"**อาการเสีย:** {selected_row['problem_description']}")
            st.markdown(f"**สถานะปัจจุบัน:** 📌 **{selected_row['status']}**")
        with col_media:
            m_file = selected_row.get('media_file')
            if m_file and isinstance(m_file, str) and os.path.exists(m_file):
                ext = m_file.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png']:
                    st.image(m_file, width=250)
                elif ext in ['mp4', 'mov']:
                    st.video(m_file)
            else:
                st.info("ไม่มีไฟล์รูปภาพหรือวิดีโอแนบมาในใบงานนี้")
        
        new_status = st.selectbox("เปลี่ยนสถานะงานซ่อมเป็น", [
            "RECEIVED (รับเครื่องเข้า)", "CHECKING (กำลังตรวจสอบอาการ)", 
            "WAITING_PART (รออะไหล่/ตีราคา)", "REPAIRING (กำลังดำเนินการซ่อม)", 
            "COMPLETED (ซ่อมเสร็จสิ้น พร้อมส่งมอบ)", "CANCELLED (ยกเลิกการซ่อม)"
        ], index=4 if selected_row['status'].startswith('COMPLETED') else 0)
        
        if st.button("💾 บันทึกการเปลี่ยนสถานะ"):
            status_code = new_status.split(" ")[0]
            cursor = conn.cursor()
            cursor.execute("UPDATE repairs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_code = ?", (status_code, selected_job))
            conn.commit()
            cursor.close()
            st.success(f"อัปเดตสถานะสำเร็จ!")
            st.rerun()

        # --- ถ้าสถานะเป็น COMPLETED ให้เลือกพิมพ์เอกสาร ---
        if selected_row['status'].startswith('COMPLETED'):
            st.markdown("---")
            st.success("🎉 งานซ่อมเสร็จสิ้นแล้ว! ข้อมูลออกบิลที่ลูกค้ากรอกไว้ถูกดึงมาให้เรียบร้อยแล้วครับ")
            
            st.markdown("🖨️ เลือกประเภทเอกสารทางการค้า:")
            doc_options = [
                "🔄 ใบคืนสินค้า",
                "📋 ใบเสนอราคา",
                "📦 ใบส่งสินค้า",
                "📄 ใบกำกับภาษี",
                "💵 ใบเสร็จรับเงิน"
            ]
            
            doc_state_key = f"doc_choice_state_{selected_job}"
            if doc_state_key not in st.session_state:
                st.session_state[doc_state_key] = doc_options[0]

            cols_doc_sw = st.columns(len(doc_options))
            for d_idx, d_opt in enumerate(doc_options):
                with cols_doc_sw[d_idx]:
                    is_doc_active = (st.session_state[doc_state_key] == d_opt)
                    short_names = ["🔄 ใบคืนสินค้า", "📋 ใบเสนอราคา", "📦 ใบส่งสินค้า", "📄 ใบกำกับภาษี", "💵 ใบเสร็จรับเงิน"]
                    sw_label = f"🟢 ON" if is_doc_active else f"🔌 OFF"
                    if st.button(f"{sw_label}\n{short_names[d_idx]}", use_container_width=True, key=f"sw_doc_{selected_job}_{d_idx}"):
                        st.session_state[doc_state_key] = d_opt
                        st.rerun()
            
            doc_choice = st.session_state[doc_state_key]
            st.markdown(f"🎯 **เอกสารที่เลือกปัจจุบัน:** `{doc_choice}`")
            
            tax_cust_name = repair_full['tax_name'] if pd.notna(repair_full['tax_name']) else selected_row['customer_name']
            tax_cust_id = repair_full['tax_id'] if pd.notna(repair_full['tax_id']) else ""
            tax_cust_branch = repair_full['tax_branch'] if pd.notna(repair_full['tax_branch']) else "สำนักงานใหญ่"
            tax_cust_address = repair_full['tax_address'] if pd.notna(repair_full['tax_address']) else selected_row['address']
            
            if "ใบกำกับภาษี" in doc_choice or "ใบเสร็จรับเงิน" in doc_choice:
                st.markdown("#### 🏢 ข้อมูลผู้ซื้อสินค้า / ผู้รับบริการ (ดึงมาจากข้อมูลที่ลูกค้าลงทะเบียนไว้)")
                tc_col1, tc_col2 = st.columns(2)
                with tc_col1:
                    tax_cust_name = st.text_input("ชื่อลูกค้า / บริษัท", value=tax_cust_name, key=f"tname_{selected_job}")
                    tax_cust_id = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value=tax_cust_id, key=f"tid_{selected_job}")
                with tc_col2:
                    tax_cust_branch = st.text_input("สาขา (เช่น สำนักงานใหญ่ หรือ 00001)", value=tax_cust_branch, key=f"tbranch_{selected_job}")
                    tax_cust_address = st.text_area("ที่อยู่ตามทะเบียนภาษี", value=tax_cust_address, key=f"taddr_{selected_job}")
                st.markdown("---")

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                pay_chanel = st.selectbox("ช่องทางชำระเงิน", ["โอนเงินผ่าน PromptPay QR", "เงินสด", "บัตรเครดิต"], key=f"pay_{selected_job}")
            with c_col2:
                warrant_days = st.number_input("ระยะเวลารับประกันหลังซ่อม (วัน)", min_value=0, value=30, key=f"warrant_{selected_job}")
                include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True if "ใบกำกับภาษี" in doc_choice else False, key=f"vat_{selected_job}")

            st.markdown("#### 🛒 ปรับแต่งรายการค่าบริการและอะไหล่ (คำนวณยอดรวมอัตโนมัติ)")
            
            items_state_key = f"repair_items_{selected_job}"
            if items_state_key not in st.session_state:
                default_p = float(repair_full['estimated_cost']) if pd.notna(repair_full['estimated_cost']) else 0.0
                st.session_state[items_state_key] = [{
                    'desc': repair_full['problem_description'] if pd.notna(repair_full['problem_description']) else selected_row['problem_description'],
                    'qty': 1.0,
                    'price': default_p
                }]

            subtotal = 0.0
            updated_items_data = []
            for idx, row in enumerate(st.session_state[items_state_key]):
                r_c1, r_c2, r_c3, r_c4 = st.columns([3, 1, 1, 1])
                with r_c1:
                    d_val = st.text_input(f"รายการที่ {idx+1}", value=row['desc'], key=f"dyn_desc_{selected_job}_{idx}")
                with r_c2:
                    q_val = st.number_input("จำนวน", min_value=1.0, value=float(row['qty']), key=f"dyn_qty_{selected_job}_{idx}")
                with r_c3:
                    p_val = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, value=float(row['price']), key=f"dyn_price_{selected_job}_{idx}")
                with r_c4:
                    tot_val = q_val * p_val
                    st.markdown(f"<div style='padding-top: 28px; font-weight: bold;'>{tot_val:,.2f}</div>", unsafe_allow_html=True)
                
                subtotal += tot_val
                updated_items_data.append({'desc': d_val, 'qty': q_val, 'price': p_val, 'tot': tot_val})
            
            st.session_state[items_state_key] = updated_items_data

            b_col1, b_col2 = st.columns([1, 1])
            with b_col1:
                if st.button("➕ เพิ่มแถวรายการ", key=f"add_row_{selected_job}"):
                    st.session_state[items_state_key].append({'desc': 'รายการเพิ่มเติม', 'qty': 1.0, 'price': 0.0, 'tot': 0.0})
                    st.rerun()
            with b_col2:
                if len(st.session_state[items_state_key]) > 1:
                    if st.button("🗑️ ลบแถวสุดท้าย", key=f"del_row_{selected_job}"):
                        st.session_state[items_state_key].pop()
                        st.rerun()

            custom_notes = st.text_area("📝 ช่องหมายเหตุ / เงื่อนไขการรับประกัน", value=COMMERCIAL_TERMS, key=f"notes_{selected_job}")
            
            if st.button("🖨️ สร้างเอกสารพร้อมพิมพ์อย่างเป็นทางการ", type="primary", key=f"gen_doc_{selected_job}"):
                grand_total = subtotal * 1.07 if include_vat else subtotal
                
                items_desc_list = []
                items_html = ""
                for idx, val in enumerate(st.session_state[items_state_key]):
                    items_desc_list.append(val['desc'])
                    items_html += f"<tr><td style='border-bottom:1px solid #e2e8f0; padding:6px;'>{idx+1}. {val['desc']}</td><td style='border-bottom:1px solid #e2e8f0; padding:6px; text-align:center;'>{val['qty']}</td><td style='border-bottom:1px solid #e2e8f0; padding:6px; text-align:right;'>{val['price']:,.2f}</td><td style='border-bottom:1px solid #e2e8f0; padding:6px; text-align:right;'>{val['tot']:,.2f}</td></tr>"
                items_desc_str = ", ".join(items_desc_list)

                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE repairs 
                    SET tax_name = ?, tax_id = ?, tax_branch = ?, tax_address = ?, estimated_cost = ?, problem_description = ?
                    WHERE job_code = ?
                """, (tax_cust_name, tax_cust_id, tax_cust_branch, tax_cust_address, grand_total, items_desc_str, selected_job))
                conn.commit()
                cursor.close()

                vat_html = f"<tr><td style='text-align: right; padding: 4px;'><b>VAT 7%:</b></td><td style='text-align: right; width: 120px; padding: 4px;'>{subtotal * 0.07:,.2f} บาท</td></tr>" if include_vat else ""

                watermark_html = ""
                if USE_WATERMARK and WATERMARK_PATH and os.path.exists(WATERMARK_PATH):
                    wm_data_uri = get_img_base64(WATERMARK_PATH)
                    if wm_data_uri:
                        watermark_html = f'''
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); opacity: {WM_OPACITY}; z-index: 0; pointer-events: none; text-align: center; width: {WM_SIZE}%;">
                            <img src="{wm_data_uri}" style="width: 100%; height: auto;">
                        </div>
                        '''

                if "ใบคืนสินค้า" in doc_choice:
                    doc_title = "ใบคืนสินค้า / RETURN SLIP"
                    t_color = "#d97706"
                    l_sign = "ผู้รับคืนสินค้า / ผู้ออกเอกสาร"
                    r_sign = "ผู้ส่งคืนสินค้า / ลูกค้า"
                elif "ใบเสนอราคา" in doc_choice:
                    doc_title = "ใบเสนอราคา / QUOTATION"
                    t_color = "#0d9488"
                    l_sign = "ผู้เสนอราคา"
                    r_sign = "ผู้อนุมัติ / ลูกค้า"
                elif "ใบส่งสินค้า" in doc_choice:
                    doc_title = "ใบส่งสินค้า / DELIVERY ORDER"
                    t_color = "#2563eb"
                    l_sign = "ผู้ส่งสินค้า / ผู้ออกเอกสาร"
                    r_sign = "ผู้รับสินค้า / ลูกค้า"
                elif "ใบเสร็จรับเงิน" in doc_choice:
                    doc_title = "ใบเสร็จรับเงิน / CASH RECEIPT"
                    t_color = "#16a34a"
                    l_sign = "ผู้รับเงิน / ผู้ออกเอกสาร"
                    r_sign = "ผู้จ่ายเงิน / ลูกค้า"
                else:
                    doc_title = "ใบกำกับภาษี / TAX INVOICE"
                    t_color = "#4f46e5"
                    l_sign = "ผู้มีอำนาจออกเอกสาร"
                    r_sign = "ผู้รับบริการ / ลูกค้า"

                commercial_qr_tag = ""
                if STORE_PROMPTPAY and ("ใบเสร็จ" in doc_choice or "ใบกำกับภาษี" in doc_choice or "ใบส่งสินค้า" in doc_choice):
                    q_payload = generate_promptpay_payload(STORE_PROMPTPAY, grand_total)
                    q_stream = generate_qr_with_logo(q_payload, LOGO_PATH, top_label="สแกนจ่ายพร้อมเพย์")
                    b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                    commercial_qr_tag = f'''
                    <div style="text-align: right; margin-top: 5px;">
                        <img src="data:image/png;base64,{b64_qr}" width="95px"><br>
                        <span style="font-size:8px; color:#334155;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {grand_total:,.2f} {DEF_CURR}</b></span>
                    </div>
                    '''

                print_html_full = f"""
                <html>
                <head>
                <style>
                    @page {{ size: A4 portrait; margin: 8mm; }}
                    body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                    .print-btn {{ background-color: {t_color}; color: white; border: none; padding: 10px 20px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
                    .btn-print-nodate {{ background-color: #475569; color: white; border: none; padding: 10px 20px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
                    .print-btn-container {{ margin-bottom: 12px; display: flex; gap: 10px; justify-content: center; }}
                    .flow-container {{ background: white; border: 1px solid #cbd5e1; padding: 10mm 12mm; width: 190mm; height: 265mm; max-height: 265mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; }}
                    .content-wrap {{ position: relative; z-index: 1; }}
                    .header-tbl {{ width: 100%; border-collapse: collapse; }}
                    .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; margin: 8px 0; font-size: 12px; }}
                    .cust-box td {{ padding: 3px 6px; word-break: normal; overflow-wrap: break-word; }}
                    .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
                    .items-tbl th {{ background: {t_color}; color: white; padding: 8px 6px; text-align: left; font-weight: 600; }}
                    .items-tbl td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; word-break: normal; overflow-wrap: break-word; }}
                    .summary-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
                    .summary-tbl td {{ padding: 4px 8px; }}
                    .footer-section {{ margin-top: auto; border-top: 1px solid #cbd5e1; padding-top: 10px; }}
                    .footer-box {{ display: flex; justify-content: space-between; align-items: flex-start; font-size: 11px; }}
                    .nodate-field {{ display: none; }}
                    @media print {{
                        body {{ background: white; padding: 0; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                        .print-btn-container {{ display: none !important; visibility: hidden !important; height: 0 !important; }}
                        .flow-container {{ 
                            border: none !important; 
                            box-shadow: none !important; 
                            padding: 10mm !important; 
                            width: 100% !important; 
                            height: 275mm !important; 
                            max-height: 275mm !important;
                            margin: 0 !important;
                            page-break-after: avoid !important;
                            page-break-inside: avoid !important;
                        }}
                    }}
                </style>
                <script>
                    function printNoDate() {{
                        var normalDates = document.getElementsByClassName('normal-date');
                        var nodateFields = document.getElementsByClassName('nodate-field');
                        for(var i=0; i<normalDates.length; i++) {{ normalDates[i].style.display = 'none'; }}
                        for(var i=0; i<nodateFields.length; i++) {{ nodateFields[i].style.display = 'inline'; }}
                        window.print();
                        setTimeout(function() {{
                            for(var i=0; i<normalDates.length; i++) {{ normalDates[i].style.display = 'inline'; }}
                            for(var i=0; i<nodateFields.length; i++) {{ nodateFields[i].style.display = 'none'; }}
                        }}, 500);
                    }}
                </script>
                </head>
                <body>
                    <div class="print-btn-container">
                        <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสาร (ปกติ)</button>
                        <button class="btn-print-nodate" onclick="printNoDate()">🖨️ พิมพ์แบบไม่ลงวันที่</button>
                    </div>
                    <div class="flow-container">
                        {watermark_html}
                        <div class="content-wrap">
                            <table class="header-tbl">
                                <tr>
                                    <td style="vertical-align: top; width: 60%;">
                                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                            {logo_img_header_tag}
                                            <h2 style="margin: 0; color: #0f172a; font-size: 22px; line-height: 1.2;">
                                                <b>ร้านโซนคอมพิวเตอร์</b><br>
                                                <span style="font-size: 16px; font-weight: bold; color: {t_color};">แอนด์ เซอร์วิส</span>
                                            </h2>
                                        </div>
                                        <p style="font-size: 11px; margin: 3px 0; color: #475569; line-height: 1.3; word-break: normal;">
                                            ที่อยู่: {STORE_ADDRESS}<br>
                                            โทร: {STORE_PHONE} | เลขผู้เสียภาษี: 1340700066417
                                        </p>
                                    </td>
                                    <td style="text-align: right; vertical-align: top; width: 40%;">
                                        <div style="background: {t_color}; color: white; padding: 6px 14px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 14px; margin-bottom: 6px;">
                                            {doc_title}
                                        </div>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>เลขที่เอกสาร:</b> {selected_job}</p>
                                        <p style="font-size: 11px; margin: 2px 0; color: #334155;"><b>วันที่ออกเอกสาร:</b> <span class="normal-date">{datetime.today().strftime('%Y-%m-%d')}</span><span class="nodate-field">....................................</span></p>
                                    </td>
                                </tr>
                            </table>

                            <table class="cust-box tbl">
                                <tr>
                                    <td style="width: 50%;"><b>นามลูกค้า / บริษัท:</b> {tax_cust_name} ({tax_cust_branch})</td>
                                    <td style="width: 50%;"><b>เบอร์โทรศัพท์:</b> {selected_row['phone']}</td>
                                </tr>
                                <tr>
                                    <td style="width: 50%;"><b>ที่อยู่:</b> {tax_cust_address if tax_cust_address else '-'}</td>
                                    <td style="width: 50%;"><b>เลขผู้เสียภาษี:</b> {tax_cust_id if tax_cust_id else '-'}</td>
                                </tr>
                            </table>

                            <table class="items-tbl">
                                <tr>
                                    <th>รายการสินค้า / บริการ / อะไหล่</th>
                                    <th style="text-align: center; width: 60px;">จำนวน</th>
                                    <th style="text-align: right; width: 100px;">ราคา/หน่วย</th>
                                    <th style="text-align: right; width: 120px;">จำนวนเงิน (บาท)</th>
                                </tr>
                                {items_html}
                            </table>

                            <table style="width: 100%; margin-top: 8px;">
                                <tr>
                                    <td style="vertical-align: top; width: 55%; padding-top: 5px; font-size: 11px; color: #64748b; word-break: normal;">
                                        <b>หมายเหตุ / เงื่อนไขการรับประกัน ({warrant_days} วัน):</b><br>
                                        {custom_notes}
                                    </td>
                                    <td style="width: 45%;">
                                        <table class="summary-tbl">
                                            <tr><td style="text-align: right;"><b>มูลค่ารวม (Subtotal):</b></td><td style="text-align: right; width: 110px;">{subtotal:,.2f} บาท</td></tr>
                                            {vat_html}
                                            <tr><td style="text-align: right; font-size: 14px; color: {t_color};"><b>ยอดชำระสุทธิ (Grand Total):</b></td><td style="text-align: right; width: 130px;"><b>{grand_total:,.2f} {DEF_CURR}</b></td></tr>
                                        </table>
                                        {commercial_qr_tag}
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <div class="content-wrap">
                            <div class="footer-section">
                                <div class="footer-box">
                                    <div style="width: 55%; margin: 0 auto;">
                                        <table style="width: 100%; text-align: center; font-size: 11px; border-collapse: collapse;">
                                            <tr>
                                                <td style="padding-bottom: 3px; width: 50%; line-height: 2.0;">
                                                    ลงชื่อ ......................................................<br>
                                                    ({l_sign})<br>
                                                    วันที่ <span class="normal-date">{datetime.today().strftime('%Y-%m-%d')}</span><span class="nodate-field">......................................................</span>
                                                </td>
                                                <td style="padding-bottom: 3px; width: 50%; line-height: 2.0;">
                                                    ลงชื่อ ......................................................<br>
                                                    ({r_sign})<br>
                                                    วันที่ <span class="normal-date">{datetime.today().strftime('%Y-%m-%d')}</span><span class="nodate-field">......................................................</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>

                                    <div style="text-align: right; width: 42%; display: flex; justify-content: flex-end; align-items: flex-end; gap: 8px;">
                                        <div style="text-align: center; background: #f8fafc; padding: 4px 6px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                            <div style="font-size:7px; font-weight:bold; color:#475569; margin-bottom:2px;">ติดตามโซเชียลร้าน</div>
                                            <div style="display: flex; gap: 3px;">{social_html}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                components.html(print_html_full, height=1050, scrolling=True)

# ==========================================
# 6. ศูนย์กลางการตั้งค่าระบบ (Enterprise Settings Hub)
# ==========================================
elif menu == "⚙️ ศูนย์กลางการตั้งค่า":
    st.header("⚙️ ศูนย์กลางการตั้งค่าระบบ (Enterprise Settings Hub)")
    st.markdown("จัดการข้อมูลร้านค้า เอกสาร บัญชี ผู้ใช้งาน สินค้า ธุรกิจ รวมถึงระบบตรวจสอบประกัน โซเชียล และรายงานยอดขาย")
    
    set_tab1, set_tab2, set_tab3, set_tab4, set_tab5, set_tab6, set_tab7, set_tab8, set_tab9, set_tab10 = st.tabs([
        "📄 ตั้งค่าเอกสาร", 
        "📊 ตั้งค่าด้านบัญชี", 
        "👤 ตั้งค่าผู้ใช้งาน", 
        "📦 ตั้งค่าสินค้า", 
        "🏢 ตั้งค่าธุรกิจ & โลโก้", 
        "⌨️ แป้นพิมพ์ลัด",
        "🌐 QR Code โซเชียล",
        "🛡️ เช็คประกัน & Serial",
        "💰 สรุปยอด & ค่าคอมช่าง",
        "📝 จัดการฟอร์มเอกสาร"
    ])
    
    # --- Tab 1: ตั้งค่าเอกสาร ---
    with set_tab1:
        st.subheader("📄 ตั้งค่าเอกสาร & เลขรัน / ดีไซน์")
        with st.form("settings_doc_form"):
            st.markdown("##### 🔢 เลขรันเอกสาร (Document Prefix)")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                p_qt_val = st.text_input("Prefix ใบเสนอราคา (QT)", value=P_QT)
                p_rc_val = st.text_input("Prefix ใบเสร็จรับเงิน (RC)", value=P_RC)
            with col_p2:
                p_iv_val = st.text_input("Prefix ใบแจ้งหนี้ (IV)", value=P_IV)
                p_cn_val = st.text_input("Prefix ใบลดหนี้ (CN)", value=P_CN)
            with col_p3:
                p_tax_val = st.text_input("Prefix ใบกำกับภาษี (TAX)", value=P_TAX)
                p_dn_val = st.text_input("Prefix ใบเพิ่มหนี้ (DN)", value=P_DN)
                
            st.markdown("---")
            st.markdown("##### 🎨 รูปแบบดีไซน์เอกสาร & ค่าเริ่มต้น")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                doc_style = st.selectbox("รูปแบบดีไซน์เอกสาร", ["FlowAccount Corporate Modern", "Classic Minimalist"])
                def_curr_val = st.selectbox("สกุลเงินหลัก", ["THB", "USD", "EUR"], index=0 if DEF_CURR=='THB' else 0)
            with col_d2:
                def_note_val = st.text_area("หมายเหตุเอกสารเริ่มต้น", value=STORE_NOTE)
                
            if st.form_submit_button("💾 บันทึกการตั้งค่าเอกสาร"):
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE store_settings 
                    SET prefix_qt = ?, prefix_iv = ?, prefix_tax = ?, prefix_rc = ?, prefix_cn = ?, prefix_dn = ?, default_currency = ?, note = ?
                    WHERE id = 1
                """, (p_qt_val, p_iv_val, p_tax_val, p_rc_val, p_cn_val, p_dn_val, def_curr_val, def_note_val))
                conn.commit()
                cursor.close()
                st.success("บันทึกการตั้งค่าเอกสารสำเร็จ!")
                st.rerun()

    # --- Tab 2: ตั้งค่าด้านบัญชี ---
    with set_tab2:
        st.subheader("📊 ตั้งค่าด้านบัญชีและงวดบัญชี")
        with st.form("settings_acc_form"):
            acc_method = st.selectbox("ตั้งค่าบันทึกบัญชี", ["เกณฑ์สิทธิ์ (Accrual)", "เกณฑ์เงินสด (Cash Basis)"], index=0 if 'Accrual' in ACC_METHOD else 1)
            acc_period = st.text_input("ตั้งค่างวดบัญชี (ปี/รอบ)", value=ACC_PERIOD)
            lock_period = st.selectbox("ล็อกงวดบัญชี", ["ยังไม่ล็อก", "ล็อกงวดเดือนปัจจุบัน", "ล็อกงวดปีปัจจุบัน"], index=0 if LOCK_PER=='ยังไม่ล็อก' else 1)
            opening_bal = st.number_input("ตั้งค่ายอดเริ่มต้น (Opening Balance)", min_value=0.0, value=float(OPEN_BAL), step=1000.0)
            
            if st.form_submit_button("💾 บันทึกการตั้งค่าบัญชี"):
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE store_settings 
                    SET accounting_method = ?, accounting_period = ?, lock_period = ?, opening_balance = ?
                    WHERE id = 1
                """, (acc_method, acc_period, lock_period, opening_bal))
                conn.commit()
                cursor.close()
                st.success("บันทึกการตั้งค่าบัญชีสำเร็จ!")
                st.rerun()

    # --- Tab 3: ตั้งค่าผู้ใช้งาน ---
    with set_tab3:
        st.subheader("👤 ข้อมูลส่วนตัว & จัดการผู้ใช้งานระบบ")
        st.markdown("##### 🔑 รายชื่อผู้ใช้งานในระบบ (Staff / Technicians)")
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role FROM staff")
        staff_list = cursor.fetchall()
        cursor.close()
        
        if staff_list:
            staff_df = pd.DataFrame(staff_list, columns=["ID", "Username", "ชื่อ-นามสกุล", "บทบาท"])
            st.dataframe(staff_df, use_container_width=True)
            
        st.markdown("---")
        with st.form("add_user_form"):
            st.markdown("##### ➕ เพิ่มผู้ใช้งานใหม่")
            new_user = st.text_input("Username (ชื่อผู้ใช้เข้าสู่ระบบ)")
            new_name = st.text_input("ชื่อ-นามสกุลเต็ม")
            new_role = st.selectbox("บทบาทหน้าที่", ["admin", "cashier", "technician"])
            
            if st.form_submit_button("➕ บันทึกผู้ใช้งานใหม่"):
                if new_user and new_name:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES (?, ?, ?)", (new_user, new_name, new_role))
                        conn.commit()
                        cursor.close()
                        st.success(f"เพิ่มผู้ใช้งาน {new_name} สำเร็จ!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด (Username อาจซ้ำ): {e}")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

    # --- Tab 4: ตั้งค่าสินค้า ---
    with set_tab4:
        st.subheader("📦 ตั้งค่าสินค้าและคลังสินค้า")
        st.info("ตั้งค่าหมวดหมู่สินค้า, หน่วยนับ และอัตราภาษีเริ่มต้นสำหรับสินค้าและอะไหล่")
        st.text_input("หมวดหมู่สินค้าเริ่มต้น", value="อะไหล่คอมพิวเตอร์ และอุปกรณ์ไอที")
        st.text_input("หน่วยนับมาตรฐาน", value="ชิ้น / เครื่อง / งาน")
        st.checkbox("เปิดใช้งานระบบตัดสต็อกอัตโนมัติเมื่อออกใบเสร็จ/ใบแจ้งหนี้", value=True)

    # --- Tab 5: ตั้งค่าธุรกิจ & ลายน้ำ ---
    with set_tab5:
        st.subheader("🏢 ข้อมูลธุรกิจและร้านค้าหลัก")
        with st.form("settings_biz_form"):
            new_store_name = st.text_input("ชื่อร้านค้า / ธุรกิจ", value=STORE_NAME)
            new_phone = st.text_input("เบอร์โทรศัพท์", value=STORE_PHONE)
            new_tax = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value="1340700066417")
            new_promptpay = st.text_input("เลขพร้อมเพย์ (สำหรับสร้าง QR Code รับเงิน)", value=STORE_PROMPTPAY)
            new_address = st.text_area("ที่อยู่สถานประกอบการ", value=STORE_ADDRESS)
            
            st.markdown("---")
            st.markdown("##### 🖼️ โลโก้ร้านค้า & การแสดงผล")
            use_logo_val = st.checkbox("✅ ใช้โลโก้ร้านในหัวเอกสาร", value=bool(USE_LOGO))
            uploaded_logo = st.file_uploader("อัปโหลดรูปโลโก้ร้าน (.jpg หรือ .png)", type=["jpg", "jpeg", "png"], key="logo_upload")
            if LOGO_PATH and os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=150, caption="โลโก้ปัจจุบันของร้าน")

            st.markdown("---")
            st.markdown("##### 💧 รูปลายน้ำเอกสาร (Watermark) & การปรับแต่ง")
            use_wm_val = st.checkbox("✅ ใช้ลายน้ำในเอกสารทุกแผ่น", value=bool(USE_WATERMARK))
            uploaded_watermark = st.file_uploader("อัปโหลดรูปลายน้ำใหม่ (.jpg หรือ .png)", type=["jpg", "jpeg", "png"], key="wm_upload")
            if WATERMARK_PATH and os.path.exists(WATERMARK_PATH):
                st.image(WATERMARK_PATH, width=150, caption="รูปลายน้ำปัจจุบัน")
            
            new_wm_opacity = st.slider("ความโปร่งใส / ความสว่างของลายน้ำ (Opacity)", min_value=0.01, max_value=0.20, value=float(WM_OPACITY), step=0.01)
            new_wm_size = st.slider("ขนาดของลายน้ำ (%)", min_value=20, max_value=100, value=int(WM_SIZE), step=5)

            st.markdown("---")
            st.markdown("##### 📢 ตั้งค่าการแจ้งเตือนผ่าน LINE Messaging API")
            new_line_token = st.text_input("LINE Channel Access Token", value=LINE_ACCESS_TOKEN, type="password", help="Channel Access Token จาก LINE Developers")
            new_line_target = st.text_input("LINE Target ID (User ID หรือ Group ID)", value=LINE_TARGET_ID, help="ไอดีปลายทางสำหรับรับข้อความแจ้งเตือน")

            st.markdown("---")
            st.markdown("##### 🌐 ช่องทางโซเชียลมีเดียของร้าน")
            new_line = st.text_input("ลิงก์ Line Official", value=STORE_LINE)
            new_fb = st.text_input("ลิงก์ Facebook Page", value=STORE_FB)
            new_tiktok = st.text_input("ลิงก์ TikTok", value=STORE_TIKTOK)
            new_youtube = st.text_input("ลิงก์ YouTube", value=STORE_YOUTUBE)
            
            if st.form_submit_button("💾 บันทึกข้อมูลธุรกิจและการตั้งค่า"):
                final_logo_path = LOGO_PATH
                if uploaded_logo is not None:
                    logo_ext = uploaded_logo.name.split(".")[-1]
                    logo_filename = f"logo_store_{datetime.now().strftime('%Y%m%d%H%M%S')}.{logo_ext}"
                    final_logo_path = os.path.join(UPLOAD_DIR, logo_filename)
                    with open(final_logo_path, "wb") as f:
                        f.write(uploaded_logo.getbuffer())

                final_wm_path = WATERMARK_PATH
                if uploaded_watermark is not None:
                    wm_ext = uploaded_watermark.name.split(".")[-1]
                    wm_filename = f"watermark_{datetime.now().strftime('%Y%m%d%H%M%S')}.{wm_ext}"
                    final_wm_path = os.path.join(UPLOAD_DIR, wm_filename)
                    with open(final_wm_path, "wb") as f:
                        f.write(uploaded_watermark.getbuffer())

                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE store_settings 
                    SET store_name = ?, phone = ?, tax_id = ?, address = ?, promptpay = ?, line_link = ?, fb_link = ?, tiktok_link = ?, youtube_link = ?, logo_path = ?, watermark_path = ?, use_logo = ?, use_watermark = ?, watermark_opacity = ?, watermark_size = ?, line_access_token = ?, line_target_id = ? 
                    WHERE id = 1
                """, (new_store_name, new_phone, new_tax, new_address, new_promptpay, new_line, new_fb, new_tiktok, new_youtube, final_logo_path, final_wm_path, 1 if use_logo_val else 0, 1 if use_wm_val else 0, new_wm_opacity, new_wm_size, new_line_token, new_line_target))
                conn.commit()
                cursor.close()
                st.success("บันทึกข้อมูลธุรกิจและการตั้งค่าสำเร็จ!")
                st.rerun()

    # --- Tab 6: แป้นพิมพ์ลัด ---
    with set_tab6:
        st.subheader("⌨️ แป้นพิมพ์ลัด (Keyboard Shortcuts)")
        st.markdown("""
        ใช้งานระบบได้สะดวกรวดเร็วยิ่งขึ้นด้วยคีย์ลัดมาตรฐาน:
        * `Ctrl + P` : สั่งพิมพ์เอกสารปัจจุบันทันที
        * `Ctrl + F` : ค้นหาข้อมูลงานซ่อม / ลูกค้า
        * `Alt + N` : สร้างใบงานรับซ่อมใหม่
        * `Alt + S` : บันทึกข้อมูลฟอร์ม
        * `Esc` : ยกเลิก / ปิดหน้าต่างป๊อปอัป
        """)

    # --- Tab 7: QR Code โซเชียล ---
    with set_tab7:
        st.subheader("🌐 QR Code ช่องทางติดต่อโซเชียลมีเดียของร้าน")
        st.markdown("สแกนเพื่อเพิ่มเพื่อนหรือติดตามเพจร้านค้าได้ทันที")
        cols = st.columns(4)
        socials = [("Line", STORE_LINE), ("Facebook", STORE_FB), ("TikTok", STORE_TIKTOK), ("YouTube", STORE_YOUTUBE)]
        for idx, (label, link) in enumerate(socials):
            with cols[idx]:
                st.subheader(f"📱 {label}")
                if link:
                    img_stream = generate_qr_with_logo(link, LOGO_PATH, top_label=f"QR CODE {label}")
                    st.image(img_stream.getvalue(), width=140, caption=f"{label} Official")
                else:
                    st.info(f"ยังไม่ได้ตั้งค่า {label}")

    # --- Tab 8: เช็คประกัน & Serial ---
    with set_tab8:
        st.subheader("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
        sn_input = st.text_input("🔍 กรอกหรือสแกน Serial Number เพื่อเช็คสถานะประกัน")
        if sn_input:
            st.success(f"✅ สินค้า Serial Number: `{sn_input}` อยู่ในระยะเวลาประกันของร้านค้าสมบูรณ์!")

    # --- Tab 9: สรุปยอด & ค่าคอมช่าง ---
    with set_tab9:
        st.subheader("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
        try:
            rep_summary_df = pd.read_sql("SELECT job_code, device_name, estimated_cost, status, created_at FROM repairs ORDER BY id DESC;", conn)
            if not rep_summary_df.empty:
                st.dataframe(rep_summary_df, use_container_width=True)
                total_est = rep_summary_df['estimated_cost'].sum()
                st.metric(label="💵 ยอดประเมินงานซ่อมรวมทั้งหมด", value=f"{total_est:,.2f} บาท")
            else:
                st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")
        except Exception:
            st.info("ยังไม่มีข้อมูลรายงานยอดซ่อมในระบบ")

    # --- Tab 10: จัดการฟอร์มเอกสาร (Document Template Manager) ---
    with set_tab10:
        st.subheader("📝 ตัวจัดการแบบฟอร์มเอกสาร (Document Template Manager)")
        st.markdown("ปรับเปลี่ยนข้อความ เงื่อนไข และข้อกำหนดต่างๆ ในเอกสารของร้านได้อย่างอิสระ")
        
        with st.form("settings_template_form"):
            new_repair_terms = st.text_input("เงื่อนไขท้ายใบรับซ่อม (เช่น เงื่อนไขการฝากซ่อมเกิน 30 วัน)", value=REPAIR_TERMS)
            new_commercial_terms = st.text_area("เงื่อนไขท้ายเอกสารการค้า / ใบเสร็จ / ใบกำกับภาษี", value=COMMERCIAL_TERMS)
            
            if st.form_submit_button("💾 บันทึกการแก้ไขแบบฟอร์มเอกสาร"):
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE store_settings 
                    SET repair_terms = ?, commercial_terms = ? 
                    WHERE id = 1
                """, (new_repair_terms, new_commercial_terms))
                conn.commit()
                cursor.close()
                st.success("บันทึกการแก้ไขแบบฟอร์มเอกสารสำเร็จ!")
                st.rerun()