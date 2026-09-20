/**
 * ============================================================================
 * AP COMPUTER SCIENCE A - COMPREHENSIVE JAVA INTRODUCTION & STUDY GUIDE
 * ============================================================================
 * 
 * This file serves as a runnable, structured breakdown of the 10 core units
 * covered in the AP Computer Science A curriculum:
 *
 *   Unit 1: Primitive Types
 *   Unit 2: Using Objects (String, Math, Wrapper classes)
 *   Unit 3: Boolean Expressions & if Statements
 *   Unit 4: Iteration (Loops & Algorithms)
 *   Unit 5: Writing Classes (OOP Design, Encapsulation, Scope)
 *   Unit 6: 1D Arrays
 *   Unit 7: ArrayLists
 *   Unit 8: 2D Arrays
 *   Unit 9: Inheritance & Polymorphism
 *   Unit 10: Recursion
 * 
 * To compile and run:
 *   javac IntroToJava.java
 *   java IntroToJava
 * ============================================================================
 */

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class IntroToJava {

    public static void main(String[] args) {
        System.out.println("=================================================");
        System.out.println("    AP COMPUTER SCIENCE A - JAVA CRASH COURSE    ");
        System.out.println("=================================================\n");

        unit1_PrimitiveTypes();
        unit2_UsingObjects();
        unit3_BooleanAndIf();
        unit4_Iteration();
        unit5_WritingClasses();
        unit6_Arrays();
        unit7_ArrayLists();
        unit8_TwoDArrays();
        unit9_InheritanceAndPolymorphism();
        unit10_Recursion();

        System.out.println("\nAll AP CS A Units Completed Successfully!");
    }

    // ========================================================================
    // UNIT 1: PRIMITIVE TYPES
    // ========================================================================
    public static void unit1_PrimitiveTypes() {
        printHeader("Unit 1: Primitive Types");

        // 1. Primitive data types in AP CS A subset: int, double, boolean (char is not explicitly tested)
        int score = 95;
        double gpa = 3.85;
        boolean isEnrolled = true;

        System.out.println("int score = " + score);
        System.out.println("double gpa = " + gpa);
        System.out.println("boolean isEnrolled = " + isEnrolled);

        // 2. Integer Division & Modulo (Classic AP Trap!)
        int a = 7;
        int b = 2;
        int intDiv = a / b; // 3 (truncated, NOT 3.5)
        int modResult = a % b; // 1 (remainder)
        System.out.println("7 / 2 = " + intDiv + " (truncated int division)");
        System.out.println("7 % 2 = " + modResult + " (remainder)");

        // 3. Type Casting
        double accurateDiv = (double) a / b; // 3.5 (casting 'a' first forces floating-point division)
        int roundedScore = (int) (gpa + 0.5); // Common technique for rounding positive doubles
        System.out.println("(double) 7 / 2 = " + accurateDiv);
        System.out.println("Rounding 3.85: (int)(3.85 + 0.5) = " + roundedScore);

        // 4. Integer Bounds & Compound Assignment
        System.out.println("Integer.MIN_VALUE = " + Integer.MIN_VALUE);
        System.out.println("Integer.MAX_VALUE = " + Integer.MAX_VALUE);
        
        score += 5; // score = score + 5
        score++;    // score = score + 1
        System.out.println("Updated score after += 5 and ++ : " + score);
    }

    // ========================================================================
    // UNIT 2: USING OBJECTS (Strings, Math, Wrappers)
    // ========================================================================
    public static void unit2_UsingObjects() {
        printHeader("Unit 2: Using Objects");

        // 1. String Methods (Strings are IMMUTABLE in Java)
        String s = "AP Computer Science";
        System.out.println("Original String: \"" + s + "\"");
        System.out.println(".length() : " + s.length());
        System.out.println(".substring(0, 2) : " + s.substring(0, 2)); // [0, 2) -> "AP"
        System.out.println(".substring(3) : " + s.substring(3));       // from 3 to end -> "Computer Science"
        System.out.println(".indexOf(\"Comp\") : " + s.indexOf("Comp")); // 3
        System.out.println(".indexOf(\"xyz\") : " + s.indexOf("xyz"));   // -1 (not found)
        System.out.println(".equals(\"AP Computer Science\") : " + s.equals("AP Computer Science"));
        System.out.println(".compareTo(\"BP\") : " + s.compareTo("BP")); // negative since 'A' comes before 'B'

        // 2. Math Class Methods (all static)
        System.out.println("Math.abs(-42) = " + Math.abs(-42));
        System.out.println("Math.pow(2, 3) = " + Math.pow(2, 3)); // 8.0 (returns double!)
        System.out.println("Math.sqrt(25) = " + Math.sqrt(25));   // 5.0 (returns double!)

        // Random numbers in range [min, max] inclusive:
        // Formula: (int) (Math.random() * (max - min + 1)) + min
        int min = 1, max = 6; // simulate a 6-sided die
        int randomDie = (int) (Math.random() * (max - min + 1)) + min;
        System.out.println("Random die roll [1, 6]: " + randomDie);

        // 3. Wrapper Classes & Autoboxing / Unboxing
        Integer wrappedInt = 100; // Autoboxing: primitive int -> Integer object
        int primitiveInt = wrappedInt; // Unboxing: Integer object -> primitive int
        System.out.println("Autoboxed & Unboxed value: " + primitiveInt);
    }

    // ========================================================================
    // UNIT 3: BOOLEAN EXPRESSIONS AND IF STATEMENTS
    // ========================================================================
    public static void unit3_BooleanAndIf() {
        printHeader("Unit 3: Boolean Expressions & if Statements");

        int age = 17;
        boolean hasPermit = true;

        // 1. Logical Operators: && (AND), || (OR), ! (NOT)
        // Short-circuit evaluation: if first operand in && is false, second is not evaluated!
        if (age >= 16 && hasPermit) {
            System.out.println("Eligible to drive with supervision.");
        } else if (age >= 18) {
            System.out.println("Eligible for full license.");
        } else {
            System.out.println("Not eligible yet.");
        }

        // 2. De Morgan's Laws:
        // !(A && B) is equivalent to (!A || !B)
        // !(A || B) is equivalent to (!A && !B)
        boolean a = true;
        boolean b = false;
        boolean lhs = !(a && b);
        boolean rhs = (!a || !b);
        System.out.println("De Morgan's Verification: " + (lhs == rhs));

        // 3. Object Equality: == vs .equals() (CRITICAL AP CONCEPT)
        String str1 = new String("Java");
        String str2 = new String("Java");
        System.out.println("str1 == str2: " + (str1 == str2) + " (Compares memory references!)");
        System.out.println("str1.equals(str2): " + str1.equals(str2) + " (Compares content values!)");
    }

    // ========================================================================
    // UNIT 4: ITERATION (LOOPS)
    // ========================================================================
    public static void unit4_Iteration() {
        printHeader("Unit 4: Iteration");

        // 1. While Loop
        System.out.print("While loop countdown: ");
        int count = 3;
        while (count > 0) {
            System.out.print(count + " ");
            count--;
        }
        System.out.println();

        // 2. Standard For Loop
        System.out.print("For loop: ");
        for (int i = 0; i < 5; i++) {
            System.out.print(i + " ");
        }
        System.out.println();

        // 3. String Traversal (Algorithm pattern)
        String word = "Algorithms";
        int vowelCount = 0;
        for (int i = 0; i < word.length(); i++) {
            String ch = word.substring(i, i + 1).toLowerCase();
            if ("aeiou".contains(ch)) {
                vowelCount++;
            }
        }
        System.out.println("Vowels in \"" + word + "\": " + vowelCount);

        // 4. Nested Loops (Multiplication table snippet)
        System.out.println("Nested loop grid (3x3):");
        for (int r = 1; r <= 3; r++) {
            for (int c = 1; c <= 3; c++) {
                System.out.print((r * c) + "\t");
            }
            System.out.println();
        }
    }

    // ========================================================================
    // UNIT 5: WRITING CLASSES (OOP Fundamentals)
    // ========================================================================
    public static void unit5_WritingClasses() {
        printHeader("Unit 5: Writing Classes");

        // Instantiating objects using constructors
        Student s1 = new Student("Alice", 11, 3.9);
        Student s2 = new Student("Bob", 12, 3.4);

        System.out.println(s1);
        System.out.println(s2);

        // Calling accessor (getter) and mutator (setter) methods
        s2.setGpa(3.7);
        System.out.println("Updated Bob's GPA: " + s2.getGpa());

        // Static variable & method access via class name
        System.out.println("Total Student instances created: " + Student.getTotalStudents());
    }

    // ========================================================================
    // UNIT 6: 1D ARRAYS
    // ========================================================================
    public static void unit6_Arrays() {
        printHeader("Unit 6: 1D Arrays");

        // 1. Declaration & Initialization
        int[] scores = new int[5]; // initialized to default values (0 for int)
        int[] primes = {2, 3, 5, 7, 11}; // initializer list

        System.out.println("Array length: " + primes.length + " (Note: length is a field, not a method!)");
        System.out.println("First element: " + primes[0] + ", Last element: " + primes[primes.length - 1]);

        // 2. Finding Maximum Value (Standard AP Algorithm)
        int max = primes[0];
        for (int i = 1; i < primes.length; i++) {
            if (primes[i] > max) {
                max = primes[i];
            }
        }
        System.out.println("Maximum prime in array: " + max);

        // 3. Enhanced For-Each Loop
        int sum = 0;
        for (int val : primes) {
            sum += val;
        }
        System.out.println("Sum of elements: " + sum);
        // Note: For-each cannot modify array elements or track current index!
    }

    // ========================================================================
    // UNIT 7: ARRAYLIST
    // ========================================================================
    public static void unit7_ArrayLists() {
        printHeader("Unit 7: ArrayList");

        // 1. Generic ArrayList declaration
        ArrayList<String> fruits = new ArrayList<String>();

        // 2. Core ArrayList Methods:
        fruits.add("Apple");          // add(E element) -> appends to end
        fruits.add("Banana");
        fruits.add(1, "Blueberry");   // add(int index, E element) -> shifts elements right
        System.out.println("After additions: " + fruits);
        System.out.println("Size: " + fruits.size());

        String item = fruits.get(0);  // get(int index)
        System.out.println("Element at 0: " + item);

        fruits.set(0, "Avocado");     // set(int index, E element) -> replaces and returns old element
        System.out.println("After set(0, \"Avocado\"): " + fruits);

        fruits.remove(1);             // remove(int index) -> shifts left, returns removed element
        System.out.println("After remove(1): " + fruits);

        // 3. Safe Removal Pattern in Loop (Traverse BACKWARDS to avoid skipping elements)
        ArrayList<Integer> nums = new ArrayList<>(Arrays.asList(1, 2, 2, 3, 4, 2, 5));
        System.out.println("Nums before filtering 2s: " + nums);
        for (int i = nums.size() - 1; i >= 0; i--) {
            if (nums.get(i) == 2) {
                nums.remove(i);
            }
        }
        System.out.println("Nums after backward removal of 2s: " + nums);
    }

    // ========================================================================
    // UNIT 8: 2D ARRAYS
    // ========================================================================
    public static void unit8_TwoDArrays() {
        printHeader("Unit 8: 2D Arrays");

        // Initializer list syntax: [row][col]
        int[][] grid = {
            {10, 20, 30},
            {40, 50, 60}
        };

        int numRows = grid.length;       // Number of rows = 2
        int numCols = grid[0].length;    // Number of columns = 3
        System.out.println("Grid dimensions: " + numRows + " rows x " + numCols + " cols");

        // Row-Major Traversal (Standard traversal on AP exam)
        System.out.println("Row-major traversal:");
        for (int r = 0; r < grid.length; r++) {
            for (int c = 0; c < grid[r].length; c++) {
                System.out.print(grid[r][c] + " ");
            }
            System.out.println();
        }

        // Summing all elements in 2D array
        int totalSum = 0;
        for (int[] row : grid) {
            for (int val : row) {
                totalSum += val;
            }
        }
        System.out.println("Total 2D Array Sum: " + totalSum);
    }

    // ========================================================================
    // UNIT 9: INHERITANCE & POLYMORPHISM
    // ========================================================================
    public static void unit9_InheritanceAndPolymorphism() {
        printHeader("Unit 9: Inheritance & Polymorphism");

        // 1. Creating subclass instances
        Shape genericShape = new Shape("Red");
        Circle circle = new Circle("Blue", 5.0);

        System.out.println(genericShape);
        System.out.println(circle);

        // 2. Polymorphism: Reference type (Shape) vs Object type (Circle)
        // Compile-time check uses Reference Type.
        // Run-time execution uses Object Type (Dynamic Method Dispatch).
        Shape polyShape = new Circle("Green", 2.5);
        System.out.println("Polymorphic Area: " + polyShape.calculateArea()); // Calls Circle's calculateArea()

        // 3. Array of polymorphic references
        Shape[] shapes = { new Shape("Yellow"), new Circle("Orange", 3.0) };
        for (Shape s : shapes) {
            System.out.println("Shape Color: " + s.getColor() + " | Area: " + s.calculateArea());
        }
    }

    // ========================================================================
    // UNIT 10: RECURSION
    // ========================================================================
    public static void unit10_Recursion() {
        printHeader("Unit 10: Recursion");

        // 1. Factorial: n! = n * (n - 1)!
        int n = 5;
        System.out.println(n + "! = " + factorial(n));

        // 2. Fibonacci: fib(n) = fib(n-1) + fib(n-2)
        int fibIndex = 6;
        System.out.println("Fibonacci(" + fibIndex + ") = " + fibonacci(fibIndex));

        // 3. Binary Search (Recursive)
        int[] sortedArr = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
        int target = 23;
        int foundIndex = binarySearch(sortedArr, target, 0, sortedArr.length - 1);
        System.out.println("Binary Search for " + target + ": found at index " + foundIndex);
    }

    // Recursive helper: Factorial
    public static int factorial(int n) {
        if (n <= 1) { // Base Case
            return 1;
        }
        return n * factorial(n - 1); // Recursive Call
    }

    // Recursive helper: Fibonacci
    public static int fibonacci(int n) {
        if (n <= 0) return 0;
        if (n == 1) return 1;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }

    // Recursive helper: Binary Search
    public static int binarySearch(int[] arr, int target, int low, int high) {
        if (low > high) {
            return -1; // Base case: Target not found
        }
        int mid = (low + high) / 2;
        if (arr[mid] == target) {
            return mid; // Base case: Found
        } else if (arr[mid] > target) {
            return binarySearch(arr, target, low, mid - 1); // Search left half
        } else {
            return binarySearch(arr, target, mid + 1, high); // Search right half
        }
    }

    private static void printHeader(String title) {
        System.out.println("\n--- " + title + " ---");
    }
}

// ============================================================================
// SUPPORTING CLASSES FOR UNIT 5 & UNIT 9
// ============================================================================

/**
 * Unit 5 Example Class: Demonstrating encapsulation, constructors,
 * instance/static variables, getters/setters, and toString().
 */
class Student {
    // Instance variables (Encapsulation: private access)
    private String name;
    private int gradeLevel;
    private double gpa;

    // Static variable (Shared across all instances of Student)
    private static int totalStudents = 0;

    // Default constructor
    public Student() {
        this("Unknown", 9, 0.0); // Constructor chaining using this()
    }

    // Overloaded Constructor
    public Student(String name, int gradeLevel, double gpa) {
        this.name = name;
        this.gradeLevel = gradeLevel;
        this.gpa = gpa;
        totalStudents++;
    }

    // Accessors (Getters)
    public String getName() { return name; }
    public int getGradeLevel() { return gradeLevel; }
    public double getGpa() { return gpa; }
    public static int getTotalStudents() { return totalStudents; }

    // Mutator (Setter)
    public void setGpa(double newGpa) {
        if (newGpa >= 0.0 && newGpa <= 4.0) {
            this.gpa = newGpa;
        }
    }

    // Overriding toString() from Object class
    @Override
    public String toString() {
        return "Student[Name=" + name + ", Grade=" + gradeLevel + ", GPA=" + gpa + "]";
    }
}

/**
 * Unit 9 Superclass Example
 */
class Shape {
    private String color;

    public Shape(String color) {
        this.color = color;
    }

    public String getColor() {
        return color;
    }

    public double calculateArea() {
        return 0.0;
    }

    @Override
    public String toString() {
        return "Shape[Color=" + color + "]";
    }
}

/**
 * Unit 9 Subclass Example: Demonstrates extends, super(), and method overriding.
 */
class Circle extends Shape {
    private double radius;

    public Circle(String color, double radius) {
        super(color); // Must be the FIRST statement in subclass constructor!
        this.radius = radius;
    }

    public double getRadius() {
        return radius;
    }

    // Method Overriding
    @Override
    public double calculateArea() {
        return Math.PI * radius * radius;
    }

    @Override
    public String toString() {
        // Calling super.toString()
        return super.toString() + " -> Circle[Radius=" + radius + ", Area=" + calculateArea() + "]";
    }
}
