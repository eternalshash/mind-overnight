#ifndef THERMAL_COMFORT_H
#define THERMAL_COMFORT_H

#include <math.h>

class ThermalComfort {
public:
    // Computes apparent temperature based on Steadman's / Australian Bureau of Meteorology equations
    // T: Dry-bulb temp (C)
    // RH: Relative Humidity (%)
    // V: Air Velocity (m/s)
    static float calculateApparentTemp(float T, float RH, float V) {
        // Vapor pressure
        float e = (RH / 100.0) * 6.105 * exp(17.27 * T / (237.7 + T));
        
        // Apparent temperature formula
        // AT = Ta + 0.33×e - 0.70×v - 4.00
        float apparent_temp = T + (0.33 * e) - (0.70 * V) - 4.00;
        
        return apparent_temp;
    }
};

#endif // THERMAL_COMFORT_H
