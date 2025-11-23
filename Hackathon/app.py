import os
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
from prophet import Prophet
import plotly.graph_objs as go
import plotly.offline as pyo
from sklearn.metrics import mean_absolute_error, mean_squared_error

#Loading the Data set into air_data

# Load CSV and handle date format
air_data = pd.read_csv("dataSet.csv")
air_data['date'] = pd.to_datetime(air_data['date'], format='%Y/%m/%d')

#Creating a data set for Prophet
pm_data=pd.DataFrame()
pm_data['ds']=air_data['date']
pm_data['y']=air_data[' pm25']

#Creating a Prophet model my instantaiting the Prophet class
model=Prophet()

#Fitting the data frame into the model
model.fit(pm_data)

#Create a future dataframe for 365 days ahead
future=model.make_future_dataframe(periods=365)

#forecasting
forecast=model.predict(future)

# Calculate model performance metrics
train_predictions = forecast[forecast['ds'].isin(pm_data['ds'])][['ds', 'yhat']]
train_merged = pd.merge(pm_data, train_predictions, on='ds', how='inner')
mae = mean_absolute_error(train_merged['y'], train_merged['yhat'])
rmse = np.sqrt(mean_squared_error(train_merged['y'], train_merged['yhat']))
mape = np.mean(np.abs((train_merged['y'] - train_merged['yhat']) / train_merged['y'])) * 100

#Extracting the predicted value
# result=int(forecast.loc[forecast['ds'].isin(['2024-12-31'])]['yhat'].values[0])


# App initialization
app = Flask(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))
app.app_context().push()


@app.route('/', methods=['GET', 'POST'])
def home():
    min_date = pm_data['ds'].min().date().isoformat()
    max_date = pm_data['ds'].max().date().isoformat()
    return render_template('date.html', min_date=min_date, max_date=max_date)


@app.route('/output', methods=['POST'])
def output():
    if request.method == 'POST':
        inputdate = str(request.form['input_date'])
        # Convert input date to datetime for matching
        input_dt = pd.to_datetime(inputdate)
        forecast['ds'] = pd.to_datetime(forecast['ds'])
        matching_rows = forecast.loc[forecast['ds'] == input_dt]
        
        # If no match, find closest available date in forecast
        if len(matching_rows) == 0:
            closest_idx = (forecast['ds'] - input_dt).abs().idxmin()
            result = int(forecast.loc[closest_idx]['yhat'])
            inputdate = str(forecast.loc[closest_idx]['ds'].date())
            date_message = f"Date not found, showing closest available: {inputdate}"
        else:
            result = int(matching_rows['yhat'].values[0])
            date_message = ""
        
        # Determine AQI category and color
        if result <= 50:
            aqi_category = "Good"
            aqi_color = "#00e400"
        elif result <= 100:
            aqi_category = "Moderate"
            aqi_color = "#ffff00"
        elif result <= 150:
            aqi_category = "Unhealthy for Sensitive Groups"
            aqi_color = "#ff7e00"
        elif result <= 200:
            aqi_category = "Unhealthy"
            aqi_color = "#ff0000"
        elif result <= 300:
            aqi_category = "Very Unhealthy"
            aqi_color = "#87ceeb"  # light blue
        else:
            aqi_category = "Hazardous"
            aqi_color = "#7e0023"
        
        # Generate chart: last 30 days actual + next 7 days forecast
        today = pd.Timestamp.now()
        last_30_days = pm_data[pm_data['ds'] >= (today - pd.Timedelta(days=30))]
        next_7_days = forecast[(forecast['ds'] >= input_dt) & (forecast['ds'] <= (input_dt + pd.Timedelta(days=7)))]
        
        # Create Plotly chart
        trace1 = go.Scatter(
            x=last_30_days['ds'],
            y=last_30_days['y'],
            mode='lines+markers',
            name='Actual (Last 30 Days)',
            line=dict(color='blue')
        )
        
        trace2 = go.Scatter(
            x=next_7_days['ds'],
            y=next_7_days['yhat'],
            mode='lines+markers',
            name='Predicted (Next 7 Days)',
            line=dict(color='red', dash='dash')
        )
        
        layout = go.Layout(
            title='AQI Trend: Last 30 Days & Next 7 Days Forecast',
            xaxis=dict(title='Date'),
            yaxis=dict(title='PM2.5 Level'),
            hovermode='closest'
        )
        
        fig = go.Figure(data=[trace1, trace2], layout=layout)
        chart_html = pyo.plot(fig, output_type='div', include_plotlyjs='cdn')
        
        return render_template('output.html',
                     inputdate=inputdate,
                     output=result,
                     aqi_category=aqi_category,
                     aqi_color=aqi_color,
                     chart=chart_html,
                     mae=round(mae, 2),
                     rmse=round(rmse, 2),
                     mape=round(mape, 2),
                     date_message=date_message)



if __name__ == '__main__':
    app.run(debug=True)
