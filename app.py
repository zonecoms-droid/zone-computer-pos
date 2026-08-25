import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import random

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ZoneOnline Service - Pro Edition", 
    page_icon="⚡", 
    layout="wide"
)

# ฟังก์ชันเชื่อมต่อฐานข้อมูล PostgreSQL
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
    st.error(f"⚠️ เชื่อมต่อฐานข้อมูลไม่สำเร็จ: {e}")

st.title("⚡ ZoneOnline Service System [Pro Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (ระดับโปร)")

# เมนูด้านข้าง (Sidebar)
menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", [
    "📥 รับเครื่องซ่อมใหม่ (Pro Intake)", 
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง"
])

# ==========================================
# 1. ระบบรับเครื่องซ่อมใหม่ (Pro Intake)
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่ (Pro Intake)":
    st.header("📥 บันทึกรับเครื่องซ่อมและมอบหมายงานช่าง")
    
    with st.form("pro_repair_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("ข้อมูลลูกค้า")
            customer_name = st.text_input("ชื่อ-นามสกุล ลูกค้า")
            phone = st.text_input("เบอร์โทรศัพท์ (ใช้เป็น Key หลัก)")
            address = st.text_area("ที่อยู่ลูกค้า (ถ้ามี)")
            
        with col2:
            st.subheader("ข้อมูลอุปกรณ์ & การซ่อม")
            device_name = st.text_input("รุ่นอุปกรณ์ (เช่น Notebook ASUS ROG / Monitor MSI)")
            serial_number = st.text_input("Serial Number (สำหรับเช็คประกัน)")
            accessories = st.text_input("อุปกรณ์ที่แนบมา (เช่น สายชาร์จ, กระเป๋า, เมาส์)")
            
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            problem_description = st.text_area("อาการเสีย / รายละเอียดจากปากลูกค้า")
            estimated_cost = st.number_input("ประเมินราคาค่าซ่อมเบื้องต้น (บาท)", min_value=0.0, step=100.0)
            
        with col4:
            # ดึงรายชื่อช่างจากฐานข้อมูลมาแสดงใน Dropdown
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, full_name FROM staff WHERE role = 'technician'")
                techs = cursor.fetchall()
                cursor.close()
                tech_dict = {t[1]: t[0] for t in techs} if techs else {"ยังไม่มีช่างในระบบ": 0}
            except:
                tech_dict = {"เชื่อมต่อฐานข้อมูลก่อน": 0}
                
            selected_tech_name = st.selectbox("มอบหมายให้ช่างผู้รับผิดชอบ", list(tech_dict.keys()))
            technician_id = tech_dict[selected_tech_name]
            
            commission = st.number_input("ค่ามือ / คอมมิชชั่นช่างงานนี้ (บาท)", min_value=0.0, step=50.0)

        submit_btn = st.form_submit_button("🚀 บันทึกรับเครื่องเข้าสู่ระบบ")
        
        if submit_btn:
            if customer_name and phone and device_name:
                try:
                    cursor = conn.cursor()
                    
                    # บันทึกหรืออัปเดตข้อมูลลูกค้า
                    cursor.execute("""
                        INSERT INTO customers (name, phone, address) 
                        VALUES (%s, %s, %s) 
                        ON CONFLICT (phone) DO UPDATE SET name = EXCLUDED.name, address = EXCLUDED.address 
                        RETURNING id;
                    """, (customer_name, phone, address))
                    customer_id = cursor.fetchone()[0]
                    
                    # สร้างรหัสใบงานอัตโนมัติ
                    job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                    
                    # บันทึกงานซ่อมลงตาราง repairs (สมมติว่าตารางรองรับฟิลด์เสริมแล้ว)
                    cursor.execute("""
                        INSERT INTO repairs (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'RECEIVED')
                    """, (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id))
                    
                    conn.commit()
                    cursor.close()
                    
                    st.success(f"🎉 บันทึกรับเครื่องสำเร็จ! เลขที่ใบงานสำหรับให้ลูกค้าเช็คสถานะ: **{job_code}**")
                    st.balloons()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญ (ชื่อลูกค้า, เบอร์โทร, รุ่นอุปกรณ์) ให้ครบถ้วน")

# ==========================================
# 2. ระบบติดตาม & อัปเดตสถานะงานซ่อม
# ==========================================
elif menu == "🔍 ติดตาม & อัปเดตสถานะงานซ่อม":
    st.header("🔍 ค้นหา จัดการ และอัปเดตสถานะงานซ่อม")
    
    search_query = st.text_input("🔍 ค้นหาด้วยเลขใบงาน, เบอร์โทร หรือชื่อลูกค้า")
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT r.id, r.job_code, c.name as customer_name, c.phone, r.device_name, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
        """
        if search_query:
            query += f" WHERE r.job_code ILIKE '%{search_query}%' OR c.phone ILIKE '%{search_query}%' OR c.name ILIKE '%{search_query}%'"
        query += " ORDER BY r.created_at DESC;"
        
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🛠️ อัปเดตสถานะงานซ่อม")
            selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการเปลี่ยนสถานะ", df['job_code'].tolist())
            
            new_status = st.selectbox("เปลี่ยนสถานะเป็น", [
                "RECEIVED (รับเครื่องเข้า)", 
                "CHECKING (กำลังตรวจสอบอาการ)", 
                "WAITING_PART (รออะไหล่/ตีราคา)", 
                "REPAIRING (กำลังดำเนินการซ่อม)", 
                "COMPLETED (ซ่อมเสร็จสิ้น พร้อมส่งมอบ)", 
                "CANCELLED (ยกเลิกการซ่อม)"
            ])
            
            if st.button("💾 บันทึกการเปลี่ยนสถานะ"):
                status_code = new_status.split(" ")[0]
                cursor.execute("UPDATE repairs SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE job_code = %s", (status_code, selected_job))
                conn.commit()
                st.success(f"อัปเดตสถานะใบงาน {selected_job} เป็น {status_code} เรียบร้อยแล้ว!")
                st.rerun()
        else:
            st.info("ไม่พบข้อมูลงานซ่อมในระบบ")
        cursor.close()
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")

# ==========================================
# 3. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number ของสินค้า/อะไหล่")
    
    if sn_input:
        # จำลองการเช็ค Serial Number จากฐานข้อมูลสินค้าหรือประวัติการซ่อม
        st.info(f"กำลังตรวจสอบข้อมูล Serial Number: **{sn_input}** ...")
        # ตรงนี้เพื่อนสามารถเขียน Query ดึงข้อมูลจากตาราง Products หรือประวัติการขาย/ซ่อมมาเทียบได้เลย
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน! (ซื้อเมื่อ: 15 มกราคม 2026 / ประกันหมดอายุ: 15 มกราคม 2027)")

# ==========================================
# 4. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
    st.info("ส่วนแสดงกราฟสรุปรายได้และคอมมิชชั่นช่างรายบุคคล เพื่อช่วยตัดรอบจ่ายเงินเดือนได้อย่างแม่นยำ")