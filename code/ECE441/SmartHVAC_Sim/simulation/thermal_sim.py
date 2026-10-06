import numpy as np
import matplotlib.pyplot as plt

def simulate_chamber(K_p, K_i, K_d, target_temp=25.0, duration=3600, dt=1.0):
    # Physical constants for 1st Order RC Thermal Model
    C_th = 5000.0   # Thermal capacity of the chamber (Joules/Kelvin)
    R_th = 0.5      # Thermal resistance of XPS walls (Kelvin/Watt)
    T_amb = 20.0    # Ambient lab temperature (C)
    P_heater = 60.0 # Max power of 12V PTC heater (W)
    P_cooling = 30.0 # Max convective cooling from blower fan (W equivalent)
    sensor_lag = 3.0 # Sensor time constant (seconds)

    # Time array
    times = np.arange(0, duration, dt)
    
    # State variables
    T_chamber = np.zeros(len(times))
    T_chamber[0] = T_amb
    T_sensor = np.zeros(len(times))
    T_sensor[0] = T_amb
    
    heater_pwm = np.zeros(len(times))
    fan_pwm = np.zeros(len(times))
    
    # PID Variables
    integral = 0.0
    prev_error = 0.0
    
    for i in range(1, len(times)):
        # 1. Read Sensor (with exponential lag filter)
        T_sensor[i] = T_sensor[i-1] + (dt / sensor_lag) * (T_chamber[i-1] - T_sensor[i-1])
        
        # 2. Split-Range PID Control Logic
        error = target_temp - T_sensor[i]
        integral += error * dt
        
        # Anti-windup
        integral = max(-100, min(100, integral))
        
        derivative = (error - prev_error) / dt
        prev_error = error
        
        pid_output = (K_p * error) + (K_i * integral) + (K_d * derivative)
        
        # Deadband / Split Range
        if pid_output > 5: # Heating needed
            h_pwm = min(100.0, pid_output)
            f_pwm = 20.0 # Baseline draft for anemometer
        elif pid_output < -5: # Cooling needed
            h_pwm = 0.0
            f_pwm = min(100.0, abs(pid_output))
        else: # Deadband
            h_pwm = 0.0
            f_pwm = 20.0
            
        heater_pwm[i] = h_pwm
        fan_pwm[i] = f_pwm
        
        # 3. Thermal Physics Update (1st Order RC)
        Q_in = (h_pwm / 100.0) * P_heater
        Q_out = (T_chamber[i-1] - T_amb) / R_th
        Q_fan = (f_pwm / 100.0) * P_cooling if T_chamber[i-1] > T_amb else 0
        
        dT = (Q_in - Q_out - Q_fan) / C_th * dt
        T_chamber[i] = T_chamber[i-1] + dT
        
        # Introduce a door-open disturbance halfway through
        if i == len(times) // 2:
            T_chamber[i] -= 3.0 # Sudden 3C drop

    return times, T_chamber, T_sensor, heater_pwm, fan_pwm

if __name__ == "__main__":
    # Ziegler-Nichols (Tuned heuristic estimates for a slow thermal plant)
    Kp = 45.0
    Ki = 0.5
    Kd = 10.0
    
    t, T_c, T_s, h_pwm, f_pwm = simulate_chamber(Kp, Ki, Kd, target_temp=28.0)
    
    print(f"--- Thermal Simulation Completed ---")
    print(f"Recommended PID Gains: Kp={Kp}, Ki={Ki}, Kd={Kd}")
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    ax1.plot(t, T_c, label='Chamber Temp (Actual)', alpha=0.5)
    ax1.plot(t, T_s, label='Sensor Temp (Measured)', linewidth=2)
    ax1.axhline(y=28.0, color='r', linestyle='--', label='Setpoint (28 C)')
    ax1.set_ylabel('Temperature (C)')
    ax1.set_title('Smart HVAC Thermal Response & Disturbance Rejection')
    ax1.legend()
    ax1.grid(True)
    
    ax2.plot(t, h_pwm, label='Heater PWM (%)', color='red')
    ax2.plot(t, f_pwm, label='Fan PWM (%)', color='blue')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Duty Cycle (%)')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('thermal_response.png')
    print("Plot saved as thermal_response.png")
