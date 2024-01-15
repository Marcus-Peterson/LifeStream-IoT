import asyncio
from bleak import BleakClient
import json
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pymongo
from datetime import datetime
import os
# MongoDb information
MONGO_URI = os.environ.get("MONGO_DB_URI")

db_client = pymongo.MongoClient(MONGO_URI)
db = db_client["health_data"]
collection = db["sensor_data"]

#Function for sending the data to the Azure Mongodb database
def send_data_to_db(username, temperature, gsr, bpm):
    try:
        current_time = datetime.now()
        data = {
            "username": username,
            "temperature": temperature,
            "gsr": gsr,
            "bpm": bpm,
            "timestamp": current_time
        }
        collection.insert_one(data)
        print("Data sent to DB:", data)  # Loggning för debugging
    except Exception as e:
        print("Error sending data to DB:", e)  # Fånga och logga eventuella fel

#Global variable for handling the data registration button
recording = False

# Function for handling button press
def toggle_recording():
    global recording
    recording = not recording
    if recording:
        record_button.config(text = "Stop Recording")
        send_data_periodically()
    else:
        record_button.config(text = "Start Recording")

# Send data every 20th second
def send_data_periodically():
    if recording:
        # Latest datapost gets sent
        if temperatures and gsr_values and bpm_values:
            send_data_to_db(username_entry.get(),temperatures[-1],gsr_values[-1],bpm_values[-1])
        root.after(10000, send_data_periodically)


# Your Arduino's BLE address
ADDRESS = "F4:12:FA:70:A9:11"
# UUID for the BLE characteristic that sends JSON data
JSON_CHAR_UUID = "19B10010-E8F2-537E-4F6C-D104768A1214"

# Data lists
temperatures = []
gsr_values = []
bpm_values = []
times = []

# Set up the matplotlib figure and axes
fig, (ax_temp, ax_gsr, ax_bpm) = plt.subplots(3, 1, figsize=(8, 6))

# Set up the tkinter root window
root = tk.Tk()
root.title("LifeStream IoT Health Monitoring")

# Status label
status_label = tk.Label(root, text="Press 'Start BLE Communication' to connect.")
status_label.pack(side=tk.BOTTOM)

# Asynchronous function to handle notifications
def notification_handler(sender, data):
    data_str = data.decode("utf-8")
    try:
        data_json = json.loads(data_str)
        temperatures.append(data_json["temperature"])
        gsr_values.append(data_json["gsr"])
        bpm_values.append(data_json["bpm"])
        times.append(len(times) + 1)
        status_label.config(text="Data is being received...")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")

# Asynchronous main function
async def main(address):
    async with BleakClient(address, timeout=60.0) as client:
        connected = await client.is_connected()
        print(f"Connected: {connected}")
        if connected:
            await client.start_notify(JSON_CHAR_UUID, notification_handler)
            while True:
                await asyncio.sleep(1)

# Function to run the asyncio event loop in a separate thread
def run_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(ADDRESS))

# Function to start the BLE communication in a separate thread
def start_ble_communication():
    status_label.config(text="Trying to connect...")
    ble_thread = threading.Thread(target=run_ble_loop, daemon=True)
    ble_thread.start()

# Function to clear the data and reset the graphs
def restart_communication():
    global temperatures, gsr_values, bpm_values, times
    temperatures.clear()
    gsr_values.clear()
    bpm_values.clear()
    times.clear()
    update_plot()
    status_label.config(text="Press 'Start BLE Communication' to connect.")

# Embedding the matplotlib figure in a tkinter Canvas
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Adding a button to start the BLE communication
start_button = tk.Button(root, text="Start BLE Communication", command=start_ble_communication)
start_button.pack(side=tk.BOTTOM)

# Adding a restart button
restart_button = tk.Button(root, text="Restart", command=restart_communication)
restart_button.pack(side=tk.BOTTOM)


# Input label to categorize data depending on user
username_label = tk.Label(root, text="Write username:")
username_label.pack()
username_entry = tk.Entry(root)
username_entry.pack()

# Record button for start and stop data recording
record_button = tk.Button(root, text="Start Recording", command=toggle_recording)
record_button.pack()

# Function to update the plot
def update_plot():
    ax_temp.clear()
    ax_gsr.clear()
    ax_bpm.clear()
    
    ax_temp.plot(times, temperatures, label='Temperature', color='red')
    ax_gsr.plot(times, gsr_values, label='GSR', color='blue')
    ax_bpm.plot(times, bpm_values, label='BPM', color='green')
    
    ax_temp.legend(loc='upper left')
    ax_gsr.legend(loc='upper left')
    ax_bpm.legend(loc='upper left')
    
    ax_temp.set_ylabel('Temp (°C)')
    ax_gsr.set_ylabel('GSR')
    ax_bpm.set_ylabel('BPM')
    ax_bpm.set_xlabel('Time')
    
    fig.canvas.draw()

# Function to update the plot in the tkinter window
def update_gui():
    update_plot()
    root.after(1000, update_gui)

# Start the GUI update loop
root.after(1000, update_gui)
root.mainloop()
