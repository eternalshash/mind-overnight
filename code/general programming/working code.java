// ==========================================
// File: Main.java (The Runner Class)
// ==========================================
public class Main {
    public static void main(String[] args) {
        
        // 4. INSTANTIATING (Building actual Dog objects in memory)
        Dog myDog = new Dog("Fido", 3, true);
        Dog yourDog = new Dog("Rex", 12, false);
        
        // 5. CALLING METHODS (Using Dot Notation to trigger behaviors)
        myDog.haveBirthday(); // Fido's age just went from 3 to 4!
        
        // Testing the Boolean Logic
        System.out.println("Does Fido need a treat? " + myDog.needsTreat());
        System.out.println("Does Rex need a treat? " + yourDog.needsTreat());
    }
}

// ==========================================
// File: Dog.java (The Blueprint Class)
// ==========================================
class Dog {
    
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
