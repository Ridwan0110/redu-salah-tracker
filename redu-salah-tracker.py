import customtkinter as ctk
import tkinter as tk
from tkinter import font, messagebox
from tkcalendar import Calendar
from screeninfo import get_monitors
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


def getOptimalFontSize():
    # Get the primary monitor (assuming there's only one monitor)
    primary_monitor = get_monitors()[0]
    screen_width = primary_monitor.width
    # Define reference screen resolution and font size
    reference_screen_width = 1920  # Width of the reference screen resolution (1080p)
    reference_font_size = 12  # Font size for the reference screen resolution
    screen_ratio = reference_font_size / reference_screen_width
    # Calculate the optimal font size for the screen resolution
    font_size = round(screen_width * screen_ratio)
    return font_size


class CustomCalendar(Calendar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_config('all_done', background='green', foreground='white')
        self.tag_config('some_done', background='yellow', foreground='black')
        self.tag_config('one_done', background='red', foreground='white')
        self.tag_config('none', background='white', foreground='black')
        self._set_font()

    def _set_font(self):
        # Customize the font family, size, and weight here
        custom_font = font.Font(family="Arial", size=getOptimalFontSize(), weight="bold")
        for child in self.winfo_children():
            self._set_widget_font(child, custom_font)

    def _set_widget_font(self, widget, custom_font):
        try:
            widget.configure(font=custom_font)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._set_widget_font(child, custom_font)

    def update_date_colors(self, date_status):
        """
        Update the colors of calendar dates based on completion status.

        Parameters: date_status (dict): A dictionary containing dates as keys and completion statuses ('all_done' or
        'some_done') as values.
        """
        # Clear all tags
        for date in list(self._tags.keys()):
            self.calevent_remove(date, 'all_done')
            self.calevent_remove(date, 'some_done')
            self.calevent_remove(date, 'one_done')
            self.calevent_remove(date, 'none')

        # Apply new tags based on status
        for date, status in date_status.items():
            date_obj = datetime.datetime.strptime(date, '%m/%d/%y').date()
            if status == 'all_done':
                self.calevent_create(date_obj, '', tags='all_done')
            elif status == 'some_done':
                self.calevent_create(date_obj, '', tags='some_done')
            elif status == 'one_done':
                self.calevent_create(date_obj, '', tags='one_done')
            elif status == 'none':
                self.calevent_create(date_obj, '', tags='none')


# Function to save data locally
def save_data(origin_reset=False):
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
    update_calendar_colors()

    if not origin_reset:
        messagebox.showinfo("Saved", "Salah data saved successfully!")
    elif origin_reset:
        messagebox.showinfo("Reset", "Salah data cleared successfully!")


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
            messagebox.showinfo("Uploaded", "Data uploaded successfully!")
        else:
            messagebox.showerror("Error", "Failed to upload data.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# Function to download data from server
def download_data():
    try:
        response = requests.get('http://www.script.ridwanabid.com/redu-salah-tracker-server/download')
        if response.status_code == 200:
            with open(json_file_path, 'wb') as f:
                f.write(response.content)
            load_data()
            update_ui()
            update_calendar_colors()
            messagebox.showinfo("Downloaded", "Data downloaded and loaded successfully!")
        else:
            messagebox.showerror("Error", "Failed to download data.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# Function to update calendar colors based on prayer completion
def update_calendar_colors():
    date_status = {}
    for date, prayers in data.items():
        completed_prayers = sum(prayers.values())
        if completed_prayers == 5:
            date_status[date] = 'all_done'
        elif completed_prayers > 1:
            date_status[date] = 'some_done'
        elif completed_prayers == 1:
            date_status[date] = "one_done"
        elif completed_prayers == 0:
            date_status[date] = "none"
    cal.update_date_colors(date_status)


# Function to reset the checkboxes and clear the data
def reset_data():
    fajr_var.set(False)
    dhuhr_var.set(False)
    asr_var.set(False)
    maghrib_var.set(False)
    isha_var.set(False)
    data.clear()  # Clear all data
    update_ui()
    save_data(True)


# Main App
load_data()

frame = ctk.CTkFrame(app)
frame.pack(pady=20, padx=20, fill="both", expand=True)

cal = CustomCalendar(frame, selectmode='day', year=datetime.datetime.now().year, month=datetime.datetime.now().month,
                     day=datetime.datetime.now().day)
cal.pack(pady=10, padx=10, fill="both", expand=True)

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

reset_button = ctk.CTkButton(frame, text="Reset", command=reset_data)
reset_button.pack()

cal.bind("<<CalendarSelected>>", lambda e: update_ui())
update_ui()
update_calendar_colors()

app.mainloop()
