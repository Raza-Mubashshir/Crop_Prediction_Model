import pandas as pd
import numpy as np
import sqlite3
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
import streamlit as st
from database import create_tables, register_user, login_user

# Ensure tables exist
create_tables()

# Connect to dataset
file_path = "DatasetSIH1647.csv"
df = pd.read_csv(file_path)

df.set_index('Commodities', inplace=True)
df = df.T
df.index = pd.date_range(start='2014', periods=len(df), freq='YE')
df = df.ffill()

commodities = df.columns.tolist()

# --- User Authentication ---
st.title("Login to CropSight")

if "user_id" not in st.session_state:
    st.session_state.user_id = None

option = st.radio("Choose an option:", ["Login", "Signup"])

if option == "Signup":
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")
    if st.button("Sign Up"):
        if register_user(username, password):
            st.success("Account created! Please log in.")
        else:
            st.error("Username already taken.")

elif option == "Login":
    username = st.text_input("Enter Username")
    password = st.text_input("Enter Password", type="password")
    if st.button("Log In"):
        user_id = login_user(username, password)
        if user_id:
            st.session_state.user_id = user_id
            st.success(f"Logged in as {username}")
        else:
            st.error("Invalid credentials.")

if st.session_state.user_id:
    st.title("Commodity Price Forecasting")

    selected_commodity = st.selectbox("Choose a Commodity", commodities)

    if st.button("Submit"):
        conn = sqlite3.connect("crop_predict.db")
        cursor = conn.cursor()

        # Check if forecast exists
        cursor.execute("SELECT year, forecast_price FROM predictions WHERE user_id=? AND commodity=?", 
                       (st.session_state.user_id, selected_commodity))
        existing_forecast = cursor.fetchall()

        if existing_forecast:
            st.write(f"### {selected_commodity} Price Forecast (2025-2029) - Stored Data")
            forecast_df = pd.DataFrame(existing_forecast, columns=['Year', f'{selected_commodity}_Price_Forecast'])
        else:
            # Generate new forecast
            data = df[selected_commodity]
            model = SARIMAX(data, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12))
            sarimax_model = model.fit(disp=False)
            forecast = sarimax_model.get_forecast(steps=5)
            forecasted_values = forecast.predicted_mean

            forecast_years = pd.date_range(start='2025', periods=5, freq='YE')
            forecast_df = pd.DataFrame({'Year': forecast_years, f'{selected_commodity}_Price_Forecast': forecasted_values})

            # Store in SQL
            for year, price in zip(forecast_years.year, forecasted_values):
                cursor.execute("INSERT INTO predictions (user_id, commodity, year, forecast_price) VALUES (?, ?, ?, ?)", 
                               (st.session_state.user_id, selected_commodity, year, price))
            conn.commit()

        conn.close()
        st.write(forecast_df)
        
        # Plot chart
        plt.figure(figsize=(10, 6))
        plt.plot(data, label=f'Actual {selected_commodity} Prices')
        plt.plot(forecast_df['Year'], forecast_df[f'{selected_commodity}_Price_Forecast'], label='Forecast', color='orange')
        plt.title(f'{selected_commodity} Price Forecast')
        plt.xlabel('Year')
        plt.ylabel('Price')
        plt.legend()
        st.pyplot(plt)
