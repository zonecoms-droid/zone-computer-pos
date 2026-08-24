import streamlit as st
import qrcode
import io
import datetime
import pandas as pd
import random
import string

# ตั้งค่าหน้าเว็บแอปพลิเคชัน
st.set_page_config(page_title="ServiceTicker Online - Ultimate", layout="wide", page_icon="💻")

# --- Initializing Session State ---
if 'repairs' not in st.session_state:
    st.session_state['repairs'] = []
if 'customers' not in st.session_state:
    st.session_state['customers'] = []
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = [
        {"id": "P001", "name": "แรม DDR4 8GB", "cost": 600, "price": 990, "unit": "ตัว", "supplier": "บิ๊กไอที ซัพพลาย", "stock": 10, "serial": "SN-884102", "is_intangible": False},
        {"id": "P002", "name": "SSD 240GB", "cost": 500, "price": 850, "unit": "ตัว", "supplier": "คอมพิวเตอร์โซน", "stock": 5, "serial": "SN-992311", "is_intangible": False}
    ]
if 'purchasing_cart' not in st.session_state:
    st.session_state['purchasing_cart'] = []
if 'sales' not in st.session_state:
    st.session_state['sales'] = []
if 'settings' not in st.session_state:
    st.session_state['settings'] = {
        "vat_rate": 7.0,
        "printer_width": "80 มม."
    }

# --- Helper Functions ---
def format_phone(phone_str):
    """จัดรูปแบบเบอร์โทรศัพท์อัตโนมัติให้มีขีด (เช่น 081-234-5678)"""
    digits = "".join(filter(str.isdigit, phone_str))
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    return phone_str

def generate_random_sn(prefix="SN"):
    """สุ่มหมายเลขและตัวอักษรสำหรับบาร์โค้ด SN เครื่องซ่อม"""
    chars = string.ascii_uppercase + string.digits
    rand_str = ''.join(random.choices(chars, k=8))
    return f"{prefix}-{rand_str}"

def calculate_vat(subtotal, vat_rate):
    """คำนวณภาษีมูลค่าเพิ่มตามมาตรฐาน (MindPHP VAT Standard Formula)"""
    vat_amount = subtotal * (vat_rate / 100)
    grand_total = subtotal + vat_amount
    return vat_amount, grand_total

# --- Sidebar: ล็อกอิน & เมนูหลัก ---
st.sidebar.header("🔐 ระบบล็อกอินผู้ใช้งาน")
tech_list = ["ช่างดิด", "ช่างเอ", "ช่างบี", "แอดมินหน้าร้าน"]
logged_in_user = st.sidebar.selectbox("เลือกชื่อช่าง / ผู้ใช้งาน", tech_list)

st.sidebar.divider()
menu = st.sidebar.radio(
    "📌 เมนูการทำงานระบบ",
    [
        "1. รับงานซ่อม & บันทึกลูกค้า",
        "2. เช็คสถานะ & เมนูจัดการ (คลิกขวา)",
        "3. จัดซื้อ & รับสินค้าเข้าระบบ",
        "4. คลังสินค้า & พิมพ์บาร์โค้ด SN",
        "5. ระบบขายสินค้า (POS) & ออกบิล",
        "6. รายงานและบัญชี",
        "7. ตั้งค่าโปรแกรม (ภาษี & เครื่องพิมพ์)"
    ]
)

# ==========================================
# 1. รับงานซ่อม & บันทึกลูกค้าอัตโนมัติ
# ==========================================
if menu == "1. รับงานซ่อม & บันทึกลูกค้า":
    st.title("🛠️ ระบบรับแจ้งซ่อมและสร้าง QR Code")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("repair_form"):
            st.subheader("กรอกข้อมูลเครื่องซ่อม")
            c_name = st.text_input("ชื่อลูกค้า")
            c_phone_raw = st.text_input("เบอร์โทรศัพท์ (ระบบจัดรูปแบบให้อัตโนมัติ)")
            c_address = st.text_area("ที่อยู่ลูกค้า")
            device_detail = st.text_input("รุ่นอุปกรณ์ / อาการเสีย")
            serial_no = st.text_input("Serial Number (S/N) อุปกรณ์ (เว้นว่างเพื่อสุ่ม SN)")
            deposit = st.number_input("เงินมัดจำ (บาท)", min_value=0.0, step=100.0)
            
            submitted = st.form_submit_button("บันทึกรับงานซ่อม")
            
            if submitted:
                if c_name and device_detail:
                    formatted_phone = format_phone(c_phone_raw)
                    # บันทึกข้อมูลลูกค้าใหม่ลงฐานข้อมูลลูกค้าอัตโนมัติเบื้องหลัง
                    new_customer = {
                        "name": c_name,
                        "phone": formatted_phone,
                        "address": c_address,
                        "registered_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state['customers'].append(new_customer)
                    
                    # ถ้าไม่มี SN มา ให้สุ่มสร้างบาร์โค้ด SN ชั่วคราวให้
                    final_sn = serial_no if serial_no else generate_random_sn("FIX")
                    
                    job_id = f"JOB-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    new_job = {
                        "job_id": job_id,
                        "customer": c_name,
                        "phone": formatted_phone,
                        "address": c_address,
                        "device": device_detail,
                        "serial": final_sn,
                        "deposit": deposit,
                        "technician": logged_in_user,
                        "status": "รอซ่อม",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state['repairs'].append(new_job)
                    st.success(f"บันทึกรับงานสำเร็จ! รหัสใบงาน: {job_id} | S/N: {final_sn}")
                else:
                    st.error("กรุณากรอกชื่อลูกค้าและอาการเสียให้ครบถ้วน")

    with col2:
        st.subheader("📲 QR Code ลงทะเบียน & สแกนจ่ายเงิน")
        qr_type = st.radio("เลือกประเภท QR Code", ["QR Code ลูกค้าลงทะเบียนเอง", "QR Code สแกนจ่ายเงิน (PromptPay)"])
        
        if st.session_state['repairs']:
            latest_job = st.session_state['repairs'][-1]
            if qr_type == "QR Code ลูกค้าลงทะเบียนเอง":
                qr_data = f"https://serviceticker-online.com/register?job={latest_job['job_id']}"
                st.info("สแกนเพื่อตรวจสอบสถานะหรือลงทะเบียนออนไลน์")
            else:
                qr_data = f"PromptPay: 081-234-5678 (ยอดชำระ/มัดจำ: {latest_job['deposit']} บาท)"
                st.info(f"สแกนชำระเงินมัดจำใบงาน {latest_job['job_id']} จำนวน {latest_job['deposit']:,.2f} บาท")
            
            img = qrcode.make(qr_data)
            buf = io.BytesIO()
            img.save(buf)
            st.image(buf.getvalue(), width=220)
        else:
            st.warning("ยังไม่มีใบงานในระบบ")

# ==========================================
# 2. เช็คสถานะ & เมนูจัดการ (คลิกขวาจำลอง)
# ==========================================
elif menu == "2. เช็คสถานะ & เมนูจัดการ (คลิกขวา)":
    st.title("📋 เช็คสถานะงานซ่อม และเมนูปฏิบัติการพิเศษ")
    
    # เพิ่มช่องค้นหางานซ่อม
    search_query = st.text_input("🔍 ค้นหางานซ่อม (พิมพ์ชื่อลูกค้า, เบอร์โทร, เลขใบงาน หรือ S/N)").strip().lower()
    
    filtered_jobs = []
    for j in st.session_state['repairs']:
        if (search_query in j['job_id'].lower() or 
            search_query in j['customer'].lower() or 
            search_query in j['phone'].lower() or 
            search_query in j['serial'].lower() or not search_query):
            filtered_jobs.append(j)

    if filtered_jobs:
        for i, job in enumerate(filtered_jobs):
            with st.expander(f"ใบงาน: {job['job_id']} | ลูกค้า: {job['customer']} | S/N: {job['serial']} | สถานะ: [{job['status']}]"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**อุปกรณ์:** {job['device']}")
                    st.write(f"**เบอร์โทร:** {job['phone']}")
                    st.write(f"**เงินมัดจำ:** {job['deposit']:,.2f} บาท")
                    st.write(f"**ช่างรับผิดชอบ:** {job['technician']}")
                    
                    new_status = st.selectbox(f"เปลี่ยนสถานะ ({job['job_id']})", ["รอซ่อม", "กำลังซ่อม", "ซ่อมเสร็จแล้ว", "ส่งคืนลูกค้าแล้ว"], index=["รอซ่อม", "กำลังซ่อม", "ซ่อมเสร็จแล้ว", "ส่งคืนลูกค้าแล้ว"].index(job['status']), key=f"status_{i}")
                    if new_status != job['status']:
                        job['status'] = new_status
                        st.success("อัปเดตสถานะเรียบร้อย!")
                        st.rerun()

                with col_b:
                    st.markdown("##### 🖲️ เมนูจัดการ (จำลองคลิกขวาที่รายการงานซ่อม)")
                    
                    # 1. ดูประวัติการซ่อมจาก SN
                    if st.button(f"🔍 ดูประวัติซ่อมด้วย S/N: {job['serial']}", key=f"hist_{i}"):
                        st.info(f"--- ประวัติการซ่อมของอุปกรณ์ S/N: {job['serial']} ---")
                        match_history = [x for x in st.session_state['repairs'] if x['serial'] == job['serial']]
                        for mh in match_history:
                            st.write(f"• ใบงาน: {mh['job_id']} | วันที่: {mh['date']} | อาการ: {mh['device']} | สถานะ: {mh['status']}")

                    # 2. ปริ้นต์เอกสาร (ย้ายปุ่มปริ้นต์มารวมที่เมนูคลิกขวา และรองรับขนาดสลิป 80/58 มม.)
                    printer_mode = st.session_state['settings']['printer_width']
                    if st.button(f"🖨️ พิมพ์ใบรับซ่อม/สลิป ({printer_mode})", key=f"print_{i}"):
                        st.success(f"กำลังส่งคำสั่งพิมพ์ไปยังเครื่องพิมพ์สลิปขนาด **{printer_mode}**...")
                        st.code(f"""
========= ร้านโซนคอมพิวเตอร์ =========
ใบรับซ่อมเครื่อง / ใบเสร็จมัดจำ
-------------------------------------
เลขที่ใบงาน: {job['job_id']}
วันที่รับ: {job['date']}
ลูกค้า: {job['customer']} ({job['phone']})
อุปกรณ์: {job['device']}
Serial No: {job['serial']}
เงินมัดจำ: {job['deposit']:,.2f} บาท
ช่างผู้รับซ่อม: {job['technician']}
-------------------------------------
ขอบคุณที่ใช้บริการ (S/N Barcode Included)
=====================================
                        """)
                    
                    # 3. พิมพ์บาร์โค้ด SN สำหรับติดเครื่องซ่อม
                    if st.button(f"🏷️ พิมพ์สติกเกอร์บาร์โค้ด SN", key=f"barcode_{i}"):
                        st.markdown(f"**[ บาร์โค้ดสติกเกอร์ SN สำหรับติดเครื่อง ]**")
                        st.code(f"*||| | |||| || ||| |* \nSN: {job['serial']}")
    else:
        st.info("ไม่พบรายการงานซ่อมที่ค้นหา")

# ==========================================
# 3. จัดซื้อ & รับสินค้าเข้าระบบ (เช็ค SN ซ้ำ)
# ==========================================
if menu == "3. จัดซื้อ & รับสินค้าเข้าระบบ":
    st.title("📦 ระบบจัดซื้อและรับสินค้าเข้าคลัง (ตรวจสอบ SN ซ้ำ)")
    
    with st.form("purchase_form", clear_on_submit=True):
        st.subheader("บันทึกรับสินค้าเข้าสต็อก")
        col1, col2 = st.columns(2)
        with col1:
            p_name = st.text_input("ชื่อสินค้า/อะไหล่")
            p_id = st.text_input("รหัสสินค้า")
            supplier_name = st.text_input("ชื่อบริษัทจัดซื้อ (Supplier)")
        with col2:
            cost_p = st.number_input("ราคาต้นทุน (บาท)", min_value=0.0)
            sell_p = st.number_input("ราคาขาย (บาท)", min_value=0.0)
            unit_name = st.text_input("หน่วยนับ (เช่น ตัว, ชิ้น, เส้น)", value="ชิ้น")
            sn_in = st.text_input("Serial Number (SN) รายชิ้น")
            
        p_submitted = st.form_submit_button("ตรวจสอบและรับสินค้าเข้า")
        if p_submitted:
            if p_name and p_id and sn_in:
                # ตรวจสอบ SN ซ้ำในระบบ
                duplicate_found = any(item['serial'] == sn_in for item in st.session_state['inventory'])
                if duplicate_found:
                    st.error(f"❌ ไม่สามารถรับเข้าได้! หมายเลข Serial Number '{sn_in}' มีอยู่แล้วในระบบสต็อกหรือเคยจำหน่ายไปแล้ว")
                else:
                    st.session_state['inventory'].append({
                        "id": p_id,
                        "name": p_name,
                        "cost": cost_p,
                        "price": sell_p,
                        "unit": unit_name,
                        "supplier": supplier_name,
                        "stock": 1,
                        "serial": sn_in,
                        "is_intangible": False
                    })
                    st.success(f"✅ รับสินค้า {p_name} (S/N: {sn_in}) เข้าสู่ระบบสำเร็จ! (เคลียร์ช่องรหัสบริษัทและฟอร์มเรียบร้อย)")
            else:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน รวมถึง Serial Number เพื่อป้องกันสินค้าซ้ำ")

# ==========================================
# 4. คลังสินค้า & แก้ไขข้อมูลได้ทันที & บาร์โค้ด
# ==========================================
elif menu == "4. คลังสินค้า & พิมพ์บาร์โค้ด SN":
    st.title("📊 จัดการสต็อกสินค้า และเพิ่มสินค้าใหม่")
    
    st.subheader("รายการสินค้าในคลังทั้งหมด (แก้ไขข้อมูล ชื่อ, ราคา, หน่วย, บริษัท ได้ทันที)")
    
    # ใช้ st.data_editor เพื่อให้แก้ไขข้อมูลชื่อสินค้า ราคาขาย หน่วยนับ อัปเดตบริษัทได้เลย
    edited_df = st.data_editor(
        pd.DataFrame(st.session_state['inventory']),
        num_rows="dynamic",
        use_container_width=True,
        key="inventory_editor"
    )
    
    # อัปเดตข้อมูลกลับสู่ session_state เมื่อมีการแก้ไขผ่านตาราง
    if st.button("💾 บันทึกการแก้ไขข้อมูลคลังสินค้า"):
        st.session_state['inventory'] = edited_df.to_dict(orient="records")
        st.success("บันทึกการปรับปรุงข้อมูลสต็อกเรียบร้อยแล้ว!")

    st.divider()
    st.subheader("➕ เพิ่มสินค้าใหม่ (แก้ไขบั๊กค่าเริ่มต้นสินค้าไม่มีตัวตน)")
    with st.form("new_stock_item"):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            new_name = st.text_input("ชื่อสินค้าใหม่")
            new_code = st.text_input("รหัสสินค้าใหม่")
            new_unit = st.text_input("หน่วยนับ", value="ชิ้น")
        with col_n2:
            new_cost = st.number_input("ราคาต้นทุน", min_value=0.0)
            new_price = st.number_input("ราคาขาย", min_value=0.0)
            # ตั้งค่าเริ่มต้น is_intangible เป็น False เสมอ (แก้บั๊กติ๊กเอง)
            is_intangible = st.checkbox("กำหนดเป็นสินค้าไม่มีตัวตน (บริการ/ค่าแรง)", value=False)
            
        add_stock_btn = st.form_submit_button("เพิ่มสินค้าเข้าระบบ")
        if add_stock_btn:
            if new_name and new_code:
                st.session_state['inventory'].append({
                    "id": new_code,
                    "name": new_name,
                    "cost": new_cost,
                    "price": new_price,
                    "unit": new_unit,
                    "supplier": "เพิ่มเองหน้าร้าน",
                    "stock": 1,
                    "serial": generate_random_sn("PRD"),
                    "is_intangible": is_intangible
                })
                st.success(f"เพิ่มสินค้า {new_name} สำเร็จ! (สถานะสินค้าไม่มีตัวตน: {is_intangible})")
                st.rerun()

# ==========================================
# 5. ระบบขายสินค้า (POS) & คำนวณภาษีถูกต้อง
# ==========================================
elif menu == "5. ระบบขายสินค้า (POS) & ออกบิล":
    st.title("🛒 ระบบขายหน้าร้าน (POS) & คำนวณภาษีมาตรฐาน")
    
    selected_prod = st.selectbox("เลือกสินค้าในสต็อก", st.session_state['inventory'], format_func=lambda x: f"{x['name']} (S/N: {x['serial']}) - ราคา {x['price']:,.2f} บาท")
    sell_qty = st.number_input("จำนวนที่ซื้อ", min_value=1, value=1)
    
    vat_rate = st.session_state['settings']['vat_rate']
    subtotal = selected_prod['price'] * sell_qty
    vat_amt, grand_total = calculate_vat(subtotal, vat_rate)
    
    st.info(f"💰 ยอดสินค้าก่อนภาษี: {subtotal:,.2f} บาท | ภาษีมูลค่าเพิ่ม ({vat_rate}%): {vat_amt:,.2f} บาท | ยอดสุทธิรวม: **{grand_total:,.2f} บาท**")
    
    if st.button("💳 ยืนยันการชำระเงินและออกใบกำกับภาษี / ใบเสร็จ"):
        st.session_state['sales'].append({
            "product": selected_prod['name'],
            "serial": selected_prod['serial'],
            "qty": sell_qty,
            "subtotal": subtotal,
            "vat": vat_amt,
            "total": grand_total,
            "seller": logged_in_user,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success(f"ออกใบเสร็จรับเงิน/ใบกำกับภาษีสำเร็จ! ยอดสุทธิ {grand_total:,.2f} บาท")

# ==========================================
# 6. รายงานและบัญชี
# ==========================================
elif menu == "6. รายงานและบัญชี":
    st.title("📊 ระบบรายงาน ยอดขาย และผลกำไรช่าง")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("รายงานการขาย (รายวัน/เดือน/ปี)")
        if st.session_state['sales']:
            df_sales = pd.DataFrame(st.session_state['sales'])
            st.dataframe(df_sales, use_container_width=True)
            total_rev = df_sales['total'].sum()
            st.metric("ยอดขายรวมสุทธิทั้งสิ้น", f"{total_rev:,.2f} บาท")
        else:
            st.info("ยังไม่มีข้อมูลการขายในระบบ")
            
    with col2:
        st.subheader("รายงานการซ่อม แยกรายช่าง & กำไร")
        if st.session_state['repairs']:
            df_repairs = pd.DataFrame(st.session_state['repairs'])
            st.dataframe(df_repairs[['job_id', 'customer', 'device', 'technician', 'deposit', 'status']], use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อม")

# ==========================================
# 7. ตั้งค่าโปรแกรม (ภาษี & เครื่องพิมพ์)
# ==========================================
elif menu == "7. ตั้งค่าโปรแกรม (ภาษี & เครื่องพิมพ์)":
    st.title("⚙️ ตั้งค่าโปรแกรม (เชื่อมโยงทั้งเครือข่าย)")
    
    with st.form("settings_form"):
        st.subheader("ตั้งค่าอัตราภาษีมูลค่าเพิ่ม (%)")
        input_vat = st.number_input("อัตราภาษี (%) สำหรับใช้คำนวณทั้งระบบ", min_value=0.0, max_value=100.0, value=st.session_state['settings']['vat_rate'])
        
        st.subheader("ตั้งค่าเครื่องพิมพ์สลิป / ใบเสร็จ")
        input_printer = st.selectbox("เลือกขนาดความกว้างสลิปเครื่องพิมพ์", ["80 มม.", "58 มม."], index=0 if st.session_state['settings']['printer_width'] == "80 มม." else 1)
        
        save_settings = st.form_submit_button("บันทึกการตั้งค่าระบบ")
        if save_settings:
            st.session_state['settings']['vat_rate'] = input_vat
            st.session_state['settings']['printer_width'] = input_printer
            st.success("บันทึกการตั้งค่าระบบเครือข่ายสำเร็จเรียบร้อยแล้ว!")