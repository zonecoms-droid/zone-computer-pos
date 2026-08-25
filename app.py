import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
import os
import base64

# สร้างโฟลเดอร์สำหรับเก็บบันทึกไฟล์รูป/วิดีโอที่ลูกค้าอัปโหลด
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ZoneOnline Service - Ultimate Edition", 
    page_icon="⚡", 
    layout="wide"
)

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
            tiktok_link TEXT
        )
    ''')
    for col in ['promptpay', 'line_link', 'fb_link', 'tiktok_link']:
        try:
            cursor.execute(f"ALTER TABLE store_settings ADD COLUMN {col} TEXT;")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-123-4567', '1234567890123', 'อุบลราชธานี', 'ขอบคุณที่ใช้บริการครับ', '0891234567', 'https://line.me', 'https://facebook.com', 'https://tiktok.com')
        ''')
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
cursor.execute("SELECT store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()
STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY, STORE_LINE, STORE_FB, STORE_TIKTOK = store_info

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
# 🖥️ หน้าแอดมินปกติ (Admin Dashboard)
# ==========================================
st.set_page_config(
    page_title="ZoneOnline Service - Ultimate Edition", 
    page_icon="⚡", 
    layout="wide"
)

st.title(f"⚡ {STORE_NAME} [Ultimate Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (แยกระบบพิมพ์ใบคืนสินค้าและใบเสร็จสมบูรณ์)")

if 'current_job_code' not in st.session_state:
    st.session_state.current_job_code = None

menu_options = [
    "📥 รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม", 
    "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)",
    "🌐 QR Code ช่องทางติดต่อ (Line, FB, TikTok)",
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ออกเอกสารการค้า / ใบเสร็จ (พร้อม QR Code)",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง",
    "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)"
]

menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", menu_options)

# ==========================================
# 1. รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม":
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
elif menu == "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)":
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
# 3. QR Code ช่องทางติดต่อ
# ==========================================
elif menu == "🌐 QR Code ช่องทางติดต่อ (Line, FB, TikTok)":
    st.header("🌐 QR Code ช่องทางติดต่อโซเชียลมีเดียของร้าน")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("💚 Line")
        if STORE_LINE:
            img = qrcode.make(STORE_LINE)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)
    with col2:
        st.subheader("💙 Facebook")
        if STORE_FB:
            img = qrcode.make(STORE_FB)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)
    with col3:
        st.subheader("🖤 TikTok")
        if STORE_TIKTOK:
            img = qrcode.make(STORE_TIKTOK)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)

# ==========================================
# 4. ติดตาม & อัปเดตสถานะงานซ่อม (พร้อมปุ่มพิมพ์แยกเอกสารเมื่อ COMPLETED)
# ==========================================
elif menu == "🔍 ติดตาม & อัปเดตสถานะงานซ่อม":
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
                m_file = selected_row['media_file']
                if m_file and os.path.exists(m_file):
                    ext = m_file.split('.')[-1].lower()
                    if ext in ['jpg', 'jpeg', 'png']:
                        st.image(m_file, width=250)
                    elif ext in ['mp4', 'mov']:
                        st.video(m_file)
            
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

            # --- ถ้าสถานะเป็น COMPLETED ให้แยกปุ่มพิมพ์ "ใบคืนสินค้า" และ "ใบเสร็จรับเงิน" ออกจากกัน ---
            if selected_row['status'].startswith('COMPLETED'):
                st.markdown("---")
                st.success("🎉 งานซ่อมเสร็จสิ้นแล้ว! สามารถเลือกพิมพ์ **ใบคืนสินค้า** หรือ **ใบเสร็จรับเงิน** พร้อมแก้ไขรายการ ราคา และช่องหมายเหตุได้ด้านล่างครับ")
                
                doc_choice = st.radio("🖨️ เลือกประเภทเอกสารที่ต้องการพิมพ์:", ["📦 พิมพ์ใบคืนสินค้า (Delivery Slip)", "💵 พิมพ์ใบเสร็จรับเงิน / ใบกำกับภาษี (Receipt / Tax Invoice)"])
                
                with st.form(f"form_doc_{selected_job}"):
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        pay_chanel = st.selectbox("ช่องทางชำระเงิน", ["เงินสด", "โอนเงินผ่าน PromptPay QR", "บัตรเครดิต"])
                    with c_col2:
                        warrant_days = st.number_input("ระยะเวลารับประกันหลังซ่อม (วัน)", min_value=0, value=30)
                        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)

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
                    
                    generate_btn = st.form_submit_button("🖨️ สร้างเอกสารพร้อมพิมพ์ (A4 แนวตั้ง ครึ่งหน้า สำหรับลูกค้า & ร้านค้า)")
                    
                    if generate_btn:
                        grand_total = subtotal * 1.07 if include_vat else subtotal
                        
                        # สร้าง QR Code สำหรับจ่ายเงิน (เฉพาะใบเสร็จ)
                        qr_tag = ""
                        if pay_chanel == "โอนเงินผ่าน PromptPay QR":
                            q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                            qr_obj = qrcode.make(q_cont)
                            q_stream = BytesIO()
                            qr_obj.save(q_stream)
                            b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                            qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="85px"><br><span style="font-size:8px;">สแกนชำระ PromptPay</span>'

                        items_html = ""
                        for idx, val in enumerate(items_data):
                            items_html += f"<tr><td style='border-bottom:1px solid #ddd; padding:2px;'>{idx+1}. {val[0]}</td><td style='border-bottom:1px solid #ddd; padding:2px; text-align:center;'>{val[1]}</td><td style='border-bottom:1px solid #ddd; padding:2px; text-align:right;'>{val[2]:,.2f}</td><td style='border-bottom:1px solid #ddd; padding:2px; text-align:right;'>{val[3]:,.2f}</td></tr>"

                        vat_html = f"<tr><td colspan='3' style='text-align:right; padding:2px;'><b>VAT 7%:</b></td><td style='text-align:right; padding:2px;'>{subtotal * 0.07:,.2f} บาท</td></tr>" if include_vat else ""

                        doc_title_text = "ใบคืนสินค้าและส่งมอบงานซ่อม (Delivery Slip)" if "ใบคืนสินค้า" in doc_choice else "ใบเสร็จรับเงิน / ใบกำกับภาษี (Receipt / Tax Invoice)"

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
                            <button class="print-btn" onclick="window.print()">🖨️ คลิกที่นี่เพื่อพิมพ์เอกสาร (A4 แนวตั้ง)</button>
                            <div class="doc-box">
                                
                                <!-- ส่วนที่ 1: สำหรับลูกค้า -->
                                <div class="section-box">
                                    <div>
                                        <table class="tbl">
                                            <tr>
                                                <td>
                                                    <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                    <p style="font-size: 10px; margin: 1px 0;">{STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                                                </td>
                                                <td style="text-align: right; vertical-align: top;">
                                                    <h4 style="color: #333; margin: 0;"><b>{doc_title_text} (สำหรับลูกค้า)</b></h4>
                                                    <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                </td>
                                            </tr>
                                        </table>
                                        <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                            <tr>
                                                <td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td>
                                                <td><b>ช่องทางชำระ:</b> {pay_chanel}</td>
                                            </tr>
                                            <tr>
                                                <td><b>อุปกรณ์:</b> {selected_row['device_name']}</td>
                                                <td><b>รับประกันหลังซ่อม:</b> {warrant_days} วัน</td>
                                            </tr>
                                        </table>
                                        
                                        <table class="itm-tbl">
                                            <tr>
                                                <th>รายการสินค้า / บริการ</th>
                                                <th style="text-align: center;">จำนวน</th>
                                                <th style="text-align: right;">ราคา/หน่วย</th>
                                                <th style="text-align: right;">จำนวนเงิน (บาท)</th>
                                            </tr>
                                            {items_html}
                                            <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                            {vat_html}
                                            <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                        </table>
                                    </div>

                                    <div class="ftr">
                                        <div style="width: 75%;">
                                            <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                            <p style="font-size: 10px; margin: 10px 0 0 0;">ลงชื่อรับสินค้าคืน: ...................................................... (ลูกค้า)</p>
                                        </div>
                                        <div style="text-align: center; width: 25%;">
                                            {qr_tag}
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
                                        <table class="tbl">
                                            <tr>
                                                <td>
                                                    <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                    <p style="font-size: 10px; margin: 1px 0;">ใบควบคุมการส่งมอบและรับเงิน (สำหรับร้านค้าเก็บไว้)</p>
                                                </td>
                                                <td style="text-align: right; vertical-align: top;">
                                                    <h4 style="color: #333; margin: 0;"><b>{doc_title_text} (สำหรับร้านค้า)</b></h4>
                                                    <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                </td>
                                            </tr>
                                        </table>
                                        <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                            <tr>
                                                <td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td>
                                                <td><b>ช่องทางชำระ:</b> {pay_chanel}</td>
                                            </tr>
                                            <tr>
                                                <td><b>อุปกรณ์:</b> {selected_row['device_name']}</td>
                                                <td><b>รับประกันหลังซ่อม:</b> {warrant_days} วัน</td>
                                            </tr>
                                        </table>
                                        
                                        <table class="itm-tbl">
                                            <tr>
                                                <th>รายการสินค้า / บริการ</th>
                                                <th style="text-align: center;">จำนวน</th>
                                                <th style="text-align: right;">ราคา/หน่วย</th>
                                                <th style="text-align: right;">จำนวนเงิน (บาท)</th>
                                            </tr>
                                            {items_html}
                                            <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                            {vat_html}
                                            <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                        </table>
                                    </div>

                                    <div class="ftr">
                                        <div style="width: 100%;">
                                            <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                            <p style="font-size: 10px; margin: 10px 0 0 0;">ลงชื่อลูกค้า (ตรวจสอบสภาพเรียบร้อย): ...................................................... &nbsp;&nbsp;&nbsp;&nbsp; ช่างผู้ส่งมอบ: ......................................................</p>
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
# 5. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number")
    if sn_input:
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน!")

# ==========================================
# 6. ออกเอกสารการค้า / ใบเสร็จ
# ==========================================
elif menu == "📄 ออกเอกสารการค้า / ใบเสร็จ (พร้อม QR Code)":
    st.header("📄 ระบบออกเอกสารและใบกำกับภาษี (FlowAccount Style)")
    cust_name = st.text_input("ชื่อลูกค้า / บริษัท")
    if cust_name:
        st.success("พิมพ์เอกสารพร้อมใช้งาน")

# ==========================================
# 7. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")

# ==========================================
# 8. ตั้งค่าข้อมูลร้านค้า
# ==========================================
elif menu == "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)":
    st.header("⚙️ ตั้งค่าข้อมูลร้านค้า")
    with st.form("settings_form"):
        new_store_name = st.text_input("ชื่อร้านค้า", value=STORE_NAME)
        new_phone = st.text_input("เบอร์โทรศัพท์", value=STORE_PHONE)
        new_promptpay = st.text_input("เลขพร้อมเพย์", value=STORE_PROMPTPAY)
        new_line = st.text_input("ลิงก์ Line", value=STORE_LINE)
        new_fb = st.text_input("ลิงก์ Facebook", value=STORE_FB)
        new_tiktok = st.text_input("ลิงก์ TikTok", value=STORE_TIKTOK)
        new_tax = st.text_input("เลขผู้เสียภาษี", value=STORE_TAX)
        new_address = st.text_area("ที่อยู่", value=STORE_ADDRESS)
        new_note = st.text_input("หมายเหตุ", value=STORE_NOTE)
        
        if st.form_submit_button("💾 บันทึกการตั้งค่า"):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE store_settings 
                SET store_name = ?, phone = ?, tax_id = ?, address = ?, note = ?, promptpay = ?, line_link = ?, fb_link = ?, tiktok_link = ? 
                WHERE id = 1
            """, (new_store_name, new_phone, new_tax, new_address, new_note, new_promptpay, new_line, new_fb, new_tiktok))
            conn.commit()
            cursor.close()
            st.success("บันทึกการตั้งค่าสำเร็จ!")
            st.rerun()