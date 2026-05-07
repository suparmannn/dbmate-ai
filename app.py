import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import json    
import os                               
from streamlit_lottie import st_lottie

# Load environment variables
load_dotenv()

def load_lottie_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    
# Import modules
from core.db_connector import DatabaseManager
from core.schema_fetcher import SchemaFetcher
from ai.engine import DeepSeekSQLEngine
from utils.safety import show_safety_warning, rollback_simulation_dialog

# ========== PAGE CONFIGURATION ==========
st.set_page_config(
    page_title="DBMate AI | SQL Co-pilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    .danger-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
    }
</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE INITIALIZATION ==========
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = False
if 'schema_fetcher' not in st.session_state:
    st.session_state.schema_fetcher = None
if 'ai_engine' not in st.session_state:
    st.session_state.ai_engine = DeepSeekSQLEngine()
if 'read_only' not in st.session_state:
    st.session_state.read_only = True
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'generated_sql' not in st.session_state:
    st.session_state.generated_sql = ""
if 'ai_explanation' not in st.session_state:
    st.session_state.ai_explanation = ""

if 'db_config' not in st.session_state:
    config_file = ".streamlit/db_config.json"
    try:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                st.session_state.db_config = json.load(f)
        else:
            st.session_state.db_config = {
                'type': 'PostgreSQL',
                'host': 'localhost',
                'port': 5432,
                'database': '',
                'user': '',
                'password': '',
                'filepath': 'database.db'
            }
    except:
        st.session_state.db_config = {
            'type': 'PostgreSQL',
            'host': 'localhost',
            'port': 5432,
            'database': '',
            'user': '',
            'password': '',
            'filepath': 'database.db'
        }
# ========== SIDEBAR ==========
with st.sidebar:
    st.title("⚙️ DBMate AI")
    st.caption("SQL Co-pilot yang ngerti database")

    st.divider()

    # Database Configuration Section
    st.subheader("🗄️ Database Configuration")

    db_type = st.selectbox(
    "Database Type",
    ["PostgreSQL", "MySQL", "MariaDB", "SQLite"],
    index=["PostgreSQL", "MySQL", "MariaDB", "SQLite"].index(st.session_state.db_config['type']) 
          if st.session_state.db_config['type'] in ["PostgreSQL", "MySQL", "MariaDB", "SQLite"] 
          else 0,
    help="Pilih tipe database yang mau dihubungkan"
)

    # Dynamic form based on DB type
        # Dynamic form based on DB type
    if db_type == "SQLite":
        db_file = st.text_input(
            "📁 File Path",
            value=st.session_state.db_config.get('filepath', 'database.db'),
            help="Lokasi file SQLite (contoh: /path/to/database.db)"
        )
        host = port = database = user = password = None
    else:
        host = st.text_input(
            "🖥️ Host",
            value=st.session_state.db_config.get('host', 'localhost'),
            help="Alamat server database (IP atau domain)"
        )
        col1, col2 = st.columns(2)
        with col1:
            port = st.number_input(
                "🔌 Port",
                value=st.session_state.db_config.get('port', 5432 if db_type == "PostgreSQL" else 3306),
                help=f"Port default: {5432 if db_type == 'PostgreSQL' else 3306}"
            )
        with col2:
            database = st.text_input(
                "📊 Database",
                value=st.session_state.db_config.get('database', ''),
                placeholder="nama_database",
                help="Nama database yang ingin diakses"
            )
        user = st.text_input(
            "👤 Username",
            value=st.session_state.db_config.get('user', ''),
            placeholder="root",
            help="Username database"
        )
        password = st.text_input(
            "🔑 Password",
            value=st.session_state.db_config.get('password', ''),
            type="password",
            help="Password database"
        )
        db_file = None

    st.divider()

    # Connection Buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        connect_btn = st.button(
            "🔌 Connect",
            type="primary",
            use_container_width=True
        )

    with col_btn2:
        disconnect_btn = st.button(
            "🔌 Disconnect",
            use_container_width=True,
            disabled=not st.session_state.connection_status
        )

    # Handle Connect
    if connect_btn:
        db_config = {
            'type': db_type.lower(),
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            'filepath': db_file
        }
        
                #Buat Save Konfig
        st.session_state.db_config = db_config
        os.makedirs(".streamlit", exist_ok=True)
        with open(".streamlit/db_config.json", "w") as f:
            json.dump(db_config, f)
        with st.spinner("🔄 Menghubungkan ke database..."):
            success, message = st.session_state.db_manager.connect(db_config)

            if success:
                st.session_state.connection_status = True
                st.session_state.schema_fetcher = SchemaFetcher(st.session_state.db_manager)
                st.success(message)
                st.balloons()
            else:
                st.session_state.connection_status = False
                st.error(message)

                # Additional tips based on error
                if "whitelist" in message.lower() or "ip" in message.lower():
                    st.info("""
                    💡 **PANDUAN WHITELIST IP:**

                    1. **CPanel Hosting:**
                       - Masuk CPanel → Remote MySQL
                       - Tambahkan IP lo atau gunakan wildcard (%)

                    2. **Cloud Database (AWS/GCP/Azure):**
                       - Buka Security Group/Firewall Rules
                       - Tambahkan inbound rule untuk IP lo di port database

                    3. **IP Local:**
                       - Cek IP lo di: https://whatismyipaddress.com
                       - Minta admin database untuk whitelist IP tersebut
                    """)

    # Handle Disconnect
    if disconnect_btn:
        st.session_state.db_manager.disconnect()
        st.session_state.connection_status = False
        st.session_state.schema_fetcher = None
        st.info("✅ Database berhasil diputuskan")

    st.divider()

    # Safety Settings
    st.subheader("🛡️ Safety Settings")

    st.session_state.read_only = st.toggle(
        "Read-Only Mode",
        value=st.session_state.read_only,
        help="AKTIFKAN: Hanya SELECT query yang diizinkan.\nNonaktifkan untuk DELETE/UPDATE/DROP (dengan konfirmasi)"
    )

    if st.session_state.read_only:
        st.success("🔒 Read-Only Mode AKTIF")
    else:
        st.error("⚠️ Read-Only Mode NONAKTIF - Hati-hati!")

    st.divider()

    # AI Engine Status
    st.subheader("🤖 AI Engine Status")

    if st.session_state.ai_engine.is_available():
        st.success("✅ DeepSeek AI Siap")
    else:
        st.warning("""
        ⚠️ **AI Engine Belum Siap**

        **Cara aktivasi (cukup 2 menit):**
        1. Buka https://platform.deepseek.com/api_keys
        2. Top-up saldo minimal $2 via PayPal/Kartu Debit
        3. Generate API Key, copy tokennya (format: sk-xxxxx)
        4. Buka file `.env`, paste: `DEEPSEEK_API_KEY=sk-token-lo`
        5. Restart aplikasi: `streamlit run app.py`

        **TANPA TOKEN pun tetap bisa:**
        - ✅ Connect ke database
        - ✅ Lihat struktur tabel (Schema Explorer)
        - ✅ Eksekusi query SQL manual
        - ✅ Rollback simulation
        - ✅ Download hasil query
        """)

    st.divider()

    # Connection Status
    if st.session_state.connection_status:
        st.success(f"🟢 Connected to {db_type}")
    else:
        st.error("🔴 Disconnected")

# ========== MAIN CONTENT ==========
col_header_left, col_header_right = st.columns([1, 8])

with col_header_left:
    lottie_robot = load_lottie_file("assets/database.json") 
    st_lottie(lottie_robot, height=190, width=190, key="robot")

with col_header_right:
    st.title("DBMate AI")
    st.caption("SQL Co-pilot yang ngerti database • Copyright M.Suparman 2026")


if st.session_state.connection_status:
    # Tab Layout
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Generate SQL (AI)",
        "📋 Schema Explorer",
        "⚙️ Query Manual",
        "📜 History"
    ])

    # ===================================
    # TAB 1: AI SQL GENERATOR
    # ===================================
    with tab1:
        st.subheader("🧠 Generate SQL dengan Bahasa Manusia")
        st.caption("Gunakan AI untuk membuat query SQL dari pertanyaan biasa")

        col_input, col_info = st.columns([2, 1])

        with col_input:
            user_prompt = st.text_area(
                "Apa yang ingin Anda query?",
                placeholder="Contoh:\n"
                          "- Tampilkan 10 customer dengan total pembelian tertinggi\n"
                          "- Cari produk yang belum pernah dibeli bulan ini\n"
                          "- Hitung rata-rata order per kategori produk\n"
                          "- Buatkan laporan penjualan per bulan tahun ini",
                height=150,
                disabled=not st.session_state.ai_engine.is_available()
            )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                generate_btn = st.button(
                    "🚀 Generate SQL",
                    type="primary",
                    disabled=not st.session_state.ai_engine.is_available() or not user_prompt,
                    use_container_width=True
                )
            with col_btn2:
                clear_btn = st.button("🗑️ Clear", key="clear_generated_sql", use_container_width=True)

        with col_info:
            st.info("""
            💡 **Tips Prompt yang Baik:**

            1. Spesifik tentang data yg diinginkan
            2. Sebutkan filter jika ada
            3. Jelaskan pengurutan (ORDER BY)
            4. Tentukan jumlah baris

            **Contoh Prompt Keren:**
            > "Tampilkan 5 produk terlaris
            > bulan Maret 2026, urutkan
            > dari yang paling laris,
            > tampilkan nama produk,
            > kategori, dan jumlah terjual"
            """)

        # Handle Generate SQL
        if generate_btn and user_prompt:
            with st.spinner("🤔 AI sedang memikirkan query..."):
                try:
                    # Ambil DDL compact
                    ddl = st.session_state.schema_fetcher.get_compact_ddl()

                    # Panggil AI
                    sql, explanation = st.session_state.ai_engine.generate_sql(
                        user_prompt=user_prompt,
                        ddl_context=ddl,
                        db_type=db_type.lower()
                    )

                    if sql:
                        st.session_state.generated_sql = sql
                        st.session_state.ai_explanation = explanation
                        st.success("✅ Query berhasil digenerate!")
                    else:
                        st.error(explanation)

                except Exception as e:
                    st.error(f"❌ Gagal generate query: {str(e)}")

        if clear_btn:
            st.session_state.generated_sql = ""
            st.session_state.ai_explanation = ""
            st.rerun()

        # Tampilkan Generated SQL
        if st.session_state.generated_sql:
            st.divider()
            st.subheader("📝 Generated SQL Query")

            # Query preview box
            st.code(st.session_state.generated_sql, language="sql")

            # AI Explanation
            if st.session_state.ai_explanation:
                with st.expander("🧠 Penjelasan AI", expanded=True):
                    st.info(st.session_state.ai_explanation)

            # Safety Analysis
            safety = st.session_state.db_manager.analyze_query_safety(
                st.session_state.generated_sql
            )

            if safety['is_dangerous']:
                st.warning(f"""
                ⚠️ **PERINGATAN:** Query ini mengandung operasi berbahaya!

                Operasi terdeteksi: **{', '.join(safety['dangers'].keys())}**

                Disarankan untuk menjalankan **Rollback Simulation** terlebih dahulu.
                """)

            # Action Buttons
            st.divider()
            st.subheader("🎬 Actions")

            col_act1, col_act2, col_act3 = st.columns(3)

            with col_act1:
                # Rollback Simulation Button
                if st.button("🔍 Rollback Simulation (EXPLAIN)", use_container_width=True):
                    with st.spinner("🔄 Menjalankan simulasi..."):
                        success, plan, message = st.session_state.db_manager.simulate_rollback(
                            st.session_state.generated_sql
                        )
                        if success:
                            rollback_simulation_dialog(plan)
                        else:
                            st.error(message)

            with col_act2:
                # Execute Button (dengan safety check)
                execute_disabled = False
                if st.session_state.read_only and safety['is_dangerous']:
                    execute_disabled = True

                if st.button(
                    "▶️ Execute Query",
                    type="primary" if not execute_disabled else "secondary",
                    disabled=execute_disabled,
                    use_container_width=True
                ):
                    # Jika read-only mode ON dan query berbahaya
                    if st.session_state.read_only and safety['is_dangerous']:
                        st.error("""
                        🔒 **TIDAK DAPAT DIEKSEKUSI**

                        Query ini mengandung operasi berbahaya dan Read-Only Mode AKTIF.

                        Untuk mengeksekusi:
                        1. Nonaktifkan Read-Only Mode di sidebar
                        2. Jalankan Rollback Simulation dulu
                        3. Konfirmasi eksekusi
                        """)
                    else:
                        # Jika query berbahaya tapi read-only OFF, minta konfirmasi
                        if safety['is_dangerous']:
                            confirmed = show_safety_warning(safety['dangers'])
                            if not confirmed:
                                st.stop()

                        # Eksekusi query
                        with st.spinner("⚡ Menjalankan query..."):
                            try:
                                result = st.session_state.db_manager.execute_query(
                                    st.session_state.generated_sql,
                                    force=(not st.session_state.read_only)
                                )

                                # Simpan ke history
                                st.session_state.query_history.append({
                                    'timestamp': datetime.now(),
                                    'query': st.session_state.generated_sql,
                                    'prompt': user_prompt,
                                    'rows': len(result),
                                    'type': 'AI Generated'
                                })

                                # Tampilkan hasil
                                st.success(f"✅ Query berhasil! Menampilkan {len(result)} baris")
                                st.dataframe(result, use_container_width=True)

                                # Download button
                                csv = result.to_csv(index=False)
                                st.download_button(
                                    "📥 Download CSV",
                                    csv,
                                    f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )

                            except Exception as e:
                                st.error(f"❌ Gagal eksekusi: {str(e)}")

            with col_act3:
                # Copy to Manual Tab button
                if st.button("📋 Copy ke Query Manual", use_container_width=True):
                    st.session_state.manual_query = st.session_state.generated_sql
                    st.success("✅ Query dicopy ke tab 'Query Manual'")

        # ===================================
    # TAB 2: SCHEMA EXPLORER
    # ===================================
    with tab2:
        st.subheader("📋 Database Schema Explorer")

        if st.button("🔄 Refresh Schema", type="primary", key="refresh_schema_btn"):
            with st.spinner("📊 Mengambil struktur database..."):
                try:
                    # Simpan schema di session_state biar persist
                    st.session_state.schema_data = st.session_state.schema_fetcher.get_full_schema()
                except Exception as e:
                    st.error(f"❌ Gagal fetch schema: {str(e)}")

        # Tampilkan schema kalo udah ada di session_state
        if 'schema_data' in st.session_state and st.session_state.schema_data:
            schema = st.session_state.schema_data

            # Stats
            total_tables = len(schema)
            total_columns = sum(len(cols) for cols in schema.values())

            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Total Tabel", total_tables)
            with col_stat2:
                st.metric("Total Kolom", total_columns)
            with col_stat3:
                # Hitung relasi FK
                fk_count = sum(
                    1 for cols in schema.values() 
                    for col in cols 
                    if col.get('foreign_key')
                )
                st.metric("Total Relasi FK", fk_count)

            st.divider()

            # Daftar tabel (quick navigation)
            st.caption("📌 **Klik tabel untuk lihat detail**")
            table_names = list(schema.keys())
            
            # Tampilin list tabel dalam bentuk pills/button grid
            cols_per_row = 6
            for i in range(0, len(table_names), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, table_name in enumerate(table_names[i:i+cols_per_row]):
                    with cols[j]:
                        fk_in_table = sum(1 for col in schema[table_name] if col.get('foreign_key'))
                        pk_in_table = sum(1 for col in schema[table_name] if col.get('primary_key'))
                        badge = ""
                        if fk_in_table > 0:
                            badge += f" 🔗{fk_in_table}"
                        if pk_in_table > 0:
                            badge += f" 🔑{pk_in_table}"
                        
                        # Cari tabel yang ngerujuk ke tabel ini
                        referenced_by = []
                        for t, cols_data in schema.items():
                            for col in cols_data:
                                if col.get('foreign_key') and col['foreign_key'].startswith(f"{table_name}."):
                                    referenced_by.append(f"{t}.{col['name']}")
                        
                        ref_count = len(referenced_by)
                        st.button(
                            f"📋 {table_name}{badge}",
                            key=f"btn_{table_name}",
                            use_container_width=True,
                            help=f"PK: {pk_in_table} | FK: {fk_in_table} | Dirujuk: {ref_count} tabel"
                        )

            st.divider()

            # Detail per tabel (dalam expander)
            st.subheader("🔍 Detail Tabel")
            for table_name, columns in schema.items():
                # Hitung relasi
                pk_cols = [col['name'] for col in columns if col.get('primary_key')]
                fk_cols = [col for col in columns if col.get('foreign_key')]
                
                # Cari tabel yang ngerujuk ke tabel ini
                referenced_by = []
                for t, cols_data in schema.items():
                    for col in cols_data:
                        if col.get('foreign_key') and col['foreign_key'].startswith(f"{table_name}."):
                            referenced_by.append(f"{t}.{col['name']} → {col['foreign_key']}")
                
                # Build summary
                summary_parts = [f"{len(columns)} kolom"]
                if pk_cols:
                    summary_parts.append(f"🔑 PK: {', '.join(pk_cols)}")
                if fk_cols:
                    fk_summary = ", ".join([f"{c['name']} → {c['foreign_key']}" for c in fk_cols])
                    summary_parts.append(f"🔗 FK: {fk_summary}")
                if referenced_by:
                    summary_parts.append(f"➡️ Dirujuk oleh: {', '.join(referenced_by)}")
                
                with st.expander(f"📋 **{table_name}** ({' | '.join(summary_parts)})"):
                    # Buat DataFrame dengan kolom relasi yang jelas
                    col_data = []
                    for col in columns:
                        relasi = ""
                        badge = ""
                        if col.get('primary_key'):
                            badge += "🔑 PRIMARY KEY"
                        if col.get('foreign_key'):
                            badge += " 🔗 FOREIGN KEY"
                            relasi = f"→ {col['foreign_key']}"
                        
                        col_data.append({
                            "Kolom": col['name'],
                            "Tipe Data": col['type'],
                            "Nullable": "YES" if col.get('nullable') else "NO",
                            "Key": badge.strip() if badge else "-",
                            "Relasi": relasi if relasi else "-",
                            "Default": str(col.get('default')) if col.get('default') else "-"
                        })
                    
                    df_cols = pd.DataFrame(col_data)
                    st.dataframe(
                        df_cols,
                        use_container_width=True,
                        hide_index=True
                    )

                    # Tombol lihat sample data (dengan unique key)
                    col_btn_sample, col_btn_empty = st.columns([1, 3])
                    with col_btn_sample:
                        if st.button("👁️ Lihat Sample Data", key=f"sample_btn_{table_name}"):
                            try:
                                sample_df = st.session_state.schema_fetcher.get_sample_data(table_name)
                                st.success(f"✅ Menampilkan {len(sample_df)} baris dari tabel **{table_name}**")
                                st.dataframe(sample_df, use_container_width=True)
                            except Exception as e:
                                st.error(f"Gagal ambil sample: {str(e)}")
                    
                    # Tampilkan relasi lengkap
                    if fk_cols or referenced_by:
                        st.caption("🔗 **Relasi Lengkap:**")
                        if fk_cols:
                            for fk in fk_cols:
                                st.info(f"↗️ **{table_name}.{fk['name']}** merujuk ke **{fk['foreign_key']}**")
                        if referenced_by:
                            for ref in referenced_by:
                                st.info(f"↘️ **{ref}**")

            # DDL Compact version
            st.divider()
            with st.expander("🔧 DDL Compact (Untuk AI Context)"):
                ddl = st.session_state.schema_fetcher.get_compact_ddl()
                st.code(ddl, language="text")
                st.caption("📝 Format ini yang dikirim ke AI untuk generate query")

        else:
            st.info("👆 Klik tombol **Refresh Schema** untuk melihat struktur database")

    # ===================================
    # TAB 3: MANUAL QUERY
    # ===================================
    with tab3:
        st.subheader("⚙️ Manual SQL Query")

        if 'manual_query' not in st.session_state:
            st.session_state.manual_query = ""

        manual_query = st.text_area(
            "Tulis query SQL di sini:",
            value=st.session_state.manual_query if st.session_state.manual_query else "",
            placeholder="SELECT * FROM users LIMIT 10;",
            height=150,
            key="manual_query_input"
        )

        # Safety warning untuk manual query
        if manual_query:
            safety = st.session_state.db_manager.analyze_query_safety(manual_query)
            if safety['is_dangerous']:
                st.warning(f"⚠️ Query mengandung operasi: {', '.join(safety['dangers'].keys())}")

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            if st.button("🔍 Simulate (EXPLAIN)", use_container_width=True):
                if manual_query.strip():
                    with st.spinner("🔄 Simulasi..."):
                        success, plan, message = st.session_state.db_manager.simulate_rollback(manual_query)
                        if success:
                            rollback_simulation_dialog(plan)
                        else:
                            st.error(message)
                else:
                    st.warning("Tulis query dulu!")

        with col_btn2:
            if st.button("▶️ Run Query", type="primary", use_container_width=True):
                if manual_query.strip():
                    # Safety check
                    safety = st.session_state.db_manager.analyze_query_safety(manual_query)

                    if st.session_state.read_only and safety['is_dangerous']:
                        st.error(f"""
                        🔒 Read-Only Mode AKTIF!

                        Query mengandung: {', '.join(safety['dangers'].keys())}

                        Nonaktifkan Read-Only mode di sidebar untuk mengeksekusi.
                        """)
                    elif safety['is_dangerous']:
                        confirmed = show_safety_warning(safety['dangers'])
                        if confirmed:
                            with st.spinner("⚡ Menjalankan query..."):
                                try:
                                    result = st.session_state.db_manager.execute_query(
                                        manual_query,
                                        force=True
                                    )

                                    # Simpan history
                                    st.session_state.query_history.append({
                                        'timestamp': datetime.now(),
                                        'query': manual_query,
                                        'prompt': 'Manual Query',
                                        'rows': len(result),
                                        'type': 'Manual'
                                    })

                                    st.success(f"✅ Berhasil! {len(result)} baris")
                                    st.dataframe(result, use_container_width=True)

                                    csv = result.to_csv(index=False)
                                    st.download_button(
                                        "📥 Download CSV",
                                        csv,
                                        f"manual_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        "text/csv",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                    else:
                        # SELECT query (aman)
                        with st.spinner("⚡ Menjalankan query..."):
                            try:
                                result = st.session_state.db_manager.execute_query(manual_query)

                                st.session_state.query_history.append({
                                    'timestamp': datetime.now(),
                                    'query': manual_query,
                                    'prompt': 'Manual Query',
                                    'rows': len(result),
                                    'type': 'Manual'
                                })

                                st.success(f"✅ Berhasil! {len(result)} baris")
                                st.dataframe(result, use_container_width=True)

                                csv = result.to_csv(index=False)
                                st.download_button(
                                    "📥 Download CSV",
                                    csv,
                                    f"manual_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("Tulis query dulu!")

        with col_btn3:
            if st.button("🗑️ Clear", key="clear_manual_query", use_container_width=True):
                st.session_state.manual_query = ""
                st.rerun()

    # ===================================
    # TAB 4: QUERY HISTORY
    # ===================================
    with tab4:
        st.subheader("📜 Query History")

        if st.session_state.query_history:
            # Clear history button
            if st.button("🗑️ Clear All History", type="secondary"):
                st.session_state.query_history = []
                st.rerun()

            st.divider()

            # Display history dari terbaru
            for i, history in enumerate(reversed(st.session_state.query_history)):
                with st.expander(f"🕐 {history['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {history['type']} | {history['rows']} rows"):
                    st.caption(f"**Prompt:** {history['prompt']}")
                    st.code(history['query'], language="sql")

                    if st.button("📋 Pakai Query Ini", key=f"reuse_{i}"):
                        st.session_state.generated_sql = history['query']
                        st.success("✅ Query dicopy ke tab Generate SQL")
        else:
            st.info("📝 Belum ada query yang dijalankan. History akan muncul di sini.")

else:
    # ========== NOT CONNECTED STATE ==========
    st.warning("👈 Silakan hubungkan ke database terlebih dahulu melalui sidebar sebelah kiri!")

    st.divider()

    st.markdown("""
    ## 🚀 Selamat Datang di DBMate AI!

    **DBMate AI** adalah SQL Co-pilot yang membantu Anda:

    1. **🔌 Koneksi Multi-Database**: PostgreSQL, MySQL, MariaDB, SQLite
    2. **🧠 Generate SQL dengan AI**: Tulis pertanyaan biasa, dapatkan query SQL
    3. **📋 Eksplorasi Schema**: Lihat struktur database dengan mudah
    4. **🛡️ Safety First**: Read-only mode, konfirmasi, rollback simulation
    5. **📊 Hasil Instan**: Lihat dan download hasil query dalam CSV

    ### 🏃‍♂️ Quick Start:
    1. Pilih tipe database di sidebar
    2. Isi kredensial database
    3. Klik **Connect**
    4. Mulai eksplorasi!

    ### 🤖 Setup AI Engine (Opsional):
    1. Buka https://platform.deepseek.com/api_keys
    2. Top-up saldo minimal $2
    3. Generate API Key
    4. Simpan di file `.env`: `DEEPSEEK_API_KEY=sk-token-lo`
    5. Restart aplikasi dan AI siap digunakan!
    """)

# ========== FOOTER ==========
st.divider()
st.caption(f"🤖 DBMate AI v1.0 | © 2026 | Status: {'🟢 Connected' if st.session_state.connection_status else '🔴 Disconnected'} | {'🔒 Read-Only' if st.session_state.read_only else '⚠️ Write Mode'}")