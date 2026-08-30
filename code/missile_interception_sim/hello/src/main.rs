fn main() {
    // Variables can be type annotated

    let logical: bool = true;

    let a_float: f64 = 1.0; // regular annotation
    let an_integer = 5i32; //suffix annoation 

    // logical -> boolean
    // a_float -> 64 bit floatig point 
    // an_integer = 5i32 -> 32 bit integer 
    // i meaning signed and u meaning unsigned

    println!("{}", logical);
    println!("{}", a_float);


}