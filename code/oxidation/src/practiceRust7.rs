#![allow(unused_variables, dead_code)]
#![allow(warnings)]

use std::mem;
// Done, Nov 21 

fn is_high_roller(badge_flags : u8) -> bool {
    let DRINKS_COMP = 0b0000_0001;
    let HIGH_ROLLER = 0x04;
    let PRIVATE_LOUNGE = 0b001_0000;

    let is_active = (HIGH_ROLLER != 0) && (badge_flags != 0);

    (is_active)
}

fn calculate_payout (bet: i32, hit_blackjack:bool) -> (i32, i32, bool) {
    let profit = if hit_blackjack == false {
        0
    } else {
        bet * 3 / 2
    };
    let return_amnt = profit + bet;
    (bet, return_amnt, hit_blackjack)
}

fn inspect_wheel(label: &str, history: &[i32]){
    println
}

fn main() {
    let chip_denominations: [u32; 5] = [25, 100, 500, 1_000, 5_000];
    let backup: [i32; 150] = [0; 150];
    

    println!("=== Rust Casino Floor ===");
    println!("VIP Check: High Roller Stauts = {}", is_high_roller(5));

    println!("-- Blackjack Hand Result --");
    let(bets, hits, totals) = calculate_payout(200, false);
    println!("Your bet: {}, Did you hit blackjack: {}, Your total return: {}", bets, totals, hits);

    println!("");
    println!("Chip chip_denominations size: {}", mem::size_of_val(&chip_denominations));

    println!("Backup vault size: {}", mem::size_of_val(&backup));


    let recent_spins: [i32; 6] = [17, 0, 22, 11, 35, 7]; 

    inspect_wheel(&recent_spins);
    inspect_wheel(&recent_spins[2..5]);

}