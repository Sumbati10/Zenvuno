"""
Zenvuno Database Models
SQLite database for storing field boundaries and analysis results
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path='zenvuno.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fields table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                coordinates TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_id INTEGER,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date TEXT,
                end_date TEXT,
                current_ndvi REAL,
                status TEXT,
                timeseries TEXT,
                FOREIGN KEY (field_id) REFERENCES fields (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_field(self, name: str, coordinates: List[List[float]]) -> int:
        """Save a field boundary to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fields (name, coordinates, updated_at)
            VALUES (?, ?, ?)
        ''', (name, json.dumps(coordinates), datetime.now().isoformat()))
        
        field_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return field_id
    
    def get_fields(self) -> List[Dict]:
        """Get all saved fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, coordinates, created_at FROM fields ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        fields = []
        for row in rows:
            fields.append({
                'id': row[0],
                'name': row[1],
                'coordinates': json.loads(row[2]),
                'created_at': row[3]
            })
        
        conn.close()
        return fields
    
    def get_field(self, field_id: int) -> Optional[Dict]:
        """Get a specific field by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, coordinates, created_at FROM fields WHERE id = ?', (field_id,))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return {
                'id': row[0],
                'name': row[1],
                'coordinates': json.loads(row[2]),
                'created_at': row[3]
            }
        
        conn.close()
        return None
    
    def delete_field(self, field_id: int) -> bool:
        """Delete a field by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM fields WHERE id = ?', (field_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def save_analysis_result(self, field_id: int, start_date: str, end_date: str, 
                            current_ndvi: float, status: str, timeseries: List[Dict]) -> int:
        """Save analysis results to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analysis_results (field_id, start_date, end_date, current_ndvi, status, timeseries)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (field_id, start_date, end_date, current_ndvi, status, json.dumps(timeseries)))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return result_id
    
    def get_field_history(self, field_id: int) -> List[Dict]:
        """Get analysis history for a field"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, analysis_date, start_date, end_date, current_ndvi, status, timeseries
            FROM analysis_results 
            WHERE field_id = ? 
            ORDER BY analysis_date DESC
        ''', (field_id,))
        
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'analysis_date': row[1],
                'start_date': row[2],
                'end_date': row[3],
                'current_ndvi': row[4],
                'status': row[5],
                'timeseries': json.loads(row[6])
            })
        
        conn.close()
        return history
