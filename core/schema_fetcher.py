from sqlalchemy import inspect, text
import pandas as pd

class SchemaFetcher:
    """Fetch DDL & Schema Information"""
    
    def __init__(self, engine_manager):
        self.db = engine_manager
    
    def get_full_schema(self) -> dict:
        """Ambil full schema: tabel + kolom + tipe data + relasi"""
        inspector = inspect(self.db.engine)
        schema_info = {}
        
        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                col_info = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': col.get('default'),
                    'primary_key': False,
                    'foreign_key': None
                }
                
                # Check primary key
                pk_constraint = inspector.get_pk_constraint(table_name)
                if col['name'] in pk_constraint.get('constrained_columns', []):
                    col_info['primary_key'] = True
                
                columns.append(col_info)
            
            # Get foreign keys
            try:
                foreign_keys = inspector.get_foreign_keys(table_name)
                for fk in foreign_keys:
                    for col in fk.get('constrained_columns', []):
                        for col_info in columns:
                            if col_info['name'] == col:
                                col_info['foreign_key'] = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
            except:
                pass  # Beberapa DB mungkin tidak support FK inspection
            
            schema_info[table_name] = columns
        
        return schema_info
    
    def get_compact_ddl(self) -> str:
        """Bikin DDL compact buat dikirim ke AI (hemat token)"""
        schema = self.get_full_schema()
        lines = []
        
        for table_name, columns in schema.items():
            col_strs = []
            for col in columns:
                parts = [f"{col['name']} {col['type']}"]
                if col['primary_key']:
                    parts.append("PK")
                if col['foreign_key']:
                    parts.append(f"FK->{col['foreign_key']}")
                col_strs.append(" ".join(parts))
            
            lines.append(f"📋 {table_name}({', '.join(col_strs)})")
        
        return "\n".join(lines)
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Ambil sample data buat context AI"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.db.execute_query(query)