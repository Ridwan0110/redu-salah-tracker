import customtkinter as ctk
import tkinter as tk
from tkcalendar import Calendar
import json
import requests
import datetime
import os

# Variables
data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
os.makedirs(data_dir, exist_ok=True)
json_file_path = os.path.join(data_dir, 'salah_data.json')  # Path to the JSON file
data = {}

# CustomTKinter look settings
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# CustomTKinter Window settings
app = ctk.CTk()
app.geometry("500x450")
app.title("Redu Salah Tracker")
app.wm_resizable(False, False)
app.wm_attributes('-topmost', False)
# app.wm_iconbitmap("icon.ico")


# Function to save data locally
def save_data():
    date = cal.get_date()
    salah_data = {
        "Fajr": fajr_var.get(),
        "Dhuhr": dhuhr_var.get(),
        "Asr": asr_var.get(),
        "Maghrib": maghrib_var.get(),
        "Isha": isha_var.get()
    }
    data[date] = salah_data
    with open(json_file_path, 'w') as f:
        json.dump(data, f)
    tk.messagebox.showinfo("Saved", "Salah data saved successfully!")


# Function to load data
def load_data():
    global data
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}


# Function to update UI from selected date
def update_ui():
    date = cal.get_date()
    if date in data:
        fajr_var.set(data[date]["Fajr"])
        dhuhr_var.set(data[date]["Dhuhr"])
        asr_var.set(data[date]["Asr"])
        maghrib_var.set(data[date]["Maghrib"])
        isha_var.set(data[date]["Isha"])
    else:
        fajr_var.set(False)
        dhuhr_var.set(False)
        asr_var.set(False)
        maghrib_var.set(False)
        isha_var.set(False)


# Function to upload data to server
def upload_data():
    try:
        with open(json_file_path, 'rb') as f:
            response = requests.post('http://www.script.ridwanabid.com/redu-salah-tracker-server/upload',
                                     files={'file': f})
        if response.status_code == 200:
            tk.messagebox.showinfo("Uploaded", "Data uploaded successfully!")
        else:
            tk.messagebox.showerror("Error", "Failed to upload data.")
    except Exception as e:
        tk.messagebox.showerror("Error", str(e))


# Function to download data from server
def download_data():
    try:
        response = requests.get('http://www.script.ridwanabid.com/redu-salah-tracker-server/download')
        if response.status_code == 200:
            with open(json_file_path, 'wb') as f:
                f.write(response.content)
            load_data()
            update_ui()
            tk.messagebox.showinfo("Downloaded", "Data downloaded and loaded successfully!")
        else:
            tk.messagebox.showerror("Error", "Failed to download data.")
    except Exception as e:
        tk.messagebox.showerror("Error", str(e))


# Main App
load_data()

frame = ctk.CTkFrame(app)
frame.pack(pady=20, padx=20, fill="both", expand=True)

cal = Calendar(frame, selectmode='day', year=datetime.datetime.now().year, month=datetime.datetime.now().month,
               day=datetime.datetime.now().day)
cal.pack(pady=10)

fajr_var = ctk.BooleanVar()
dhuhr_var = ctk.BooleanVar()
asr_var = ctk.BooleanVar()
maghrib_var = ctk.BooleanVar()
isha_var = ctk.BooleanVar()

fajr_check = ctk.CTkCheckBox(frame, text="Fajr", variable=fajr_var)
dhuhr_check = ctk.CTkCheckBox(frame, text="Dhuhr", variable=dhuhr_var)
asr_check = ctk.CTkCheckBox(frame, text="Asr", variable=asr_var)
maghrib_check = ctk.CTkCheckBox(frame, text="Maghrib", variable=maghrib_var)
isha_check = ctk.CTkCheckBox(frame, text="Isha", variable=isha_var)

fajr_check.pack()
dhuhr_check.pack()
asr_check.pack()
maghrib_check.pack()
isha_check.pack()

button_frame = ctk.CTkFrame(frame)
button_frame.pack(pady=10)

save_button = ctk.CTkButton(button_frame, text="Save Data", command=save_data)
save_button.grid(row=0, column=0, padx=5)

upload_button = ctk.CTkButton(button_frame, text="Upload Data", command=upload_data)
upload_button.grid(row=0, column=1, padx=5)

download_button = ctk.CTkButton(button_frame, text="Download Data", command=download_data)
download_button.grid(row=0, column=2, padx=5)

cal.bind("<<CalendarSelected>>", lambda e: update_ui())
update_ui()

app.mainloop()
