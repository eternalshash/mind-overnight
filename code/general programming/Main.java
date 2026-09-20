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
