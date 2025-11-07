import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import psutil
import winsound
from plyer import notification
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import datetime
import json
import os

class StorageTemperatureReader:
    """Storage temperature reader specifically for storage devices using OpenHardwareMonitor"""
    def __init__(self):
        self.wmi_available = False
        self.ohm_available = True
        self.initialize_wmi()
    
    def initialize_wmi(self):
        """Initialize WMI connection and check OpenHardwareMonitor availability"""
        try:
            import wmi
            self.wmi_available = True
            print("✅ WMI support initialized")
            
            # Test if OpenHardwareMonitor is running
            try:
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                sensors = w.Sensor()
                self.ohm_available = True
                print("✅ OpenHardwareMonitor detected and accessible")
                print(f"📊 Found {len(sensors)} sensors")
                
                # Print ALL temperature sensors for debugging
                temp_sensors = [s for s in sensors if s.SensorType == "Temperature"]
                print("🌡️ All temperature sensors:")
                for sensor in temp_sensors:
                    print(f"  - {sensor.Name}: {sensor.Value}°C (Parent: {sensor.Parent})")
                    
            except Exception as e:
                print("❌ OpenHardwareMonitor not detected or not running")
                print("💡 Please run OpenHardwareMonitor as Administrator")
                self.ohm_available = False
                
        except ImportError:
            print("❌ WMI not available - install: pip install wmi")
            self.wmi_available = False
            self.ohm_available = False
    
    def _is_storage_sensor(self, sensor_name, parent_name):
        """Check if sensor belongs to a storage device"""
        storage_keywords = [
            'hdd', 'ssd', 'disk', 'drive', 'nvme', 'sata', 
            'hard disk', 'solid state', 'samsung', 'crucial',
            'western digital', 'seagate', 'kingston', 'adata',
            'sandisk', 'intel ssd', 'toshiba', 'hitachi'
        ]
        
        sensor_lower = sensor_name.lower()
        parent_lower = parent_name.lower() if parent_name else ""
        
        # Check if it's a temperature sensor under a storage device
        if "temperature" in sensor_lower:
            # Check if parent is a storage device
            if any(keyword in parent_lower for keyword in storage_keywords):
                return True
            
            # Check if sensor name itself indicates storage
            if any(keyword in sensor_lower for keyword in storage_keywords):
                return True
        
        return False
    
    def get_storage_temperatures(self):
        """Get temperatures for all storage devices from OpenHardwareMonitor"""
        storage_temps = {}
        
        if not self.ohm_available:
            print("❌ OpenHardwareMonitor not available - no temperature data")
            return None
        
        try:
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            sensors = w.Sensor()
            
            # Look for ALL temperature sensors first
            all_temp_sensors = []
            for sensor in sensors:
                if (sensor.SensorType == "Temperature" and 
                    sensor.Value is not None):
                    
                    all_temp_sensors.append({
                        'name': sensor.Name,
                        'value': float(sensor.Value),
                        'parent': sensor.Parent if hasattr(sensor, 'Parent') else "Unknown"
                    })
            
            print(f"🔍 Found {len(all_temp_sensors)} temperature sensors total")
            
            # Filter for storage temperatures
            storage_sensors = []
            for sensor in all_temp_sensors:
                if self._is_storage_sensor(sensor['name'], sensor['parent']):
                    storage_sensors.append(sensor)
                else:
                    print(f"  Skipping non-storage: {sensor['name']} (Parent: {sensor['parent']})")
            
            print(f"💾 Found {len(storage_sensors)} storage temperature sensors")
            
            # Organize storage temperatures
            for sensor in storage_sensors:
                # Use parent name if available, otherwise use sensor name
                if sensor['parent'] and sensor['parent'] != "Unknown":
                    device_name = sensor['parent']
                else:
                    device_name = sensor['name']
                
                temp_value = sensor['value']
                storage_temps[device_name] = temp_value
            
            # If we found storage temperatures, return them
            if storage_temps:
                print("📊 Storage temperatures found:")
                for device, temp in storage_temps.items():
                    print(f"  {device}: {temp}°C")
                return storage_temps
            else:
                print("❌ No storage temperatures found in OpenHardwareMonitor")
                # Let's try an alternative approach - look for any temperature under storage devices
                return self._find_storage_temps_alternative(sensors)
            
        except Exception as e:
            print(f"❌ Error reading storage temperatures: {e}")
            self.ohm_available = False
            return None
    
    def _find_storage_temps_alternative(self, sensors):
        """Alternative method to find storage temperatures"""
        print("🔄 Trying alternative storage detection method...")
        storage_temps = {}
        
        # Get all hardware items to find storage devices
        try:
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            hardware_items = w.Hardware()
            
            storage_devices = []
            for hardware in hardware_items:
                hw_name = hardware.Name if hardware.Name else ""
                hw_lower = hw_name.lower()
                
                # Check if this is a storage device
                storage_keywords = ['ssd', 'hdd', 'disk', 'drive', 'samsung', 'crucial', 'wd', 'seagate']
                if any(keyword in hw_lower for keyword in storage_keywords):
                    storage_devices.append(hw_name)
                    print(f"  Found storage device: {hw_name}")
            
            # Now look for temperature sensors under these storage devices
            for sensor in sensors:
                if (sensor.SensorType == "Temperature" and 
                    sensor.Value is not None and
                    hasattr(sensor, 'Parent') and
                    sensor.Parent in storage_devices):
                    
                    storage_temps[sensor.Parent] = float(sensor.Value)
                    print(f"  Found temperature for {sensor.Parent}: {sensor.Value}°C")
        
        except Exception as e:
            print(f"❌ Alternative method failed: {e}")
        
        return storage_temps if storage_temps else None
    
    def get_average_storage_temperature(self):
        """Get the average temperature across all storage devices"""
        storage_temps = self.get_storage_temperatures()
        if storage_temps:
            avg_temp = sum(storage_temps.values()) / len(storage_temps)
            print(f"📈 Average storage temperature: {avg_temp:.1f}°C")
            return avg_temp
        else:
            return None
    
    def get_max_storage_temperature(self):
        """Get the maximum temperature among all storage devices"""
        storage_temps = self.get_storage_temperatures()
        if storage_temps:
            max_temp = max(storage_temps.values())
            max_device = max(storage_temps, key=storage_temps.get)
            print(f"🔥 Hottest storage: {max_device} at {max_temp:.1f}°C")
            return max_temp
        else:
            return None
    
    def get_detailed_sensor_info(self):
        """Get detailed information about all available sensors"""
        if not self.wmi_available:
            return "WMI not available"
        
        try:
            import wmi
            info = []
            
            # OpenHardwareMonitor sensors
            if self.ohm_available:
                try:
                    w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                    sensors = w.Sensor()
                    info.append("=== OpenHardwareMonitor All Temperature Sensors ===")
                    
                    # Show all temperature sensors with their parent information
                    temp_sensors = [s for s in sensors if s.SensorType == "Temperature" and s.Value is not None]
                    
                    if temp_sensors:
                        for sensor in temp_sensors:
                            parent_info = sensor.Parent if hasattr(sensor, 'Parent') else "No parent"
                            info.append(f"  {sensor.Name}: {sensor.Value}°C (Parent: {parent_info})")
                    else:
                        info.append("No temperature sensors found")
                        
                except Exception as e:
                    info.append(f"OpenHardwareMonitor error: {e}")
            
            return "\n".join(info) if info else "No sensor information available"
            
        except Exception as e:
            return f"Error getting sensor info: {e}"

class TemperatureMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("ThermoGuard - Storage Temperature Monitor")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Temperature thresholds (actual values)
        self.critical_temp = 80  # °C
        self.warning_temp = 70   # °C
        
        # Monitoring state
        self.is_monitoring = True
        self.alert_monitoring_active = True
        self.monitor_thread = None
        
        # Alert tracking
        self.last_warning_time = 0
        self.warning_cooldown = 30
        
        # Temperature history for graphing
        self.temp_history = deque(maxlen=50)
        self.time_history = deque(maxlen=50)
        
        # Storage temperatures storage
        self.storage_temperatures = {}
        
        # Storage temperature reader
        self.temp_reader = StorageTemperatureReader()
        
        self.load_settings()
        self.setup_ui()
        self.start_realtime_updates()
        
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('temperature_monitor_settings.json'):
                with open('temperature_monitor_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.critical_temp = settings.get('critical_temp', 80)
                    self.warning_temp = settings.get('warning_temp', 70)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'critical_temp': self.critical_temp,
                'warning_temp': self.warning_temp
            }
            with open('temperature_monitor_settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="ThermoGuard - Storage Temperature Monitor", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Sensor status display
        self.sensor_status_var = tk.StringVar()
        sensor_status_label = ttk.Label(main_frame, textvariable=self.sensor_status_var,
                                      font=("Arial", 9), foreground="green")
        sensor_status_label.grid(row=1, column=0, columnspan=3, pady=(0, 5))
        self.update_sensor_status()
        
        # Current time display
        self.time_var = tk.StringVar(value="Loading...")
        time_label = ttk.Label(main_frame, textvariable=self.time_var,
                              font=("Arial", 10), foreground="gray")
        time_label.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        # Storage temperatures display frame
        storage_frame = ttk.LabelFrame(main_frame, text="Storage Device Temperatures", padding="10")
        storage_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Create scrollable frame for storage devices
        storage_canvas = tk.Canvas(storage_frame, height=150)
        scrollbar = ttk.Scrollbar(storage_frame, orient="vertical", command=storage_canvas.yview)
        self.scrollable_storage_frame = ttk.Frame(storage_canvas)
        
        self.scrollable_storage_frame.bind(
            "<Configure>",
            lambda e: storage_canvas.configure(scrollregion=storage_canvas.bbox("all"))
        )
        
        storage_canvas.create_window((0, 0), window=self.scrollable_storage_frame, anchor="nw")
        storage_canvas.configure(yscrollcommand=scrollbar.set)
        
        storage_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        storage_frame.grid_rowconfigure(0, weight=1)
        storage_frame.grid_columnconfigure(0, weight=1)
        
        # Average and Max temperature display
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Label(stats_frame, text="Average Storage Temp:", 
                 font=("Arial", 12)).grid(row=0, column=0, padx=(0, 10))
        
        self.avg_temp_var = tk.StringVar(value="-- °C")
        self.avg_temp_display = ttk.Label(stats_frame, textvariable=self.avg_temp_var, 
                                         font=("Arial", 14, "bold"))
        self.avg_temp_display.grid(row=0, column=1, padx=(0, 30))
        
        ttk.Label(stats_frame, text="Max Storage Temp:", 
                 font=("Arial", 12)).grid(row=0, column=2, padx=(0, 10))
        
        self.max_temp_var = tk.StringVar(value="-- °C")
        self.max_temp_display = ttk.Label(stats_frame, textvariable=self.max_temp_var, 
                                         font=("Arial", 14, "bold"))
        self.max_temp_display.grid(row=0, column=3)
        
        # Temperature status indicator
        self.status_indicator = tk.Canvas(main_frame, width=20, height=20, bg="gray")
        self.status_indicator.grid(row=4, column=2, padx=(10, 0), pady=10)
        
        # Status display
        self.status_var = tk.StringVar(value="Status: Initializing...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                font=("Arial", 11))
        status_label.grid(row=5, column=0, columnspan=3, pady=5)
        
        # Last update time
        self.last_update_var = tk.StringVar(value="Last update: --")
        last_update_label = ttk.Label(main_frame, textvariable=self.last_update_var,
                                     font=("Arial", 9), foreground="blue")
        last_update_label.grid(row=6, column=0, columnspan=3, pady=(0, 10))
        
        # Controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Monitoring Controls", padding="10")
        controls_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Start/Stop buttons
        self.start_button = ttk.Button(controls_frame, text="Start Alert Monitoring", 
                                      command=self.start_alert_monitoring)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(controls_frame, text="Stop Alert Monitoring", 
                                     command=self.stop_alert_monitoring, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Refresh rate control
        ttk.Label(controls_frame, text="Update every:").grid(row=0, column=2, padx=(20,5))
        self.refresh_rate_var = tk.StringVar(value="2")
        refresh_combo = ttk.Combobox(controls_frame, textvariable=self.refresh_rate_var,
                                    values=["1", "2", "5", "10"], width=5, state="readonly")
        refresh_combo.grid(row=0, column=3, padx=5)
        ttk.Label(controls_frame, text="seconds").grid(row=0, column=4, padx=(0,10))
        
        # Manual refresh button
        ttk.Button(controls_frame, text="Refresh Now", 
                  command=self.manual_refresh).grid(row=0, column=5, padx=5)
        
        # Sensor Info button
        ttk.Button(controls_frame, text="Sensor Info", 
                  command=self.show_sensor_info).grid(row=0, column=6, padx=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Temperature Settings (°C)", padding="10")
        settings_frame.grid(row=8, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Warning temperature
        ttk.Label(settings_frame, text="Warning Temp:").grid(row=0, column=0, sticky=tk.W)
        self.warning_var = tk.StringVar(value=str(self.warning_temp))
        warning_entry = ttk.Entry(settings_frame, textvariable=self.warning_var, width=8)
        warning_entry.grid(row=0, column=1, padx=5)
        
        # Critical temperature
        ttk.Label(settings_frame, text="Critical Temp:").grid(row=0, column=2, padx=(20,0))
        self.critical_var = tk.StringVar(value=str(self.critical_temp))
        critical_entry = ttk.Entry(settings_frame, textvariable=self.critical_var, width=8)
        critical_entry.grid(row=0, column=3, padx=5)
        
        # Update settings button
        ttk.Button(settings_frame, text="Update Settings", 
                  command=self.update_settings).grid(row=0, column=4, padx=10)
        
        # Temperature graph
        graph_frame = ttk.LabelFrame(main_frame, text="Max Storage Temperature History (Last 5 minutes)", padding="10")
        graph_frame.grid(row=9, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
    
    def update_sensor_status(self):
        """Update sensor status display"""
        if self.temp_reader.ohm_available:
            status = "✅ Reading storage temperatures via OpenHardwareMonitor"
            color = "green"
        else:
            status = "❌ OpenHardwareMonitor not available - please run OpenHardwareMonitor as Administrator"
            color = "red"
        
        self.sensor_status_var.set(status)
    
    def show_sensor_info(self):
        """Show detailed sensor information"""
        info = self.temp_reader.get_detailed_sensor_info()
        messagebox.showinfo("Storage Sensor Information", info)
    
    def start_realtime_updates(self):
        """Start real-time temperature updates immediately"""
        self.is_monitoring = True
        self.update_time_display()
        self.monitor_thread = threading.Thread(target=self.monitor_temperature, daemon=True)
        self.monitor_thread.start()
        
    def update_time_display(self):
        """Update the current time display"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(f"Current Time: {current_time}")
        self.root.after(1000, self.update_time_display)
        
    def get_system_info(self):
        """Get system usage info"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            return cpu_percent, memory_percent
        except:
            return None, None
    
    def update_status_indicator(self, temperature):
        """Update the status indicator color based on temperature"""
        if temperature is None:
            color = "gray"
        elif temperature >= self.critical_temp:
            color = "red"
        elif temperature >= self.warning_temp:
            color = "orange"
        else:
            color = "green"
        
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline="black")
    
    def send_desktop_notification(self, title, message, temp):
        """Send system desktop notification"""
        try:
            notification.notify(
                title=title,
                message=f"{message}\nHottest storage: {temp:.1f}°C",
                timeout=10,
                app_name="Storage Temperature Monitor"
            )
            print(f"Desktop notification sent: {title}")
        except Exception as e:
            print(f"Error sending desktop notification: {e}")
        
        # Play sound alert
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except:
            pass
    
    def update_storage_display(self):
        """Update the storage devices display"""
        # Clear existing labels
        for widget in self.scrollable_storage_frame.winfo_children():
            widget.destroy()
        
        # Create new labels for each storage device
        if self.storage_temperatures:
            row = 0
            for device_name, temp in self.storage_temperatures.items():
                # Device label
                device_label = ttk.Label(self.scrollable_storage_frame, text=f"{device_name}:", 
                                       font=("Arial", 9))
                device_label.grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
                
                # Temperature value
                temp_label = ttk.Label(self.scrollable_storage_frame, text=f"{temp:.1f} °C", 
                                     font=("Arial", 9, "bold"))
                temp_label.grid(row=row, column=1, padx=5, pady=2, sticky=tk.W)
                
                row += 1
        else:
            no_data_label = ttk.Label(self.scrollable_storage_frame, text="No storage temperature sensors found", 
                                    font=("Arial", 9), foreground="red")
            no_data_label.grid(row=0, column=0, padx=5, pady=5)
    
    def update_graph(self):
        """Update the temperature history graph"""
        self.ax.clear()
        
        if len(self.temp_history) > 0:
            time_minutes = [t/60 for t in self.time_history]
            
            self.ax.plot(time_minutes, list(self.temp_history), 'r-', linewidth=2, label='Max Storage Temperature')
            self.ax.axhline(y=self.warning_temp, color='orange', linestyle='--', alpha=0.7, label=f'Warning ({self.warning_temp}°C)')
            self.ax.axhline(y=self.critical_temp, color='red', linestyle='--', alpha=0.7, label=f'Critical ({self.critical_temp}°C)')
            
            self.ax.set_ylabel('Temperature (°C)')
            self.ax.set_xlabel('Time (minutes)')
            self.ax.set_title('Max Storage Temperature History')
            self.ax.legend()
            self.ax.grid(True, alpha=0.3)
            
            if self.temp_history:
                self.ax.set_ylim(max(0, min(self.temp_history) - 5), max(100, max(self.temp_history) + 10))
        
        self.canvas.draw()
    
    def monitor_temperature(self):
        """Main monitoring loop"""
        start_time = time.time()
        
        while self.is_monitoring:
            try:
                # Get all storage temperatures
                self.storage_temperatures = self.temp_reader.get_storage_temperatures()
                max_temp = self.temp_reader.get_max_storage_temperature()
                avg_temp = self.temp_reader.get_average_storage_temperature()
                cpu_percent, memory_percent = self.get_system_info()
                
                if max_temp is not None:
                    current_time = time.time() - start_time
                    
                    # Update display immediately
                    self.root.after(0, self.update_display, max_temp, avg_temp, cpu_percent, memory_percent, current_time)
                    
                    # Update history with max temperature
                    self.temp_history.append(max_temp)
                    self.time_history.append(current_time)
                    
                    # Check for alerts only if alert monitoring is active
                    if self.alert_monitoring_active:
                        current_absolute_time = time.time()
                        
                        if max_temp >= self.critical_temp:
                            # Send critical alerts (with cooldown)
                            if current_absolute_time - self.last_warning_time > self.warning_cooldown:
                                self.root.after(0, self.send_desktop_notification,
                                              "🔥 CRITICAL STORAGE TEMPERATURE ALERT!",
                                              "Storage temperature is critically high!",
                                              max_temp)
                                self.last_warning_time = current_absolute_time
                                
                        elif max_temp >= self.warning_temp:
                            # Send warning alerts (with cooldown)
                            if current_absolute_time - self.last_warning_time > self.warning_cooldown:
                                self.root.after(0, self.send_desktop_notification,
                                              "⚠️ HIGH STORAGE TEMPERATURE WARNING",
                                              "Storage temperature is above normal",
                                              max_temp)
                                self.last_warning_time = current_absolute_time
                else:
                    # No temperature data available
                    current_time = time.time() - start_time
                    self.root.after(0, self.update_display, None, None, None, None, current_time)
                
                # Get refresh rate from UI
                try:
                    refresh_delay = max(1, float(self.refresh_rate_var.get()))
                except:
                    refresh_delay = 2
                    
                time.sleep(refresh_delay)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(5)
    
    def update_display(self, max_temp, avg_temp, cpu_percent, memory_percent, current_time):
        """Update the UI display with current readings"""
        # Update storage devices display
        self.update_storage_display()
        
        # Update average and max temperatures
        if avg_temp is not None:
            self.avg_temp_var.set(f"{avg_temp:.1f} °C")
        else:
            self.avg_temp_var.set("-- °C")
            
        if max_temp is not None:
            self.max_temp_var.set(f"{max_temp:.1f} °C")
        else:
            self.max_temp_var.set("-- °C")
        
        self.update_status_indicator(max_temp)
        
        if max_temp is None:
            status_text = "Status: No storage temperature data available - check OpenHardwareMonitor"
            self.max_temp_display.config(foreground='red')
            self.avg_temp_display.config(foreground='red')
        elif max_temp >= self.critical_temp:
            status_text = f"Status: CRITICAL - Max storage: {max_temp:.1f}°C"
            self.max_temp_display.config(foreground='red')
            self.avg_temp_display.config(foreground='red')
        elif max_temp >= self.warning_temp:
            status_text = f"Status: WARNING - Max storage: {max_temp:.1f}°C"
            self.max_temp_display.config(foreground='orange')
            self.avg_temp_display.config(foreground='orange')
        else:
            status_text = f"Status: Normal - Max storage: {max_temp:.1f}°C"
            self.max_temp_display.config(foreground='green')
            self.avg_temp_display.config(foreground='green')
        
        # Add alert status to display
        if self.alert_monitoring_active:
            status_text += " | Alerts: ON"
        else:
            status_text += " | Alerts: OFF"
            
        self.status_var.set(status_text)
        
        update_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.last_update_var.set(f"Last update: {update_time}")
        
        self.update_graph()
    
    def start_alert_monitoring(self):
        """Start alert monitoring (notifications)"""
        self.alert_monitoring_active = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        messagebox.showinfo("Alerts Enabled", "Storage temperature alert monitoring is now active!\n\nYou will receive notifications when storage temperatures exceed thresholds.")
    
    def stop_alert_monitoring(self):
        """Stop alert monitoring (notifications)"""
        self.alert_monitoring_active = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        messagebox.showinfo("Alerts Disabled", "Storage temperature alert monitoring is now inactive.")
    
    def manual_refresh(self):
        """Force an immediate temperature refresh"""
        self.storage_temperatures = self.temp_reader.get_storage_temperatures()
        max_temp = self.temp_reader.get_max_storage_temperature()
        avg_temp = self.temp_reader.get_average_storage_temperature()
        cpu_percent, memory_percent = self.get_system_info()
        if max_temp is not None:
            self.update_display(max_temp, avg_temp, cpu_percent, memory_percent, 
                              len(self.time_history) * float(self.refresh_rate_var.get()))
    
    def update_settings(self):
        """Update temperature threshold settings"""
        try:
            new_warning = float(self.warning_var.get())
            new_critical = float(self.critical_var.get())
            
            if new_warning >= new_critical:
                messagebox.showerror("Error", "Warning temperature must be lower than critical temperature")
                return
            
            self.warning_temp = new_warning
            self.critical_temp = new_critical
            self.save_settings()
            
            messagebox.showinfo("Success", "Temperature settings updated successfully")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for temperature thresholds")
    
    def on_closing(self):
        """Clean up when closing the application"""
        self.is_monitoring = False
        self.save_settings()
        self.root.destroy()

def main():
    # Check dependencies
    try:
        import psutil
        from plyer import notification
        # Try to import WMI (required)
        try:
            import wmi
            print("✅ WMI support available")
        except ImportError:
            print("❌ WMI not available - install with: pip install wmi")
            messagebox.showerror("Missing Dependency", "WMI is required for this application.\n\nPlease install it with: pip install wmi")
            return
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install psutil plyer matplotlib wmi")
        messagebox.showerror("Missing Dependencies", f"Missing required packages:\n\nPlease install: pip install psutil plyer matplotlib wmi")
        return
    
    # Create and run the application
    root = tk.Tk()
    app = TemperatureMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()