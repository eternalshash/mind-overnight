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
    inferred type = 4294967296i64;

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
        
    
    
     */




}