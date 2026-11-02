#![allow(unused_variables, dead_code, unused_parens)]

/* =========================================================================
   PRACTICE 4: TUPLES & FUNCTIONS IN RUST (Rust By Example)
   =========================================================================
   Reference: https://doc.rust-lang.org/rust-by-example/primitives/tuples.html

   KEY CONCEPTS:
   1. WHAT IS A TUPLE?
      - A collection of values of different (heterogeneous) types.
      - Constructed using parentheses `(value1, value2, ...)`.
      - Type signature matches element types: `(i32, f64, u8, bool)`.

   2. HOW FUNCTIONS & FUNCTION CALLS WORK IN RUST:
      - Declared with `fn name(param1: Type1, param2: Type2) -> ReturnType { ... }`.
      - Parameter type annotations are MANDATORY (Rust does not infer signatures).
      - Expression-based return: The final expression without a semicolon is
        implicitly returned! (Using `return val;` works too, but idiomatic Rust
        omits `return` and semicolon at the end of a block).
      - If no return type is specified, the function implicitly returns the "unit type" `()`.
      - Multiple return values: Rust functions return multiple values naturally
        by packing them into a tuple, e.g., `-> (i32, bool)`.

   3. TUPLE INDEXING & DESTRUCTURING:
      - Member access: 0-indexed dot notation (`my_tuple.0`, `my_tuple.1`).
      - Destructuring: Unpack into variables with `let (a, b, c) = my_tuple;`.

   4. THE 1-ELEMENT TUPLE QUIRK:
      - `(5u32)` is just the literal 5 wrapped in parentheses.
      - `(5u32,)` with a trailing comma is a 1-element tuple.

   5. THE >12 ELEMENT TRAIT LIMITATION:
      - Standard library traits (`Debug`, `PartialEq`, etc.) are implemented
        for tuples up to 12 elements. A tuple with 13+ elements cannot be printed with `{:?}`!

   Run this file anytime using:
       cargo run --bin practiceTuples
   ========================================================================= */

use std::fmt;

// -----------------------------------------------------------------------------
// HELPER FUNCTIONS (How functions work in Rust)
// -----------------------------------------------------------------------------

/// Takes a tuple with (i32, bool) and returns a new tuple with reversed elements (bool, i32).
/// Notice: The last line has no semicolon — that's Rust's implicit return expression!
fn reverse(pair: (i32, bool)) -> (bool, i32) {
    let (integer, boolean) = pair; // Destructuring the argument tuple
    (boolean, integer)             // Implicit return
}

/// Helper function taking two numbers and returning both min and max as a tuple.
fn min_max(a: i32, b: i32) -> (i32, i32) {
    if a < b {
        (a, b)
    } else {
        (b, a)
    }
}

// -----------------------------------------------------------------------------
// ACTIVITY: Matrix Struct & Formatting (from Rust By Example)
// -----------------------------------------------------------------------------
#[derive(Debug)]
struct Matrix(f32, f32, f32, f32);

// Custom Display formatting for Matrix: prints it as a 2x2 grid
impl fmt::Display for Matrix {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "( {} {} )\n( {} {} )", self.0, self.1, self.2, self.3)
    }
}

/// Transposes a 2x2 matrix:
/// [ a  b ]   transposed to   [ a  c ]
/// [ c  d ]                   [ b  d ]
fn transpose(matrix: Matrix) -> Matrix {
    Matrix(matrix.0, matrix.2, matrix.1, matrix.3)
}

// -----------------------------------------------------------------------------
// MAIN FUNCTION & EXERCISES
// -----------------------------------------------------------------------------
fn main() {
    println!("=== Practice 4: Tuples & Functions in Rust ===\n");

    // -------------------------------------------------------------------------
    // EXERCISE 1: Tuple Construction & Debug Printing
    // -------------------------------------------------------------------------
    // 1. Declare a tuple `person` containing:
    //    - a string slice `&str` ("Alice")
    //    - an age `u8` (28)
    //    - an active status `bool` (true)
    //    - a score `f32` (95.5)
    // 2. Print it using debug formatting `{:?}`.

    // TODO: Write Exercise 1 code below:
    let person: (&str, u8, bool, f32) = ("Alice", 28, true, 95.5);
    println!("Exercise 1 -> person tuple: {:?}", person);


    // -------------------------------------------------------------------------
    // EXERCISE 2: Member Access via Dot Indexing
    // -------------------------------------------------------------------------
    // Access individual members using `.0`, `.1`, `.2`, etc.
    // 1. Print the name using `person.0`
    // 2. Print the age using `person.1`
    
    // TODO: Write Exercise 2 code below:
    println!("Exercise 2 -> Name: {}, Age: {}", person.0, person.1);


    // -------------------------------------------------------------------------
    // EXERCISE 3: Tuple Destructuring
    // -------------------------------------------------------------------------
    // Unpack all values from `person` into separate variables:
    // `let (name, age, is_active, score) = person;`
    // Then print them.

    // TODO: Write Exercise 3 code below:
    let (name, age, is_active, score) = person;
    println!("Exercise 3 -> Destructured: {} is {} years old, active: {}, score: {}", 
             name, age, is_active, score);


    // -------------------------------------------------------------------------
    // EXERCISE 4: Functions with Tuples as Arguments & Return Values
    // -------------------------------------------------------------------------
    // 1. Call `reverse((42, true))` and print the result.
    // 2. Call `min_max(100, 25)` and destructure into `(smallest, largest)`.
    // 3. Print `smallest` and `largest`.

    // TODO: Write Exercise 4 code below:
    let original_pair = (42, true);
    let reversed_pair = reverse(original_pair);
    println!("Exercise 4a -> Original: {:?}, Reversed: {:?}", original_pair, reversed_pair);

    let (smallest, largest) = min_max(100, 25);
    println!("Exercise 4b -> Min: {}, Max: {}", smallest, largest);


    // -------------------------------------------------------------------------
    // EXERCISE 5: The 1-Element Tuple vs Parentheses Quirk
    // -------------------------------------------------------------------------
    // Notice what happens with and without a comma:
    let not_a_tuple = (5u32);   // Just a u32 inside parentheses
    let actual_tuple = (5u32,); // A 1-element tuple!

    println!("Exercise 5 -> not_a_tuple type is integer: {}", not_a_tuple);
    println!("Exercise 5 -> actual_tuple type is 1-tuple: {:?}", actual_tuple);


    // -------------------------------------------------------------------------
    // EXERCISE 6: Tuples of Tuples (Tuples can be nested!)
    // -------------------------------------------------------------------------
    let nested_tuple = ((1u8, 2u16), (3u32, 4u64), -5i32);
    println!("Exercise 6 -> Nested tuple: {:?}", nested_tuple);
    // Access nested member:
    println!("Exercise 6 -> Inner item (nested_tuple.1).0 = {}", (nested_tuple.1).0);


    // -------------------------------------------------------------------------
    // ACTIVITY: Matrix & Transpose (from Rust By Example)
    // -------------------------------------------------------------------------
    let matrix = Matrix(1.1, 1.2, 2.1, 2.2);
    println!("\nActivity -> Matrix Display formatting:\n{}", matrix);

    let transposed = transpose(matrix);
    println!("\nActivity -> Transposed Matrix:\n{}", transposed);

    println!("\nPractice 4 finished!");
}
