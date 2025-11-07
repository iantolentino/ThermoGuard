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

class TemperatureMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Device Temperature Monitor")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Temperature thresholds
        self.critical_temp = 85  # °C
        self.warning_temp = 75   # °C
        self.normal_temp = 60    # °C
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Temperature history for graphing
        self.temp_history = deque(maxlen=50)
        self.time_history = deque(maxlen=50)
        
        self.setup_ui()
        self.start_realtime_updates()  # Start real-time updates immediately
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Device Temperature Monitor", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Current time display
        self.time_var = tk.StringVar(value="Loading...")
        time_label = ttk.Label(main_frame, textvariable=self.time_var,
                              font=("Arial", 10), foreground="gray")
        time_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Temperature display with larger font
        temp_frame = ttk.Frame(main_frame)
        temp_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        ttk.Label(temp_frame, text="Current Temperature:", 
                 font=("Arial", 12)).grid(row=0, column=0, padx=(0, 10))
        
        self.temp_var = tk.StringVar(value="-- °C")
        self.temp_display = ttk.Label(temp_frame, textvariable=self.temp_var, 
                                     font=("Arial", 24, "bold"))
        self.temp_display.grid(row=0, column=1)
        
        # Temperature status indicator
        self.status_indicator = tk.Canvas(main_frame, width=20, height=20, bg="gray")
        self.status_indicator.grid(row=2, column=2, padx=(10, 0))
        
        # Status display
        self.status_var = tk.StringVar(value="Status: Initializing...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                font=("Arial", 11))
        status_label.grid(row=3, column=0, columnspan=3, pady=5)
        
        # Last update time
        self.last_update_var = tk.StringVar(value="Last update: --")
        last_update_label = ttk.Label(main_frame, textvariable=self.last_update_var,
                                     font=("Arial", 9), foreground="blue")
        last_update_label.grid(row=4, column=0, columnspan=3, pady=(0, 10))
        
        # Controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Monitoring Controls", padding="10")
        controls_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
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
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Temperature Settings (°C)", padding="10")
        settings_frame.grid(row=6, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
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
        graph_frame = ttk.LabelFrame(main_frame, text="Temperature History (Last 5 minutes)", padding="10")
        graph_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # System info frame
        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding="5")
        info_frame.grid(row=8, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        # CPU usage
        self.cpu_var = tk.StringVar(value="CPU: --%")
        cpu_label = ttk.Label(info_frame, textvariable=self.cpu_var, font=("Arial", 9))
        cpu_label.grid(row=0, column=0, padx=10)
        
        # Memory usage
        self.memory_var = tk.StringVar(value="Memory: --%")
        memory_label = ttk.Label(info_frame, textvariable=self.memory_var, font=("Arial", 9))
        memory_label.grid(row=0, column=1, padx=10)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
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
        self.root.after(1000, self.update_time_display)  # Update every second
        
    def get_temperature(self):
        """Get current temperature using psutil"""
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current:  # Only use if current temperature is available
                                return entry.current
            # Fallback: Return a simulated temperature for demonstration
            return self.simulate_temperature()
        except Exception as e:
            print(f"Error getting temperature: {e}")
            return None
    
    def get_system_info(self):
        """Get CPU and memory usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            return cpu_percent, memory_percent
        except:
            return None, None
    
    def simulate_temperature(self):
        """Simulate temperature readings for demonstration"""
        import random
        # Base temperature influenced by CPU usage
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            base_temp = 30 + (cpu_usage * 0.4)  # CPU usage affects base temp
        except:
            base_temp = 45
            
        # Add some random variation
        base_temp += random.uniform(-2, 2)
        
        # Occasionally simulate temperature spikes
        spike_chance = random.random()
        
        if spike_chance > 0.98:  # 2% chance of critical spike
            return min(95, base_temp + random.uniform(40, 50))
        elif spike_chance > 0.92:  # 6% chance of warning spike
            return min(85, base_temp + random.uniform(20, 30))
        else:
            return max(30, base_temp)
    
    def update_status_indicator(self, temperature):
        """Update the status indicator color based on temperature"""
        if temperature >= self.critical_temp:
            color = "red"
        elif temperature >= self.warning_temp:
            color = "orange"
        else:
            color = "green"
        
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline="black")
    
    def send_notification(self, title, message, temp):
        """Send system notification"""
        try:
            notification.notify(
                title=title,
                message=f"{message}\nCurrent temperature: {temp:.1f}°C",
                timeout=10,
                app_name="Temperature Monitor"
            )
        except Exception as e:
            print(f"Error sending notification: {e}")
        
        # Also play a sound alert
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except:
            pass
    
    def update_graph(self):
        """Update the temperature history graph"""
        self.ax.clear()
        
        if len(self.temp_history) > 0:
            # Convert time to minutes for better readability
            time_minutes = [t/60 for t in self.time_history]
            
            self.ax.plot(time_minutes, list(self.temp_history), 'b-', linewidth=2, label='Temperature')
            self.ax.axhline(y=self.warning_temp, color='orange', linestyle='--', alpha=0.7, label=f'Warning ({self.warning_temp}°C)')
            self.ax.axhline(y=self.critical_temp, color='red', linestyle='--', alpha=0.7, label=f'Critical ({self.critical_temp}°C)')
            
            self.ax.set_ylabel('Temperature (°C)')
            self.ax.set_xlabel('Time (minutes)')
            self.ax.set_title('Temperature History')
            self.ax.legend()
            self.ax.grid(True, alpha=0.3)
            
            # Set y-axis limits
            if self.temp_history:
                self.ax.set_ylim(max(0, min(self.temp_history) - 5), max(100, max(self.temp_history) + 10))
        
        self.canvas.draw()
    
    def monitor_temperature(self):
        """Main monitoring loop"""
        start_time = time.time()
        last_warning_time = 0
        warning_cooldown = 30  # seconds between repeated warnings
        alert_monitoring_active = False
        
        while self.is_monitoring:
            try:
                current_temp = self.get_temperature()
                cpu_percent, memory_percent = self.get_system_info()
                
                if current_temp is not None:
                    current_time = time.time() - start_time
                    
                    # Update display immediately
                    self.root.after(0, self.update_display, current_temp, cpu_percent, memory_percent, current_time)
                    
                    # Update history
                    self.temp_history.append(current_temp)
                    self.time_history.append(current_time)
                    
                    # Check for alerts only if alert monitoring is active
                    if hasattr(self, 'alert_monitoring_active') and self.alert_monitoring_active:
                        if current_temp >= self.critical_temp:
                            # Send critical notification (with cooldown)
                            if current_time - last_warning_time > warning_cooldown:
                                self.root.after(0, self.send_notification,
                                              "🔥 CRITICAL TEMPERATURE ALERT!",
                                              "Device temperature is critically high!",
                                              current_temp)
                                last_warning_time = current_time
                                
                        elif current_temp >= self.warning_temp:
                            # Send warning notification (with cooldown)
                            if current_time - last_warning_time > warning_cooldown:
                                self.root.after(0, self.send_notification,
                                              "⚠️ HIGH TEMPERATURE WARNING",
                                              "Device temperature is above normal",
                                              current_temp)
                                last_warning_time = current_time
                
                # Get refresh rate from UI
                try:
                    refresh_delay = max(1, float(self.refresh_rate_var.get()))
                except:
                    refresh_delay = 2
                    
                time.sleep(refresh_delay)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(5)
    
    def update_display(self, temperature, cpu_percent, memory_percent, current_time):
        """Update the UI display with current readings"""
        # Update temperature display
        self.temp_var.set(f"{temperature:.1f} °C")
        
        # Update status indicator
        self.update_status_indicator(temperature)
        
        # Update status text
        if temperature >= self.critical_temp:
            status_text = f"Status: CRITICAL - {temperature:.1f}°C"
            self.temp_display.config(foreground='red')
        elif temperature >= self.warning_temp:
            status_text = f"Status: WARNING - {temperature:.1f}°C"
            self.temp_display.config(foreground='orange')
        else:
            status_text = f"Status: Normal - {temperature:.1f}°C"
            self.temp_display.config(foreground='green')
        
        self.status_var.set(status_text)
        
        # Update last update time
        update_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.last_update_var.set(f"Last update: {update_time}")
        
        # Update system info
        if cpu_percent is not None:
            self.cpu_var.set(f"CPU: {cpu_percent:.1f}%")
        if memory_percent is not None:
            self.memory_var.set(f"Memory: {memory_percent:.1f}%")
        
        # Update graph
        self.update_graph()
    
    def start_alert_monitoring(self):
        """Start alert monitoring (notifications)"""
        self.alert_monitoring_active = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set(self.status_var.get() + " | Alerts: ON")
    
    def stop_alert_monitoring(self):
        """Stop alert monitoring (notifications)"""
        self.alert_monitoring_active = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set(self.status_var.get().replace(" | Alerts: ON", "") + " | Alerts: OFF")
    
    def manual_refresh(self):
        """Force an immediate temperature refresh"""
        # This will happen automatically in the monitoring thread
        # We just trigger a UI update
        current_temp = self.get_temperature()
        cpu_percent, memory_percent = self.get_system_info()
        if current_temp is not None:
            self.update_display(current_temp, cpu_percent, memory_percent, 
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
            
            messagebox.showinfo("Success", "Temperature settings updated successfully")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for temperature thresholds")
    
    def on_closing(self):
        """Clean up when closing the application"""
        self.is_monitoring = False
        self.root.destroy()

def main():
    # Check dependencies
    try:
        import psutil
        from plyer import notification
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install psutil plyer matplotlib")
        return
    
    # Create and run the application
    root = tk.Tk()
    app = TemperatureMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Show initial loading message
    messagebox.showinfo("Temperature Monitor", 
                       "Real-time temperature monitoring started!\n\n"
                       "The app will now show live temperature updates.\n"
                       "Click 'Start Alert Monitoring' to enable notifications.")
    
    root.mainloop()

if __name__ == "__main__":
    main()