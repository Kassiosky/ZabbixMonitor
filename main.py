import tkinter as tk
from tkinter import ttk
import threading
import time
from pystray import MenuItem as item, Icon
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageTk
import requests
import os
from io import BytesIO
from dotenv import load_dotenv
import json
from bs4 import BeautifulSoup


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # If running as a bundled app, access the PyInstaller temp folder
        base_path = sys._MEIPASS
    else:
        # Use current directory in dev mode
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Join the base path with the relative path to get the full path to the resource
    full_path = os.path.join(base_path, relative_path)

    # Debug: Print the path to verify
    print(f"Resource path: {full_path}")

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")

    return full_path


class ZabbixMonitor:
    def __init__(self):
        # Load .env file
        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        env_path = os.path.join(BASE_DIR, "includes", ".env")
        print(f"DEBUG: .env path = {env_path}")  # Debug line

        if not os.path.exists(env_path):
            raise FileNotFoundError(f".env file not found: {env_path}")

        load_dotenv(env_path)

        # Verify environment variables
        zabbix_url = os.getenv('zabbix_url')
        if not zabbix_url:
            raise ValueError("zabbix_url not found in .env")
        print(f"DEBUG: zabbix_url = {zabbix_url}")  # Debug line





        # Initialize application settings
        self.__app_name = 'DetranSC'
        self.zabbix_url = f"{os.getenv('zabbix_url')}/api_jsonrpc.php"
        self.web_url = os.getenv('zabbix_url')  # Base URL for web interface
        self.username = os.getenv('zabbix_user')
        self.password = os.getenv('zabbix_password')
        self.auth_token = os.getenv('zabbix_token')
        self.problems = []
        self.update_interval = 10  # 10 seconds
        self.recent_minutes = 120  # Time window for recent issues
        self.graph_buttons = {}  # Store graph buttons for removal later

        # Setup session with web interface authentication
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'ZabbixMonitorApp'})
        self.perform_web_login()  # Authenticate with web interface

        # GUI setup
        self.root = tk.Tk()
        self.root.title(f"{self.__app_name} - Zabbix Recent Incident Monitor")
        self.root.geometry("800x400")
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)

        # Create treeview
        self.tree = ttk.Treeview(self.root, columns=('Time', 'Host', 'Problem', 'Severity'), show='headings')
        self.tree.heading('Time', text='Time')
        self.tree.heading('Host', text='Host')
        self.tree.heading('Problem', text='Problem')
        self.tree.heading('Severity', text='Severity')
        self.tree.pack(fill=tk.BOTH, expand=True)



        # Container frame for buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, pady=5)

        # System tray icon
        self.tray_icon = self.create_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_incidents, daemon=True)
        self.monitor_thread.start()

        self.root.mainloop()
    def perform_web_login(self):
        """Authenticate with Zabbix web interface to maintain session cookies"""
        login_url = f"{self.web_url}/index.php"

        try:
            # Get login page to retrieve CSRF token
            response = self.session.get(login_url, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'sid'}).get('value', '') if soup.find('input',
                                                                                           {'name': 'sid'}) else ''

            # Prepare login payload
            login_data = {
                'name': self.username,
                'password': self.password,
                'enter': 'Sign in',
                'sid': csrf_token
            }

            # Perform login
            response = self.session.post(login_url, data=login_data, verify=False)

            # Verify successful login
            if 'zbx_sessionid' in self.session.cookies:
                print("Web interface login successful")
            else:
                print("Web login failed. Check credentials")
        except Exception as e:
            print(f"Web login error: {str(e)}")


    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), 'green')
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='white')

        menu = (
            item('Show', self.show_window),
            item('Exit', self.exit_app)
        )
        return Icon('zabbix_monitor', image, f"{self.__app_name} Zabbix Monitor", menu)

    def zabbix_api_call(self, method, params):
        headers = {'Content-Type': 'application/json-rpc'}
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        if self.auth_token and method != "user.login":
            data["auth"] = self.auth_token

        response = self.session.post(self.zabbix_url, data=json.dumps(data), headers=headers, verify=False)
        return response.json()

    def get_zabbix_problems(self):
        if not self.auth_token:
            auth = self.zabbix_api_call("user.login", {
                "user": self.username,
                "password": self.password
            })
            if 'error' in auth:
                print("API authentication failed:", auth['error']['data'])
                return []
            self.auth_token = auth['result']

        time_from = int(time.time()) - (self.recent_minutes * 60)

        problems = self.zabbix_api_call("problem.get", {
            "output": "extend",
            "selectTags": "extend",
            "selectSuppressionData": "extend",
            "time_from": time_from,
            "sortfield": ["eventid"],
            "sortorder": "DESC"
        })

        if 'error' in problems or not problems.get('result'):
            return []

        # Get host names for each problem using trigger.get
        for problem in problems['result']:
            trigger_data = self.zabbix_api_call("trigger.get", {
                "output": ["triggerid"],
                "selectHosts": ["host"],  # Request host names
                "triggerids": problem['objectid']  # objectid = triggerid
            })

            if trigger_data.get('result'):
                # Attach host names to the problem
                problem['hosts'] = trigger_data['result'][0].get('hosts', [])



        return problems['result']

    def update_problems_display(self, problems):
        # Remove old buttons for resolved problems
        for button in list(self.graph_buttons.values()):
            button.destroy()
        self.graph_buttons.clear()

        self.tree.delete(*self.tree.get_children())
        for problem in problems:


            item_id = problem.get('objectid', '')
            severity = problem.get('severity','')
            row = self.tree.insert('', 'end', values=(
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(problem['clock']))),
                problem.get('hosts', [{}])[0].get('host', 'Unknown Host'),
                problem['name'],
                problem['severity'],
            ))

            if item_id:
                self.create_graph_button(row, problem['name'])

    def monitor_incidents(self):
        while True:
            try:
                problems = self.get_zabbix_problems()
                if problems != self.problems:
                    if len(problems) > 0 and len(self.problems) == 0:
                        # New incidents discovered, notify
                        self.notify_tray(f"{self.__app_name} New incident discovered", "There is a new problem in Zabbix.")
                    elif len(problems) == 0 and len(self.problems) > 0:
                        # All incidents cleared, notify
                        self.notify_tray(f"{self.__app_name} All incidents cleared", "There are no active problems in Zabbix.")

                    self.problems = problems
                    self.root.after(0, self.update_problems_display, problems)
                    self.update_tray_icon(len(problems))
                time.sleep(self.update_interval)
            except Exception as e:
                print("Monitoring error:", str(e))
                time.sleep(60)

    def update_tray_icon(self, problem_count):
        color = 'green' if problem_count == 0 else 'red'
        image = Image.new('RGB', (64, 64), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='white')
        if problem_count > 0:
            draw.text((32, 32), str(problem_count), fill='black')
        self.tray_icon.icon = image

    def notify_tray(self, title, message):
        """Notify in system tray"""
        self.tray_icon.notify(message, title=title)

    def show_window(self, icon, item):
        self.root.after(0, self.root.deiconify)

    def hide_window(self):
        self.root.withdraw()

    def exit_app(self, icon, item):
        self.tray_icon.stop()
        self.root.destroy()

    def open_graph(self, event_name):
        """Handle graph display with web authentication"""
        trigger_id = self.get_trigger_for_event(event_name)
        if not trigger_id:
            return

        item_id = self.get_itemid_from_trigger(trigger_id)
        if not item_id:
            return

        graph_url = f"{self.web_url}/chart.php?from=now-30m&to=now&itemids[]={item_id}&type=0&profileIdx=web.item.graph.filter&profileIdx2={item_id}&width=1082&height=200&_={self.get_timestamp()}&screenid="

        try:
            headers = {
                'Referer': f"{self.web_url}/zabbix.php?action=problem.view&filter_triggerids[]={trigger_id}",
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
            }

            response = self.session.get(graph_url, headers=headers, verify=False)

            if 'image' in response.headers.get('Content-Type', ''):
                image = Image.open(BytesIO(response.content))
                image_tk = ImageTk.PhotoImage(image)

                graph_window = tk.Toplevel(self.root)
                graph_window.title(f"{self.__app_name} Zabbix Graph")
                graph_label = tk.Label(graph_window, image=image_tk)
                graph_label.image = image_tk  # Keep reference
                graph_label.pack()
            else:
                print("Graph response contains:", response.text[:200])
        except Exception as e:
            print(f"Graph error: {str(e)}")

    def get_timestamp(self):
        return str(int(time.time()))

    def get_trigger_for_event(self, event_name):
        events = self.zabbix_api_call("event.get", {
            "output": "extend",
            "filter": {"name": event_name},
            "sortfield": "clock",
            "sortorder": "DESC"
        })

        if events.get('result'):
            return events['result'][0]['objectid']
        return None

    def get_itemid_from_trigger(self, trigger_id):
        triggers = self.zabbix_api_call("trigger.get", {
            "output": "extend",
            "triggerids": trigger_id,
            "selectItems": "extend"
        })

        if triggers.get('result'):
            items = triggers['result'][0].get('items', [])
            if items:
                return items[0]['itemid']
        return None

    def create_graph_button(self, row, event_name):
        button = tk.Button(self.button_frame, text=f"{event_name} - Show Graph 30Minutes",
                           command=lambda: self.open_graph(event_name))
        button.grid(row=self.button_frame.grid_size()[1], column=0, padx=5, pady=5, sticky="w")
        self.graph_buttons[event_name] = button


if __name__ == "__main__":
    monitor = ZabbixMonitor()
