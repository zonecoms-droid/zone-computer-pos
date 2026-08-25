# เพิ่มเมนูใหม่เข้าไปใน Sidebar ของเดิม
menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", [
    "📥 รับเครื่องซ่อมใหม่ (Pro Intake)", 
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)",  # <-- เมนูใหม่สไตล์ FlowAccount
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง"
])

# ==========================================
# 📄 4. ระบบออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)
# ==========================================
if menu == "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)":
    st.header("📄 ระบบออกเอกสารและใบกำกับภาษี (FlowAccount Style)")
    st.markdown("สร้างใบเสนอราคา ใบเสร็จรับเงิน และใบกำกับภาษีแบบมืออาชีพ ถูกต้องตามรูปแบบธุรกิจไทย")
    
    # เลือกประเภทเอกสาร
    doc_type = st.selectbox("เลือกประเภทเอกสารที่ต้องการออก", [
        "ใบเสนอราคา (Quotation)", 
        "ใบเสร็จรับเงิน / ใบกำกับภาษี (Cash Sale / Tax Invoice)", 
        "บิลเงินสด / ใบเสร็จรับเงิน (Cash Receipt)"
    ])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ข้อมูลลูกค้า / คู่ค้า")
        cust_name = st.text_input("ชื่อลูกค้า / บริษัท", placeholder="บริษัท โซนคอมพิวเตอร์ จำกัด")
        cust_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี (13 หลัก)", placeholder="01055xxxxxxxx")
        cust_address = st.text_area("ที่อยู่สำหรับออกใบกำกับภาษี")
        
    with col2:
        st.subheader("รายละเอียดเอกสาร")
        import datetime
        doc_date = st.date_input("วันที่เอกสาร", datetime.date.today())
        due_date = st.date_input("วันครบกำหนดชำระ", datetime.date.today())
        payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "โอนเงินผ่านธนาคาร (QR Code)", "บัตรเครดิต"])

    st.markdown("### 🛒 รายการสินค้าและบริการ")
    
    # จำลองการกรอกรายการสินค้าแบบตาราง
    num_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
    
    subtotal = 0.0
    items_data = []
    
    for i in range(int(num_items)):
        cols = st.columns([3, 1, 1, 1])
        with cols[0]:
            item_desc = st.text_input(f"รายการที่ {i+1}", key=f"desc_{i}", placeholder="เช่น ประกอบคอมพิวเตอร์สเปคเล่นเกม / ค่าบริการซ่อม")
        with cols[1]:
            qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{i}")
        with cols[2]:
            price = st.number_input("ราคา/หน่วย (บาท)", min_value=0.0, step=100.0, key=f"price_{i}")
        with cols[3]:
            total_item = qty * price
            st.text_input("รวม (บาท)", value=f"{total_item:,.2f}", disabled=True, key=f"total_{i}")
        subtotal += total_item

    st.markdown("---")
    
    # คำนวณภาษีมูลค่าเพิ่ม (VAT 7%)
    col_a, col_b = st.columns([2, 1])
    with col_a:
        notes = st.text_area("หมายเหตุท้ายเอกสาร", value="เงื่อนไขการรับประกันสินค้าเป็นไปตามที่บริษัทกำหนด")
        
    with col_b:
        st.markdown(f"**มูลค่ารวมสินค้า/บริการ:** `{subtotal:,.2f} บาท`")
        
        # เช็คว่าต้องการคำนวณ VAT 7% ไหม (สไตล์ FlowAccount)
        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        
        if include_vat:
            vat_amount = subtotal * 0.07
            grand_total = subtotal + vat_amount
            st.markdown(s