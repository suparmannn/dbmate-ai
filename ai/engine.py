"""
AI ENGINE - DEEPSEEK SQL GENERATOR
===================================
Cara Dapetin Token:
1. Buka: https://platform.deepseek.com/api_keys
2. Login/Daftar pake email
3. Top-up saldo minimal $2 via PayPal/Kartu Debit
4. Generate API Key
5. Copy token (format: sk-xxxxxxxx)
6. Bikin file .env dan isi DEEPSEEK_API_KEY=sk-xxxxxxxx

Token contoh (sample - TIDAK VALID):
    DEEPSEEK_API_KEY=sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Harga:
- Input: $0.14 per 1M token
- Output: $0.28 per 1M token
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load token dari file .env
load_dotenv()

class DeepSeekSQLEngine:
    """
    AI Engine buat generate SQL query dari prompt bahasa manusia.
    Pake DeepSeek API (via OpenAI compatible endpoint).
    """
    
    def __init__(self, api_key: str = None):
        """
        Init AI Engine.
        Kalo api_key kosong, otomatis baca dari .env
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        if self.api_key and self.api_key != "sk-your-deepseek-api-key-here":
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            self.is_ready = True
        else:
            self.client = None
            self.is_ready = False
    
    def is_available(self) -> bool:
        """Cek apakah AI Engine siap digunakan"""
        return self.is_ready
    
    def generate_sql(self, user_prompt: str, ddl_context: str, db_type: str) -> tuple[str, str]:
        """
        Generate SQL dari prompt user + DDL context.
        
        Parameters:
        - user_prompt: Pertanyaan user dalam bahasa manusia
        - ddl_context: DDL compact dari database
        - db_type: PostgreSQL/MySQL/MariaDB/SQLite
        
        Returns:
        - (sql_query, explanation)
        """
        if not self.is_ready:
            return None, "⚠️ AI Engine belum siap. Tambahkan token DeepSeek di file .env\n\nPanduan: https://platform.deepseek.com/api_keys"
        
        system_prompt = f"""Kamu adalah database expert senior dengan 20 tahun pengalaman di {db_type}.

## ATURAN STRICT:
1. HANYA generate SQL query yang diakhiri dengan tanda titik koma (;)
2. Query HARUS valid untuk {db_type}
3. Selalu gunakan LIMIT 1000 untuk SELECT query (kecuali user minta spesifik)
4. Gunakan nama tabel dan kolom PERSIS seperti di DDL
5. Untuk DELETE/UPDATE/DROP, TOLAK dan jelaskan kenapa tidak direkomendasikan
6. Gunakan INNER JOIN / LEFT JOIN sesuai kebutuhan
7. Tambahkan komentar SQL (--) untuk menjelaskan logika kompleks
8. Hindari SELECT *
9. Selalu pertimbangkan performance (gunakan index, hindari subquery berlebihan)

## FORMAT OUTPUT:
Setelah query, berikan penjelasan singkat 2-3 kalimat tentang:
- Apa yang dilakukan query ini
- Potensi performance issue (jika ada)
- Saran optimasi (jika ada)

Pisahkan query dan penjelasan dengan '---EXPLANATION---'"""

        user_message = f"""## STRUKTUR DATABASE:
{ddl_context}

## PERMINTAAN USER:
{user_prompt}

Buatkan query SQL yang efisien dan aman."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,  # Low temperature buat konsistensi
                max_tokens=2000,
                stream=False
            )
            
            full_response = response.choices[0].message.content
            
            # Parse query dan explanation
            if '---EXPLANATION---' in full_response:
                sql_query, explanation = full_response.split('---EXPLANATION---', 1)
            else:
                sql_query = full_response
                explanation = "Tidak ada penjelasan tambahan."
            
            # Bersihin query dari markdown
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            return sql_query, explanation.strip()
            
        except Exception as e:
            error_msg = str(e)
            
            if "401" in error_msg or "Unauthorized" in error_msg:
                return None, "🔒 TOKEN TIDAK VALID!\n\nToken DeepSeek lo salah atau expired.\nCek di: https://platform.deepseek.com/api_keys"
            elif "402" in error_msg or "insufficient" in error_msg.lower():
                return None, "💰 SALDO HABIS!\n\nTop-up saldo lo di: https://platform.deepseek.com/billing"
            elif "429" in error_msg:
                return None, "⏱️ TERLALU BANYAK REQUEST!\n\nTunggu sebentar dan coba lagi."
            elif "500" in error_msg or "503" in error_msg:
                return None, "🔧 SERVER DEEPSEEK SIBUK!\n\nCoba lagi dalam beberapa menit."
            else:
                return None, f"❌ ERROR: {error_msg}\n\n💡 Cek koneksi internet atau coba lagi nanti."


# ====================================
# CONTOH PENGGUNAAN (buat testing)
# ====================================
if __name__ == "__main__":
    # Contoh token (GANTI INI!)
    SAMPLE_TOKEN = "sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    
    # Init engine
    engine = DeepSeekSQLEngine(api_key=SAMPLE_TOKEN)
    
    if engine.is_available():
        print("✅ AI Engine siap digunakan!")
    else:
        print("❌ AI Engine belum siap. Isi token dulu.")
        print("📝 Panduan: https://platform.deepseek.com/api_keys")