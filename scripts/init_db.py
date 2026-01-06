import sqlite3
from pathlib import Path

def init_database():
    db_path = Path("database/leads.db")
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables from schema.sql
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            role TEXT NOT NULL,
            industry TEXT NOT NULL,
            website TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            linkedin_url TEXT NOT NULL,
            country TEXT NOT NULL,
            status TEXT DEFAULT 'NEW',
            company_size TEXT,
            persona_tag TEXT,
            pain_points TEXT,
            buying_triggers TEXT,
            confidence_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            lead_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            variant TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            sent_at TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );
        
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'RUNNING',
            dry_run BOOLEAN DEFAULT 1,
            total_leads INTEGER DEFAULT 0,
            leads_enriched INTEGER DEFAULT 0,
            messages_generated INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            messages_failed INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_messages_lead ON messages(lead_id);
        CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()