// Attribute to hide warnings for unused code & variables
#![allow(dead_code, unused_variables)]

/* =========================================================================
   DAY 2 NOTES: STRUCTS IN RUST
   =========================================================================
   Rust supports three kinds of structures (structs):
   1. Classic C-like Structs:
      - Named fields with types (e.g. `struct Person { name: String, age: u8 }`).
      - Best for general data modeling where each field has a clear semantic name.

   2. Tuple Structs:
      - Essentially named tuples (e.g. `struct Point2D(i32, i32);`).
      - Useful when you want to give a tuple a distinct type without naming every field.

   3. Unit Structs:
      - Field-less structs (e.g. `struct Unit;`).
      - Useful for implementing traits on a type when you don't need to store any state.
   ========================================================================= */

// 1. Classic C-like structure
#[derive(Debug)]
struct Person {
    name: String,
    age: u8,
}

// 2. Tuple structure (named tuple)
#[derive(Debug)]
struct Point2D(f64, f64);

// 3. Unit structure (field-less, useful for traits and generics)
#[derive(Debug)]
struct Unit;

fn main() {
    println!("=== Day 2: Structs in Rust ===\n");

    // Instantiating a classic struct
    let person = Person {
        name: String::from("Shashwat"),
        age: 21,
    };
    println!("Classic Struct: {:?}", person);
    println!("Person name: {}, age: {}", person.name, person.age);

    // Instantiating a tuple struct
    let origin = Point2D(0.0, 0.0);
    println!("Tuple Struct: Point2D({:.1}, {:.1})", origin.0, origin.1);

    // Instantiating a unit struct
    let _unit = Unit;
    println!("Unit Struct created successfully!");
}
