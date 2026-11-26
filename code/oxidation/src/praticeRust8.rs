// Practice Rust # 8 

#![allow(unused_variables, dead_code)]
#![allow(warnings)]

use std::mem;

fn check_car_system(status: u8, flag_mask: u8) -> bool {
    let Limit_Status: bool = (status & flag_mask != 0);
    (Limit_Status)   
}

//fn analyze_tire_strat(target: f64, current: f64) -> () {


fn main() {
    let DRS_ENABLED = 0b0000_0001;
    let ERS_DEPLOY = 0b0000_0010;
    let PIT_LIMITTER: u8 = 0b0000_0100;
    let RAIN_LIGHT: u8 = 0x08;
    
    let mut car_status = (DRS_ENABLED | ERS_DEPLOY);

    println!(" ");
    println!("=== F1 Pit Wall & Telemetry Engine ===");

    println!("-- Phase A: Steering Wheel Bitwise Flags & Literals --");
    println!("Intial status: Pit Limiter? {}", check_car_system(car_status, PIT_LIMITTER));

    car_status |= PIT_LIMITTER;

    println!("Updated status: Pit Limeter active now? {}", check_car_system(car_status, PIT_LIMITTER));

    let engine_rpm = (150_000u32);
    let aero_downforce = (3.25e-2f64);

    println!("Engine RPM limit: {}", engine_rpm);
    println!("Aero downforce coefficient: {}", aero_downforce);

    println!("-- Phase B: Struct Triad --");
    let CarTelemetry = (44, "HAM", 104.2, true);
    println!("{:?}", CarTelemetry);
    println!("Car Telemetry:{} Car Number: {}, Driver Tag: {}, tire temp: {}, in drs zone: {}", 
            stringify!(CarTelemetry),CarTelemetry.0 , CarTelemetry.1, CarTelemetry.2, CarTelemetry.3);
    
    let GForceVector = (3.8, -4.2, 1.1);
    println!("G-Force Vector: Lateral = {}, Longitudinal = {}", GForceVector.0, GForceVector.1);

    #[derive(Debug)]
    struct PitCrewStatus;
    let readyState = PitCrewStatus;
    println!("{:?}", readyState);
    println!("Pit Crew Status: PitCrewReady confirmed - pit box clear!");


    println!("-- Phase C: Strategy Tuples & Destructuring --");    


    println!(" "); 

}



