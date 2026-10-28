#![allow(unused_variables, dead_code)]

/* =========================================================================
   PRACTICE 3: LITERALS AND OPERATORS (Rust By Example)
   =========================================================================
   Reference: https://doc.rust-lang.org/rust-by-example/primitives/literals.html

   KEY CONCEPTS FROM YOUR NOTES:
   1. Number bases:
      - Hexadecimal: `0x` (e.g., 0xFA)
      - Octal:       `0o` (e.g., 0o77)
      - Binary:      `0b` (e.g., 0b1010_0011)
   2. Underscores improve readability: `1_000_000u32` instead of commas.
   3. Scientific notation: `1e6` is treated as floating-point (`f64`).
   4. Suffix annotations: Tell the compiler literal types directly (`1i32`, `100u8`).
   5. Bitwise operators: `&` (AND), `|` (OR), `^` (XOR), `<<` (shift left), `>>` (shift right).
   6. Memory inspection: `std::mem::size_of_val(&variable)` returns size in bytes.

   Run this file anytime using:
       cargo run --bin practiceRust3
   ========================================================================= */

fn main() {
    println!("=== Practice 3: Literals & Operators ===\n");

    // -------------------------------------------------------------------------
    // EXERCISE 1: Number Bases & Readable Underscores
    // -------------------------------------------------------------------------
    // 1. Declare a variable `hex_val` with the value 255 in hexadecimal (0xFF).
    // 2. Declare a variable `bin_val` with the value 42 in binary (0b0010_1010) using an underscore.
    // 3. Declare a variable `one_million` with 1000000 typed as u32 with underscores (e.g., 1_000_000u32).
    
    // TODO: Write Exercise 1 code below:

    let hex_val =0xFF;
    let bin_val = 0b0010_1010;
    let one_million: u32 = 1_000_000;

    println!("{}", one_million);

    // -------------------------------------------------------------------------
    // EXERCISE 2: Scientific Notation & Floats
    // -------------------------------------------------------------------------
    // 1. Declare a variable `sci_mil` using scientific notation `1e6`.
    // 2. Declare a variable `tiny` with value 0.00001 using scientific notation (`1e-5`).
    // TODO: Write Exercise 2 code below:
    let sci_mil = 1e6;
    let tiny = 1e-5;

    // -------------------------------------------------------------------------
    // EXERCISE 3: Arithmetic Operations with Literal Suffixes
    // -------------------------------------------------------------------------
    // 1. Calculate integer division: divide `22i32` by `7i32` and store in `int_div`.
    // 2. Calculate float division: divide `22.0f64` by `7.0f64` and store in `float_div`.
    // 3. Calculate the remainder (modulo): `43i32 % 5i32` and store in `remainder`.
    // Notice the difference between integer division (truncates) and float division!

    // TODO: Write Exercise 3 code below:
    let int_div = (22i32 / 7i32);

    let float_div = (22.0f64/ 7.0f64);

    let remainder = (43i32 % 5i32);

    println!("{}", int_div); 


    // -------------------------------------------------------------------------
    // EXERCISE 4: Bitwise Operations
    // -------------------------------------------------------------------------
    // Given the two 8-bit unsigned values below:
    let byte_a: u8 = 0b1010_1100;
    let byte_b: u8 = 0b0101_1110;

    // 1. Perform bitwise AND (`byte_a & byte_b`) and store in `and_res`.
    // 2. Perform bitwise OR  (`byte_a | byte_b`) and store in `or_res`.
    // 3. Perform bitwise XOR (`byte_a ^ byte_b`) and store in `xor_res`.
    // 4. Shift `1u8` to the left by 3 bits (`1u8 << 3`) and store in `shift_res`.
    //    (Hint: shifting 1 left by 3 produces 2^3 = 8).

    // TODO: Write Exercise 4 code below:

    let and_res = byte_a & byte_b ;

    let or_res = byte_a | byte_b ;

    let shift_res = 1u8<<3 ;
 
    println!("Checking shift {}", shift_res);


    // -------------------------------------------------------------------------
    // EXERCISE 5: Memory Size Inspection (`std::mem::size_of_val`)
    // -------------------------------------------------------------------------
    // Check how many bytes different types take up in memory:
    let small_int: i8 = 42;
    let big_int: i64 = 42;
    let default_float = 3.14; // remember this defaults to f64

    // Print the size in bytes of each using `std::mem::size_of_val(&...):
    // Example: println!("size of small_int: {} byte(s)", std::mem::size_of_val(&small_int));

    // TODO: Print the size of big_int and default_float below
    
    println!("size of the small int {}", std::mem::size_of_val(&small_int));
    println!("size of the big int {}", std::mem::size_of_val(&big_int));
    println!("size of the default float {}", std::mem::size_of_val(&default_float)); // since it defautls to f64 -> should be 8 bytes not 4

    println!("\nPractice 3 finished!");
}
