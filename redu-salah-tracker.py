import re
import customtkinter as ctk
import tkinter as tk
from tkinter import font, messagebox
from tkcalendar import Calendar
from screeninfo import get_monitors
import json
import requests
from urllib.parse import urlparse, urlunparse
import datetime
import os
import platform
import hashlib
import socket

# Variables
data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
os.makedirs(data_dir, exist_ok=True)
json_file_path = os.path.join(data_dir, 'salah_data.json')  # Path to the JSON file
server_file_path = os.path.join(data_dir, 'server.txt')  # Path to the preference file
version_file_path = os.path.join(os.getcwd(), 'version.txt')  # Path to the preference file
data = {}
cancelled = False
protocol = ['http://', 'https://']
protocol_no = 0

# CustomTKinter look settings
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# CustomTKinter Window settings
app = ctk.CTk()
app.geometry("500x450")
app.title("Redu Salah Tracker")
app.wm_resizable(False, False)
app.wm_attributes('-topmost', False)
app.wm_iconbitmap("icon.ico")


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


def compute_sha256(file_path):
    """
    Compute the SHA-256 hash of a file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    # Got from https://stackoverflow.com/questions/237079/how-do-i-get-file-creation-and-modification-date-times
    if platform.system() == 'Windows':
        return os.path.getmtime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def startup():
    global server_url_actual
    local_file_timestamp = creation_date(json_file_path)
    local_file_modified_date = datetime.datetime.fromtimestamp(local_file_timestamp)
    local_file_hash = compute_sha256(json_file_path)

    is_reachable, response = check_server_status(server_url_actual)

    if is_reachable:
        print(f"{server_url_actual} response: {response}")
        try:
            response = requests.get(f'{server_url_actual}/file-metadata')
            if response.status_code == 200:
                metadata = response.json()
                cloud_file_timestamp = response.json().get('last_modified')
                cloud_file_modified_date = datetime.datetime.fromtimestamp(cloud_file_timestamp)
                cloud_file_hash = metadata.get('sha256')

                print("Local file last modified time:", local_file_modified_date)
                print("Cloud file last modified time:", cloud_file_modified_date)

                # Compare the dates
                if local_file_modified_date > cloud_file_modified_date:
                    print("Local file is newer than the cloud file")
                elif local_file_modified_date < cloud_file_modified_date:
                    print("Local file is older than the cloud file")
                else:
                    print("Local file and cloud file are the same")

                print("Local file SHA-256 hash:", local_file_hash)
                print("Cloud file SHA-256 hash:", cloud_file_hash)

                # Compare the hash values
                if local_file_hash == cloud_file_hash:
                    print("Local file and cloud file are the same")
                else:
                    print("Local file and cloud file are different")
                    # Prompt the user for further action
            else:
                print("Failed to get cloud file metadata:", response.json().get('error'))
        except requests.exceptions.InvalidSchema:
            # Might happen cause the protocol i.e. http is not correct.
            print("Exiting..")
            exit(1)
        except requests.exceptions.JSONDecodeError:
            # Might happen cause there is no JSON file or JSON file is not properly formated.
            print("Error: Might happen cause there is no JSON file or JSON file is not properly formated. Server:")
            print(server_url_actual)
            prompt_for_server_address()
        except requests.exceptions.ConnectionError:
            # Might happen cause server is not responding.
            print("Exiting..")
            exit(1)
        except requests.exceptions.InvalidURL:
            # Might happen cause url is invalid
            print("Exiting..")
            exit(1)
    elif not is_reachable:
        print(f"{server_url_actual} response time: {response}")
        messagebox.showwarning("Error", "Server is not reachable.")
        prompt_for_server_address()

        if not cancelled:
            _, server_url_actual, _ = update_server_address()
            startup()
        else:
            exit(0)


def current_version(file):
    with open(file, 'r') as f:
        return f.read().strip()


def check_server_file():
    if not os.path.exists(server_file_path):
        return False
    else:
        return True


def dns_resolution_check(server):
    """
    Check if the domain can be resolved to an IP address.
    """
    try:
        # Remove protocol if included
        parsed_url = urlparse(server)
        hostname = parsed_url.netloc if parsed_url.netloc else parsed_url.path
        ip = socket.gethostbyname(hostname)
        return True, f"Resolved IP: {ip}"
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"


def hyper_text_transfer_protocol_check(server):
    """
    Check if the server is reachable by making an HTTP GET request.
    """
    try:
        response = requests.get(server, timeout=5)
        if response.status_code == 200:
            return True, f"Server is reachable. Status code: {response.status_code}", response.status_code
        else:
            return False, f"Server returned a non-200 status code: {response.status_code}", response.status_code
    except requests.ConnectionError:
        return False, "Connection error", None
    except requests.Timeout:
        return False, "Request timed out", None
    except requests.RequestException as e:
        return False, str(e), None


def check_server_status(server):
    if server_address_type == "ip":
        server_port = return_port(server)
        server = remove_port(server)
        http_server = f"{protocol[protocol_no]}{server}:{server_port}"
        http_check, http_response, http_status_code = hyper_text_transfer_protocol_check(server=http_server)
    else:
        http_check, http_response, http_status_code = hyper_text_transfer_protocol_check(server)

    dns_check, dns_response = dns_resolution_check(server)
    dns_check_pass = False
    http_check_pass = False

    if dns_check:
        dns_check_pass = True
    if http_check:
        http_check_pass = True

    if dns_check_pass and http_check_pass:
        return True, f"\n\tDNS check: {dns_response},\tHTTP check: {http_response}"
    elif dns_check_pass and http_response == f"Server returned a non-200 status code: {http_status_code}":
        return True, f"\n\tDNS check: {dns_response},\tHTTP check: {http_response}"
    else:
        return False, f"\n\tDNS check: {dns_response},\tHTTP check: {http_response}"


def prompt_for_server_address():
    global server_url_actual
    dialog = ctk.CTkToplevel(app)
    dialog.title("Server Address")
    dialog.geometry("300x150")

    # Delay setting the icon to avoid the customtkinter override issue
    dialog.after(250, lambda: dialog.iconbitmap('icon.ico'))

    def on_ok():
        global server_url_actual
        server_address = entry.get()
        server_url_actual = "http://www." + server_address
        server_url_no_www = remove_www(server_url_actual)
        if server_url_actual:
            if is_valid_url(server_url_actual):
                with open(server_file_path, 'w') as f:
                    f.write(server_address)
                messagebox.showinfo("Success", "Server address saved successfully.")
                dialog.destroy()
            elif is_valid_url(server_url_no_www):
                with open(server_file_path, 'w') as f:
                    f.write(server_address)
                messagebox.showinfo("Success", "Server address saved successfully.")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Invalid server address or server unreachable.")
        else:
            messagebox.showerror("Error", "Server address cannot be empty.")

    def on_cancel():
        global cancelled
        cancelled = True
        dialog.destroy()

    def on_close():
        on_cancel()

    # Set up the close protocol to call on_close
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    popup_frame = ctk.CTkFrame(dialog)
    popup_frame.pack(pady=20, padx=20, fill="both", expand=True)

    ctk.CTkLabel(popup_frame, text="Please enter the server address:").pack(pady=5)
    entry = ctk.CTkEntry(popup_frame)
    entry.pack(pady=5)
    entry.focus_set()

    popup_button_frame = ctk.CTkFrame(popup_frame)
    popup_button_frame.pack(pady=5)
    ctk.CTkButton(popup_button_frame, text="OK", command=on_ok).pack(side=ctk.LEFT, padx=5)
    ctk.CTkButton(popup_button_frame, text="Cancel", command=on_cancel).pack(side=ctk.LEFT, padx=5)

    app.wait_window(dialog)


def about():
    about_window = ctk.CTkToplevel(app)
    about_window.title("About")
    about_window.geometry("300x200")

    # Delay setting the icon to avoid the customtkinter override issue
    about_window.after(250, lambda: about_window.iconbitmap('icon.ico'))

    popup_frame = ctk.CTkFrame(about_window)
    popup_frame.pack(pady=20, padx=20, fill="both", expand=True)

    name = ctk.CTkLabel(popup_frame, 200, 20, text="Redu Salah Tracker", font=("Arial", 24))
    name.pack(pady=10)

    details = ctk.CTkTextbox(popup_frame, 100, 20, 0, 0, fg_color="transparent")
    details.pack(pady=10)
    details.insert(0.0, f"Version: {current_version(version_file_path)}")
    details.configure(state="disabled")

    author = ctk.CTkTextbox(popup_frame, 200, 20, 0, 0, fg_color="transparent")
    author.pack(pady=10)
    author.insert(0.0, "Made by Ridwan Hossain Abid")
    author.configure(state="disabled")


def get_server_address():
    with open(server_file_path, 'r') as f:
        return f.read().strip()


def update_server_address():
    file_status = check_server_file()
    if file_status:
        server = get_server_address()
        server_url_main = f"{protocol[protocol_no]}www." + server
        server_type = is_ip_or_domain(server_url_main)
        if server_type == "ip":
            server_url_main = remove_www(server_url_main)
        print(f"Server type: {server_type}")
        return server, server_url_main, server_type
    elif not file_status:
        prompt_for_server_address()
        server = get_server_address()
        server_url_main = f"{protocol[protocol_no]}www." + server
        server_type = is_ip_or_domain(server_url_main)
        print(f"Server type: {server_type}")
        return server, server_url_main, server_type


def is_valid_url(url):
    # Check if the URL is well-formed
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        return False

    # Check if the URL is reachable
    try:
        response = requests.head(url)
        if response.status_code < 400:  # Check for a valid status code
            return True
        else:
            return False
    except requests.RequestException:
        return False


def remove_www(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc

    # Remove 'www.' if it exists at the beginning of the netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    # Reconstruct the URL without 'www.'
    new_url = urlunparse((parsed_url.scheme, netloc, parsed_url.path,
                          parsed_url.params, parsed_url.query, parsed_url.fragment))
    return new_url


def remove_port(url):
    netloc = urlparse(url).netloc

    # Strip the port number if present
    if ':' in netloc:
        netloc = netloc.split(':')[0]
        print("Netloc: " + netloc)
        return netloc


def return_port(url):
    parsed_url = urlparse(url)
    port = parsed_url.port
    if port:
        return str(port)


def is_ip_or_domain(url):
    url = remove_www(url)
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc

    if server_address_type == "ip":
        netloc = remove_port(url)

    # Regular expression for matching an IPv4 address
    ipv4_pattern = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')

    # Regular expression for matching an IPv6 address
    ipv6_pattern = re.compile(r'^[0-9a-fA-F:]+$')

    if ipv4_pattern.match(netloc) or ipv6_pattern.match(netloc):
        return "ip"
    else:
        return "domain"


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
            response = requests.post(f'{server_url_actual}/upload', files={'file': f})
        if response.status_code == 200:
            messagebox.showinfo("Uploaded", "Data uploaded successfully!")
        else:
            messagebox.showerror("Error", "Failed to upload data.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# Function to download data from server
def download_data():
    try:
        response = requests.get(f'{server_url_actual}/download')
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
server_url, server_url_actual, server_address_type = update_server_address()
load_data()

# GUI START
frame = ctk.CTkFrame(app)
frame.pack(pady=20, padx=20, fill="both", expand=True)

# MENUBAR
menubar = tk.Menu(app)
app.config(menu=menubar)
app_menu = tk.Menu(menubar, tearoff=False)
menubar.add_cascade(label="Settings", menu=app_menu)
app_menu.add_command(label="Change Server", command=prompt_for_server_address)
app_menu.add_command(label="About", command=about)

# CALENDAR
cal = CustomCalendar(frame, selectmode='day', year=datetime.datetime.now().year, month=datetime.datetime.now().month,
                     day=datetime.datetime.now().day)
cal.pack(pady=10, padx=10, fill="both", expand=True)

# SALAH VARIABLES
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

# BUTTON FRAME AND BUTTONS
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
# GUI END

startup()
cal.bind("<<CalendarSelected>>", lambda e: update_ui())
update_ui()
update_calendar_colors()

app.mainloop()
