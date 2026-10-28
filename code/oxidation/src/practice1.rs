#![allow(unused_variables, unused_assignments)]

/* =========================================================================
   PRACTICE 1: PRIMITIVE TYPES IN RUST
   =========================================================================
   SUMMARY OF KEY CONCEPTS PRACTICED:
   - Booleans (bool): 1 byte, explicit `: bool` or inferred `true`/`false`.
   - Integers:
       * `u8`: Unsigned 8-bit integer (0 to 255).
       * `i32`: Signed 32-bit integer (-2^31 to 2^31 - 1). Supports negative values.
       * Suffix annotation (e.g. `100i32`, `100u32`): Binds type directly to literal.
   - Floating-Point: `f32` (single) and `f64` (double precision).
   - Mutability (`mut`): Variables in Rust are immutable by default. `mut` allows reassignment.
   - Compound Types:
       * Arrays `[T; N]`: Fixed-length `N`, uniform type `T`.
       * Tuples `(T1, T2, ...)`: Heterogeneous grouping of values.
   ========================================================================= */

fn main() {
    /* -------------------------------------------------------------------------
       EXERCISE 1: Booleans (bool)
       1. Declare an immutable boolean variable named `is_rust_fun` and set it to true with explicit type annotation (: bool).
       2. Declare a boolean named `is_learning_hard` and set it to false without explicit type annotation.
       ------------------------------------------------------------------------- */
    // Note: In Rust, variables are immutable by default without `mut`
    let is_rust_fun: bool = true;
    let is_learning_hard = false;
    println!("Exercise 1 -> is_rust_fun: {}, is_learning_hard: {}", is_rust_fun, is_learning_hard);

    /* -------------------------------------------------------------------------
       EXERCISE 2: Integers (Signed & Unsigned)
       1. Declare an immutable variable named `my_age` of type `u8` (unsigned 8-bit integer) and set it to your age.
       2. Declare an immutable variable named `temperature` of type `i32` (signed 32-bit integer) with a negative value (e.g., -5).
       3. Declare a variable named `count` with value 100 using suffix annotation (e.g., 100u32 or 100i32).
       ------------------------------------------------------------------------- */
    let my_age: u8 = 21; // Unsigned 8-bit integer (0 to 255)
    let temperature: i32 = -10; // Signed 32-bit integer
    let count = 100i32; // Suffix annotation
    println!("Exercise 2 -> my_age: {}, temperature: {}, count: {}", my_age, temperature, count);

    /* -------------------------------------------------------------------------
       EXERCISE 3: Floating-Point Numbers (f32 & f64)
       1. Declare a variable named `pi` of type `f64` with the value 3.14159.
       2. Declare a variable named `rating` of type `f32` with the value 4.5.
       ------------------------------------------------------------------------- */
    let pi: f64 = 3.14159;
    let rating: f32 = 4.5;
    println!("Exercise 3 -> pi: {}, rating: {}", pi, rating);

    /* -------------------------------------------------------------------------
       EXERCISE 4: Mutability (mut)
       1. Declare a MUTABLE integer variable named `score` initialized to 0.
       2. On the next line, update `score` to 10.
       ------------------------------------------------------------------------- */
    let mut score = 0;
    println!("Exercise 4 -> initial score: {}", score);
    score = 10;
    println!("Exercise 4 -> updated score: {}", score);

    /* -------------------------------------------------------------------------
       BONUS EXERCISE: Tuples and Arrays
       1. Declare an array named `favorite_numbers` containing 3 integers (i32) with type annotation `[i32; 3]`.
       2. Declare a tuple named `person_info` containing a name initial ('S'), age (25u8), and an active status (true).
       ------------------------------------------------------------------------- */
    let favorite_numbers: [i32; 3] = [13, 23, 11];
    let person_info = ('S', 25u8, true);
    println!("Bonus -> favorite_numbers: {:?}", favorite_numbers);
    println!("Bonus -> person_info (initial: {}, age: {}, active: {})",
             person_info.0, person_info.1, person_info.2);

    println!("\nPractice 1 completed successfully!");
}
