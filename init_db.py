import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

DB_FILE = "crop_predict.db"

def init_database():
    # Connect to database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Drop existing table to start fresh
    cursor.execute('DROP TABLE IF EXISTS commodity_prices')
    
    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS commodity_prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        commodity TEXT,
                        price REAL)''')
    
    # Generate sample data for the last 2 years
    commodities = [
        "Rice", "Wheat", "Gram Dal", "Tur/Arhar Dal", "Urad Dal", "Moong Dal", "Masoor Dal",
        "Groundnut Oil", "Mustard Oil", "Vanaspati", "Soya Oil", "Sunflower Oil", "Palm Oil",
        "Sugar", "Gur", "Tea Loose", "Milk", "Salt Pack (Iodised)",
        "Potato", "Onion", "Tomato"
    ]
    
    # Base prices for each commodity (in rupees)
    base_prices = {
        "Rice": 35, "Wheat": 25,
        "Gram Dal": 80, "Tur/Arhar Dal": 110, "Urad Dal": 105, "Moong Dal": 100, "Masoor Dal": 85,
        "Groundnut Oil": 180, "Mustard Oil": 170, "Vanaspati": 120, "Soya Oil": 140, 
        "Sunflower Oil": 160, "Palm Oil": 130,
        "Sugar": 40, "Gur": 45, "Tea Loose": 250, "Milk": 55, "Salt Pack (Iodised)": 20,
        "Potato": 25, "Onion": 30, "Tomato": 40
    }
    
    # Generate dates for the last 2 years
    end_date = datetime.now().replace(day=1)  # Start from beginning of current month
    start_date = end_date - timedelta(days=730)  # 2 years ago
    dates = pd.date_range(start=start_date, end=end_date, freq='M')
    dates = [d.strftime('%Y-%m-%d') for d in dates]
    
    # Generate and insert sample data
    for commodity in commodities:
        base_price = base_prices[commodity]
        trend = np.random.uniform(-0.1, 0.15)  # Random trend between -10% and +15%
        
        for date in dates:
            # Add some randomness and trend to the price
            current_date = datetime.strptime(date, '%Y-%m-%d')
            month = current_date.month
            
            # Seasonal variation
            seasonal_factor = 1.0
            if month in [6, 7, 8]:  # Summer months
                seasonal_factor = 1.1
            elif month in [12, 1, 2]:  # Winter months
                seasonal_factor = 0.9
            
            # Calculate price with trend, seasonality and some randomness
            days_passed = (current_date - datetime.strptime(dates[0], '%Y-%m-%d')).days
            trend_factor = 1 + (trend * days_passed / 365)  # Yearly trend
            random_factor = np.random.uniform(0.95, 1.05)  # ±5% random variation
            
            price = base_price * trend_factor * seasonal_factor * random_factor
            
            # Insert the data
            cursor.execute('''INSERT INTO commodity_prices (date, commodity, price)
                            VALUES (?, ?, ?)''', (date, commodity, round(price, 2)))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database initialized with sample data!")

if __name__ == "__main__":
    init_database() 