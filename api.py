from flask import Flask, request, jsonify, render_template, send_from_directory, session
import sqlite3
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from flask_cors import CORS
import os
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import random
from datetime import datetime, timedelta
from database import verify_database, store_otp, verify_otp, DB_FILE
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, supports_credentials=True)  # Allow frontend access with credentials
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USERNAME = "your-email@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "your-app-password"     # Replace with your app password

# SMS configuration (using Twilio)
TWILIO_ACCOUNT_SID = "your-twilio-sid"
TWILIO_AUTH_TOKEN = "your-twilio-token"
TWILIO_PHONE_NUMBER = "your-twilio-phone"

def send_email_otp(contact, otp):
    """Send OTP via email."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USERNAME
        msg['To'] = contact
        msg['Subject'] = "Your Verification Code"

        body = f"""
        <html>
            <body>
                <h2>Your Verification Code</h2>
                <p>Your OTP for registration is: <strong>{otp}</strong></p>
                <p>This code will expire in 5 minutes.</p>
                <p>If you didn't request this code, please ignore this email.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        app.logger.error(f"Error sending email: {str(e)}")
        return False

def send_sms_otp(contact, otp):
    """Send OTP via SMS using Twilio."""
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=f"Your verification code is: {otp}. This code will expire in 5 minutes.",
            from_=TWILIO_PHONE_NUMBER,
            to=contact
        )
        return True
    except Exception as e:
        app.logger.error(f"Error sending SMS: {str(e)}")
        return False

def send_otp(contact, otp):
    """Send OTP based on contact type (email or phone)."""
    if '@' in contact:
        return send_email_otp(contact, otp)
    else:
        return send_sms_otp(contact, otp)

# Authentication middleware
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

# User Authentication Endpoints
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        contact = data.get('contact')

        if not username or not password or not contact:
            app.logger.error("Missing required fields in registration")
            return jsonify({"error": "Username, password, and contact are required"}), 400

        # Validate contact format
        is_email = '@' in contact
        is_phone = contact.isdigit() and len(contact) == 10
        
        if not (is_email or is_phone):
            app.logger.error(f"Invalid contact format: {contact}")
            return jsonify({"error": "Invalid contact format. Please enter a valid email or phone number"}), 400

        # Verify database setup
        try:
            verify_database()
        except Exception as e:
            app.logger.error(f"Database verification failed: {str(e)}")
            return jsonify({"error": "Database setup failed"}), 500

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # Check if username exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                app.logger.error(f"Username already exists: {username}")
                return jsonify({"error": "Username already exists"}), 409

            # Check if contact exists
            cursor.execute("SELECT id FROM users WHERE contact = ?", (contact,))
            if cursor.fetchone():
                app.logger.error(f"Contact already registered: {contact}")
                return jsonify({"error": "Contact already registered"}), 409

            # Hash password and store user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, contact) VALUES (?, ?, ?)",
                (username, hashed_password, contact)
            )
            conn.commit()
            app.logger.info(f"User {username} registered successfully")

            # Generate and send OTP
            otp = ''.join(random.choices('0123456789', k=6))
            expiry = datetime.now() + timedelta(minutes=5)
            
            # Store OTP in database
            if not store_otp(contact, otp, expiry.strftime('%Y-%m-%d %H:%M:%S')):
                app.logger.error(f"Failed to store OTP for {contact}")
                return jsonify({"error": "Failed to generate verification code"}), 500
            
            # Send OTP via email or SMS
            if not send_otp(contact, otp):
                app.logger.error(f"Failed to send OTP to {contact}")
                return jsonify({"error": "Failed to send verification code"}), 500

            return jsonify({"message": "Registration successful. Please check your email/phone for verification code."}), 201

        except sqlite3.Error as e:
            app.logger.error(f"Database error during registration: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        finally:
            conn.close()

    except Exception as e:
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        contact = data.get('contact')
        otp = data.get('otp')

        if not contact or not otp:
            return jsonify({"error": "Contact and OTP are required"}), 400

        if verify_otp(contact, otp):
            return jsonify({"message": "Verification successful"}), 200
        else:
            return jsonify({"error": "Invalid or expired OTP"}), 400

    except Exception as e:
        app.logger.error(f"OTP verification error: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500

@app.route("/resend_otp", methods=["POST"])
def resend_otp():
    try:
        data = request.get_json()
        contact = data.get('contact')

        if not contact:
            return jsonify({"error": "Contact is required"}), 400

        # Generate new OTP
        otp = ''.join(random.choices('0123456789', k=6))
        expiry = datetime.now() + timedelta(minutes=5)
        
        # Store new OTP in database
        store_otp(contact, otp, expiry.strftime('%Y-%m-%d %H:%M:%S'))
        
        # TODO: Implement actual OTP sending via email/SMS
        print(f"New OTP for {contact}: {otp}")  # For development only

        return jsonify({"message": "New verification code sent"}), 200

    except Exception as e:
        app.logger.error(f"Resend OTP error: {str(e)}")
        return jsonify({"error": "Failed to resend code"}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get user
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return jsonify({
                "message": "Login successful",
                "user": {"id": user[0], "username": username}
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/check_auth", methods=["GET"])
def check_auth():
    if 'user_id' in session:
        return jsonify({
            "authenticated": True,
            "user": {"id": session['user_id'], "username": session['username']}
        }), 200
    return jsonify({"authenticated": False}), 401

# ✅ Serve index.html (Frontend)
@app.route("/")
def home():
    return render_template("index.html")

# ✅ Serve Static Files (script.js, styles.css)
@app.route("/static/<path:filename>")
def static_files(filename):
    try:
        return send_from_directory("static", filename)
    except Exception as e:
        app.logger.error(f"Error serving static file {filename}: {str(e)}")
        return f"Error: {str(e)}", 500

# ✅ Fetch Historical Prices
@app.route("/get_prices", methods=["GET"])
@login_required
def get_prices():
    commodity = request.args.get("commodity")
    if not commodity:
        return jsonify({"error": "Commodity is required"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Use case-insensitive comparison
    cursor.execute("""
        SELECT date, price 
        FROM commodity_prices 
        WHERE LOWER(commodity) = LOWER(?) 
        ORDER BY date
    """, (commodity,))
    
    data = cursor.fetchall()
    conn.close()

    if not data:
        return jsonify({"error": f"No data available for {commodity}"}), 404

    prices = [{"date": row[0], "price": row[1]} for row in data]
    return jsonify(prices)

# ✅ Predict Future Prices Using ML Model
@app.route("/predict_prices", methods=["GET"])
@login_required
def predict_prices():
    try:
        commodity = request.args.get("commodity")
        if not commodity:
            return jsonify({"error": "Commodity is required"}), 400

        # Fetch historical price data with case-insensitive comparison
        conn = sqlite3.connect(DB_FILE)
        query = """
            SELECT date, price 
            FROM commodity_prices 
            WHERE LOWER(commodity) = LOWER(?) 
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(commodity,))
        conn.close()

        if df.empty:
            return jsonify({"error": f"No data available for {commodity}"}), 404

        # Convert date column to datetime index and handle duplicates
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
        df = df.drop_duplicates(subset=["date"], keep="first")
        df.set_index("date", inplace=True)
        df = df.sort_index()
        
        # Ensure we have numeric prices and handle missing values
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df.dropna()

        if len(df) < 12:  # Need at least 12 months of data
            return jsonify({"error": f"Insufficient historical data for {commodity}"}), 400

        # Resample to yearly frequency and fill missing values
        yearly_df = df.resample('Y').mean()
        yearly_df = yearly_df.fillna(method='ffill').fillna(method='bfill')

        # Calculate historical trend
        historical_prices = yearly_df["price"].values
        historical_years = len(historical_prices)
        
        # Special handling for different commodity categories
        def get_commodity_category(commodity):
            commodity = commodity.lower()
            categories = {
                'vegetables': ['onion', 'potato', 'tomato'],
                'pulses': ['gram dal', 'tur/arhar dal', 'urad dal', 'moong dal', 'masoor dal'],
                'oils': ['groundnut oil', 'mustard oil', 'vanaspati', 'soya oil', 'sunflower oil', 'palm oil'],
                'cereals': ['rice', 'wheat'],
                'others': ['sugar', 'gur', 'tea loose', 'milk', 'salt pack (iodised)']
            }
            for category, items in categories.items():
                if commodity in items:
                    return category
            return 'others'

        # Get category-specific parameters
        category = get_commodity_category(commodity)
        
        # Define seasonal patterns and volatility by category
        category_params = {
            'vegetables': {
                'min_growth': 0.08,
                'max_growth': 0.25,
                'volatility_range': (0.85, 1.15),
                'peak_months': {
                    'onion': [7, 8, 9],    # July-September
                    'potato': [11, 12, 1],  # November-January
                    'tomato': [6, 7, 8]     # June-August
                },
                'harvest_months': {
                    'onion': [1, 2, 3],     # January-March
                    'potato': [2, 3, 4],    # February-April
                    'tomato': [2, 3, 4]     # February-April
                },
                'peak_factor': 1.4,
                'harvest_factor': 0.9,
                'min_threshold': 0.9
            },
            'pulses': {
                'min_growth': 0.06,
                'max_growth': 0.18,
                'volatility_range': (0.95, 1.08),
                'peak_months': [10, 11, 12],  # October-December
                'harvest_months': [2, 3, 4],  # February-April
                'peak_factor': 1.2,
                'harvest_factor': 0.95,
                'min_threshold': 0.95
            },
            'oils': {
                'min_growth': 0.05,
                'max_growth': 0.15,
                'volatility_range': (0.97, 1.06),
                'peak_months': [11, 12, 1],  # November-January
                'harvest_months': [3, 4, 5],  # March-May
                'peak_factor': 1.15,
                'harvest_factor': 0.95,
                'min_threshold': 0.97
            },
            'cereals': {
                'min_growth': 0.04,
                'max_growth': 0.12,
                'volatility_range': (0.98, 1.05),
                'peak_months': [8, 9, 10],  # August-October
                'harvest_months': [3, 4, 5],  # March-May
                'peak_factor': 1.1,
                'harvest_factor': 0.97,
                'min_threshold': 0.98
            },
            'others': {
                'min_growth': 0.03,
                'max_growth': 0.10,
                'volatility_range': (0.99, 1.02),
                'peak_months': [11, 12, 1],  # November-January
                'harvest_months': None,
                'peak_factor': 1.05,
                'harvest_factor': 1.0,
                'min_threshold': 0.99
            }
        }

        params = category_params[category]
        
        if historical_years >= 2:
            avg_yearly_growth = (historical_prices[-1] / historical_prices[0]) ** (1 / historical_years) - 1
            growth_rate = np.clip(avg_yearly_growth, params['min_growth'], params['max_growth'])
        else:
            growth_rate = params['min_growth']

        # Train SARIMAX Model with category-specific parameters
        if category in ['vegetables', 'pulses']:
            model = SARIMAX(
                yearly_df["price"],
                order=(2, 1, 2),
                seasonal_order=(2, 1, 1, 12),
                enforce_stationarity=False
            )
        else:
            model = SARIMAX(
                yearly_df["price"],
                order=(1, 1, 1),
                seasonal_order=(1, 1, 0, 12),
                enforce_stationarity=False
            )
        
        sarimax_model = model.fit(disp=False)

        # Make predictions for the next 5 years
        forecast = sarimax_model.get_forecast(steps=5)
        forecasted_values = forecast.predicted_mean
        confidence_intervals = forecast.conf_int()

        # Get the last actual price and historical volatility
        last_actual_price = yearly_df["price"].iloc[-1]
        historical_volatility = df["price"].std() / df["price"].mean()

        # Apply growth and seasonal adjustments
        forecasted_values_adj = []
        current_price = last_actual_price
        for i in range(len(forecasted_values)):
            model_prediction = forecasted_values[i]
            month = (yearly_df.index[-1].month + i) % 12
            
            # Calculate seasonal factor
            seasonal_factor = 1.0
            if category == 'vegetables':
                peak_months = params['peak_months'][commodity.lower()]
                harvest_months = params['harvest_months'][commodity.lower()]
            else:
                peak_months = params['peak_months']
                harvest_months = params['harvest_months']

            if peak_months and month in peak_months:
                seasonal_factor = params['peak_factor'] + (historical_volatility * 0.8)
            elif harvest_months and month in harvest_months:
                seasonal_factor = params['harvest_factor'] - (historical_volatility * 0.2)

            min_next_price = current_price * (1 + growth_rate) * seasonal_factor
            max_next_price = current_price * (1 + growth_rate * 2) * seasonal_factor
            adjusted_price = np.clip(model_prediction * seasonal_factor, min_next_price, max_next_price)
            
            forecasted_values_adj.append(adjusted_price)
            current_price = adjusted_price

        forecasted_values = np.array(forecasted_values_adj)

        # Prepare yearly predictions
        future_dates = pd.date_range(
            start=yearly_df.index[-1] + pd.DateOffset(years=1),
            periods=5,
            freq='Y'
        )
        
        yearly_data = []
        for date, price in zip(future_dates, forecasted_values):
            safe_price = float(price) if not np.isnan(price) else last_actual_price * (1 + growth_rate)
            yearly_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": round(safe_price, 2)
            })

        # Generate monthly data by interpolating between yearly predictions
        monthly_dates = pd.date_range(
            start=future_dates[0],
            end=future_dates[-1] + pd.DateOffset(years=1),
            freq='M'
        )[:-1]  # Remove last month to get exactly 60 months

        # Create a series with yearly predictions for interpolation
        yearly_series = pd.Series(
            [last_actual_price] + [pred["price"] for pred in yearly_data],
            index=[yearly_df.index[-1]] + [pd.to_datetime(pred["date"]) for pred in yearly_data]
        )

        # Interpolate monthly values with improved method
        monthly_series = yearly_series.reindex(monthly_dates)
        monthly_series = monthly_series.interpolate(method='cubic')
        
        # Adjust monthly variations based on category
        random_variations = np.random.uniform(*params['volatility_range'], len(monthly_series))
        month_indices = pd.DatetimeIndex(monthly_dates).month
        seasonal_factors = np.ones(len(monthly_series))

        # Apply seasonal patterns
        if category == 'vegetables':
            peak_months = params['peak_months'][commodity.lower()]
            harvest_months = params['harvest_months'][commodity.lower()]
        else:
            peak_months = params['peak_months']
            harvest_months = params['harvest_months']

        if peak_months:
            peak_months_mask = np.isin(month_indices, peak_months)
            seasonal_factors[peak_months_mask] *= (params['peak_factor'] + historical_volatility)

        if harvest_months:
            harvest_months_mask = np.isin(month_indices, harvest_months)
            seasonal_factors[harvest_months_mask] *= (params['harvest_factor'] - historical_volatility * 0.2)

        monthly_series = monthly_series * random_variations * seasonal_factors

        # Ensure no values are below minimum threshold
        min_threshold = last_actual_price * params['min_threshold']
        monthly_series = monthly_series.clip(lower=min_threshold)
        monthly_series = monthly_series.fillna(method='ffill').fillna(method='bfill')
        
        monthly_data = []
        for date, price in zip(monthly_dates, monthly_series):
            safe_price = float(price) if not np.isnan(price) else yearly_data[0]["price"]
            monthly_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": round(safe_price, 2)
            })

        return jsonify({
            "yearly_predictions": yearly_data,
            "monthly_predictions": monthly_data
        })

    except Exception as e:
        app.logger.error(f"Error in predict_prices: {str(e)}")
        return jsonify({"error": f"Error generating predictions: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
