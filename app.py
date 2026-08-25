import streamlit as st
import pandas as pd
import psycopg2

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ZoneOnline Service System", page_icon="💻", layout="wide")

# ฟังก์ชันเชื่อมต่อ PostgreSQL (ดึงค่าจาก Streamlit Secrets)
def init_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )

try:
    conn = init_connection()
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลไม่สำเร็จ: {e}")

st.title("💻 ZoneOnline Service - ระบบบริหารจัดการร้านคอมพิวเตอร์")

# เมนูด้านข้าง (Sidebar)
menu = st.sidebar.selectbox("เลือกเมนูการทำงาน", ["📥 รับเครื่องซ่อมใหม่", "🔍 ติดตาม/อัปเดตสถานะงานซ่อม", "📦 จัดการสต็อกสินค้า"])

if menu == "📥 รับเครื่องซ่อมใหม่":
    st.header("บันทึกรับเครื่องซ่อม")
    
    with st.form("repair_form"):
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("ชื่อลูกค้า")
            phone = st.text_input("เบอร์โทรศัพท์")
            device_name = st.text_input("ชื่อรุ่นอุปกรณ์ (เช่น Notebook ASUS ROG)")
        with col2:
            serial_number = st.text_input("Serial Number (ถ้ามี)")
            estimated_cost = st.number_input("ประเมินราคาเบื้องต้น (บาท)", min_value=0.0, step=100.0)
            accessories = st.text_input("อุปกรณ์ที่แนบมา (เช่น สายชาร์จ, กระเป๋า)")
        
        problem_description = st.text_area("อาการเสีย / รายละเอียดงานซ่อม")
        
        submit_btn = st.form_submit_button("บันทึกข้อมูลรับเครื่อง")
        
        if submit_btn:
            if customer_name and phone and device_name:
                try:
                    cursor = conn.cursor()
                    # 1. บันทึกข้อมูลลูกค้า หรือดึง ID ถ้ามีเบอร์โทรนี้แล้ว
                    cursor.execute("INSERT INTO customers (name, phone) VALUES (%s, %s) ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name RETURNING id;", (customer_name, phone))
                    customer_id = cursor.fetchone()[0]
                    
                    # 2. สร้างเลขใบงาน
                    import random
                    from datetime import datetime
                    job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                    
                    # 3. บันทึกงานซ่อม
                    cursor.execute("""
                        INSERT INTO repairs (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'RECEIVED')
                    """, (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost))
                    
                    conn.commit()
                    cursor.close()
                    st.success(f"บันทึกสำเร็จ! เลขที่ใบงาน: **{job_code}**")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("กรุณากรอกข้อมูลสำคัญให้ครบถ้วน (ชื่อ, เบอร์โทร, รุ่นอุปกรณ์)")

elif menu == "🔍 ติดตาม/อัปเดตสถานะงานซ่อม":
    st.header("ติดตามและอัปเดตสถานะงานซ่อม")
    
    try:
        query = """
            SELECT r.job_code, c.name as customer_name, r.device_name, r.problem_description, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
            ORDER BY r.created_at DESC;
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")
            
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")

elif menu == "📦 จัดการสต็อกสินค้า":
    st.header("คลังสินค้าและอะไหล่")
    st.info("ส่วนจัดการสต็อกสินค้ากำลังพัฒนา สามารถเชื่อมต่อเพิ่มได้ที่นี่ครับ")