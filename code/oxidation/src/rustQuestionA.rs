// practicerustTuple2


// tuples are a colleciton of values that can be differing types
// constructed using parahtness()

// tuples can be used as fucntion arguments and even return values


fn invert_pair(pair: (i32, &str)) -> (&str, i32) {
    // tuple with int an string slice 
    // new tuple with swwap 
    // int string -> string int   
    let (int_param, string_param) = pair;
    (string_param, int_param)
}



fn main(){
    let sensor = ("ID-402", 98.6f32, true);
    println!("Sensor ID value: {}", sensor.0);
    println!("Temerature value: {}", sensor.1);

    let (a, b, c) = sensor;
    println!("{:?}, {:?}, {:?}", a, b, c);

    println!("One element tuple with value and trailing comma: {:?}", (42u8,));


}

/*                
  

*/