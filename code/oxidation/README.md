# Oxidation - Rust Learning Workspace

A clean, organized workspace for learning Rust fundamentals, starting with primitive types, mutability, type inference, and compound data structures.

## Structure

- **`src/main.rs`**: Core notes and demonstrations covering:
  - Explicit & suffix type annotations
  - Default literal types (`i32`, `f64`)
  - Bidirectional type inference
  - Immutability by default vs. `mut`
  - Arrays (`[T; length]`) and Tuples (`(T1, T2, ...)`)
  - Detailed summary of concepts formatted as in-code comments
- **`src/practice1.rs`**: Interactive exercises covering primitive types (booleans, signed/unsigned integers, floating points, mutability, arrays, and tuples)
- **`src/rustday2.rs`**: Structs in Rust (Classic C-like structs, Tuple structs, and Unit structs)
- **`c_comparison/checkingCode.cpp`**: C++ memory out-of-bounds example showing Rust's safety advantages

## Running with Cargo

```bash
# Run the main primitives lesson & notes:
cargo run

# Run practice 1 exercises:
cargo run --bin practice1

# Run day 2 structs:
cargo run --bin rustday2
```

## Running directly with `rustc`

```bash
rustc src/main.rs && ./main
rustc src/practice1.rs && ./practice1
rustc src/rustday2.rs && ./rustday2
```
