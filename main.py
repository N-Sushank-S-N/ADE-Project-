import numpy as np
import time
import sqlite3
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI

# --- 1. Database Setup ---
DB_FILE = "abdee.db"

def init_db():
    """Creates the database table if it doesn't exist yet."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feature_states (
            user_id TEXT,
            feature_id TEXT,
            score REAL,
            last_updated REAL,
            activity_density REAL,
            decay_multiplier REAL,
            UNIQUE(user_id, feature_id)
        )
    ''')
    conn.commit()
    conn.close()

# Run this the moment the server starts
init_db() 

# --- 2. Data Models ---
class FeatureState(BaseModel):
    feature_id: str
    score: float
    last_updated: float
    activity_density: float
    decay_multiplier: float

class NewEvent(BaseModel):
    user_id: str
    feature_id: str
    weight: float = 1.0

class Feedback(BaseModel):
    user_id: str
    feature_id: str
    action: str 

app = FastAPI()

# --- 3. API Endpoints ---
@app.get("/active_features")
def get_active_features(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Fetch data directly from the SQLite Database
    c.execute("SELECT feature_id, score, last_updated, activity_density, decay_multiplier FROM feature_states WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"message": "User not found"}

    current_time = time.time()
    active_features = []
    
    for row in rows:
        f_id, score, last_updated, density, multiplier = row
        
        # Calculate mathematical decay
        base_lambda = 0.000005 
        dynamic_lambda = base_lambda * multiplier
        decayed_score = score * np.exp(-dynamic_lambda * (current_time - last_updated))
        decayed_score = max(0, decayed_score)

        # Filtering Logic (Score > 0.05 and Freshness < 7 days)
        if decayed_score >= 0.05 and (current_time - last_updated) < (86400 * 7):
            active_features.append({
                "feature_id": f_id,
                "score": decayed_score,
                "last_updated": last_updated,
                "activity_density": density,
                "decay_multiplier": multiplier
            })
            
    return {"user_id": user_id, "active_features": active_features}

@app.post("/add_event")
def add_event(event: NewEvent):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current_time = time.time()
    
    # 1. Check if the user/feature combination already exists
    c.execute("SELECT score, activity_density FROM feature_states WHERE user_id=? AND feature_id=?", (event.user_id, event.feature_id))
    row = c.fetchone()
    
    if row:
        # Update existing feature (Reinforcement)
        new_score = min(1.0, row[0] + (event.weight * 0.2))
        new_density = row[1] + 1.0
        c.execute("UPDATE feature_states SET score=?, last_updated=?, activity_density=? WHERE user_id=? AND feature_id=?", 
                  (new_score, current_time, new_density, event.user_id, event.feature_id))
    else:
        # Insert brand new feature
        c.execute("INSERT INTO feature_states (user_id, feature_id, score, last_updated, activity_density, decay_multiplier) VALUES (?, ?, ?, ?, ?, ?)",
                  (event.user_id, event.feature_id, min(1.0, event.weight * 0.5), current_time, 1.0, 1.0))
        
    # 2. Apply Cross-Suppression to all *other* features this user has
    suppression = event.weight * 0.05
    c.execute("UPDATE feature_states SET score = MAX(0.0, score - ?) WHERE user_id=? AND feature_id != ?", 
              (suppression, event.user_id, event.feature_id))
              
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/feedback")
def process_feedback(fb: Feedback):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT score, decay_multiplier FROM feature_states WHERE user_id=? AND feature_id=?", (fb.user_id, fb.feature_id))
    row = c.fetchone()
    
    if row:
        score, multiplier = row
        if fb.action == 'engage':
            new_mult = multiplier * 0.8
            new_score = min(1.0, score + 0.1)
        else: # ignore
            new_mult = multiplier * 1.5
            new_score = max(0.0, score - 0.2)
            
        c.execute("UPDATE feature_states SET score=?, decay_multiplier=?, last_updated=? WHERE user_id=? AND feature_id=?",
                  (new_score, new_mult, time.time(), fb.user_id, fb.feature_id))
        conn.commit()
        conn.close()
        return {"status": "learned"}
        
    conn.close()
    return {"status": "not found"}