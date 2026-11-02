// practicerustTuple2


// tuples are a colleciton of values that can be differing types
// constructed using parahtness()

// tuples can be used as fucntion arguments and even return values
/*                
   Call invert_pair((100, "Altitude")) and print the swapped tuple.
    1. invert_pair(pair: (i32, &str)) -> (&str, i32)                                                       
      • Takes a tuple containing an integer and a string slice.                                          
      • Destructures the tuple.                                                                          
      • Returns a new tuple with the elements swapped (implicit return, no semicolon!).   

*/



fn invert_pair(pair: (i32, &str)) -> (&str, i32) {
    let (int_param, str_param) = pair;
    (str_param, int_param)
    
}



fn main(){
    let sensor = ("ID-402", 98.6f32, true);
    println!("Sensor ID value: {}", sensor.0);
    println!("Temerature value: {}", sensor.1);

    let (a, b, c) = sensor;
    println!("{:?}, {:?}, {:?}", a, b, c);

    println!("One element tuple with value and trailing comma: {:?}", (42u8,));

    let pair = (100i32, "Altitude"); 
    println!("Inverted pair is {:?}: ", invert_pair(pair));



} 