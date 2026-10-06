import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# PHYSICAL ENVIRONMENT MODELS
# ---------------------------------------------------------
class RoomEnvironment:
    def __init__(self, volume_m3=50.0, R_th=0.5, T_out=20.0, T_init=20.0):
        # Thermal mass (Joules / Kelvin) based on volume of air
        self.C_th = volume_m3 * 100.0  
        self.R_th = R_th       # Thermal resistance (insulation quality)
        self.T_out = T_out     # Ambient outdoor temperature (C)
        self.T = T_init        # Current indoor temperature (C)

    def update(self, Q_hvac_watts, dt):
        # Heat exchange with the outdoors through the walls
        Q_leak = (self.T_out - self.T) / self.R_th
        # Total change in temperature
        dT = (Q_hvac_watts + Q_leak) / self.C_th * dt
        self.T += dT

class SmartHVAC:
    def __init__(self, Kp=45.0, Ki=0.5, Kd=10.0, max_heat_W=60.0, max_cool_W=40.0):
        # PID Constants
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        # Actuator capacities
        self.max_heat_W = max_heat_W
        self.max_cool_W = max_cool_W
        
        # State variables
        self.integral = 0.0
        self.prev_error = 0.0
        
        # Hardware Health / Efficiency
        self.efficiency = 1.0

    def compute(self, T_sensor, setpoint, dt):
        error = setpoint - T_sensor
        
        # PID Math
        self.integral += error * dt
        self.integral = max(-100, min(100, self.integral)) # Anti-windup
        derivative = (error - self.prev_error) / dt
        self.prev_error = error

        pid_output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        # Split-range actuation
        if pid_output > 5.0: # Heating
            h_pwm = min(100.0, pid_output)
            f_pwm = 20.0 # baseline ventilation
            Q_watts = (h_pwm / 100.0) * self.max_heat_W * self.efficiency
        elif pid_output < -5.0: # Cooling
            h_pwm = 0.0
            f_pwm = min(100.0, abs(pid_output))
            Q_watts = -(f_pwm / 100.0) * self.max_cool_W * self.efficiency
        else: # Deadband satisfied
            h_pwm = 0.0
            f_pwm = 20.0
            Q_watts = 0.0

        return h_pwm, f_pwm, Q_watts

# ---------------------------------------------------------
# SCENARIO RUNNER
# ---------------------------------------------------------
def run_scenario(name, T_out_init, setpoint, duration=3600, dt=1.0, event_callback=None):
    room = RoomEnvironment(T_out=T_out_init, T_init=T_out_init)
    hvac = SmartHVAC()
    
    times = np.arange(0, duration, dt)
    T_room_history = []
    T_out_history = []
    h_pwm_history = []
    f_pwm_history = []

    T_sensor = T_out_init # Simulated BME280 sensor

    for t in times:
        # Trigger dynamic events (e.g. open window, break hardware)
        if event_callback:
            event_callback(t, room, hvac)
        
        # Exponential sensor lag (takes ~3 seconds to read real temp)
        T_sensor += (dt / 3.0) * (room.T - T_sensor)
        
        # Compute HVAC response
        h_pwm, f_pwm, Q_watts = hvac.compute(T_sensor, setpoint, dt)
        
        # Update Room Environment Physics
        room.update(Q_watts, dt)

        # Log metrics
        T_room_history.append(room.T)
        T_out_history.append(room.T_out)
        h_pwm_history.append(h_pwm)
        f_pwm_history.append(f_pwm)

    return times, T_room_history, T_out_history, h_pwm_history, f_pwm_history


# ---------------------------------------------------------
# DEFINING THE 4 SITUATIONS
# ---------------------------------------------------------
def event_normal(t, room, hvac): 
    pass

def event_heatwave(t, room, hvac):
    # At t=1000s, an extreme heatwave hits, outdoor temp spikes to 42C
    if t > 1000: room.T_out = 42.0 

def event_open_window(t, room, hvac):
    # At t=1500s in winter, someone opens a window, ruining room insulation (R_th drops)
    if t > 1500: room.R_th = 0.05 

def event_clogged_filter(t, room, hvac):
    # At t=1000s, dust clogs the air filter, dropping HVAC thermal transfer efficiency to 25%
    if t > 1000: hvac.efficiency = 0.25 


# ---------------------------------------------------------
# EXECUTE AND PLOT
# ---------------------------------------------------------
if __name__ == "__main__":
    fig, axs = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Smart HVAC Environment Simulation - 4 Dynamic Scenarios', fontsize=16, fontweight='bold', y=0.98)
    
    scenarios = [
        ("Situation 1: Standard Cold Start", 15.0, 25.0, event_normal, axs[0,0]),
        ("Situation 2: Extreme Summer Heatwave", 25.0, 22.0, event_heatwave, axs[0,1]),
        ("Situation 3: Winter Window Opened", 5.0, 25.0, event_open_window, axs[1,0]),
        ("Situation 4: Clogged Air Filter (Hardware Degradation)", 15.0, 25.0, event_clogged_filter, axs[1,1])
    ]

    for title, T_out, setpoint, event, ax in scenarios:
        t, T_room, T_env, h_pwm, f_pwm = run_scenario(title, T_out, setpoint, event_callback=event)
        
        # Plot Temperatures
        ax.plot(t, T_room, 'k-', linewidth=2.5, label='Room Temp')
        ax.plot(t, T_env, 'orange', linestyle='--', linewidth=2, label='Outdoor Temp')
        ax.axhline(setpoint, color='g', linestyle=':', linewidth=2, label='Target Setpoint')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_ylabel('Temperature (°C)', fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Plot HVAC Effort (PWM) on secondary Y-axis
        ax2 = ax.twinx()
        ax2.fill_between(t, h_pwm, color='red', alpha=0.25, label='Heater Effort %')
        ax2.fill_between(t, f_pwm, color='blue', alpha=0.25, label='Fan / Cool Effort %')
        ax2.set_ylabel('HVAC Actuator PWM (%)', color='gray')
        ax2.set_ylim(0, 105)
        
        # Combine legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9, facecolor='white', framealpha=0.9)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('advanced_scenarios.png', dpi=150)
    print("Advanced environment scenarios successfully simulated and saved to advanced_scenarios.png")
