import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import qrcode
from io import BytesIO

st.set_page_config(
    page_title="ServiceTicker Pro - Enterprise Edition",
    layout="wide",
    page_icon="💻"
)

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('serviceticker_enterprise.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Shop Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT, tax_id TEXT, address TEXT, phone TEXT, email TEXT, footer_message TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, password TEXT, fullname TEXT, role TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT, serial_no TEXT, category TEXT, 
            buy_price REAL, sell_price REAL, qty INTEGER, status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_no TEXT UNIQUE, date TEXT, customer TEXT, phone TEXT, 
            device_model TEXT, serial_no TEXT, issue TEXT, 
            parts_cost REAL, labor_cost REAL, total_price REAL, 
            status TEXT, technician TEXT, payment_status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_no TEXT, date TEXT, customer TEXT, item TEXT, 
            qty INTEGER, total REAL, profit REAL, payment_method TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_no TEXT, date TEXT, customer TEXT, item TEXT, 
            serial_no TEXT, issue TEXT, status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, username TEXT, action TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# Seed default shop info if empty
cursor.execute('SELECT COUNT(*) FROM shop_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('''
        INSERT INTO shop_settings (shop_name, tax_id, address, phone, email, footer_message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '0123456789000', '123/45 ถนนพหลโยธิน กรุงเทพฯ 10900', '02-xxx-xxxx', 'zonecomputer@email.com', '*ขอบคุณที่ใช้บริการครับ*'))
    conn.commit()

# Seed default users & stock
cursor.execute('SELECT COUNT(*) FROM users')
if cursor.fetchone()[0] == 0:
    default_users = [
        ('admin', '1234', 'ผู้ดูแลระบบสูงสุด (Admin)', 'Admin'),
        ('tech1', '1234', 'ช่างสมชาย (Technician)', 'Technician'),
        ('cashier', '1234', 'พนักงานแคชเชียร์ (Cashier)', 'Cashier')
    ]
    cursor.executemany("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)", default_users)
    conn.commit()

cursor.execute('SELECT COUNT(*) FROM inventory')
if cursor.fetchone()[0] == 0:
    default_stock = [
        ('P001', 'SSD 500GB M.2 NVMe', 'SN-SSD500-001', 'อะไหล่', 1100, 1550, 10, 'In Stock'),
        ('P002', 'RAM DDR4 16GB', 'SN-RAM16-002', 'อะไหล่', 1000, 1450, 8, 'In Stock'),
        ('P003', 'Thermal Paste MX-4', 'N/A', 'อุปกรณ์เสริม', 80, 150, 25, 'In Stock')
    ]
    cursor.executemany("INSERT INTO inventory (code, name, serial_no, category, buy_price, sell_price, qty, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", default_stock)
    conn.commit()

# Helper: Get Shop Profile
def get_shop_info():
    df = pd.read_sql("SELECT * FROM shop_settings WHERE id=1", conn)
    if not df.empty:
        return df.iloc[0]
    return {
        "shop_name": "ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส",
        "tax_id": "0123456789000",
        "address": "123/45 ถนนพหลโยธิน กรุงเทพฯ",
        "phone": "02-xxx-xxxx",
        "email": "zone@email.com",
        "footer_message": "*ขอบคุณที่ใช้บริการครับ*"
    }

# Helper: QR Code Generator
def make_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Check Query Params for Customer Portal Mode
query_params = st.query_params
shop_info = get_shop_info()
mode = query_params.get("mode", "")

# ====================================================
# 📱 MOBILE PORTAL: ลูกค้าสแกนลงทะเบียนซ่อมเอง
# ====================================================
if mode == "register":
    st.title(f"🛠️ {shop_info['shop_name']}")
    st.subheader("📝 ลงทะเบียนแจ้งซ่อมด้วยตนเอง")
    st.write("กรุณากรอกข้อมูลอุปกรณ์และอาการเสียเพื่อให้ช่างตรวจสอบเบื้องต้นครับ")
    
    with st.form("cust_reg_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์มือถือ")
        c_model = st.text_input("รุ่นคอมพิวเตอร์ / โน้ตบุ๊ก (เช่น ASUS TUF)")
        c_sn = st.text_input("Serial Number (ถ้ามี)")
        c_issue = st.text_area("อาการเสีย / ปัญหาที่พบ")
        
        submitted = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อม")
        if submitted:
            if c_name and c_phone and c_model:
                cursor.execute("SELECT COUNT(*) FROM repairs")
                cnt = cursor.fetchone()[0] + 1
                j_no = f"JOB-{datetime.now().strftime('%y%m')}-{str(cnt).zfill(3)}"
                d_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                cursor.execute("""
                    INSERT INTO repairs (job_no, date, customer, phone, device_model, serial_no, issue, parts_cost, labor_cost, total_price, status, technician, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 'รอตรวจสอบ', 'รอมอบหมายช่าง', 'ยังไม่ชำระ')
                """, (j_no, d_str, c_name, c_phone, c_model, c_sn, c_issue))
                conn.commit()
                st.success(f"🎉 ลงทะเบียนแจ้งซ่อมสำเร็จ! เลขที่ใบงานของคุณคือ: **{j_no}**")
            else:
                st.error("❌ กรุณากรอกชื่อ เบอร์โทร และรุ่นคอมพิวเตอร์ให้ครบถ้วน")
    
    st.markdown("---")
    if st.button("🔐 สำหรับเจ้าของร้าน: กลับสู่ระบบหลังบ้าน"):
        st.query_params.clear()
        st.rerun()
    st.stop()

# ====================================================
# 🔐 LOGIN SYSTEM
# ====================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>💻 {shop_info['shop_name']}</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)
            if submit:
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = {"id": user[0], "username": user[1], "name": user[3], "role": user[4]}
                    cursor.execute("INSERT INTO audit_logs (timestamp, username, action) VALUES (?, ?, ?)", 
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user[1], "Login เข้าสู่ระบบ"))
                    conn.commit()
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        st.info("💡 **ทดสอบระบบ:** Admin: `admin`/`1234` | ช่าง: `tech1`/`1234` | แคชเชียร์: `cashier`/`1234`")
    st.stop()

# ====================================================
# 🛠️ SIDEBAR NAVIGATION
# ====================================================
current_user = st.session_state.user

with st.sidebar:
    st.markdown(f"### 👤 ผู้ใช้งาน: {current_user['name']}")
    st.write(f"**สิทธิ์:** {current_user['role']}")
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    st.markdown("---")
    st.markdown("### 🛠️ เมนูระบบหลัก")
    
    menu = st.sidebar.radio("เลือกเมนูการทำงาน", [
        "🛠️ ระบบรับ-ส่งงานซ่อม",
        "⚙️ จัดการข้อมูลร้านค้า (Shop Admin)",
        "⚙️ ระบบจัดการหลังบ้าน (Master Back-office)",
        "📄 ออกเอกสาร & ฟอร์มทางธุรกิจ (A4)",
        "📱 QR Code สำหรับลูกค้าสแกนซ่อม",
        "📦 สต็อกสินค้า & Serial Number (S/N)",
        "🔄 ระบบเคลมสินค้า (Claims)",
        "🛒 ระบบขายหน้าร้าน (POS)",
        "💰 งานบัญชี & ลูกหนี้คงค้าง",
        "📊 รายงานสรุปผล (Reports)",
        "📋 ตรวจสอบการเข้าใช้งาน (Audit Log)"
    ])

# ----------------------------------------------------
# 1. ระบบรับ-ส่งงานซ่อม
# ----------------------------------------------------
if menu == "🛠️ ระบบรับ-ส่งงานซ่อม":
    st.subheader("🛠️ ระบบบริหารจัดการงานซ่อมคอมพิวเตอร์")
    
    tab1, tab2 = st.tabs(["รับเครื่องเข้าซ่อม (หน้าร้าน)", "ติดตาม & จัดการสถานะซ่อม"])
    
    with tab1:
        with st.form("new_repair"):
            col1, col2 = st.columns(2)
            with col1:
                cust_name = st.text_input("ชื่อ-นามสกุลลูกค้า")
                cust_phone = st.text_input("เบอร์โทรศัพท์")
                device_model = st.text_input("รุ่นอุปกรณ์ (เช่น ASUS TUF Gaming)")
            with col2:
                serial_no = st.text_input("Serial Number (S/N) อุปกรณ์", value="N/A")
                technician = st.selectbox("มอบหมายช่างผู้รับผิดชอบ", [u[3] for u in cursor.execute("SELECT * FROM users WHERE role='Technician'").fetchall()] or ["ช่างทั่วไป"])
                issue = st.text_area("อาการเสีย / ตำหนิภายนอก")
                
            submitted = st.form_submit_button("บันทึกรับเครื่องซ่อม")
            if submitted and cust_name and cust_phone:
                cursor.execute("SELECT COUNT(*) FROM repairs")
                job_count = cursor.fetchone()[0] + 1
                job_no = f"JOB-{datetime.now().strftime('%y%m')}-{str(job_count).zfill(3)}"
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                cursor.execute("""
                    INSERT INTO repairs (job_no, date, customer, phone, device_model, serial_no, issue, parts_cost, labor_cost, total_price, status, technician, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 'รอตรวจสอบ', ?, 'ยังไม่ชำระ')
                """, (job_no, date_str, cust_name, cust_phone, device_model, serial_no, issue, technician))
                conn.commit()
                st.success(f"บันทึกรับซ่อมสำเร็จ! เลขที่ใบงาน: **{job_no}**")
                
    with tab2:
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df[['job_no', 'date', 'customer', 'device_model', 'serial_no', 'status', 'technician', 'total_price']], use_container_width=True)
            
            st.markdown("### ⚙️ อัปเดตสถานะและคำนวณค่าบริการ")
            selected_job = st.selectbox("เลือกเลขที่ใบงานซ่อม", repairs_df['job_no'].tolist())
            row = repairs_df[repairs_df['job_no'] == selected_job].iloc[0]
            
            with st.form("update_repair"):
                new_status = st.selectbox("สถานะงานซ่อม", ["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"], 
                                         index=["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"].index(row['status']) if row['status'] in ["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"] else 0)
                parts_cost = st.number_input("ต้นทุนอะไหล่ (บาท)", min_value=0.0, value=float(row['parts_cost']))
                labor_cost = st.number_input("ค่าบริการ / ค่าแรง (บาท)", min_value=0.0, value=float(row['labor_cost']))
                total_price = parts_cost + labor_cost
                payment_status = st.selectbox("สถานะการชำระเงิน", ["ยังไม่ชำระ", "ชำระแล้ว (เงินสด/โอน)", "ค้างชำระ (ลูกหนี้)"], index=0 if row['payment_status']=='ยังไม่ชำระ' else 1)
                
                if st.form_submit_button("บันทึกการอัปเดต"):
                    cursor.execute("UPDATE repairs SET status=?, parts_cost=?, labor_cost=?, total_price=?, payment_status=? WHERE job_no=?",
                                   (new_status, parts_cost, labor_cost, total_price, payment_status, selected_job))
                    conn.commit()
                    st.success("อัปเดตข้อมูลงานซ่อมสำเร็จ!")
                    st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")

# ----------------------------------------------------
# 2. จัดการข้อมูลร้านค้า (Shop Admin)
# ----------------------------------------------------
elif menu == "⚙️ จัดการข้อมูลร้านค้า (Shop Admin)":
    st.subheader("⚙️ ระบบจัดการข้อมูลร้านค้า (Administrator Shop Profile)")
    st.write("ตั้งค่าชื่อร้าน ที่อยู่ เบอร์โทรศัพท์ เลขประจำตัวผู้เสียภาษี และข้อความท้ายใบเสร็จ ข้อมูลนี้จะเชื่อมโยงไปแสดงผลบนเอกสารทางธุรกิจทั้งหมดโดยอัตโนมัติ")
    
    current_shop = get_shop_info()
    with st.form("shop_admin_form"):
        s_name = st.text_input("ชื่อร้านค้า / ชื่อบริษัท", value=current_shop['shop_name'])
        s_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", value=current_shop['tax_id'])
        s_addr = st.text_area("ที่อยู่ร้านค้า", value=current_shop['address'])
        s_phone = st.text_input("เบอร์โทรศัพท์ติดต่อ", value=current_shop['phone'])
        s_email = st.text_input("อีเมลติดต่อ", value=current_shop['email'])
        s_footer = st.text_input("ข้อความท้ายใบเสร็จ (Footer Message)", value=current_shop['footer_message'])
        
        if st.form_submit_button("💾 บันทึกการเปลี่ยนแปลงข้อมูลร้าน"):
            cursor.execute("""
                UPDATE shop_settings 
                SET shop_name=?, tax_id=?, address=?, phone=?, email=?, footer_message=? 
                WHERE id=1
            """, (s_name, s_tax, s_addr, s_phone, s_email, s_footer))
            conn.commit()
            st.success("บันทึกข้อมูลร้านค้าสำเร็จ! ข้อมูลถูกอัปเดตลงในเอกสารทั้งหมดเรียบร้อยแล้ว")
            st.rerun()

# ----------------------------------------------------
# 3. ระบบจัดการหลังบ้าน (Master Back-office)
# ----------------------------------------------------
elif menu == "⚙️ ระบบจัดการหลังบ้าน (Master Back-office)":
    st.subheader("⚙️ ระบบจัดการและแก้ไขข้อมูลหลังบ้าน (Master Management)")
    st.write("โมดูลนี้ช่วยให้คุณสามารถแก้ไข ปรับปรุง หรือลบข้อมูลในทุกฟังก์ชันของระบบได้อย่างอิสระ")
    
    bo_tab1, bo_tab2, bo_tab3, bo_tab4, bo_tab5 = st.tabs([
        "👥 จัดการผู้ใช้งาน", 
        "📦 จัดการสต็อกสินค้า", 
        "🛠️ จัดการงานซ่อม", 
        "🛒 จัดการประวัติการขาย", 
        "🔄 จัดการรายการเคลม"
    ])
    
    with bo_tab1:
        st.markdown("### 👥 แก้ไข / ลบข้อมูลผู้ใช้งานในระบบ")
        users_df = pd.read_sql("SELECT * FROM users", conn)
        st.dataframe(users_df, use_container_width=True)
        
        if not users_df.empty:
            edit_user_id = st.selectbox("เลือกผู้ใช้ที่ต้องการแก้ไข/ลบ (ID)", users_df['id'].tolist(), key="sel_user")
            u_row = users_df[users_df['id'] == edit_user_id].iloc[0]
            
            with st.form("edit_user_form"):
                e_user = st.text_input("Username", value=u_row['username'])
                e_pass = st.text_input("Password", value=u_row['password'])
                e_name = st.text_input("ชื่อ-นามสกุล", value=u_row['fullname'])
                e_role = st.selectbox("สิทธิ์การใช้งาน", ["Admin", "Technician", "Cashier"], index=["Admin", "Technician", "Cashier"].index(u_row['role']) if u_row['role'] in ["Admin", "Technician", "Cashier"] else 0)
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    save_u = st.form_submit_button("💾 บันทึกการแก้ไข")
                with c_btn2:
                    del_u = st.form_submit_button("🗑️ ลบผู้ใช้นี้")
                    
                if save_u:
                    cursor.execute("UPDATE users SET username=?, password=?, fullname=?, role=? WHERE id=?", (e_user, e_pass, e_name, e_role, edit_user_id))
                    conn.commit()
                    st.success("แก้ไขข้อมูลผู้ใช้สำเร็จ!")
                    st.rerun()
                if del_u:
                    cursor.execute("DELETE FROM users WHERE id=?", (edit_user_id,))
                    conn.commit()
                    st.warning("ลบผู้ใช้งานสำเร็จ!")
                    st.rerun()

    with bo_tab2:
        st.markdown("### 📦 แก้ไข / ลบข้อมูลคลังสินค้าและอะไหล่")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        st.dataframe(inv_df, use_container_width=True)
        
        if not inv_df.empty:
            edit_inv_id = st.selectbox("เลือกสินค้าที่ต้องการแก้ไข/ลบ (ID)", inv_df['id'].tolist(), key="sel_inv")
            i_row = inv_df[inv_df['id'] == edit_inv_id].iloc[0]
            
            with st.form("edit_inv_form"):
                i_code = st.text_input("รหัสสินค้า", value=i_row['code'])
                i_name = st.text_input("ชื่อสินค้า", value=i_row['name'])
                i_sn = st.text_input("Serial Number", value=i_row['serial_no'])
                i_cat = st.text_input("หมวดหมู่", value=i_row['category'])
                i_buy = st.number_input("ราคาทุน", value=float(i_row['buy_price']))
                i_sell = st.number_input("ราคาขาย", value=float(i_row['sell_price']))
                i_qty = st.number_input("จำนวนคงเหลือ", value=int(i_row['qty']))
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    save_i = st.form_submit_button("💾 บันทึกการแก้ไขสต็อก")
                with c_btn2:
                    del_i = st.form_submit_button("🗑️ ลบสินค้านี้")
                    
                if save_i:
                    cursor.execute("UPDATE inventory SET code=?, name=?, serial_no=?, category=?, buy_price=?, sell_price=?, qty=? WHERE id=?", 
                                   (i_code, i_name, i_sn, i_cat, i_buy, i_sell, i_qty, edit_inv_id))
                    conn.commit()
                    st.success("แก้ไขข้อมูลสต็อกสำเร็จ!")
                    st.rerun()
                if del_i:
                    cursor.execute("DELETE FROM inventory WHERE id=?", (edit_inv_id,))
                    conn.commit()
                    st.warning("ลบสินค้าสำเร็จ!")
                    st.rerun()

    with bo_tab3:
        st.markdown("### 🛠️ แก้ไข / ลบข้อมูลงานซ่อมทั้งหมดในระบบ")
        rep_df = pd.read_sql("SELECT * FROM repairs", conn)
        st.dataframe(rep_df[['job_no', 'customer', 'device_model', 'serial_no', 'status', 'total_price']], use_container_width=True)
        
        if not rep_df.empty:
            edit_job_no = st.selectbox("เลือกเลขที่ใบงานที่ต้องการแก้ไข/ลบ", rep_df['job_no'].tolist(), key="sel_job_bo")
            r_row = rep_df[rep_df['job_no'] == edit_job_no].iloc[0]
            
            with st.form("edit_repair_master"):
                r_cust = st.text_input("ชื่อลูกค้า", value=r_row['customer'])
                r_phone = st.text_input("เบอร์โทร", value=r_row['phone'])
                r_dev = st.text_input("รุ่นอุปกรณ์", value=r_row['device_model'])
                r_sn = st.text_input("Serial No", value=r_row['serial_no'])
                r_issue = st.text_area("อาการเสีย", value=r_row['issue'])
                r_parts = st.number_input("ต้นทุนอะไหล่", value=float(r_row['parts_cost']))
                r_labor = st.number_input("ค่าแรง", value=float(r_row['labor_cost']))
                r_tot = r_parts + r_labor
                r_status = st.text_input("สถานะงาน", value=r_row['status'])
                r_pay = st.text_input("สถานะชำระเงิน", value=r_row['payment_status'])
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    save_r = st.form_submit_button("💾 บันทึกแก้ไขใบงาน")
                with c_btn2:
                    del_r = st.form_submit_button("🗑️ ลบใบงานนี้")
                    
                if save_r:
                    cursor.execute("UPDATE repairs SET customer=?, phone=?, device_model=?, serial_no=?, issue=?, parts_cost=?, labor_cost=?, total_price=?, status=?, payment_status=? WHERE job_no=?",
                                   (r_cust, r_phone, r_dev, r_sn, r_issue, r_parts, r_labor, r_tot, r_status, r_pay, edit_job_no))
                    conn.commit()
                    st.success("แก้ไขใบงานซ่อมสำเร็จ!")
                    st.rerun()
                if del_r:
                    cursor.execute("DELETE FROM repairs WHERE job_no=?", (edit_job_no,))
                    conn.commit()
                    st.warning("ลบใบงานซ่อมสำเร็จ!")
                    st.rerun()

    with bo_tab4:
        st.markdown("### 🛒 แก้ไข / ลบประวัติการขายหน้าร้าน (POS)")
        sales_df = pd.read_sql("SELECT * FROM sales", conn)
        st.dataframe(sales_df, use_container_width=True)
        
        if not sales_df.empty:
            edit_sale_id = st.selectbox("เลือกรายการขายที่ต้องการจัดการ (ID)", sales_df['id'].tolist(), key="sel_sale_bo")
            s_row = sales_df[sales_df['id'] == edit_sale_id].iloc[0]
            
            with st.form("edit_sale_form"):
                s_cust = st.text_input("ชื่อลูกค้า", value=s_row['customer'])
                s_item = st.text_input("รายการสินค้า", value=s_row['item'])
                s_qty = st.number_input("จำนวน", value=int(s_row['qty']))
                s_tot = st.number_input("ยอดเงินรวม", value=float(s_row['total']))
                s_prof = st.number_input("กำไร", value=float(s_row['profit']))
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    save_s = st.form_submit_button("💾 บันทึกแก้ไขรายการขาย")
                with c_btn2:
                    del_s = st.form_submit_button("🗑️ ลบรายการขายนี้")
                    
                if save_s:
                    cursor.execute("UPDATE sales SET customer=?, item=?, qty=?, total=?, profit=? WHERE id=?", (s_cust, s_item, s_qty, s_tot, s_prof, edit_sale_id))
                    conn.commit()
                    st.success("แก้ไขรายการขายสำเร็จ!")
                    st.rerun()
                if del_s:
                    cursor.execute("DELETE FROM sales WHERE id=?", (edit_sale_id,))
                    conn.commit()
                    st.warning("ลบรายการขายสำเร็จ!")
                    st.rerun()

    with bo_tab5:
        st.markdown("### 🔄 แก้ไข / ลบรายการเคลมสินค้า")
        claim_df = pd.read_sql("SELECT * FROM claims", conn)
        st.dataframe(claim_df, use_container_width=True)
        
        if not claim_df.empty:
            edit_claim_id = st.selectbox("เลือกรายการเคลมที่ต้องการจัดการ (ID)", claim_df['id'].tolist(), key="sel_claim_bo")
            c_row = claim_df[claim_df['id'] == edit_claim_id].iloc[0]
            
            with st.form("edit_claim_form"):
                cl_cust = st.text_input("ชื่อลูกค้า", value=c_row['customer'])
                cl_item = st.text_input("ชื่อสินค้า", value=c_row['item'])
                cl_sn = st.text_input("Serial No", value=c_row['serial_no'])
                cl_issue = st.text_area("อาการเสีย", value=c_row['issue'])
                cl_stat = st.text_input("สถานะเคลม", value=c_row['status'])
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    save_cl = st.form_submit_button("💾 บันทึกแก้ไขรายการเคลม")
                with c_btn2:
                    del_cl = st.form_submit_button("🗑️ ลบรายการเคลมนี้")
                    
                if save_cl:
                    cursor.execute("UPDATE claims SET customer=?, item=?, serial_no=?, issue=?, status=? WHERE id=?", (cl_cust, cl_item, cl_sn, cl_issue, cl_stat, edit_claim_id))
                    conn.commit()
                    st.success("แก้ไขรายการเคลมสำเร็จ!")
                    st.rerun()
                if del_cl:
                    cursor.execute("DELETE FROM claims WHERE id=?", (edit_claim_id,))
                    conn.commit()
                    st.warning("ลบรายการเคลมสำเร็จ!")
                    st.rerun()

# ----------------------------------------------------
# 4. ออกเอกสาร & ฟอร์มทางธุรกิจ (A4 ปะรอยฉีก & ฟอร์มครบชุด)
# ----------------------------------------------------
elif menu == "📄 ออกเอกสาร & ฟอร์มทางธุรกิจ (A4)":
    st.subheader("📄 ศูนย์รวมออกเอกสารและใบสำคัญทางธุรกิจ (ขนาด A4)")
    
    doc_type = st.selectbox("เลือกประเภทเอกสารที่ต้องการพิมพ์", [
        "ใบรับซ่อม (A4 แบบมีรอยฉีกปะ)",
        "ใบประเมินราคา (Evaluation Sheet)",
        "ใบเสนอราคา (Quotation)",
        "ใบส่งของ (Delivery Note)",
        "ใบกำกับภาษี (Tax Invoice)",
        "บิลเงินสด (Cash Bill)",
        "ใบเสร็จรับเงิน (Receipt)"
    ])
    
    shop = get_shop_info()
    rep_list = pd.read_sql("SELECT job_no, customer, device_model FROM repairs", conn)
    if not rep_list.empty:
        target_job = st.selectbox("เลือกใบงานซ่อมที่เกี่ยวข้อง", rep_list['job_no'].tolist())
        j_data = pd.read_sql(f"SELECT * FROM repairs WHERE job_no='{target_job}'", conn).iloc[0]
        
        if doc_type == "ใบรับซ่อม (A4แบบมีรอยฉีกปะ)":
            st.markdown("### 🖨️ ตัวอย่างเอกสาร A4 (ต้นฉบับร้าน + สำเนาลูกค้า ปะรอยฉีก)")
            st.markdown(f"""
            <div style="border: 2px solid #333; padding: 20px; font-family: 'Kanit', sans-serif; background: #fff; color: #000;">
                <h3 style="text-align:center; margin:0;">{shop['shop_name']} (ต้นฉบับสำหรับร้าน)</h3>
                <p style="text-align:center; font-size:12px; margin:2px;">ที่อยู่: {shop['address']} | โทร. {shop['phone']} | Tax ID: {shop['tax_id']}</p>
                <hr>
                <table style="width:100%; font-size:14px;">
                    <tr><td><b>เลขที่ใบงาน:</b> {j_data['job_no']}</td><td><b>วันที่รับ:</b> {j_data['date']}</td></tr>
                    <tr><td><b>ชื่อลูกค้า:</b> {j_data['customer']}</td><td><b>เบอร์โทร:</b> {j_data['phone']}</td></tr>
                    <tr><td><b>รุ่นอุปกรณ์:</b> {j_data['device_model']}</td><td><b>Serial No:</b> {j_data['serial_no']}</td></tr>
                    <tr><td colspan="2"><b>อาการเสีย:</b> {j_data['issue']}</td></tr>
                    <tr><td><b>ช่างผู้รับผิดชอบ:</b> {j_data['technician']}</td><td><b>สถานะ:</b> {j_data['status']}</td></tr>
                </table>
                <br><br>
                <div style="display:flex; justify-content:space-between;">
                    <div style="text-align:center;">____________________<br>ผู้รับเครื่อง (ร้าน)</div>
                    <div style="text-align:center;">____________________<br>ลูกค้าผู้ส่งซ่อม</div>
                </div>
            </div>
            
            <div style="border-top: 3px dashed #666; margin: 30px 0; text-align: center; color: #666; font-size:14px;">
                ✂️ ------------------------------------ ตัดตามรอยปะสำหรับลูกค้า ------------------------------------ ✂️
            </div>

            <div style="border: 2px solid #333; padding: 20px; font-family: 'Kanit', sans-serif; background: #fff; color: #000;">
                <h3 style="text-align:center; margin:0;">{shop['shop_name']} (สำเนาสำหรับลูกค้า)</h3>
                <p style="text-align:center; font-size:12px; margin:2px;">โทร. {shop['phone']} | {shop['footer_message']}</p>
                <hr>
                <table style="width:100%; font-size:14px;">
                    <tr><td><b>เลขที่ใบงาน:</b> {j_data['job_no']}</td><td><b>วันที่รับ:</b> {j_data['date']}</td></tr>
                    <tr><td><b>ชื่อลูกค้า:</b> {j_data['customer']}</td><td><b>เบอร์โทร:</b> {j_data['phone']}</td></tr>
                    <tr><td><b>รุ่นอุปกรณ์:</b> {j_data['device_model']}</td><td><b>Serial No:</b> {j_data['serial_no']}</td></tr>
                    <tr><td colspan="2"><b>อาการเสีย:</b> {j_data['issue']}</td></tr>
                    <tr><td><b>ประเมินค่าใช้จ่าย:</b> {j_data['total_price']:,.2f} บาท</td><td><b>สถานะ:</b> {j_data['status']}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.markdown(f"""
            <div style="border: 2px solid #222; padding: 30px; font-family: 'Kanit', sans-serif; background: #fff; color: #000;">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <h2>{shop['shop_name']}</h2>
                        <p style="font-size:12px; margin:0;">{shop['address']}<br>โทร: {shop['phone']} | เลขประจำตัวผู้เสียภาษี: {shop['tax_id']}</p>
                    </div>
                    <div style="text-align:right;">
                        <h2 style="color:#1E3A8A; margin:0;">{doc_type.upper()}</h2>
                        <p style="font-size:12px; margin:0;"><b>เลขที่:</b> DOC-{j_data['job_no']}<br><b>วันที่:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
                    </div>
                </div>
                <hr>
                <p><b>นามลูกค้า:</b> {j_data['customer']} (โทร: {j_data['phone']})</p>
                <table style="width:100%; border-collapse: collapse; margin-top: 20px;" border="1">
                    <tr style="background:#f2f2f2;">
                        <th style="padding:10px; text-align:left;">ลำดับ</th>
                        <th style="padding:10px; text-align:left;">รายการสินค้า / บริการซ่อม</th>
                        <th style="padding:10px; text-align:center;">จำนวน</th>
                        <th style="padding:10px; text-align:right;">ราคาต่อหน่วย</th>
                        <th style="padding:10px; text-align:right;">จำนวนเงิน (บาท)</th>
                    </tr>
                    <tr>
                        <td style="padding:10px;">1</td>
                        <td style="padding:10px;">ค่าบริการซ่อมและตรวจเช็ค ({j_data['device_model']} - S/N: {j_data['serial_no']})</td>
                        <td style="padding:10px; text-align:center;">1</td>
                        <td style="padding:10px; text-align:right;">{j_data['total_price']:,.2f}</td>
                        <td style="padding:10px; text-align:right;">{j_data['total_price']:,.2f}</td>
                    </tr>
                </table>
                <br>
                <div style="text-align:right; font-size:16px;">
                    <p><b>ยอดรวมทั้งสิ้น:</b> {j_data['total_price']:,.2f} บาท</p>
                </div>
                <br><br>
                <div style="display:flex; justify-content:space-between; margin-top:50px;">
                    <div style="text-align:center;">______________________________<br>ผู้มีอำนาจลงนาม / ผู้ออกเอกสาร</div>
                    <div style="text-align:center;">______________________________<br>ผู้รับสินค้า / ลูกค้า</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ยังไม่มีข้อมูลใบงานซ่อมในระบบสำหรับออกเอกสาร")

# ----------------------------------------------------
# 5. QR Code สำหรับลูกค้าสแกนซ่อม
# ----------------------------------------------------
elif menu == "📱 QR Code สำหรับลูกค้าสแกนซ่อม":
    st.subheader("📱 สร้าง QR Code ตั้งหน้าร้าน (ให้ลูกค้าสแกนลงทะเบียนซ่อมเอง)")
    st.write("คุณสามารถปริ้นท์ป้ายนี้ตั้งไว้ที่เคาน์เตอร์ เพื่อให้ลูกค้าใช้มือถือสแกนกรอกข้อมูลแจ้งซ่อมได้ทันที")
    
    try:
        current_url = st.context.url.split("?")[0].strip('/')
    except:
        current_url = "http://localhost:8501"
        
    target_url = f"{current_url}/?mode=register"
    st.info(f"🔗 ลิงก์สำหรับสแกน: `{target_url}`")
    
    qr_img = make_qr(target_url)
    st.image(qr_img, caption=f"สแกนเพื่อลงทะเบียนแจ้งซ่อม {shop_info['shop_name']}", width=300)
    st.success("✅ สร้าง QR Code สำเร็จ! คลิกขวาที่รูปเพื่อบันทึกไปปริ้นท์ใช้งานได้เลยครับ")

# ----------------------------------------------------
# 6. สต็อกสินค้า & Serial Number (S/N)
# ----------------------------------------------------
elif menu == "📦 สต็อกสินค้า & Serial Number (S/N)":
    st.subheader("📦 จัดการสต็อกสินค้าและติดตาม Serial Number (S/N)")
    
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    
    with st.expander("➕ นำเข้าสินค้าใหม่ / อะไหล่เข้าระบบ"):
        with st.form("add_stock"):
            code = st.text_input("รหัสสินค้า (Code)")
            name = st.text_input("ชื่อสินค้า / อะไหล่")
            serial_no = st.text_input("Serial Number (ถ้ามี)", value="N/A")
            category = st.selectbox("หมวดหมู่", ["อะไหล่", "อุปกรณ์เสริม", "คอมพิวเตอร์ประกอบ"])
            buy_price = st.number_input("ราคาทุนซื้อเข้า (บาท)", min_value=0.0, value=100.0)
            sell_price = st.number_input("ราคาขายออก (บาท)", min_value=0.0, value=200.0)
            qty = st.number_input("จำนวน", min_value=1, value=1)
            
            if st.form_submit_button("บันทึกนำเข้าสต็อก"):
                cursor.execute("INSERT INTO inventory (code, name, serial_no, category, buy_price, sell_price, qty, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'In Stock')",
                               (code, name, serial_no, category, buy_price, sell_price, qty))
                conn.commit()
                st.success("นำเข้าสินค้าและ S/N สำเร็จ!")
                st.rerun()

# ----------------------------------------------------
# 7. ระบบเคลมสินค้า (Claims)
# ----------------------------------------------------
elif menu == "🔄 ระบบเคลมสินค้า (Claims)":
    st.subheader("🔄 ระบบรับเคลมสินค้าและอุปกรณ์จากลูกค้า")
    
    with st.form("claim_form"):
        cust = st.text_input("ชื่อลูกค้า / ตัวแทนจำหน่าย")
        item = st.text_input("ชื่อสินค้าที่ส่งเคลม")
        sn = st.text_input("Serial Number (S/N) สินค้าเคลม")
        issue = st.text_area("อาการเสียที่ส่งเคลม")
        
        if st.form_submit_button("บันทึกรับเคลม"):
            claim_no = f"CLM-{datetime.now().strftime('%y%m%d')}-{str(pd.read_sql('SELECT COUNT(*) FROM claims', conn).iloc[0,0]+1).zfill(3)}"
            cursor.execute("INSERT INTO claims (claim_no, date, customer, item, serial_no, issue, status) VALUES (?, ?, ?, ?, ?, ?, 'รอส่งเคลม Supplier')",
                           (claim_no, datetime.now().strftime("%Y-%m-%d"), cust, item, sn, issue))
            conn.commit()
            st.success(f"บันทึกใบเคลมสำเร็จ! เลขที่เคลม: {claim_no}")
            
    st.markdown("### 📋 รายการสินค้าเคลมทั้งหมดในระบบ")
    claims_df = pd.read_sql("SELECT * FROM claims", conn)
    if not claims_df.empty:
        st.dataframe(claims_df, use_container_width=True)
    else:
        st.info("ยังไม่มีรายการเคลมสินค้า")

# ----------------------------------------------------
# 8. ระบบขายหน้าร้าน (POS)
# ----------------------------------------------------
elif menu == "🛒 ระบบขายหน้าร้าน (POS)":
    st.subheader("🛒 ระบบขายหน้าร้าน & ตัดสต็อกอัตโนมัติ")
    
    stock_df = pd.read_sql("SELECT * FROM inventory WHERE qty > 0", conn)
    if not stock_df.empty:
        with st.form("pos_form"):
            customer = st.text_input("ชื่อลูกค้า", value="ลูกค้าทั่วไป")
            selected_item = st.selectbox("เลือกสินค้าจากสต็อก", stock_df['name'].tolist())
            
            row = stock_df[stock_df['name'] == selected_item].iloc[0]
            max_q = int(row['qty'])
            sell_p = float(row['sell_price'])
            buy_p = float(row['buy_price'])
            
            qty = st.number_input("จำนวน", min_value=1, max_value=max_q, value=1)
            total = sell_p * qty
            profit = (sell_p - buy_p) * qty
            
            payment = st.selectbox("ช่องทางชำระเงิน", ["เงินสด", "QR Code โอนเงิน", "บัตรเครดิต"])
            
            if st.form_submit_button("💳 ยืนยันการขาย & ออกใบเสร็จ"):
                cursor.execute("UPDATE inventory SET qty = qty - ? WHERE id = ?", (qty, int(row['id'])))
                sale_no = f"POS-{datetime.now().strftime('%y%m%d%H%M')}"
                cursor.execute("INSERT INTO sales (sale_no, date, customer, item, qty, total, profit, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (sale_no, datetime.now().strftime("%Y-%m-%d %H:%M"), customer, selected_item, qty, total, profit, payment))
                conn.commit()
                st.success("ขายสินค้าสำเร็จ! ตัดสต็อกอัตโนมัติเรียบร้อย")
                st.code(f"""
========================================
       {shop_info['shop_name']}       
========================================
เลขที่: {sale_no} | วันที่: {datetime.now().strftime('%Y-%m-%d %H:%M')}
ลูกค้า: {customer}
----------------------------------------
รายการ: {selected_item} x {qty}
ยอดรวมสุทธิ: {total:,.2f} บาท
ชำระผ่าน: {payment}
========================================
    {shop_info['footer_message']}
                """, language="text")
    else:
        st.warning("สินค้าในสต็อกหมดเกลี้ยง")

# ----------------------------------------------------
# 9. งานบัญชี & ลูกหนี้คงค้าง
# ----------------------------------------------------
elif menu == "💰 งานบัญชี & ลูกหนี้คงค้าง":
    st.subheader("💰 ตรวจสอบลูกหนี้คงค้างและรายรับ")
    debtors_df = pd.read_sql("SELECT job_no, date, customer, phone, total_price, payment_status FROM repairs WHERE payment_status = 'ค้างชำระ (ลูกหนี้)'", conn)
    
    if not debtors_df.empty:
        st.dataframe(debtors_df, use_container_width=True)
        st.metric("ยอดลูกหนี้คงค้างรวม", f"{debtors_df['total_price'].sum():,.2f} บาท")
        
        pay_job = st.selectbox("เลือกใบงานที่ลูกหนี้มาชำระเงิน", debtors_df['job_no'].tolist())
        if st.button("บันทึกรับชำระเงินหนี้"):
            cursor.execute("UPDATE repairs SET payment_status = 'ชำระแล้ว (เงินสด/โอน)' WHERE job_no = ?", (pay_job,))
            conn.commit()
            st.success("บันทึกรับชำระเงินเรียบร้อย ยอดลูกหนี้ถูกเคลียร์แล้ว")
            st.rerun()
    else:
        st.success("ยอดเยี่ยม! ไม่มีลูกหนี้คงค้างในระบบขณะนี้")

# ----------------------------------------------------
# 10. รายงานสรุปผล (Reports)
# ----------------------------------------------------
elif menu == "📊 รายงานสรุปผล (Reports)":
    st.subheader("📊 รายงานสรุปยอดขาย กำไร และงานซ่อม")
    
    r_tab1, r_tab2, r_tab3 = st.tabs(["รายงานยอดขาย POS", "รายงานกำไรงานซ่อม", "รายงานสต็อกสินค้า"])
    
    with r_tab1:
        sales_data = pd.read_sql("SELECT * FROM sales", conn)
        if not sales_data.empty:
            st.dataframe(sales_data, use_container_width=True)
            st.metric("ยอดขายหน้าร้านรวม", f"{sales_data['total'].sum():,.2f} บาท")
            st.metric("กำไรขายหน้าร้านรวม", f"{sales_data['profit'].sum():,.2f} บาท")
        else:
            st.info("ยังไม่มีข้อมูลการขาย")
            
    with r_tab2:
        repair_data = pd.read_sql("SELECT job_no, date, customer, device_model, total_price, technician FROM repairs", conn)
        if not repair_data.empty:
            st.dataframe(repair_data, use_container_width=True)
            st.metric("รายได้จากงานซ่อมรวม", f"{repair_data['total_price'].sum():,.2f} บาท")
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อม")
            
    with r_tab3:
        st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ----------------------------------------------------
# 11. Audit Log
# ----------------------------------------------------
elif menu == "📋 ตรวจสอบการเข้าใช้งาน (Audit Log)":
    st.subheader("📋 ประวัติการใช้งานระบบ (Audit Log)")
    logs_df = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", conn)
    st.dataframe(logs_df, use_container_width=True)