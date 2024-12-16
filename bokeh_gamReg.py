import numpy as np
import pandas as pd
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, HoverTool, CheckboxGroup
from bokeh.plotting import figure
from bokeh.models.formatters import DatetimeTickFormatter, NumeralTickFormatter
from pygam import LinearGAM, s
import requests

def fetch_binance_data(symbol="SOLUSDT", interval="5m", limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])
    df["time"] = pd.to_datetime(df["time"], unit='ms')
    df["open"] = pd.to_numeric(df["open"])
    df["close"] = pd.to_numeric(df["close"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["volume"] = pd.to_numeric(df["volume"])
    
    df['candle_color'] = np.where(df['close'] > df['open'], 'green', 'red')
    
    return df

def calculate_gam(df, column, spline_order, n_splines):
    X = np.linspace(0, len(df) - 1, len(df)).reshape(-1, 1)
    y = df[column]
    gam = LinearGAM(s(0, n_splines=n_splines, spline_order=spline_order)).fit(X, y)
    return gam.predict(X)

initial_df = fetch_binance_data()

source = ColumnDataSource(data=dict(time=[], open=[], high=[], low=[], close=[], volume=[], candle_color=[], volume_gam=[], close_gam_20=[], close_gam_50=[]))

def update_data():
    df = fetch_binance_data()
    
    df['volume_gam'] = calculate_gam(df, 'volume', spline_order=5, n_splines=20)
    
    df['close_gam_20'] = calculate_gam(df, 'close', spline_order=5, n_splines=20)
    df['close_gam_50'] = calculate_gam(df, 'close', spline_order=5, n_splines=50)
    
    df['candle_color'] = np.where(df['close'] > df['open'], 'green', 'red')
    
    source.data = df.to_dict(orient='list')


curdoc().add_periodic_callback(update_data, 1000)

p1 = figure(width=1200, height=400, x_axis_type="datetime", y_axis_location="right", toolbar_location="right")
p1.background_fill_color = "#000E14"
p1.xgrid.grid_line_color = None
p1.ygrid.grid_line_color = None
p1.xaxis[0].formatter = DatetimeTickFormatter(days="%m/%d", hours="%H:%M", minutes="%H:%M")
p1.yaxis[0].formatter = NumeralTickFormatter(format="$:.0000")
p1.toolbar.autohide = True

w = 1000 * 60 * 4  # 5 dakika genişliği
p1.segment(x0="time", y0="low", x1="time", y1="high", line_color="candle_color", line_width=0.8, source=source)
p1.vbar(x="time", top="close", bottom="open", width=w, fill_color="candle_color", line_color=None, source=source)

p2 = figure(width=1200, height=150, x_axis_type="datetime", y_axis_location="right", toolbar_location="right")
p2.background_fill_color = "#000E14"
p2.xgrid.grid_line_color = None
p2.ygrid.grid_line_color = None
p2.xaxis[0].formatter = DatetimeTickFormatter(days="%m/%d", hours="%H:%M", minutes="%H:%M")
p2.yaxis[0].formatter = NumeralTickFormatter(format="0")
p2.xaxis.visible = False

p2.vbar(x="time", top="volume", width=w, fill_color="blue", line_color=None, source=source)

volume_gam = p2.line(x="time", y="volume_gam", source=source, color="orange", legend_label="Volume GAM")

close_gam_20_line = p1.line(x="time", y="close_gam_20", source=source, color="orange", legend_label="Close GAM 20", visible=True)
close_gam_50_line = p1.line(x="time", y="close_gam_50", source=source, color="cyan", legend_label="Close GAM 50", visible=False)

hover1 = HoverTool(tooltips=[("Close", "@close{0.00}, @high{0.00}, @low{0.00}, @open{0.00}"),
                            ("Time", "@time{%F %T.%3N}")],
                  formatters={"@time": "datetime"}, mode="mouse")
p1.add_tools(hover1)

hover2 = HoverTool(tooltips=[("Volume", "@volume{0.00}"), ("Time", "@time{%F %T.%3N}")],
                  formatters={"@time": "datetime"}, mode="mouse")
p2.add_tools(hover2)

checkbox_close = CheckboxGroup(labels=["Close GAM 20", "Close GAM 50"], active=[0], width=20)

def checkbox_update_close(attr, old, new):
    close_gam_20_line.visible = 0 in checkbox_close.active
    close_gam_50_line.visible = 1 in checkbox_close.active

checkbox_close.on_change('active', checkbox_update_close)


checkbox_volume = CheckboxGroup(labels=["Volume GAM"], active=[0], width=20)

def checkbox_update_volume(attr, old, new):
    volume_gam.visible = 0 in checkbox_volume.active

checkbox_volume.on_change('active', checkbox_update_volume)

layout = column(row(p1, checkbox_close), row(p2, checkbox_volume))
curdoc().add_root(layout)
