// ==========================================
// File: Dog.java (The Blueprint Class)
// ==========================================
public class Dog {
    
    // 1. INSTANCE VARIABLES (What a Dog knows)
    private String name;
    private int age;
    private boolean isGoodBoy;

    // 2. CONSTRUCTOR (How we build a Dog object)
    public Dog(String n, int a, boolean g) {
        name = n;
        age = a;
        isGoodBoy = g;
    }
    
    // 3. METHODS (What a Dog does)
    
    // Accessor Method (Returns the age)
    public int getAge() {
        return age;
    }

    // Mutator Method (Changes the age instance variable)
    public void haveBirthday() {
        age = age + 1; // Or you can write age++;
    }

    // Boolean Logic Method (Returns true or false)
    public boolean needsTreat() {
        if (isGoodBoy == true && age < 10) {
            return true;
        } else {
            return false;
        }
    }
}
