fn main() {
    /* =========================================================================
       PRACTICE 1: PRIMITIVE TYPES IN RUST
       =========================================================================
       Instructions:
       Fill in the code below each exercise prompt according to the instructions.
       To test your code, you can run: rustc src/practice1.rs -o practice1 && ./practice1
       ========================================================================= */

    /* -------------------------------------------------------------------------
       EXERCISE 1: Booleans (bool)
       1. Declare an immutable boolean variable named `is_rust_fun` and set it to true with explicit type annotation (: bool).
       2. Declare a boolean named `is_learning_hard` and set it to false without explicit type annotation.
       ------------------------------------------------------------------------- */

    // Write your code for Exercise 1 below:
   let  is_rust_fun: bool = true;  // in rust variables are immutable by default 
   let is_learning_hard = false;


    /* -------------------------------------------------------------------------
       EXERCISE 2: Integers (Signed & Unsigned)
       1. Declare an immutable variable named `my_age` of type `u8` (unsigned 8-bit integer) and set it to your age.
       2. Declare an immutable variable named `temperature` of type `i32` (signed 32-bit integer) with a negative value (e.g., -5).
       3. Declare a variable named `count` with value 100 using suffix annotation (e.g., 100u32 or 100i32).
       ------------------------------------------------------------------------- */

    // Write your code for Exercise 2 below:
    let my_age: u8 = 21;  // unsigned int should be 21, first you declare the variable and then specify type with u8

    let temperature: i32 = -10;

    let count = 100i32;

    /* -------------------------------------------------------------------------
       EXERCISE 3: Floating-Point Numbers (f32 & f64)
       1. Declare a variable named `pi` of type `f64` with the value 3.14159.
       2. Declare a variable named `rating` of type `f32` with the value 4.5.
       ------------------------------------------------------------------------- */

    // Write your code for Exercise 3 below:

   let pi: f64 = 3.1415;
   let rating: f32 = 4.5;

    /* -------------------------------------------------------------------------
       EXERCISE 5: Mutability (mut)
       1. Declare a MUTABLE integer variable named `score` initialized to 0.
       2. On the next line, update `score` to 10.
       ------------------------------------------------------------------------- */

    // Write your code for Exercise 5 below:

    let mut score = 0;
    score = 10;


    /* -------------------------------------------------------------------------
       BONUS EXERCISE: Tuples and Arrays
       1. Declare an array named `favorite_numbers` containing 3 integers (i32) with type annotation `[i32; 3]`.
       2. Declare a tuple named `person_info` containing a name initial ('S'), age (25u8), and an active status (true).
       ------------------------------------------------------------------------- */

    // Write your code for Bonus Exercise below:

    let favorite_numbers: [i32; 3] = [13, 23, 11];
    let person_info = ('S', 25u8, true);




    // Print statement to confirm code runs
    println!("Practice 1 completed!");
}
