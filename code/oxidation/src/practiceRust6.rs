// practiceRust6.rs
#![allow(unused_imports, unused_variables, dead_code)]
/* =========================================================================
   PRACTICE 6: ARRAYS AND SLICES
   =========================================================================
   Reference: https://doc.rust-lang.org/rust-by-example/primitives/tuples.html
              https://doc.rust-lang.org/rust-by-example/primitives/array.html

   KEY CONCEPTS:
   • Array signature: `[T; length]` — fixed size known at compile-time, 
     homogeneous types, allocated contiguously on the stack.
   • Repeat initialization: `[val; count]` (e.g., `[0; 100]` creates 100 zeros).
   • Slices: `&[T]` — a dynamically-sized view / borrow into a contiguous sequence.
   • Slicing syntax: `&arr[start..end]` (exclusive of end), `&arr[..]` (whole array).
   • Array length: `arr.len()`
   • Memory footprint: `std::mem::size_of_val(&arr)`
   • Safe element access: `arr.get(index)` returns `Option<&T>` (`Some(&val)` or `None`).

   -------------------------------------------------------------------------
   TASK INSTRUCTIONS:
   -------------------------------------------------------------------------

   1. Function: `inspect_slice`
      - Signature: fn inspect_slice(slice: &[i32])
      - What it does:
        • Prints the length of the slice using `.len()`.
        • Prints the memory size occupied by the slice elements using
          `std::mem::size_of_val(slice)`.
        • Prints the first element (`slice[0]`) and last element (`slice[slice.len() - 1]`).
          (Assume slice has at least 1 element).

   2. Function: `safe_read`
      - Signature: fn safe_read(slice: &[i32], index: usize)
      - What it does:
        • Uses `slice.get(index)` to safely check for out-of-bounds without panicking.
        • Uses `match` or `if let`:
          - If `Some(val)`: prints `"Index {}: found value {}"`
          - If `None`: prints `"Index {}: out of bounds!"`

   3. In `main()`:
      - Create array `numbers: [i32; 5]` with values `[10, 20, 30, 40, 50]`.
      - Create array `buffer: [i32; 100]` initialized with all zeros using repeat syntax `[0; 100]`.
      - Print the total memory allocated for `numbers` and `buffer` in bytes using `std::mem::size_of_val`.
      - Pass the whole `numbers` array as a slice to `inspect_slice`.
      - Borrow a middle section of `numbers` as a slice (containing 20, 30, 40 -> range `1..4`)
        and pass it to `inspect_slice`.
      - Test `safe_read` on `numbers` with:
        • A valid index (e.g., index 2)
        • An out-of-bounds index (e.g., index 99)

   Run anytime using:
       cargo run --bin practiceRust6
   ========================================================================= */

use std::mem;
// the std:mem -> allows the user to interact with low level memory 
// library that contains the modules that lets user(s) safely interact with memory 
//  added benefit of not having to perform manual pointer arithmetic for everything 

// slices are a two word object 
// with the first word being a pointer to the data 
// and the 2nd being the length of the slice 

// slices can be used to borrow a seciotn of a array
// array are created using brackets and their length is known at compile time 


fn inspect_slice(slice: &[i32]){
    println!("First and last element of the slice: {} and {}", slice[0], slice[slice.len() - 1]);
    println!("Slice size in bytes {}", mem::size_of_val(slice));
    //println!()
}

fn safe_read(slice: &[i32], index: usize){
    for i in 0..slice.len() + 1 {
        match slice.get(i){
            Some(xval) => println!("{}: {}", i, xval),
            None => println!("Out of bounds ! ")
        }
    }
}


fn main() {
    let numbers: [i32; 5] = [10, 20, 30, 40, 50];
    let buffers: [i32; 100] = [0; 100];

    println!("Array {} occupies {} bytes", stringify!(numbers), mem::size_of_val(&numbers));
    println!("Array {} occupies {} bytes", stringify!(buffer), mem::size_of_val(&buffers));


    inspect_slice(&numbers);

    inspect_slice(&numbers[1 .. 4]);
    
    safe_read(&numbers, 5);
    // safe_read(&numbers[10..20], 20); <- this would cause the runtime error 
    // indexing on a slice ^

    
    
}
// worked well 

