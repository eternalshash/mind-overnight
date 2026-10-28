#![allow(unused_variables, unused_assignments, dead_code)]

/* =========================================================================
   PRACTICE & REVISION: RUST FUNDAMENTALS
   =========================================================================
   Use this file to practice what you've learned:
   - Scalar Primitives: bool, i32, u8, f64, char
   - Type Annotations vs. Suffix Literals (e.g., 42u32, 3.14f32)
   - Mutability: `let` (immutable) vs `let mut` (mutable)
   - Bidirectional Type Inference
   - Compound Types: Arrays `[T; length]` & Tuples `(...)`
   - Structs: Classic, Tuple, and Unit

   Run with:
       cargo run --bin practiceRevise
   Or compile directly with:
       rustc src/practiceRevise.rs -o practiceRevise && ./practiceRevise
   ========================================================================= */

fn main() {
    println!("=== Practice & Revision ===");

    // TODO 1: Declare an immutable boolean `is_rust_awesome` set to true.
    let is_rust_awesome = true;

    // TODO 2: Declare an unsigned 8-bit integer `my_byte` set to 255.
    let my_byte: u8 = 225;    

    // TODO 3: Declare a signed 64-bit integer `big_number` using suffix notation.
    let big_number = 5f64;    

    // TODO 4: Declare a mutable variable `counter` initialized to 1, then update it to 2.
    let mut counter = 1;
    counter = 2; // counter+=1 -> would that work ?    

    // TODO 5: Create an array `scores` of 4 integers (i32) and print its length and first element.
    let scores: [i32 ; 4] = [1, 2, 3, 4];

    println!("{}", scores[0]);
    println!("{}", scores.len());


    // TODO 6: Create a tuple `user` holding an ID (u32), username initial ('A'), and active status (bool).
    let user = (5u32, 'A', true ); 

    println!("Revision template ready for coding!");
}
