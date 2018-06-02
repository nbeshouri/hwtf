import sqlite3
import bz2
import pickle
from io import BytesIO


class KeyValueStore:
        
    def __init__(self, file_path):
        self._db_conn = sqlite3.connect(file_path)
        tables = self._db_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        tables = list(tables)
        if not tables or tables[0][0] != 'key_value_store':
            self._db_conn.execute('CREATE TABLE key_value_store (key, value)')
            self._db_conn.commit()
    
    # def __setitem__(self, key, value):
    #     if key in self:
    #         del self[key]
    #     self._db_conn.execute("INSERT INTO key_value_store VALUES (?, ?)", (key, value))
    #     self._db_conn.commit()
    # 
    # def get(self, key):
    #     sql = "SELECT value FROM key_value_store WHERE key = ?"
    #     results = self._db_conn.execute(sql, (key,))
    #     results = list(results)
    #     if not results:
    #         return None
    #     return results[0][0]
    
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        bytes_io = BytesIO()
        pickle.dump(value, bytes_io, protocol=pickle.HIGHEST_PROTOCOL)
        value = bz2.compress(bytes_io.getvalue())
        self._db_conn.execute(f"INSERT INTO key_value_store VALUES (?, ?)", (key, value))
        self._db_conn.commit()
    
    def get(self, key):
        sql = "SELECT value FROM key_value_store WHERE key = ?"
        results = self._db_conn.execute(sql, (key,))
        results = list(results)
        if not results:
            return None
        result = results[0][0]
        decompressed = bz2.decompress(result)
        bytes_io = BytesIO(decompressed)
        return pickle.load(bytes_io)
    
    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(f"Does not contain '{key}'.")
        return value
        
    def __contains__(self, key):
        value = self.get(key)
        return value is not None
        
    def __delitem__(self, key):
        self._db_conn.execute("DELETE FROM key_value_store WHERE key = ?", (key,))
        self._db_conn.commit()
        
    def __del__(self):
        self._db_conn.close()
        
    def keys(self):
        sql = "SELECT key FROM key_value_store"
        results = self._db_conn.execute(sql)
        for result in results:
            yield result[0]
            
    def __len__(self):
        count = 0
        for _ in self.keys():
            count += 1
        return count
