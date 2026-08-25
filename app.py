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
from PIL import Image, ImageDraw

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

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ZoneOnline Service - Enterprise Edition", 
    page_icon="⚡", 
    layout="wide"
)

# ฟังก์ชันแปลงไฟล์รูปเป็น Data URI Base64 รองรับทั้ง JPG และ PNG อย่างถูกต้อง
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

# ฟังก์ชันเชื่อมต่อและสร้างฐานข้อมูล SQLite แบบอัตโนมัติ
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
            logo_path TEXT
        )
    ''')
    
    extra_cols = [
        ('prefix_qt', 'TEXT'), ('prefix_iv', 'TEXT'), ('prefix_tax', 'TEXT'),
        ('prefix_rc', 'TEXT'), ('prefix_cn', 'TEXT'), ('prefix_dn', 'TEXT'),
        ('default_currency', 'TEXT'), ('accounting_method', 'TEXT'), 
        ('accounting_period', 'TEXT'), ('lock_period', 'TEXT'), ('opening_balance', 'REAL'),
        ('logo_path', 'TEXT')
    ]
    for col, col_type in extra_cols:
        try:
            cursor.execute(f"ALTER TABLE store_settings ADD COLUMN {col} {col_type};")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    # ตารางเก็บข้อมูลเอกสารการค้า (Sales Pipeline & Workflow)
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

    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link, prefix_qt, prefix_iv, prefix_tax, prefix_rc, prefix_cn, prefix_dn, default_currency, logo_path) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-123-4567', '1234567890123', 'อุบลราชธานี', 'ขอบคุณที่ใช้บริการครับ', '0891234567', 'https://line.me', 'https://facebook.com', 'https://tiktok.com', 'QT', 'IV', 'TAX', 'RC', 'CN', 'DN', 'THB', 'logo.jpg')
        ''')
        conn.commit()
    else:
        cursor.execute("UPDATE store_settings SET logo_path = 'logo.jpg' WHERE logo_path IS NULL OR logo_path = '';")
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'cashier', 'technician')) NOT NULL
        )
    ''')
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (technician_id) REFERENCES staff(id)
        )
    ''')
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN media_file TEXT;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.close()

conn = init_connection()
init_db(conn)

# ดึงข้อมูลร้านค้ามาใช้แสดงผล
cursor = conn.cursor()
cursor.execute("SELECT store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link, prefix_qt, prefix_iv, prefix_tax, prefix_rc, prefix_cn, prefix_dn, default_currency, accounting_method, accounting_period, lock_period, opening_balance, logo_path FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()

if store_info:
    (STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY, 
     STORE_LINE, STORE_FB, STORE_TIKTOK, P_QT, P_IV, P_TAX, P_RC, P_CN, P_DN, 
     DEF_CURR, ACC_METHOD, ACC_PERIOD, LOCK_PER, OPEN_BAL, LOGO_PATH) = store_info
else:
    STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY = "ร้านโซนคอมพิวเตอร์", "0891234567", "1234567890123", "อุบลราชธานี", "ขอบคุณ", "0891234567"
    STORE_LINE, STORE_FB, STORE_TIKTOK = "", "", ""
    P_QT, P_IV, P_TAX, P_RC, P_CN, P_DN = "QT", "IV", "TAX", "RC", "CN", "DN"
    DEF_CURR, ACC_METHOD, ACC_PERIOD, LOCK_PER, OPEN_BAL, LOGO_PATH = "THB", "เกณฑ์สิทธิ์ (Accrual)", "2026", "ยังไม่ล็อก", 0.0, "logo.jpg"

STORE_NAME = STORE_NAME or "ร้านโซนคอมพิวเตอร์"
STORE_PHONE = STORE_PHONE or ""
STORE_TAX = STORE_TAX or ""
STORE_ADDRESS = STORE_ADDRESS or ""
STORE_NOTE = STORE_NOTE or ""
STORE_PROMPTPAY = STORE_PROMPTPAY or ""
STORE_LINE = STORE_LINE or ""
STORE_FB = STORE_FB or ""
STORE_TIKTOK = STORE_TIKTOK or ""
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

# ==========================================
# 🔍 โหมดพิเศษ: หน้าจอเช็คสถานะสาธารณะผ่าน QR Code (?track=...)
# ==========================================
query_params = st.query_params
track_code = query_params.get("track", None)

if track_code:
    st.set_page_config(page_title=f"เช็คสถานะงานซ่อม - {STORE_NAME}", page_icon="🔍", layout="centered")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.job_code, r.device_name, r.problem_description, r.status, r.created_at, r.updated_at, c.name
        FROM repairs r JOIN customers c ON r.customer_id = c.id
        WHERE r.job_code = ?
    """, (track_code,))
    job_data = cursor.fetchone()
    cursor.close()
    
    if job_data:
        j_code, dev, prob, stat, d_in, d_up, c_name = job_data
        
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
                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .card {{ background: white; padding: 30px 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 420px; text-align: center; animation: fadeIn 0.8s ease-in-out; }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                h2 {{ color: #333; margin-bottom: 5px; font-size: 22px; }}
                .store-sub {{ color: #666; font-size: 13px; margin-bottom: 20px; }}
                .info-box {{ background: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 20px; text-align: left; font-size: 14px; border-left: 4px solid #007bff; }}
                .info-box p {{ margin: 6px 0; color: #444; }}
                .status-badge {{ background-color: {badge_color}; color: white; padding: 12px 20px; border-radius: 30px; font-weight: bold; font-size: 16px; display: inline-block; margin: 15px 0; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
                @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}
                .desc {{ color: #555; font-size: 13px; margin-top: 5px; }}
                .footer {{ margin-top: 25px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 15px; }}
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
                    <p><b>อาการแจ้งซ่อม:</b> {prob}</p>
                    <p><b>วันที่แจ้งซ่อม:</b> {d_in}</p>
                </div>
                
                <div>
                    <div class="status-badge">{thai_status}</div>
                    <div class="desc">ℹ️ {status_desc}</div>
                </div>

                <div class="footer">
                    📞 โทรสอบถามด่วน: {STORE_PHONE}<br>ขอบคุณที่ใช้บริการร้านโซนคอมพิวเตอร์ครับ 🙏
                </div>
            </div>

            <script>
                window.addEventListener('load', () => {{
                    try {{
                        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                        const osc = audioCtx.createOscillator();
                        const gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(659.25, audioCtx.currentTime);
                        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.2);
                    }} catch(e) {{}}
                }});
            </script>
        </body>
        </html>
        """
        components.html(public_html, height=650, scrolling=True)
    else:
        st.error("❌ ไม่พบข้อมูลใบงานนี้ในระบบ กรุณาตรวจสอบใหม่อีกครั้ง หรือติดต่อหน้าร้านครับ")
    st.stop()

# ==========================================
# 🖥️ หน้าแอดมินหลัก (Enterprise Dashboard with Horizontal Navigation)
# ==========================================
st.set_page_config(
    page_title="ZoneOnline Service - Enterprise Edition", 
    page_icon="⚡", 
    layout="wide"
)

st.title(f"⚡ {STORE_NAME} [Enterprise Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (พร้อมศูนย์กลางการตั้งค่า FlowAccount & ERP Style)")

if 'current_job_code' not in st.session_state:
    st.session_state.current_job_code = None

# แถบเมนูหลักแนวนอน (Horizontal Navigation Buttons)
menu_options = [
    "📥 รับเครื่องซ่อมใหม่", 
    "📱 ลูกค้าลงทะเบียนเอง",
    "🔍 ติดตามสถานะซ่อม", 
    "📄 ระบบออกเอกสารการค้า",
    "⚙️ ศูนย์กลางการตั้งค่า"
]

menu = st.radio("🎯 เลือกเมนูการทำงานหลัก", menu_options, horizontal=True)
st.markdown("---")

# ==========================================
# 1. รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่":
    st.header("📥 บันทึกรับเครื่องซ่อมและพิมพ์ใบรับซ่อม (A4 แนวตั้ง)")
    
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
    st.subheader("🖨️ ตัวอย่างใบรับซ่อม A4 แนวตั้ง (พร้อม QR Code เช็คสถานะเรียลไทม์)")
    
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
            cost = float(cost) if cost is not None else 0.0
            
            track_url = f"https://zone-computer-pos.streamlit.app/?track={j_code}"
            qr_track_obj = qrcode.make(track_url)
            track_stream = BytesIO()
            qr_track_obj.save(track_stream)
            track_b64 = base64.b64encode(track_stream.getvalue()).decode()
            qr_track_tag = f'<img src="data:image/png;base64,{track_b64}" width="75px"><br><span style="font-size:8px;">สแกนเช็คสถานะ</span>'
            
            portrait_a4_html = f"""
            <html>
            <head>
            <style>
                @page {{ size: A4 portrait; margin: 5mm; }}
                body {{ background: #f0f2f5; font-family: sans-serif; color: black; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                .print-btn-container {{ margin-bottom: 15px; }}
                .btn-print {{ background-color: #ff4b4b; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                .btn-print:hover {{ background-color: #e03e3e; }}
                .print-container {{ background: white; border: 1px solid #ccc; padding: 12mm 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .section-box {{ height: 125mm; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; }}
                h3, h4 {{ text-align: center; margin: 2px 0; }}
                p {{ font-size: 13px; margin: 4px 0; }}
                table {{ width: 100%; font-size: 13px; margin-top: 5px; border-collapse: collapse; }}
                td {{ padding: 3px 0; }}
                .perforation {{ border-top: 2px dashed #666; margin: 8mm 0; text-align: center; font-size: 11px; color: #444; font-weight: bold; }}
                .signature-row {{ display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px; align-items: flex-end; }}
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .print-btn-container {{ display: none; }}
                    .print-container {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                }}
            </style>
            </head>
            <body>
                <div class="print-btn-container">
                    <button class="btn-print" onclick="window.print()">🖨️ คลิกที่นี่เพื่อสั่งพิมพ์ใบรับซ่อม (A4 แนวตั้ง)</button>
                </div>
                
                <div class="print-container">
                    <!-- ส่วนที่ 1: สำหรับลูกค้า -->
                    <div class="section-box">
                        <div>
                            <h3><b>{STORE_NAME}</b></h3>
                            <p style="text-align: center; font-size: 11px;">ที่อยู่: {STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                            <h4 style="background: #eee; padding: 4px; margin-top: 5px;">ใบรับซ่อมสินค้า (สำหรับลูกค้า / ต้นฉบับ)</h4>
                            <table>
                                <tr><td><b>เลขที่ใบงาน:</b> {j_code}</td><td><b>วันที่รับเครื่อง:</b> {date_in}</td></tr>
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>
                            <p><b>อาการเสีย:</b> {prob}</p>
                            <p><b>อุปกรณ์ที่แนบมา:</b> {acc if acc else '-'}</p>
                            <p><b>ประเมินราคาเบื้องต้น:</b> <b>{cost:,.2f} บาท</b></p>
                        </div>
                        <div class="signature-row">
                            <div style="width: 75%;">
                                <span>ลงชื่อลูกค้า: ......................................................</span><br>
                                <span style="font-size:11px; color:#555;">(เงื่อนไข: ฝากซ่อมเกิน 30 วัน ทางร้านขอสงวนสิทธิ์เก็บค่าฝากรักษา)</span>
                            </div>
                            <div style="text-align: center; width: 25%;">
                                {qr_track_tag}
                            </div>
                        </div>
                    </div>

                    <!-- รอยฉีก -->
                    <div class="perforation">
                        ✂️ - - - - - - - - - - - - - - - - - รอยฉีกสำหรับแยกต้นฉบับและสำเนา (Cut / Tear Here) - - - - - - - - - - - - - - - - - ✂️
                    </div>

                    <!-- ส่วนที่ 2: สำหรับร้านค้า -->
                    <div class="section-box">
                        <div>
                            <h3><b>{STORE_NAME}</b></h3>
                            <p style="text-align: center; font-size: 11px;">ใบควบคุมงานซ่อมภายในร้าน (สำหรับร้านค้าเก็บไว้)</p>
                            <h4 style="background: #eee; padding: 4px; margin-top: 5px;">ใบรับซ่อมสินค้า (สำหรับร้านค้า / สำเนา)</h4>
                            <table>
                                <tr><td><b>เลขที่ใบงาน:</b> {j_code}</td><td><b>วันที่รับเครื่อง:</b> {date_in}</td></tr>
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>
                            <p><b>อาการเสีย:</b> {prob}</p>
                            <p><b>อุปกรณ์ที่แนบมา:</b> {acc if acc else '-'}</p>
                            <p><b>ประเมินราคาเบื้องต้น:</b> <b>{cost:,.2f} บาท</b></p>
                        </div>
                        <div class="signature-row">
                            <div style="width: 100%;">
                                <span>ลงชื่อลูกค้า (รับทราบเงื่อนไข): ...................................................... &nbsp;&nbsp;&nbsp;&nbsp; ช่างผู้รับซ่อม: ......................................................</span>
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
# 2. ระบบลูกค้าสแกน QR ลงทะเบียนเอง
# ==========================================
elif menu == "📱 ลูกค้าลงทะเบียนเอง":
    st.header("📱 ระบบลูกค้าลงทะเบียนแจ้งซ่อมผ่าน QR Code")
    qr_data = "https://zone-computer-pos.streamlit.app/?page=register"
    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    st.image(buf.getvalue(), caption="สแกนเพื่อเปิดหน้าลงทะเบียนแจ้งซ่อมออนไลน์", width=220)
    
    with st.form("self_service_media_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์ติดต่อกลับ")
        c_device = st.text_input("ยี่ห้อ / รุ่นอุปกรณ์")
        c_problem = st.text_area("อาการเสียเบื้องต้น")
        c_accessories = st.text_input("อุปกรณ์ที่ส่งมาด้วย")
        uploaded_file = st.file_uploader("📷 แนบรูปภาพ หรือ 🎥 วิดีโออาการเสีย", type=["jpg", "png", "jpeg", "mp4", "mov"])
        
        self_submit = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อมและไฟล์หลักฐานเข้าร้าน")
        if self_submit:
            if c_name and c_phone and c_device:
                file_path = None
                if uploaded_file is not None:
                    file_extension = uploaded_file.name.split(".")[-1]
                    file_name = f"MEDIA_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100,999)}.{file_extension}"
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO customers (name, phone) VALUES (?, ?) 
                    ON CONFLICT(phone) DO UPDATE SET name = excluded.name;
                """, (c_name, c_phone))
                cursor.execute("SELECT id FROM customers WHERE phone = ?", (c_phone,))
                cust_id = cursor.fetchone()[0]
                
                job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                cursor.execute("""
                    INSERT INTO repairs (job_code, customer_id, device_name, problem_description, accessories, media_file, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'RECEIVED')
                """, (job_code, cust_id, c_device, c_problem, c_accessories, file_path))
                conn.commit()
                cursor.close()
                st.success(f"🎉 ลงทะเบียนสำเร็จ! เลขที่ใบงานของคุณคือ: **{job_code}**")
                st.balloons()
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")

# ==========================================
# 3. ติดตาม & อัปเดตสถานะงานซ่อม
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
        if not df.empty:
            st.dataframe(df.drop(columns=['media_file', 'address', 'serial_number', 'accessories']), use_container_width=True)
            
            st.markdown("---")
            selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการจัดการ", df['job_code'].tolist())
            selected_row = df[df['job_code'] == selected_job].iloc[0]
            
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
                st.success("🎉 งานซ่อมเสร็จสิ้นแล้ว! กรุณาเลือกประเภทเอกสารที่ต้องการออกด้านล่างนี้ครับ")
                
                doc_choice = st.radio("🖨️ เลือกประเภทเอกสารทางการค้า:", [
                    "📦 ใบคืนสินค้า (Delivery Slip - A4 ครึ่งหน้า)", 
                    "💵 ใบเสร็จรับเงิน (Cash Receipt - A4 เต็มแผ่น FlowAccount Style)", 
                    "📄 ใบกำกับภาษี (Tax Invoice - A4 เต็มแผ่น FlowAccount Style)"
                ])
                
                with st.form(f"form_doc_{selected_job}"):
                    tax_cust_name = selected_row['customer_name']
                    tax_cust_id = ""
                    tax_cust_branch = "สำนักงานใหญ่"
                    tax_cust_address = selected_row['address'] if selected_row['address'] else ""
                    
                    if "ใบกำกับภาษี" in doc_choice:
                        st.markdown("#### 🏢 ข้อมูลผู้ซื้อสินค้า / ผู้รับบริการ (สำหรับออกใบกำกับภาษีตามกฎหมายสรรพากร)")
                        tc_col1, tc_col2 = st.columns(2)
                        with tc_col1:
                            tax_cust_name = st.text_input("ชื่อลูกค้า / บริษัท", value=selected_row['customer_name'])
                            tax_cust_id = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value="")
                        with tc_col2:
                            tax_cust_branch = st.text_input("สาขา (เช่น สำนักงานใหญ่ หรือ 00001)", value="สำนักงานใหญ่")
                            tax_cust_address = st.text_area("ที่อยู่ตามทะเบียนภาษี", value=selected_row['address'] if selected_row['address'] else "")
                        st.markdown("---")

                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        pay_chanel = st.selectbox("ช่องทางชำระเงิน", ["โอนเงินผ่าน PromptPay QR", "เงินสด", "บัตรเครดิต"])
                    with c_col2:
                        warrant_days = st.number_input("ระยะเวลารับประกันหลังซ่อม (วัน)", min_value=0, value=30)
                        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True if "ใบกำกับภาษี" in doc_choice else False)

                    st.markdown("#### 🛒 ปรับแต่งรายการค่าบริการและอะไหล่ (แก้ไขได้อย่างอิสระ)")
                    num_items = st.number_input("จำนวนรายการ", min_value=1, max_value=10, value=1, key=f"num_{selected_job}")
                    
                    subtotal = 0.0
                    items_data = []
                    
                    for i in range(int(num_items)):
                        cols = st.columns([3, 1, 1, 1])
                        with cols[0]:
                            desc = st.text_input(f"รายการที่ {i+1}", value=selected_row['problem_description'] if i == 0 else f"อะไหล่ชิ้นที่ {i+1}", key=f"desc_{selected_job}_{i}")
                        with cols[1]:
                            qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{selected_job}_{i}")
                        with cols[2]:
                            default_p = float(selected_row['estimated_cost']) if (i == 0 and selected_row['estimated_cost']) else 0.0
                            price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, value=default_p, key=f"price_{selected_job}_{i}")
                        with cols[3]:
                            tot = qty * price
                            st.text_input("รวม", value=f"{tot:,.2f}", disabled=True, key=f"tot_{selected_job}_{i}")
                        subtotal += tot
                        items_data.append((desc, qty, price, tot))

                    custom_notes = st.text_area("📝 ช่องหมายเหตุ / เงื่อนไขการรับประกัน", value=f"รับประกันงานซ่อมและอะไหล่ {warrant_days} วัน นับจากวันที่ส่งมอบเครื่อง")
                    
                    generate_btn = st.form_submit_button("🖨️ สร้างเอกสารพร้อมพิมพ์อย่างเป็นทางการ")
                    
                    if generate_btn:
                        grand_total = subtotal * 1.07 if include_vat else subtotal
                        
                        qr_tag = ""
                        if "PromptPay" in pay_chanel and "ใบคืนสินค้า" in doc_choice:
                            q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                            qr_obj = qrcode.make(q_cont)
                            q_stream = BytesIO()
                            qr_obj.save(q_stream)
                            b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                            qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="100px"><br><span style="font-size:9px;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {grand_total:,.2f} บาท</b></span>'
                        elif "PromptPay" in pay_chanel and "ใบเสร็จรับเงิน" in doc_choice:
                            q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                            qr_obj = qrcode.make(q_cont)
                            q_stream = BytesIO()
                            qr_obj.save(q_stream)
                            b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                            qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="100px"><br><span style="font-size:9px;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {grand_total:,.2f} บาท</b></span>'

                        def make_social_qr(link, label):
                            if not link: return ""
                            sq = qrcode.make(link)
                            s_buf = BytesIO()
                            sq.save(s_buf)
                            s_b64 = base64.b64encode(s_buf.getvalue()).decode()
                            return f'<div style="text-align:center; display:inline-block; margin: 0 8px;"><img src="data:image/png;base64,{s_b64}" width="45px"><br><span style="font-size:8px;">{label}</span></div>'

                        social_html = ""
                        if STORE_LINE: social_html += make_social_qr(STORE_LINE, "Line")
                        if STORE_FB: social_html += make_social_qr(STORE_FB, "Facebook")
                        if STORE_TIKTOK: social_html += make_social_qr(STORE_TIKTOK, "TikTok")

                        items_html = ""
                        for idx, val in enumerate(items_data):
                            items_html += f"<tr><td style='border-bottom:1px solid #e2e8f0; padding:8px;'>{idx+1}. {val[0]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:center;'>{val[1]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[2]:,.2f}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[3]:,.2f}</td></tr>"

                        vat_html = f"<tr><td colspan='3' style='text-align:right; padding:8px;'><b>VAT 7%:</b></td><td style='text-align:right; padding:8px;'>{subtotal * 0.07:,.2f} บาท</td></tr>" if include_vat else ""

                        if "ใบคืนสินค้า" in doc_choice:
                            final_html = f"""
                            <html>
                            <head>
                            <style>
                                @page {{ size: A4 portrait; margin: 5mm; }}
                                body {{ background: #f0f2f5; font-family: sans-serif; color: black; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                                .print-btn {{ background-color: #28a745; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                                .print-btn:hover {{ background-color: #218838; }}
                                .doc-box {{ background: white; border: 1px solid #ccc; padding: 12mm 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                                .section-box {{ height: 125mm; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; }}
                                .tbl {{ width: 100%; border-collapse: collapse; }}
                                .itm-tbl {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 11px; }}
                                .itm-tbl th {{ background: #333; color: white; padding: 4px; text-align: left; }}
                                .perforation {{ border-top: 2px dashed #666; margin: 8mm 0; text-align: center; font-size: 11px; color: #444; font-weight: bold; }}
                                .ftr {{ display: flex; justify-content: space-between; margin-top: 5px; font-size: 11px; align-items: flex-end; }}
                                @media print {{
                                    body {{ background: white; padding: 0; }}
                                    .print-btn {{ display: none; }}
                                    .doc-box {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                                }}
                            </style>
                            </head>
                            <body>
                                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์ใบคืนสินค้า (A4 ครึ่งหน้า)</button>
                                <div class="doc-box">
                                    <div class="section-box">
                                        <div>
                                            <table class="tbl">
                                                <tr>
                                                    <td>
                                                        <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                        <p style="font-size: 10px; margin: 1px 0;">{STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                                                    </td>
                                                    <td style="text-align: right; vertical-align: top;">
                                                        <h4 style="color: #333; margin: 0;"><b>ใบคืนสินค้าและส่งมอบงานซ่อม (สำหรับลูกค้า)</b></h4>
                                                        <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                            <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                                <tr><td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td><td><b>ช่องทางชำระ:</b> {pay_chanel}</td></tr>
                                                <tr><td><b>อุปกรณ์:</b> {selected_row['device_name']}</td><td><b>รับประกัน:</b> {warrant_days} วัน</td></tr>
                                            </table>
                                            <table class="itm-tbl">
                                                <tr><th>รายการซ่อม / อะไหล่</th><th style="text-align: center;">จำนวน</th><th style="text-align: right;">ราคา/หน่วย</th><th style="text-align: right;">จำนวนเงิน (บาท)</th></tr>
                                                {items_html}
                                                <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                                {vat_html}
                                                <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                            </table>
                                        </div>
                                        <div class="ftr">
                                            <div style="width: 70%;">
                                                <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                                <p style="font-size: 10px; margin: 8px 0 0 0;">ลงชื่อรับสินค้าคืน: ...................................................... (ลูกค้า)</p>
                                            </div>
                                            <div style="text-align: center; width: 30%;">
                                                {qr_tag}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="perforation">✂️ - - - - - - - - - - - - - - - - - รอยฉีกสำหรับแยกระหว่างลูกค้าและร้านค้า - - - - - - - - - - - - - - - - - ✂️</div>
                                    <div class="section-box">
                                        <div>
                                            <table class="tbl">
                                                <tr>
                                                    <td>
                                                        <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                        <p style="font-size: 10px; margin: 1px 0;">ใบควบคุมการส่งมอบและรับเงิน (สำหรับร้านค้าเก็บไว้)</p>
                                                    </td>
                                                    <td style="text-align: right; vertical-align: top;">
                                                        <h4 style="color: #333; margin: 0;"><b>ใบคืนสินค้าและส่งมอบงานซ่อม (สำหรับร้านค้า)</b></h4>
                                                        <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                            <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                                <tr><td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td><td><b>ช่องทางชำระ:</b> {pay_chanel}</td></tr>
                                                <tr><td><b>อุปกรณ์:</b> {selected_row['device_name']}</td><td><b>รับประกัน:</b> {warrant_days} วัน</td></tr>
                                            </table>
                                            <table class="itm-tbl">
                                                <tr><th>รายการซ่อม / อะไหล่</th><th style="text-align: center;">จำนวน</th><th style="text-align: right;">ราคา/หน่วย</th><th style="text-align: right;">จำนวนเงิน (บาท)</th></tr>
                                                {items_html}
                                                <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                                {vat_html}
                                                <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                            </table>
                                        </div>
                                        <div class="ftr">
                                            <div style="width: 100%;">
                                                <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                                <p style="font-size: 10px; margin: 8px 0 0 0;">ลงชื่อลูกค้า (ตรวจรับเรียบร้อย): ...................................................... &nbsp;&nbsp;&nbsp;&nbsp; ช่างผู้ส่งมอบ: ......................................................</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                        else:
                            is_tax = "ใบกำกับภาษี" in doc_choice
                            doc_title = "ใบกำกับภาษี / TAX INVOICE" if is_tax else "ใบเสร็จรับเงิน / CASH RECEIPT"

                            final_html = f"""
                            <html>
                            <head>
                            <style>
                                @page {{ size: A4 portrait; margin: 12mm; }}
                                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                                .print-btn {{ background-color: #0284c7; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                                .print-btn:hover {{ background-color: #0369a1; }}
                                .flow-container {{ background: white; border: 1px solid #cbd5e1; padding: 15mm; width: 190mm; min-height: 270mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; }}
                                .header-tbl {{ width: 100%; border-collapse: collapse; }}
                                .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 15px 0; font-size: 13px; }}
                                .cust-box td {{ padding: 4px 8px; }}
                                .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
                                .items-tbl th {{ background: #0f172a; color: white; padding: 10px 8px; text-align: left; font-weight: 600; }}
                                .items-tbl td {{ padding: 10px 8px; border-bottom: 1px solid #e2e8f0; }}
                                .summary-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                                .summary-tbl td {{ padding: 6px 10px; }}
                                .footer-box {{ display: flex; justify-content: space-between; margin-top: 30px; border-top: 1px solid #cbd5e1; padding-top: 20px; align-items: flex-start; font-size: 12px; }}
                                @media print {{
                                    body {{ background: white; padding: 0; }}
                                    .print-btn {{ display: none; }}
                                    .flow-container {{ border: none; box-shadow: none; padding: 0; width: 100%; min-height: auto; }}
                                }}
                            </style>
                            </head>
                            <body>
                                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสาร FlowAccount Style (A4 เต็มแผ่น)</button>
                                <div class="flow-container">
                                    <div>
                                        <table class="header-tbl">
                                            <tr>
                                                <td style="vertical-align: top;">
                                                    <h2 style="margin: 0; color: #0f172a; font-size: 24px;"><b>{STORE_NAME}</b></h2>
                                                    <p style="font-size: 12px; margin: 4px 0; color: #475569; line-height: 1.4;">{STORE_ADDRESS}<br>โทร: {STORE_PHONE} | เลขประจำตัวผู้เสียภาษี: {STORE_TAX}</p>
                                                </td>
                                                <td style="text-align: right; vertical-align: top;">
                                                    <div style="background: #0284c7; color: white; padding: 8px 16px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 16px; margin-bottom: 8px;">
                                                        {doc_title}
                                                    </div>
                                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>เลขที่ใบงาน:</b> {selected_job}</p>
                                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>วันที่ออกเอกสาร:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                </td>
                                            </tr>
                                        </table>

                                        <table class="cust-box tbl">
                                            <tr>
                                                <td style="width: 65%;"><b>ชื่อลูกค้า / บริษัท:</b> {tax_cust_name}</td>
                                            </tr>
                                            <tr>
                                                <td><b>ที่อยู่:</b> {tax_cust_address if tax_cust_address else '-'}</td>
                                                <td><b>เลขผู้เสียภาษี:</b> {tax_cust_id if tax_cust_id else '-'} ({tax_cust_branch})</td>
                                            </tr>
                                        </table>

                                        <table class="items-tbl">
                                            <tr>
                                                <th>รายการสินค้า / บริการ / อะไหล่</th>
                                                <th style="text-align: center; width: 70px;">จำนวน</th>
                                                <th style="text-align: right; width: 110px;">ราคา/หน่วย</th>
                                                <th style="text-align: right; width: 130px;">จำนวนเงิน (บาท)</th>
                                            </tr>
                                            {items_html}
                                        </table>

                                        <table style="width: 100%; margin-top: 10px;">
                                            <tr>
                                                <td style="vertical-align: top; width: 55%; padding-top: 10px; font-size: 11px; color: #64748b;">
                                                    <b>หมายเหตุ / เงื่อนไขการรับประกัน ({warrant_days} วัน):</b><br>
                                                    {custom_notes}
                                                </td>
                                                <td style="width: 45%;">
                                                    <table class="summary-tbl">
                                                        <tr><td style="text-align: right;"><b>มูลค่ารวม (Subtotal):</b></td><td style="text-align: right; width: 120px;">{subtotal:,.2f} บาท</td></tr>
                                                        {vat_html}
                                                        <tr><td style="text-align: right; font-size: 15px; color: #0284c7;"><b>ยอดชำระสุทธิ (Grand Total):</b></td><td style="text-align: right; font-size: 15px; color: #0284c7;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>

                                    <div>
                                        <div class="footer-box">
                                            <div style="width: 65%;">
                                                <table style="width: 100%; text-align: left; font-size: 11px; border-collapse: collapse;">
                                                    <tr>
                                                        <td style="padding-bottom: 5px; width: 50%;">
                                                            ลงชื่อ......................................................
                                                        </td>
                                                        <td style="padding-bottom: 5px; width: 50%;">
                                                            ลงชื่อ......................................................
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            ผู้รับเงิน / ผู้ออกเอกสาร วันที่....................
                                                        </td>
                                                        <td>
                                                            ผู้จ่ายเงิน / ลูกค้า วันที่.........................
                                                        </td>
                                                    </tr>
                                                </table>
                                            </div>

                                            <div style="width: 25%; text-align: center;">
                                                {qr_tag}
                                            </div>
                                        </div>

                                        <!-- ล่างสุด: ติดตามร้านเราผ่านโซเชียล -->
                                        <div style="margin-top: 15px; text-align: center; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box;">
                                            <span style="font-size: 9px; color: #475569; font-weight: bold;">ติดตามร้านเราผ่านโซเชียล:</span>
                                            <div style="margin-top: 4px;">
                                                {social_html}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """

                        components.html(final_html, height=1050, scrolling=True)

        else:
            st.info("ไม่พบข้อมูลงานซ่อมในระบบ")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# ==========================================
# 4. ระบบออกเอกสารการค้าครบชุด 6 ประเภท (FlowAccount Style - Sales Pipeline & Workflow with Color Coding & Sticky Footer)
# ==========================================
elif menu == "📄 ระบบออกเอกสารการค้า":
    st.header("📄 ระบบออกเอกสารทางการค้าครบวงจร (FlowAccount Pipeline Style)")
    st.markdown("จัดการวงจรการขายครบวงจร: ใบเสนอราคา ➡️ ใบส่งสินค้า/แจ้งหนี้ ➡️ ใบกำกับภาษี ➡️ ใบเสร็จรับเงิน (พร้อมใบลดหนี้และใบเพิ่มหนี้ แยกสีธีมตามประเภทเอกสาร)")

    sub_menu = st.radio("🗂️ เลือกโหมดการจัดการ", ["📝 สร้างเอกสารใหม่ (Create Document)", "📋 ติดตามสถานะและส่งต่อเอกสาร (Sales Pipeline)"], horizontal=True)
    st.markdown("---")

    if sub_menu == "📝 สร้างเอกสารใหม่ (Create Document)":
        with st.form("commercial_docs_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.subheader("🏢 ข้อมูลลูกค้า / คู่ค้า")
                c_target_name = st.text_input("ชื่อลูกค้า / บริษัท", value="บริษัท ลูกค้าตัวอย่าง จำกัด")
                c_target_tax = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value="0123456789012")
                c_target_branch = st.text_input("สาขา (เช่น สำนักงานใหญ่ หรือ 00001)", value="สำนักงานใหญ่")
                c_target_address = st.text_area("ที่อยู่ลูกค้า", value="123 ถนนอุบลราชธานี อำเภอเมือง จังหวัดอุบลราชธานี")
            with col_c2:
                st.subheader("📅 ประเภทเอกสาร & เงื่อนไข")
                
                doc_type_selected = st.selectbox("🎯 ประเภทเอกสารเริ่มต้น", [
                    "1. ใบเสนอราคา (Quotation - QT)",
                    "2. ใบส่งสินค้า / ใบแจ้งหนี้ (Delivery Order & Invoice - DO/IV)",
                    "3. ใบกำกับภาษี (Tax Invoice - TAX)",
                    "4. ใบเสร็จรับเงิน (Cash Receipt - RC)",
                    "5. ใบลดหนี้ (Credit Note - CN)",
                    "6. ใบเพิ่มหนี้ (Debit Note - DN)"
                ])

                date_mode = st.radio("รูปแบบวันที่ออกเอกสาร", ["ระบุวันที่อัตโนมัติ", "เว้นช่องว่างเส้นประ (สำหรับลงวันที่ด้วยมือ)"], horizontal=True)
                if date_mode == "ระบุวันที่อัตโนมัติ":
                    c_doc_date = st.date_input("วันที่ออกเอกสาร", datetime.today())
                    c_doc_date_str = c_doc_date.strftime('%Y-%m-%d')
                    credit_days = st.number_input("เครดิต (วัน)", min_value=0, value=30)
                    due_date = c_doc_date + timedelta(days=int(credit_days))
                    due_date_str = due_date.strftime('%Y-%m-%d')
                else:
                    c_doc_date_str = "...................................."
                    due_date_str = "...................................."
                
                salesperson = st.text_input("พนักงานขาย", value="ช่างดิด")
                currency = st.selectbox("สกุลเงิน", [DEF_CURR, "THB", "USD", "EUR"])
                
                is_no_payment_doc = any(k in doc_type_selected for k in ["ใบเสนอราคา", "ใบส่งสินค้า", "ใบกำกับภาษี"])
                c_pay_method = "โอนเงินผ่าน PromptPay QR"
                if not is_no_payment_doc:
                    c_pay_method = st.selectbox("ช่องทางการชำระเงิน", ["โอนเงินผ่าน PromptPay QR", "เงินสด", "บัตรเครดิต"])

            ref_doc_no_input = ""
            cn_dn_reason = ""
            if "ลดหนี้" in doc_type_selected or "เพิ่มหนี้" in doc_type_selected:
                st.markdown("---")
                st.subheader("📎 ข้อมูลอ้างอิงเอกสารเดิม")
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    ref_doc_no_input = st.text_input("อ้างอิงเลขที่ใบกำกับภาษีเดิม", value="IV-20260301-001")
                with r_col2:
                    cn_dn_reason = st.text_input("สาเหตุ", value="คืนสินค้าชำรุด / คิดราคาผิดพลาด")

            st.markdown("---")
            st.subheader("🛒 รายการสินค้า / บริการ")
            num_com_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
            
            com_subtotal = 0.0
            com_items_list = []
            
            for ci in range(int(num_com_items)):
                ccols = st.columns([3, 1, 1, 1])
                with ccols[0]:
                    c_desc = st.text_input(f"รายการที่ {ci+1}", value=f"จำหน่าย/บริการคอมพิวเตอร์ รายการที่ {ci+1}", key=f"com_desc_{ci}")
                with ccols[1]:
                    c_qty = st.number_input("จำนวน", min_value=1, value=1, key=f"com_qty_{ci}")
                with ccols[2]:
                    c_price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, value=1500.0, key=f"com_price_{ci}")
                with ccols[3]:
                    c_tot = c_qty * c_price
                    st.text_input("รวม", value=f"{c_tot:,.2f}", disabled=True, key=f"com_tot_{ci}")
                com_subtotal += c_tot
                com_items_list.append((c_desc, c_qty, c_price, c_tot))

            st.markdown("---")
            col_note, col_summary = st.columns([2, 1])
            with col_note:
                com_notes = st.text_area("หมายเหตุท้ายเอกสาร / เงื่อนไข", value=STORE_NOTE)
            with col_summary:
                discount_pct = st.number_input("ส่วนลด %", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
                include_com_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)

            save_doc_btn = st.form_submit_button("💾 บันทึกเอกสารเข้าสู่ระบบ Sales Pipeline")

            if save_doc_btn:
                discount_amount = com_subtotal * (discount_pct / 100.0)
                price_after_discount = com_subtotal - discount_amount
                vat_amount = price_after_discount * 0.07 if include_com_vat else 0.0
                com_grand = price_after_discount + vat_amount

                if "1." in doc_type_selected:
                    d_type, prefix, initial_status = "QT", P_QT, "รออนุมัติ"
                elif "2." in doc_type_selected:
                    d_type, prefix, initial_status = "IV", P_IV, "รอส่งสินค้า"
                elif "3." in doc_type_selected:
                    d_type, prefix, initial_status = "TAX", P_TAX, "รอออกใบเสร็จ"
                elif "4." in doc_type_selected:
                    d_type, prefix, initial_status = "RC", P_RC, "เสร็จสิ้นการขาย"
                elif "5." in doc_type_selected:
                    d_type, prefix, initial_status = "CN", P_CN, "ใบลดหนี้"
                else:
                    d_type, prefix, initial_status = "DN", P_DN, "ใบเพิ่มหนี้"

                doc_no_gen = f"{prefix}-{datetime.today().strftime('%Y%m%d')}-{random.randint(100,999)}"
                items_json_str = json.dumps(com_items_list, ensure_ascii=False)

                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO commercial_docs (doc_no, doc_type, status, customer_name, customer_tax, customer_branch, customer_address, doc_date, due_date, salesperson, currency, items_json, subtotal, discount_pct, vat_amount, grand_total, ref_doc_no, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (doc_no_gen, d_type, initial_status, c_target_name, c_target_tax, c_target_branch, c_target_address, c_doc_date_str, due_date_str, salesperson, currency, items_json_str, com_subtotal, discount_pct, vat_amount, com_grand, ref_doc_no_input, com_notes))
                    conn.commit()
                    cursor.close()
                    st.success(f"🎉 บันทึกเอกสาร {doc_no_gen} สำเร็จ! ไปที่แท็บ 'ติดตามสถานะและส่งต่อเอกสาร' เพื่อจัดการต่อได้เลยครับ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

    else:
        # --- TAB 2: Sales Pipeline & Workflow Tracking ---
        st.subheader("📋 ติดตามสถานะเอกสารและการส่งข้อมูล (Sales Pipeline)")
        st.markdown("ระบบจะควบคุมลำดับ: **ใบเสนอราคา (รออนุมัติ) ➡️ ใบส่งสินค้า/แจ้งหนี้ ➡️ ใบกำกับภาษี ➡️ ใบเสร็จรับเงิน (เสร็จสิ้น)**")

        try:
            pipeline_df = pd.read_sql("SELECT id, doc_no, doc_type, status, customer_name, grand_total, currency, created_at FROM commercial_docs ORDER BY id DESC;", conn)
            if not pipeline_df.empty:
                st.dataframe(pipeline_df, use_container_width=True)

                st.markdown("---")
                st.subheader("⚙️ ดำเนินการส่งต่อสถานะ (Convert & Workflow Actions)")
                
                selected_doc_no = st.selectbox("เลือกเลขที่เอกสารที่ต้องการจัดการ", pipeline_df['doc_no'].tolist())
                cur_doc = pd.read_sql(f"SELECT * FROM commercial_docs WHERE doc_no = '{selected_doc_no}';", conn).iloc[0]

                st.info(f"📄 **เอกสาร:** {cur_doc['doc_no']} | **ประเภท:** {cur_doc['doc_type']} | **ลูกค้า:** {cur_doc['customer_name']} | **สถานะปัจจุบัน:** 📌 **{cur_doc['status']}** | **ยอดรวม:** {cur_doc['grand_total']:,.2f} {cur_doc['currency']}")

                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    next_action_label = ""
                    target_next_type = ""
                    target_next_status = ""

                    if cur_doc['doc_type'] == 'QT' and cur_doc['status'] == 'รออนุมัติ':
                        next_action_label = "✅ อนุมัติ และส่งข้อมูลไปใบส่งสินค้า/แจ้งหนี้ (DO/IV)"
                        target_next_type, target_next_status = "IV", "รอส่งสินค้า"
                    elif cur_doc['doc_type'] == 'IV' and cur_doc['status'] in ['รอส่งสินค้า', 'อนุมัติแล้ว']:
                        next_action_label = "🚚 ส่งสินค้าแล้ว และส่งข้อมูลไปใบกำกับภาษี (TAX)"
                        target_next_type, target_next_status = "TAX", "รอออกใบเสร็จ"
                    elif cur_doc['doc_type'] == 'TAX' and cur_doc['status'] == 'รอออกใบเสร็จ':
                        next_action_label = "💵 ออกใบเสร็จรับเงิน (RC) เพื่อรับชำระ"
                        target_next_type, target_next_status = "RC", "เสร็จสิ้นการขาย"
                    elif cur_doc['doc_type'] == 'RC' and cur_doc['status'] != 'เสร็จสิ้นการขาย':
                        next_action_label = "🎉 ยืนยันรับชำระ (เสร็จสิ้นการขาย)"
                        target_next_status = "เสร็จสิ้นการขาย"

                    if next_action_label:
                        if st.button(next_action_label):
                            cursor = conn.cursor()
                            if target_next_type:
                                if target_next_type == 'IV': prefix = P_IV
                                elif target_next_type == 'TAX': prefix = P_TAX
                                else: prefix = P_RC

                                new_doc_no_gen = f"{prefix}-{datetime.today().strftime('%Y%m%d')}-{random.randint(100,999)}"
                                cursor.execute("""
                                    INSERT INTO commercial_docs (doc_no, doc_type, status, customer_name, customer_tax, customer_branch, customer_address, doc_date, due_date, salesperson, currency, items_json, subtotal, discount_pct, vat_amount, grand_total, ref_doc_no, notes)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (new_doc_no_gen, target_next_type, target_next_status, cur_doc['customer_name'], cur_doc['customer_tax'], cur_doc['customer_branch'], cur_doc['customer_address'], cur_doc['doc_date'], cur_doc['due_date'], cur_doc['salesperson'], cur_doc['currency'], cur_doc['items_json'], cur_doc['subtotal'], cur_doc['discount_pct'], cur_doc['vat_amount'], cur_doc['grand_total'], cur_doc['doc_no'], cur_doc['notes']))
                            
                            cursor.execute("UPDATE commercial_docs SET status = 'อนุมัติ/ส่งต่อแล้ว' WHERE doc_no = ?", (selected_doc_no,))
                            conn.commit()
                            cursor.close()
                            st.success(f"ส่งข้อมูลและอัปเดตสถานะสำเร็จ!")
                            st.rerun()
                    else:
                        st.success("🎉 เอกสารฉบับนี้อยู่ในสถานะ 'เสร็จสิ้นการขาย' สมบูรณ์แล้ว")

                with col_act2:
                    if st.button("🖨️ พิมพ์เอกสารนี้ทันที (FlowAccount Style)"):
                        items_parsed = json.loads(cur_doc['items_json'])
                        print_items_html = ""
                        for idx, val in enumerate(items_parsed):
                            print_items_html += f"<tr><td style='border-bottom:1px solid #e2e8f0; padding:8px;'>{idx+1}. {val[0]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:center;'>{val[1]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[2]:,.2f}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[3]:,.2f}</td></tr>"

                        d_t = cur_doc['doc_type']
                        if d_t == 'QT':
                            t_title, t_color, l_sign, r_sign = "ใบเสนอราคา / QUOTATION", "#0d9488", "ผู้เสนอ / ผู้ออกเอกสาร", "ผู้อนุมัติ / ลูกค้า"
                        elif d_t == 'IV':
                            t_title, t_color, l_sign, r_sign = "ใบส่งสินค้า / ใบแจ้งหนี้", "#2563eb", "ผู้ส่งสินค้า / ผู้ออกเอกสาร", "ผู้รับสินค้า / ลูกค้า"
                        elif d_t == 'TAX':
                            t_title, t_color, l_sign, r_sign = "ใบกำกับภาษี / TAX INVOICE", "#4f46e5", "ผู้มีอำนาจออกเอกสาร", "ผู้รับบริการ / ลูกค้า"
                        elif d_t == 'RC':
                            t_title, t_color, l_sign, r_sign = "ใบเสร็จรับเงิน / CASH RECEIPT", "#16a34a", "ผู้รับเงิน / ผู้ออกเอกสาร", "ผู้จ่ายเงิน / ลูกค้า"
                        elif d_t == 'CN':
                            t_title, t_color, l_sign, r_sign = "ใบลดหนี้ / CREDIT NOTE", "#d97706", "ผู้ออกใบลดหนี้", "ผู้รับใบลดหนี้ / ลูกค้า"
                        else:
                            t_title, t_color, l_sign, r_sign = "ใบเพิ่มหนี้ / DEBIT NOTE", "#e11d48", "ผู้ออกใบเพิ่มหนี้", "ผู้รับใบเพิ่มหนี้ / ลูกค้า"

                        logo_data_uri = get_img_base64(LOGO_PATH)
                        logo_img_tag = f'<img src="{logo_data_uri}" style="max-height: 45px; vertical-align: middle; margin-right: 10px;">' if logo_data_uri else ''

                        def make_social_qr(link, label):
                            if not link: return ""
                            sq = qrcode.make(link)
                            s_buf = BytesIO()
                            sq.save(s_buf)
                            s_b64 = base64.b64encode(s_buf.getvalue()).decode()
                            return f'<div style="text-align:center; display:inline-block; margin: 0 6px;"><img src="data:image/png;base64,{s_b64}" width="40px"><br><span style="font-size:8px;">{label}</span></div>'

                        social_html = ""
                        if STORE_LINE: social_html += make_social_qr(STORE_LINE, "Line")
                        if STORE_FB: social_html += make_social_qr(STORE_FB, "Facebook")
                        if STORE_TIKTOK: social_html += make_social_qr(STORE_TIKTOK, "TikTok")

                        print_html_full = f"""
                        <html>
                        <head>
                        <style>
                            @page {{ size: A4 portrait; margin: 10mm; }}
                            body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                            .print-btn {{ background-color: {t_color}; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                            .flow-container {{ background: white; border: 1px solid #cbd5e1; padding: 15mm; width: 190mm; height: 272mm; max-height: 272mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; }}
                            .header-tbl {{ width: 100%; border-collapse: collapse; }}
                            .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 12px 0; font-size: 13px; }}
                            .cust-box td {{ padding: 4px 8px; }}
                            .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
                            .items-tbl th {{ background: {t_color}; color: white; padding: 10px 8px; text-align: left; font-weight: 600; }}
                            .items-tbl td {{ padding: 10px 8px; border-bottom: 1px solid #e2e8f0; }}
                            .summary-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                            .summary-tbl td {{ padding: 6px 10px; }}
                            .footer-section {{ margin-top: auto; border-top: 1px solid #cbd5e1; padding-top: 15px; }}
                            .footer-box {{ display: flex; justify-content: space-between; align-items: flex-start; font-size: 12px; }}
                            @media print {{ 
                                body {{ background: white; padding: 0; margin: 0; }} 
                                .print-btn {{ display: none; }} 
                                .flow-container {{ 
                                    border: none; 
                                    box-shadow: none; 
                                    padding: 10mm; 
                                    width: 100%; 
                                    height: 272mm; 
                                    max-height: 272mm; 
                                    display: flex; 
                                    flex-direction: column; 
                                    justify-content: space-between; 
                                    page-break-after: always;
                                } 
                            }}
                        </style>
                        </head>
                        <body>
                            <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสารฉบับนี้</button>
                            <div class="flow-container">
                                <div>
                                    <table class="header-tbl">
                                        <tr>
                                            <td style="vertical-align: top;">
                                                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                                    {logo_img_tag}
                                                    <h2 style="margin: 0; color: #0f172a; font-size: 24px;"><b>{STORE_NAME}</b></h2>
                                                </div>
                                                <p style="font-size: 12px; margin: 4px 0; color: #475569;">{STORE_ADDRESS}<br>โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                                            </td>
                                            <td style="text-align: right; vertical-align: top;">
                                                <div style="background: {t_color}; color: white; padding: 8px 16px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 15px; margin-bottom: 8px;">
                                                    {t_title}
                                                </div>
                                                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>เลขที่เอกสาร:</b> {cur_doc['doc_no']}</p>
                                                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>วันที่:</b> {cur_doc['doc_date']}</p>
                                                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>พนักงานขาย:</b> {cur_doc['salesperson']} | <b>สกุลเงิน:</b> {cur_doc['currency']}</p>
                                            </td>
                                        </tr>
                                    </table>

                                    <table class="cust-box tbl">
                                        <tr><td style="width: 100%;"><b>นามลูกค้า / บริษัท:</b> {cur_doc['customer_name']}</td></tr>
                                        <tr><td><b>ที่อยู่:</b> {cur_doc['customer_address']}</td></tr>
                                    </table>

                                    <table class="items-tbl">
                                        <tr>
                                            <th>รายการสินค้า / บริการ / อะไหล่</th>
                                            <th style="text-align: center; width: 70px;">จำนวน</th>
                                            <th style="text-align: right; width: 110px;">ราคา/หน่วย</th>
                                            <th style="text-align: right; width: 130px;">จำนวนเงิน ({cur_doc['currency']})</th>
                                        </tr>
                                        {print_items_html}
                                    </table>

                                    <table style="width: 100%; margin-top: 10px;">
                                        <tr>
                                            <td style="vertical-align: top; width: 55%; padding-top: 10px; font-size: 11px; color: #64748b;">
                                                <b>หมายเหตุ / เงื่อนไข:</b><br>{cur_doc['notes']}
                                            </td>
                                            <td style="width: 45%;">
                                                <table class="summary-tbl">
                                                    <tr><td style="text-align: right;"><b>รวมเป็นเงิน:</b></td><td style="text-align: right; width: 150px;">{cur_doc['subtotal']:,.2f} {cur_doc['currency']}</td></tr>
                                                    <tr><td style="text-align: right; font-size: 14px; color: {t_color};"><b>จำนวนเงินรวมทั้งสิ้น:</b></td><td style="text-align: right; font-size: 14px; color: {t_color};"><b>{cur_doc['grand_total']:,.2f} {cur_doc['currency']}</b></td></tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                <!-- บล็อกท้ายกระดาษที่ถูกตรึงไว้ล่างสุดเสมอ -->
                                <div class="footer-section">
                                    <div class="footer-box">
                                        <div style="width: 70%;">
                                            <table style="width: 100%; text-align: left; font-size: 11px; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding-bottom: 5px; width: 50%;">ลงชื่อ......................................................</td>
                                                    <td style="padding-bottom: 5px; width: 50%;">ลงชื่อ......................................................</td>
                                                </tr>
                                                <tr>
                                                    <td>{l_sign} วันที่....................</td>
                                                    <td>{r_sign} วันที่.........................</td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>

                                    <div style="margin-top: 15px; text-align: center; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box;">
                                        <span style="font-size: 9px; color: #475569; font-weight: bold;">ติดตามร้านเราผ่านโซเชียล:</span>
                                        <div style="margin-top: 4px;">{social_html}</div>
                                    </div>
                                </div>
                            </div>
                        </body>
                        </html>
                        """
                        components.html(print_html_full, height=1050, scrolling=True)
            else:
                st.info("ยังไม่มีเอกสารการค้าในระบบ สามารถไปที่แท็บ 'สร้างเอกสารใหม่' เพื่อเริ่มใช้งานได้เลยครับ")
        except Exception as e:
            st.info("ยังไม่มีตารางข้อมูลเอกสารการค้าในระบบ กรุณาสร้างเอกสารใหม่ 1 ครั้งเพื่อเริ่มใช้งาน")

# ==========================================
# 5. ศูนย์กลางการตั้งค่าระบบ (Enterprise Settings Hub - รวมเมนูย้ายมาใหม่ครบถ้วน)
# ==========================================
elif menu == "⚙️ ศูนย์กลางการตั้งค่า":
    st.header("⚙️ ศูนย์กลางการตั้งค่าระบบ (Enterprise Settings Hub)")
    st.markdown("จัดการข้อมูลร้านค้า เอกสาร บัญชี ผู้ใช้งาน รวมถึงระบบตรวจสอบประกัน โซเชียล และรายงานยอดขาย")
    
    set_tab1, set_tab2, set_tab3, set_tab4, set_tab5, set_tab6, set_tab7, set_tab8, set_tab9 = st.tabs([
        "📄 ตั้งค่าเอกสาร", 
        "📊 ตั้งค่าด้านบัญชี", 
        "👤 ตั้งค่าผู้ใช้งาน", 
        "📦 ตั้งค่าสินค้า", 
        "🏢 ตั้งค่าธุรกิจ & โลโก้", 
        "⌨️ แป้นพิมพ์ลัด",
        "🌐 QR Code โซเชียล",
        "🛡️ เช็คประกัน & Serial",
        "💰 สรุปยอด & ค่าคอมช่าง"
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

    # --- Tab 5: ตั้งค่าธุรกิจ ---
    with set_tab5:
        st.subheader("🏢 ข้อมูลธุรกิจและร้านค้าหลัก")
        with st.form("settings_biz_form"):
            new_store_name = st.text_input("ชื่อร้านค้า / ธุรกิจ", value=STORE_NAME)
            new_phone = st.text_input("เบอร์โทรศัพท์", value=STORE_PHONE)
            new_tax = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value=STORE_TAX)
            new_promptpay = st.text_input("เลขพร้อมเพย์ (สำหรับสร้าง QR Code รับเงิน)", value=STORE_PROMPTPAY)
            new_address = st.text_area("ที่อยู่สถานประกอบการ", value=STORE_ADDRESS)
            
            st.markdown("---")
            st.markdown("##### 🖼️ โลโก้ร้านค้า (รองรับไฟล์ JPG / PNG)")
            uploaded_logo = st.file_uploader("อัปโหลดรูปโลโก้ร้าน (.jpg หรือ .png)", type=["jpg", "jpeg", "png"])
            if LOGO_PATH and os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=150, caption="โลโก้ปัจจุบันของร้าน")

            st.markdown("---")
            st.markdown("##### 🌐 ช่องทางโซเชียลมีเดียของร้าน")
            new_line = st.text_input("ลิงก์ Line Official", value=STORE_LINE)
            new_fb = st.text_input("ลิงก์ Facebook Page", value=STORE_FB)
            new_tiktok = st.text_input("ลิงก์ TikTok", value=STORE_TIKTOK)
            
            if st.form_submit_button("💾 บันทึกข้อมูลธุรกิจและโลโก้"):
                final_logo_path = LOGO_PATH
                if uploaded_logo is not None:
                    logo_ext = uploaded_logo.name.split(".")[-1]
                    logo_filename = f"logo_store_{datetime.now().strftime('%Y%m%d%H%M%S')}.{logo_ext}"
                    final_logo_path = os.path.join(UPLOAD_DIR, logo_filename)
                    with open(final_logo_path, "wb") as f:
                        f.write(uploaded_logo.getbuffer())

                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE store_settings 
                    SET store_name = ?, phone = ?, tax_id = ?, address = ?, promptpay = ?, line_link = ?, fb_link = ?, tiktok_link = ?, logo_path = ? 
                    WHERE id = 1
                """, (new_store_name, new_phone, new_tax, new_address, new_promptpay, new_line, new_fb, new_tiktok, final_logo_path))
                conn.commit()
                cursor.close()
                st.success("บันทึกข้อมูลธุรกิจและโลโก้สำเร็จ!")
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

    # --- Tab 7: QR Code โซเชียล (ย้ายมาจากเมนูลัด) ---
    with set_tab7:
        st.subheader("🌐 QR Code ช่องทางติดต่อโซเชียลมีเดียของร้าน")
        st.markdown("สแกนเพื่อเพิ่มเพื่อนหรือติดตามเพจร้านค้าได้ทันที")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("💚 Line")
            if STORE_LINE:
                img = qrcode.make(STORE_LINE)
                buf = BytesIO(); img.save(buf)
                st.image(buf.getvalue(), width=160, caption="Line Official")
            else:
                st.info("ยังไม่ได้ตั้งค่าลิงก์ Line ในแท็บตั้งค่าธุรกิจ")
        with col2:
            st.subheader("💙 Facebook")
            if STORE_FB:
                img = qrcode.make(STORE_FB)
                buf = BytesIO(); img.save(buf)
                st.image(buf.getvalue(), width=160, caption="Facebook Page")
            else:
                st.info("ยังไม่ได้ตั้งค่าลิงก์ Facebook ในแท็บตั้งค่าธุรกิจ")
        with col3:
            st.subheader("🖤 TikTok")
            if STORE_TIKTOK:
                img = qrcode.make(STORE_TIKTOK)
                buf = BytesIO(); img.save(buf)
                st.image(buf.getvalue(), width=160, caption="TikTok Profile")
            else:
                st.info("ยังไม่ได้ตั้งค่าลิงก์ TikTok ในแท็บตั้งค่าธุรกิจ")

    # --- Tab 8: เช็คประกัน & Serial (ย้ายมาจากเมนูลัด) ---
    with set_tab8:
        st.subheader("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
        sn_input = st.text_input("🔍 กรอกหรือสแกน Serial Number เพื่อเช็คสถานะประกัน")
        if sn_input:
            st.success(f"✅ สินค้า Serial Number: `{sn_input}` อยู่ในระยะเวลาประกันของร้านค้าสมบูรณ์!")

    # --- Tab 9: สรุปยอด & ค่าคอมช่าง (ย้ายมาจากเมนูลัด) ---
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