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

    let default_float = 3.0; // 'f64'
    let default_integer = 7; // 'i32'

    //type inferred from context 
    let mut inferred_type = 12;  // the type i64 is inferred from another line
    inferred_type = 4294967296i64;

    // rust by default is interpreting the interger literal as a default type
    // being i32 (a signed 32 bit integer)
    // Rust uses a bidirectional type inference
    // so it won't just read line 21 by itself 

    /*
    Inference in rust :
        line 21 -> let mut inferred_type =12;
        rust is creating a mutable variable, which sees 12 
        but it leaves the exacct type undecided for a moment 
        Rust knows it is a integer type
        once line 22 is executed 
        a explcit type is assigned to the inferred_type
        In Rust a varibale type can never change at runtime
        Since inferred_type recives i64 on line 22
        the compiler can infere that the inferred type 
        must have been a i64 the entire time 
        so it treates the 12 as 12i64 instead of defaulting to i32 
     */

    // mutable variable means th evalue can be changed 
    // the type of variable however cannot be changed 

    // Array signature occurs with type T and length as 
    //      [T: length]

    let my_array: [i32; 5] = [1, 2, 3, 4, 5];

    // array -> integer signed with 32 bit representation
    //          length of 5 
    //          index 0 1 2 3 4 

    // whereas a typle is a collection of values of differing types
    // constructed with ()

    let my_tuple = (5u32, 1u8, true, -5.04f32);




}