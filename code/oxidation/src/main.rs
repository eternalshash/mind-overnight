#![allow(unused_variables, unused_assignments)]

/* ================================================================================================
   SUMMARY OF NOTES: RUST PRIMITIVE TYPES & THE TYPE SYSTEM
   ================================================================================================
   1. VARIABLES & MUTABILITY:
      - In Rust, variables are IMMUTABLE by default (`let x = 5;`).
      - To allow a variable's value to change, you must explicitly mark it with `mut` (`let mut x = 5;`).
      - STATIC TYPING GUARANTEE: In Rust, a variable's type is strictly fixed at compile time and can
        NEVER change at runtime. Only its stored value can change if marked `mut`.

   2. PRIMITIVE SCALAR TYPES:
      - Booleans:
        * `bool` -> stores either `true` or `false` (1 byte).
      - Integers:
        * Signed: `i8`, `i16`, `i32`, `i64`, `i128`, `isize` ('i' = signed, allows negative & positive).
        * Unsigned: `u8`, `u16`, `u32`, `u64`, `u128`, `usize` ('u' = unsigned, non-negative values only).
        * Default: Unannotated integer literals default to `i32` if no other context is provided.
        * Suffix annotation: Literal suffix sets the exact type (e.g., `5i32`, `100u32`, `25u8`).
      - Floating-Point:
        * `f32` -> 32-bit single-precision floating point.
        * `f64` -> 64-bit double-precision floating point.
        * Default: Unannotated float literals default to `f64` (e.g., `3.0` is `f64`).
      - Characters:
        * `char` -> 4-byte Unicode scalar value represented in single quotes (`'S'`).

   3. BIDIRECTIONAL TYPE INFERENCE:
      - Rust does NOT just look at a variable declaration line in isolation.
      - When you write `let mut inferred_type = 12;`, Rust recognizes it as an integer literal, but
        temporarily postpones locking down the concrete integer type.
      - If later in the same scope you assign `inferred_type = 4294967296i64;`, Rust infers backwards
        that `inferred_type` must have been `i64` from the very beginning.
      - Therefore, Rust treats the initial `12` as `12i64` instead of defaulting to `i32`.

   4. PRIMITIVE COMPOUND TYPES:
      - Arrays (`[T; length]`):
        * Homogeneous: All elements must share the exact same type `T`.
        * Fixed length: Size is fixed at compile time and allocated directly on the stack.
        * Indexing: 0-indexed (`0`, `1`, `2`, ...). Rust enforces bounds checking at runtime,
          safely panicking instead of corrupting memory (unlike C/C++ buffer overflows).
      - Tuples (`(T1, T2, ...)`):
        * Heterogeneous: Can group together multiple elements of DIFFERENT types.
        * Constructed with parentheses `(...)`.
        * Accessed via positional index dot syntax (e.g., `my_tuple.0`, `my_tuple.1`).
   ================================================================================================ */

fn main() {
    println!("=== Rust Primitives & Type System Notes ===\n");

    // -------------------------------------------------------------------------
    // 1. Explicit Type Annotations vs. Suffix Annotations
    // -------------------------------------------------------------------------
    let logical: bool = true;                // Explicit boolean annotation
    let a_float: f64 = 1.0;                 // Regular 64-bit float annotation
    let an_integer = 5i32;                  // Suffix annotation (32-bit signed int)

    println!("logical bool: {}", logical);
    println!("a_float f64: {}", a_float);
    println!("an_integer (5i32): {}", an_integer);

    // -------------------------------------------------------------------------
    // 2. Default Inferred Types for Literals
    // -------------------------------------------------------------------------
    let default_float = 3.0;                // Defaults to 'f64'
    let default_integer = 7;                // Defaults to 'i32'

    println!("default_float: {}", default_float);
    println!("default_integer: {}", default_integer);

    // -------------------------------------------------------------------------
    // 3. Bidirectional Type Inference & Mutability
    // -------------------------------------------------------------------------
    // Rust leaves the exact integer type undecided at line declaration.
    // When 4294967296i64 is assigned, compiler infers inferred_type is i64 throughout!
    let mut inferred_type = 12;
    println!("inferred_type (initially 12): {}", inferred_type);

    inferred_type = 4294967296i64;
    println!("inferred_type (updated to 4294967296i64): {}", inferred_type);

    // -------------------------------------------------------------------------
    // 4. Compound Types: Arrays & Tuples
    // -------------------------------------------------------------------------
    // Array: [T; length] - fixed size, uniform type, 0-indexed
    let my_array: [i32; 5] = [1, 2, 3, 4, 5];
    println!("my_array: {:?}", my_array);
    println!("my_array first element: {}", my_array[0]);

    // Tuple: (T1, T2, ...) - collection of differing types
    let my_tuple = (5u32, 1u8, true, -5.04f32);
    println!("my_tuple: {:?}", my_tuple);
    println!(
        "my_tuple fields -> 0: {}, 1: {}, 2: {}, 3: {}",
        my_tuple.0, my_tuple.1, my_tuple.2, my_tuple.3
    );

    println!("\nAll primitive examples ran successfully!");
}



