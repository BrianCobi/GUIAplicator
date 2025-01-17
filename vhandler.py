import socket
import threading
import gi
import logging
import os
from datetime import datetime
import subprocess
import os
import subprocess
import shutil

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format of the log messages
    handlers=[
        logging.FileHandler('app.log'),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

logger = logging.getLogger(__name__)  # Create a logger object

# Configuration
IP_ADDRESS = "192.168.111.192"
PORT = 2212
IP_ADDRESS_CLIENT = "192.168.111.179"

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((IP_ADDRESS, PORT))

current_values = [1400, 0, 0, 0, 0, 300, 0, 0]
value_names = ["Speed", "Offset", "Calibration", "Feed", "Stop", "Count", "Paperlow", "Head"]

def format_current_values():
    return f"[{current_values[0]}|{current_values[1]}|{current_values[2]}|{current_values[3]}|{current_values[4]}]"

def receive_messages():
    while True:
        try:
            message, addr = udp_socket.recvfrom(1024)
            logger.debug(f"Received message from {addr}: {message.decode()}")
            new_values = parse_message(message.decode())
            if new_values:
                update_current_values(new_values)
                # ConnectionLabel.set_text("Connected")
        except Exception as e:
            
            logger.error(f"Error receiving message: {e}")
            # ConnectionLabel.set_text("Conneciton Down")
            break

def send_messages(message):
    try:
        udp_socket.sendto(message.encode(), (IP_ADDRESS_CLIENT, PORT))

        logger.debug(f"Sent message to {IP_ADDRESS_CLIENT}: {message}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def parse_message(message):
    try:
        values = message.strip('[]').split('|')
        if len(values) == 8:
            logger.debug(f"Parsed message: {values}")
            return [int(value) for value in values]
        else:
            logger.warning("Received message with incorrect format.")
            return None
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return None

def update_current_values(new_values):
    global current_values
    for i in range(len(current_values)):
        if current_values[i] != new_values[i]:
            logger.debug(f"Updating {value_names[i]} from {current_values[i]} to {new_values[i]}")
            if value_names[i] == "Head" and new_values[i] == 1:
                logger.debug("Head open!")
            if value_names[i] == "Paperlow" and new_values[i] == 1:
                logger.debug("Paper low!")
            current_values[i] = new_values[i]
            update_gui()

def update_gui():
    GLib.idle_add(_update_gui)

def _update_gui():
    global current_values
    print("Calling function update GUI")
    try:
        count_label.set_text(f"{current_values[5]}")
        speed_label.set_text(f"{current_values[0]}")
        offset_label.set_text(f"{current_values[1]}")
        stop_label.set_name("my_button_normal" if current_values[4] == 0 else "my_button_active")
        start_button.set_name("my_button_normal" if current_values[4] == 1 else "my_button_active")
        calibration_button.set_name("my_button_normal" if current_values[2] == 0 else "my_button_active")
        feed_button.set_name("my_button_normal" if current_values[3] == 0 else "my_button_active")
        headOpenWIndow.show() if current_values[7] == 1 else headOpenWIndow.hide()
        PaperLowWIndow.show() if current_values[6] == 1 else PaperLowWIndow.hide()
        StateLabel.set_text("Running" if current_values[4] == 0 else "Stopped")
        Spinner.start() if current_values[4] == 0 else Spinner.stop()
        StateLabel.set_name("Running" if current_values[4] == 0 else "Stopped")
        load_logwindow()
        logger.debug("GUI updated with current values")
    except Exception as e:
        logger.error(f"Error updating GUI: {e}")
    return False

def load_logwindow():
    buffer = textview.get_buffer()
    try:
        with open('app.log', 'r') as file:
            log_text = file.read()
        buffer.set_text(log_text)
    except FileNotFoundError:
        buffer.set_text('Log file not found.')

def save_log():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_log_filename = f'app_{timestamp}.log'
    os.rename('app.log', new_log_filename)
    logger.info("Application terminated")
    logger.info(f"Log file saved as {new_log_filename}")

def ping(host):
    command = ['ping', '-c', '1', host]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        return 1
    except subprocess.CalledProcessError:
        return 0

class MainWindow:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('vhandler1.ui')
        self.builder.connect_signals(self)

        global headOpenWIndow, PaperLowWIndow, TextViewWindow, AdminWindow
        headOpenWIndow = self.builder.get_object("Head_Open")
        PaperLowWIndow = self.builder.get_object("Paper_Low")
        TextViewWindow = self.builder.get_object('LogFIleViewer')
        AdminWindow = self.builder.get_object('AdminWindow')

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path('style.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        global stop_label, start_button, calibration_button, feed_button, textview
        stop_label = self.builder.get_object("btnstop")
        start_button = self.builder.get_object("btnstart")
        calibration_button = self.builder.get_object("btn_calibrate")
        feed_button = self.builder.get_object("btnman")
        textview = self.builder.get_object('LogText')

        global speed_label, offset_label, count_label, ConnectionLabel, StateLabel, Spinner, btnAdminCancel, bntAccept, AdminEntry, AlertLabel, AdminMode
        speed_label = self.builder.get_object("lblspeed")
        offset_label = self.builder.get_object("lbloffset")
        count_label = self.builder.get_object("count_lbl")

        ConnectionLabel = self.builder.get_object("ConnectionLabel")

        StateLabel = self.builder.get_object("StateLabel")
        Spinner = self.builder.get_object("Spinner")
        btnAdminCancel = self.builder.get_object("btnAdminCancel")
        bntAccept = self.builder.get_object("bntAccept")
        AdminEntry = self.builder.get_object("AdminEntry")
        AlertLabel = self.builder.get_object('AlertLabel')
        AdminMode = self.builder.get_object('AdminMode')
        # AdminWindow.present()
        # AdminEntry.present()
        # AdminEntry.set_visibility(False)

    def on_window_destroy(self, widget, data=None):
        Gtk.main_quit()
        logger.info("Application closed")

    def on_offsetplus_clicked(self, widget, data=None):
        self._change_value("Offset", 10)

    def on_offsetmin_clicked(self, widget, data=None):
        self._change_value("Offset", -10)

    def on_speedplus_clicked(self, widget, data=None):
        self._change_value("Speed", 100)

    def on_speedmin_clicked(self, widget, data=None):
        self._change_value("Speed", -100)

    def on_btnstart_clicked(self, widget, data=None):
        self._set_value("Stop", 0)

    def on_btnstop_clicked(self, widget, data=None):
        self._set_value("Stop", 1)

    def on_btnman_clicked(self, widget, data=None):
        self._toggle_value("Feed")

    def on_btn_calibrate_clicked(self, widget, data=None):
        self._toggle_value("Calibration")

    def on_view_clicked(self, widget, data=None):
        logger.info("Log button clicked")
        TextViewWindow.present()
        update_gui()

    def on_LogFIleViewer_delete_event(self, widget, event, data=None):
        logger.info("Log File Viewer window closed")
        widget.hide()
        return True

    def on_btnConection_clicked(self, widget, data=None):
        logger.info("Pinging IP")
        response = ping(IP_ADDRESS_CLIENT)
        ConnectionLabel.set_text("Connected" if response else "Connection down")
        logger.info("System Connection Button Clicked")
        self._set_value("Stop", 0)

    def on_AdminMode_button_press_event(self, widget, data=None):
        # AlertLabel.set_text("")
        logger.info("Admin Mode Clicked")
        AdminWindow.present()

    def on_AdminWindow_delete_event(self, widget, event, data=None):
        logger.info("Admin window closed")
        widget.hide()
        return True

    def on_btnAdminCancel_clicked(self, widget):
        logger.info("Admin window closed")
        AdminWindow.hide()




    def on_bntAccept_clicked(self, widget):
        logger.info('Button accept pressed')
        entered_text = AdminEntry.get_text()
        password = 'vbsinc1'
        if entered_text == password:
            logger.info('Accessing Command Window')
            try:
                command = f'echo {password}; clear; exec bash'
                terminal = get_default_terminal()
                if not terminal:
                    logger.error("Terminal not found")
                if terminal in ["gnome-terminal", "konsole", "tilix", "xfce4-terminal"]:
                    subprocess.run([terminal, "--", "bash", "-c", command])
                elif terminal == "x-terminal-emulator":
                    subprocess.run([terminal, "-e", f"bash -c '{command}'"])
                elif terminal == "lxterminal":
                    subprocess.run([terminal, "-e", f"bash -c \"{command}\""])
                else:
                    subprocess.run([terminal, "-e", command]) 
                logger.info("Admin window closed")
                AdminEntry.set_text("")
                AdminWindow.hide()
            except subprocess.CalledProcessError as e:
                print(f"An error occurred: {e}")
        else:
            logger.info(f'Wrong password: {entered_text}')
            AlertLabel.set_text("Wrong password")
            AdminEntry.set_placeholder_text("")

    def _change_value(self, value_name, delta):
        index = value_names.index(value_name)
        current_values[index] += delta
        logger.info(f"{value_name} {'increased' if delta > 0 else 'decreased'} by {abs(delta)}")
        message = format_current_values()
        send_messages(message)
        update_gui()

    def _set_value(self, value_name, new_value):
        index = value_names.index(value_name)
        current_values[index] = new_value
        logger.info(f"{value_name} set to {new_value}")
        message = format_current_values()
        send_messages(message)
        update_gui()

    def _toggle_value(self, value_name):
        index = value_names.index(value_name)
        current_values[index] = 1 - current_values[index]
        logger.info(f"{value_name} toggled")
        message = format_current_values()
        send_messages(message)
        update_gui()


def get_default_terminal():

    terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "x-terminal-emulator", "lxterminal", "tilix", "mate-terminal", "terminator", "urxvt"]
    for terminal in terminals:
        path = shutil.which(terminal)
        if path:  
            return terminal
    return None

if __name__ == '__main__':
    logger.info("Application started")
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.daemon = True
    receive_thread.start()
    MainWindow()
    Gtk.main()
    save_log()
