import streamlit as st

def show_safety_warning(dangers: dict) -> bool:
    """
    Tampilkan warning dialog untuk query berbahaya.
    Returns True jika user konfirmasi.
    """
    st.warning(f"""
    ⚠️ **PERINGATAN KEAMANAN!**
    
    Query ini mengandung operasi berbahaya:
    {', '.join(dangers.keys())}
    
    Tindakan ini dapat:
    - Menghapus data secara permanen
    - Mengubah struktur database
    - Menyebabkan kehilangan data
    
    **Apakah Anda yakin ingin melanjutkan?**
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        confirm = st.button("✅ Ya, Saya Yakin", type="primary")
    with col2:
        cancel = st.button("❌ Batal")
    
    if cancel:
        st.info("Operasi dibatalkan.")
        return False
    
    if confirm:
        # Konfirmasi kedua (double confirmation)
        st.error("INI ADALAH KONFIRMASI TERAKHIR!")
        final_confirm = st.text_input(
            "Ketik 'YA' (huruf besar) untuk melanjutkan:",
            max_chars=3
        )
        if final_confirm == "YA":
            return True
        elif final_confirm:
            st.warning("Konfirmasi tidak valid.")
    
    return False

def rollback_simulation_dialog(plan: str):
    """Tampilkan hasil EXPLAIN query dalam dialog yang informatif"""
    st.info("""
    📊 **ROLLBACK SIMULATION (EXPLAIN QUERY)**
    
    Berikut adalah rencana eksekusi query. Ini menunjukkan bagaimana 
    database akan menjalankan query tanpa benar-benar mengeksekusinya.
    
    **PENTING:** Ini BUKAN eksekusi sebenarnya. Data Anda AMAN.
    """)
    
    st.code(plan, language="sql")
    
    st.success("""
    ✅ Simulasi selesai. Tidak ada data yang berubah.
    
    Untuk mengeksekusi query sebenarnya, nonaktifkan Read-Only Mode dan 
    gunakan tombol Execute dengan konfirmasi.
    """)