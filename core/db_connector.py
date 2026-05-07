import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import re

class DatabaseManager:
    """
    Universal Database Connector dengan Safety Layer
    Features:
    - Read-only mode (default)
    - Konfirmasi DELETE/UPDATE/DROP
    - Query preview sebelum eksekusi
    - Rollback simulation (EXPLAIN dulu)
    - Deteksi error koneksi (termasuk IP Whitelist)
    """
    
    # Patterns buat deteksi query berbahaya
    DANGEROUS_PATTERNS = {
        'DROP': r'\bDROP\b',
        'DELETE': r'\bDELETE\b',
        'UPDATE': r'\bUPDATE\b',
        'INSERT': r'\bINSERT\b',
        'ALTER': r'\bALTER\b',
        'TRUNCATE': r'\bTRUNCATE\b',
        'CREATE': r'\bCREATE\b',
    }
    
    def __init__(self):
        self.engine = None
        self.connection_status = False
        self.db_type = None
        self.read_only = True  # Default: Read-only mode
    
    def build_connection_string(self, db_config: dict) -> str:
        """Bangun connection string berdasarkan tipe database"""
        db_type = db_config.get('type', '').lower()
        self.db_type = db_type
        
        connectors = {
            'postgresql': f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
            'mysql': f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
            'mariadb': f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
            'sqlite': f"sqlite:///{db_config.get('filepath', 'database.db')}"
        }
        
        if db_type not in connectors:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return connectors[db_type]
    
    def connect(self, db_config: dict) -> tuple[bool, str]:
        """
        Test koneksi dan simpan engine.
        Returns: (success, message)
        """
        try:
            connection_string = self.build_connection_string(db_config)
            self.engine = create_engine(
                connection_string, 
                echo=False,
                connect_args={'connect_timeout': 10}  # Timeout 10 detik
            )
            
            # Test koneksi dengan ping
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.connection_status = True
            return True, "✅ Berhasil terhubung ke database!"
            
        except OperationalError as e:
            self.connection_status = False
            error_msg = str(e)
            
            # Deteksi error spesifik
            if "timeout" in error_msg.lower():
                return False, f"⏱️ KONEKSI TIMEOUT: Server database tidak merespon.\n\nDetail: {error_msg}\n\n💡 Tips: Cek apakah IP lo perlu di-whitelist di server database."
            
            elif "access denied" in error_msg.lower():
                return False, f"🔒 AKSES DITOLAK: Username atau password salah.\n\nDetail: {error_msg}\n\n💡 Tips: Cek kembali username/password lo."
            
            elif "unknown database" in error_msg.lower():
                return False, f"🗄️ DATABASE TIDAK DITEMUKAN: Nama database tidak ada.\n\nDetail: {error_msg}\n\n💡 Tips: Cek nama database atau buat database baru."
            
            elif "host" in error_msg.lower() and ("not allowed" in error_msg.lower() or "refused" in error_msg.lower()):
                return False, f"🚫 IP TIDAK DIIZINKAN: IP lo mungkin belum di-whitelist.\n\nDetail: {error_msg}\n\n💡 Tips: Tambahkan IP lo ke whitelist di server database (CPanel, Plesk, atau firewall)."
            
            else:
                return False, f"❌ GAGAL KONEKSI: {error_msg}\n\n💡 Tips: Periksa host, port, dan pastikan database server menyala."
        
        except SQLAlchemyError as e:
            self.connection_status = False
            return False, f"❌ DATABASE ERROR: {str(e)}"
        
        except Exception as e:
            self.connection_status = False
            return False, f"❌ ERROR TIDAK DIKENAL: {str(e)}"
    
    def disconnect(self):
        """Putuskan koneksi"""
        if self.engine:
            self.engine.dispose()
        self.connection_status = False
        self.engine = None
    
    def analyze_query_safety(self, query: str) -> dict:
        """
        Analisis keamanan query.
        Returns dict dengan info bahaya dan rekomendasi.
        """
        query_upper = query.upper().strip()
        dangers_found = {}
        
        for danger_type, pattern in self.DANGEROUS_PATTERNS.items():
            if re.search(pattern, query_upper):
                dangers_found[danger_type] = True
        
        is_select_only = query_upper.startswith('SELECT') or query_upper.startswith('EXPLAIN')
        is_dangerous = len(dangers_found) > 0 and not is_select_only
        
        return {
            'is_read_safe': is_select_only,
            'is_dangerous': is_dangerous,
            'dangers': dangers_found,
            'needs_confirmation': is_dangerous
        }
    
    def simulate_rollback(self, query: str) -> tuple[bool, str, str]:
        """
        Simulasi query dengan EXPLAIN.
        Returns: (success, execution_plan, estimated_cost)
        """
        try:
            # Wrap query dengan EXPLAIN (format berbeda per DB)
            if self.db_type == 'postgresql':
                explain_query = f"EXPLAIN (FORMAT TEXT, ANALYZE false) {query}"
            elif self.db_type in ['mysql', 'mariadb']:
                explain_query = f"EXPLAIN {query}"
            else:
                explain_query = f"EXPLAIN {query}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(explain_query))
                plan = "\n".join([str(row) for row in result.fetchall()])
            
            return True, plan, "Estimasi biaya query berhasil didapatkan"
            
        except Exception as e:
            return False, "", f"Gagal simulasi: {str(e)}"
    
    def execute_query(self, query: str, force: bool = False) -> pd.DataFrame:
        """
        Eksekusi SELECT query dan return DataFrame.
        Ada safety check otomatis.
        """
        if not self.connection_status:
            raise Exception("Belum connect ke database!")
        
        # Safety check
        if self.read_only and not force:
            safety = self.analyze_query_safety(query)
            if safety['is_dangerous']:
                dangerous_ops = ", ".join(safety['dangers'].keys())
                raise Exception(f"🔒 READ-ONLY MODE AKTIF\n\nQuery mengandung operasi: {dangerous_ops}\nUntuk mengeksekusi, nonaktifkan Read-Only mode dan konfirmasi.")
        
        try:
            with self.engine.connect() as conn:
                result = pd.read_sql(text(query), conn)
            return result
        except SQLAlchemyError as e:
            raise Exception(f"Query error: {str(e)}")
    
    def get_tables_list(self) -> list:
        """Ambil daftar tabel"""
        if not self.connection_status:
            raise Exception("Database belum terkoneksi")
        inspector = inspect(self.engine)
        return inspector.get_table_names()