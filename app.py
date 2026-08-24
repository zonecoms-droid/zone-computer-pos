import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(
    page_title="ระบบแจ้งซ่อม (Repair Management System)",
    layout="wide",
    page_icon="🛠️"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
        background-color: #F3F4F6;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #172554 100%);
        color: white;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #3B82F6;
        text-align: center;
    }
    
    .badge-pending { background-color: #FEF3C7; color: #D97706; padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; }
    .badge-approve { background-color: #DBEAFE; color: #1E40AF; padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; }
    .badge-progress { background-color: #E0E7FF; color: #4338CA; padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; }
    .badge-success { background-color: #D1FAE5; color: #065F46; padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; }
    .badge-cancel { background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 20px; font-weight: 500; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE SETUP (SQLite) ---
def init_db():
    conn = sqlite3.connect('repair_system.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Table 1: Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            fullname TEXT,
            role TEXT,
            department TEXT
        )
    ''')
    
    # Table 2: Categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            color TEXT,
            icon TEXT
        )
    ''')
    
    # Table 3: Repairs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            running_no TEXT,
            date TEXT,
            issue TEXT,
            category TEXT,
            location TEXT,
            details TEXT,
            files TEXT,
            reporter TEXT,
            status TEXT,
            parts_fee REAL,
            labor_fee REAL,
            total_price REAL,
            technician TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# Seed default data if empty
cursor.execute('SELECT COUNT(*) FROM users')
if cursor.fetchone()[0] == 0:
    default_users = [
        ('admin', '1234', 'ผู้ดูแลระบบ ระบบ (Admin)', 'Admin', 'ศูนย์คอมพิวเตอร์'),
        ('officer', '1234', 'เจ้าหน้าที่ พัสดุ (Officer)', 'Officer', 'งานพัสดุและซ่อมบำรุง'),
        ('tech', '1234', 'ช่าง สมชาย (Technician)', 'Technician', 'ฝ่ายช่างเทคนิค'),
        ('director', '1234', 'ผอ. สมเกียรติ (Director)', 'Director', 'ฝ่ายบริหาร'),
        ('user', '1234', 'พนักงาน ทั่วไป (Reporter)', 'Reporter', 'ฝ่ายบัญชี')
    ]
    cursor.executemany("INSERT INTO users (username, password, fullname, role, department) VALUES (?, ?, ?, ?, ?)", default_users)
    conn.commit()

cursor.execute('SELECT COUNT(*) FROM categories')
if cursor.fetchone()[0] == 0:
    default_cats = [
        ('1. คอมพิวเตอร์/โน้ตบุ๊ก', '#3B82F6', 'fas fa-laptop'),
        ('2. เครื่องพิมพ์ (Printer)', '#10B981', 'fas fa-print'),
        ('3. เครือข่าย/อินเทอร์เน็ต (Network)', '#F59E0B', 'fas fa-wifi'),
        ('4. อุปกรณ์สำนักงานอื่นๆ', '#EF4444', 'fas fa-tools')
    ]
    cursor.executemany("INSERT INTO categories (name, color, icon) VALUES (?, ?, ?)", default_cats)
    conn.commit()

# --- 3. AUTHENTICATION (LOGIN STATE) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div class='main-header' style='text-align: center;'>
                <h2>🛠️ เข้าสู่ระบบแจ้งซ่อม</h2>
                <p>Repair Management System (SPA)</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submit = st.form_submit_button("🔑 เข้าสู่ระบบ", use_container_width=True)
            
            if submit:
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user_data = cursor.fetchone()
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user = {
                        "id": user_data[0],
                        "username": user_data[1],
                        "fullname": user_data[3],
                        "role": user_data[4],
                        "department": user_data[5]
                    }
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
                    
        st.info("💡 **บัญชีทดสอบระบบ:**\n- Admin: `admin` / `1234`\n- Officer: `officer` / `1234`\n- User: `user` / `1234`\n- Technician: `tech` / `1234`")
    st.stop()

# --- 4. MAIN SPA INTERFACE (LOGGED IN) ---
current_user = st.session_state.user

# Header & Profile Bar
st.markdown(f"""
    <div class='main-header' style='display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h2>🛠️ ระบบบริหารจัดการงานแจ้งซ่อม</h2>
            <p>ยินดีต้อนรับคุณ <b>{current_user['fullname']}</b> | สิทธิ์ผู้ใช้งาน: <b>{current_user['role']}</b> ({current_user['department']})</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Logout Button in Sidebar
with st.sidebar:
    st.markdown(f"### 👤 บัญชีผู้ใช้")
    st.write(f"**ชื่อ:** {current_user['fullname']}")
    st.write(f"**บทบาท:** {current_user['role']}")
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    st.markdown("---")
    st.markdown("### 📌 เมนูนำทาง")

# --- 5. ROLE-BASED NAVIGATION ---
role = current_user['role']

if role in ['Admin', 'Officer']:
    menu = st.sidebar.radio("เลือกเมนู", ["📊 แดชบอร์ด (Dashboard)", "👥 จัดการผู้ใช้งาน (Users)", "📂 จัดการหมวดหมู่ (Categories)", "📋 รายการแจ้งซ่อมทั้งหมด (All Repairs)"])
    
    # ----------------------------------------------------
    # 5.1 ADMIN / OFFICER DASHBOARD
    # ----------------------------------------------------
    if menu == "📊 แดชบอร์ด (Dashboard)":
        st.subheader("📊 สรุปภาพรวมสถานะงานซ่อม")
        
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        total_all = len(repairs_df)
        waiting_assess = len(repairs_df[repairs_df['status'] == 'รอประเมิน']) if total_all > 0 else 0
        waiting_approve = len(repairs_df[repairs_df['status'] == 'รออนุมัติ']) if total_all > 0 else 0
        in_progress = len(repairs_df[repairs_df['status'] == 'กำลังซ่อม']) if total_all > 0 else 0
        completed = len(repairs_df[repairs_df['status'] == 'เสร็จสิ้น']) if total_all > 0 else 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("ทั้งหมด", f"{total_all} รายการ")
        col2.metric("รอประเมิน", f"{waiting_assess} รายการ")
        col3.metric("รออนุมัติ", f"{waiting_approve} รายการ")
        col4.metric("กำลังซ่อม", f"{in_progress} รายการ")
        col5.metric("เสร็จสิ้น", f"{completed} รายการ")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🍩 สัดส่วนงานซ่อมแยกตามหมวดหมู่")
            if not repairs_df.empty:
                cat_counts = repairs_df['category'].value_counts()
                st.bar_chart(cat_counts)
            else:
                st.info("ยังไม่มีข้อมูลสถิติ")
        with c2:
            st.markdown("#### 📈 สถิติจำนวนงานซ่อมย้อนหลัง")
            if not repairs_df.empty:
                repairs_df['month'] = pd.to_datetime(repairs_df['date']).dt.strftime('%Y-%m')
                month_counts = repairs_df['month'].value_counts().sort_index()
                st.line_chart(month_counts)
            else:
                st.info("ยังไม่มีข้อมูลสถิติเชิงเวลา")

    # ----------------------------------------------------
    # 5.2 USER MANAGEMENT
    # ----------------------------------------------------
    elif menu == "👥 จัดการผู้ใช้งาน (Users)":
        st.subheader("👥 ระบบจัดการข้อมูลผู้ใช้งาน")
        
        with st.expander("➕ เพิ่มผู้ใช้งานใหม่"):
            with st.form("add_user_form"):
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                new_name = st.text_input("ชื่อ-นามสกุล")
                new_role = st.selectbox("บทบาท (Role)", ["Admin", "Officer", "Technician", "Director", "Reporter"])
                new_dept = st.text_input("หน่วยงาน / แผนก")
                submit_user = st.form_submit_button("บันทึกผู้ใช้ใหม่")
                
                if submit_user and new_user and new_name:
                    try:
                        cursor.execute("INSERT INTO users (username, password, fullname, role, department) VALUES (?, ?, ?, ?, ?)",
                                       (new_user, new_pass, new_name, new_role, new_dept))
                        conn.commit()
                        st.success("เพิ่มผู้ใช้สำเร็จ!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
                        
        users_df = pd.read_sql("SELECT id, username, fullname, role, department FROM users", conn)
        st.dataframe(users_df, use_container_width=True)

    # ----------------------------------------------------
    # 5.3 CATEGORIES MANAGEMENT
    # ----------------------------------------------------
    elif menu == "📂 จัดการหมวดหมู่งาน (Categories)":
        st.subheader("📂 จัดการหมวดหมู่งานแจ้งซ่อม")
        
        with st.expander("➕ เพิ่มหมวดหมู่ใหม่"):
            with st.form("add_cat_form"):
                cat_name = st.text_input("ชื่อหมวดหมู่")
                cat_color = st.color_picker("เลือกสีป้ายกำกับ", "#3B82F6")
                cat_icon = st.text_input("FontAwesome Icon Class (เช่น fas fa-laptop)", "fas fa-tools")
                submit_cat = st.form_submit_button("บันทึกหมวดหมู่")
                
                if submit_cat and cat_name:
                    try:
                        cursor.execute("INSERT INTO categories (name, color, icon) VALUES (?, ?, ?)", (cat_name, cat_color, cat_icon))
                        conn.commit()
                        st.success("เพิ่มหมวดหมู่สำเร็จ!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
                        
        cat_df = pd.read_sql("SELECT * FROM categories", conn)
        st.dataframe(cat_df, use_container_width=True)

    # ----------------------------------------------------
    # 5.4 ALL REPAIRS MANAGEMENT
    # ----------------------------------------------------
    elif menu == "📋 รายการแจ้งซ่อมทั้งหมด (All Repairs)":
        st.subheader("📋 รายการแจ้งซ่อมทั้งหมดในระบบ")
        
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        
        if not repairs_df.empty:
            # Filters
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                search_query = st.text_input("🔍 ค้นหา (เลขที่/อาการ/ผู้แจ้ง)")
            with col_f2:
                status_filter = st.selectbox("📌 กรองตามสถานะ", ["ทั้งหมด", "รอประเมิน", "รออนุมัติ", "กำลังซ่อม", "เสร็จสิ้น", "ยกเลิก"])
            with col_f3:
                cats = ["ทั้งหมด"] + list(pd.read_sql("SELECT name FROM categories", conn)['name'])
                cat_filter = st.selectbox("📂 กรองตามหมวดหมู่", cats)
                
            filtered_df = repairs_df.copy()
            if search_query:
                filtered_df = filtered_df[filtered_df['issue'].str.contains(search_query, na=False) | filtered_df['running_no'].str.contains(search_query, na=False) | filtered_df['reporter'].str.contains(search_query, na=False)]
            if status_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
            if cat_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['category'] == cat_filter]
                
            st.dataframe(filtered_df[['running_no', 'date', 'issue', 'category', 'location', 'status', 'reporter', 'total_price']], use_container_width=True)
            
            st.markdown("---")
            st.markdown("### ⚙️ ดำเนินการอัปเดตสถานะและบันทึกค่าใช้จ่าย")
            repair_ids = filtered_df['id'].tolist()
            if repair_ids:
                selected_id = st.selectbox("เลือกรหัสแจ้งซ่อม (ID)", repair_ids)
                selected_row = filtered_df[filtered_df['id'] == selected_id].iloc[0]
                
                st.info(f"**เลขที่:** {selected_row['running_no']} | **อาการ:** {selected_row['issue']} | **สถานที่:** {selected_row['location']}")
                
                with st.form("update_repair_form"):
                    new_status = st.selectbox("เปลี่ยนสถานะ", ["รอประเมิน", "รออนุมัติ", "กำลังซ่อม", "เสร็จสิ้น", "ยกเลิก"], index=["รอประเมิน", "รออนุมัติ", "กำลังซ่อม", "เสร็จสิ้น", "ยกเลิก"].index(selected_row['status']) if selected_row['status'] in ["รอประเมิน", "รออนุมัติ", "กำลังซ่อม", "เสร็จสิ้น", "ยกเลิก"] else 0)
                    parts_fee = st.number_input("ค่าอะไหล่ (บาท)", min_value=0.0, value=float(selected_row['parts_fee'] if selected_row['parts_fee'] else 0))
                    labor_fee = st.number_input("ค่าบริการ/ค่าแรง (บาท)", min_value=0.0, value=float(selected_row['labor_fee'] if selected_row['labor_fee'] else 0))
                    technician = st.text_input("ช่างผู้รับผิดชอบ", value=str(selected_row['technician'] if selected_row['technician'] else ''))
                    
                    submit_update = st.form_submit_button("💾 บันทึกการเปลี่ยนแปลง")
                    if submit_update:
                        total_price = parts_fee + labor_fee
                        cursor.execute("UPDATE repairs SET status = ?, parts_fee = ?, labor_fee = ?, total_price = ?, technician = ? WHERE id = ?",
                                       (new_status, parts_fee, labor_fee, total_price, technician, selected_id))
                        conn.commit()
                        st.success("อัปเดตสถานะและค่าใช้จ่ายเรียบร้อยแล้ว!")
                        st.rerun()
        else:
            st.info("ยังไม่มีรายการแจ้งซ่อมในระบบ")

elif role in ['Reporter', 'User']:
    menu = st.sidebar.radio("เลือกเมนู", ["📊 แดชบอร์ดของฉัน (Dashboard)", "➕ แจ้งซ่อมใหม่ (New Request)", "📂 ติดตามสถานะ (My Repairs)"])
    
    # ----------------------------------------------------
    # 5.5 USER DASHBOARD & REQUEST PORTAL
    # ----------------------------------------------------
    if menu == "📊 แดชบอร์ดของฉัน (Dashboard)":
        st.subheader("📊 แดชบอร์ดสรุปรายการแจ้งซ่อมของคุณ")
        my_repairs = pd.read_sql(f"SELECT * FROM repairs WHERE reporter = '{current_user['fullname']}'", conn)
        
        t_all = len(my_repairs)
        t_prog = len(my_repairs[my_repairs['status'].isin(['รอประเมิน', 'รออนุมัติ', 'กำลังซ่อม'])]) if t_all > 0 else 0
        t_done = len(my_repairs[my_repairs['status'] == 'เสร็จสิ้น']) if t_all > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("แจ้งซ่อมทั้งหมดของฉัน", f"{t_all} รายการ")
        c2.metric("กำลังดำเนินการ", f"{t_prog} รายการ")
        c3.metric("เสร็จสิ้นแล้ว", f"{t_done} รายการ")
        
        st.markdown("---")
        st.markdown("### 📋 รายการล่าสุดของคุณ")
        if not my_repairs.empty:
            st.dataframe(my_repairs[['running_no', 'date', 'issue', 'category', 'status']], use_container_width=True)
        else:
            st.info("คุณยังไม่เคยมีรายการแจ้งซ่อม")

    elif menu == "➕ แจ้งซ่อมใหม่ (New Request)":
        st.subheader("➕ ฟอร์มบันทึกแจ้งซ่อมใหม่")
        
        cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
        
        with st.form("new_request_form"):
            issue = st.text_input("อาการ / ปัญหาที่พบ (หัวข้อสั้นๆ)")
            category = st.selectbox("หมวดหมู่งานซ่อม", cats)
            location = st.text_input("สถานที่ / ห้อง / อาคาร")
            details = st.text_area("รายละเอียดเพิ่มเติม / อาการเสียโดยละเอียด")
            uploaded_files = st.file_uploader("อัพโหลดรูปภาพประกอบ (ก่อนซ่อม)", accept_multiple_files=True)
            
            submit_req = st.form_submit_button("📤 ส่งใบแจ้งซ่อม")
            
            if submit_req:
                if issue and location:
                    # Generate Running Number (e.g., RE-69/001)
                    cursor.execute("SELECT COUNT(*) FROM repairs")
                    count = cursor.fetchone()[0] + 1
                    year_code = datetime.now().year + 543 - 2500 # พ.ศ. สองตัวท้าย
                    running_no = f"RE-{year_code}/{str(count).zfill(3)}"
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    file_names = ", ".join([f.name for f in uploaded_files]) if uploaded_files else "ไม่มีไฟล์แนบ"
                    
                    cursor.execute("""
                        INSERT INTO repairs (running_no, date, issue, category, location, details, files, reporter, status, parts_fee, labor_fee, total_price, technician)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'รอมอบหมาย')
                    """, (running_no, date_str, issue, category, location, details, file_names, current_user['fullname'], 'รอประเมิน'))
                    conn.commit()
                    st.success(f"🎉 ส่งใบแจ้งซ่อมสำเร็จ! เลขที่ใบแจ้งซ่อมของคุณคือ: **{running_no}**")
                else:
                    st.error("กรุณากรอกอาการและสถานที่ให้ครบถ้วน")

    elif menu == "📂 ติดตามสถานะ (My Repairs)":
        st.subheader("📂 ติดตามสถานะงานแจ้งซ่อมของคุณ")
        my_repairs = pd.read_sql(f"SELECT * FROM repairs WHERE reporter = '{current_user['fullname']}'", conn)
        
        if not my_repairs.empty:
            st.dataframe(my_repairs[['running_no', 'date', 'issue', 'category', 'status', 'total_price', 'technician']], use_container_width=True)
            
            # Cancel option for pending items
            pending_items = my_repairs[my_repairs['status'] == 'รอประเมิน']
            if not pending_items.empty:
                st.markdown("---")
                st.markdown("### ❌ ยกเลิกคำขอแจ้งซ่อม (เฉพาะสถานะรอประเมิน)")
                cancel_id = st.selectbox("เลือกเลขที่ใบแจ้งซ่อมที่ต้องการยกเลิก", pending_items['id'].tolist())
                if st.button("ยืนยันยกเลิกคำขอ"):
                    cursor.execute("UPDATE repairs SET status = 'ยกเลิก' WHERE id = ?", (cancel_id,))
                    conn.commit()
                    st.warning("ยกเลิกคำขอเรียบร้อยแล้ว")
                    st.rerun()
        else:
            st.info("ยังไม่มีประวัติการแจ้งซ่อมของคุณ")

elif role in ['Technician', 'Director']:
    menu = st.sidebar.radio("เลือกเมนู", ["📋 รายการงานซ่อมทั้งหมด", "📊 รายงานสรุปภาพรวม"])
    
    if menu == "📋 รายการงานซ่อมทั้งหมด":
        st.subheader("📋 รายการงานซ่อมในระบบ")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df[['running_no', 'date', 'issue', 'category', 'location', 'status', 'technician', 'total_price']], use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อม")
    elif menu == "📊 รายงานสรุปภาพรวม":
        st.subheader("📊 รายงานสรุปผู้บริหารและช่างเทคนิค")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        total = len(repairs_df)
        done = len(repairs_df[repairs_df['status'] == 'เสร็จสิ้น']) if total > 0 else 0
        total_cost = repairs_df['total_price'].sum() if total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("งานทั้งหมด", f"{total} รายการ")
        c2.metric("ซ่อมเสร็จสิ้น", f"{done} รายการ")
        c3.metric("งบประมาณค่าใช้จ่ายรวม", f"{total_cost:,.2f} บาท")