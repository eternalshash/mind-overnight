# AP Computer Science A - Java Quick Reference & Study Guide

This folder contains introductory material and reference code tailored to the College Board **AP Computer Science A** curriculum.

## File Overview

- [`IntroToJava.java`](file:///Users/schoudhry/Desktop/mind-overnight/code/general%20programming/IntroToJava.java): A comprehensive, fully runnable Java program covering all 10 AP CSA units with in-depth comments, practical demonstrations, and common exam traps.

---

## The 10 AP CS A Units Covered

| Unit | Topic | Key Concepts & Exam Tips |
| :--- | :--- | :--- |
| **Unit 1** | **Primitive Types** | `int`, `double`, `boolean`, integer division truncation (`7 / 2 == 3`), modulo arithmetic, casting `(double) a / b`, `Integer.MIN_VALUE` / `Integer.MAX_VALUE`. |
| **Unit 2** | **Using Objects** | `String` immutability, methods (`length()`, `substring()`, `indexOf()`, `equals()`, `compareTo()`), `Math.random()`, `Math.abs()`, `Math.pow()`, `Math.sqrt()`, wrapper classes and autoboxing/unboxing. |
| **Unit 3** | **Boolean Expressions & `if`** | Relational operators, short-circuit evaluation (`&&`, `\|\|`, `!`), De Morgan's Laws, `==` (reference equality) vs `.equals()` (content equality). |
| **Unit 4** | **Iteration** | `while` and `for` loops, loop bounds/off-by-one errors, string traversals, nested loop grid tracing. |
| **Unit 5** | **Writing Classes** | Encapsulation (`private` instance variables, `public` methods), constructors, `this` keyword, accessor/mutator methods, `static` vs instance variables & methods, scope. |
| **Unit 6** | **1D Arrays** | Array creation (`int[] arr = new int[n]`), `.length` property (field, not a method), element modification, standard algorithms (min/max/sum/reverse), enhanced `for` (for-each) limitations. |
| **Unit 7** | **`ArrayList`** | `ArrayList<E>`, methods (`add`, `get`, `set`, `remove`, `size`), traversing while removing (reverse iteration technique to avoid skipped items). |
| **Unit 8** | **2D Arrays** | Matrix declaration `matrix[row][col]`, row count (`matrix.length`), col count (`matrix[0].length`), row-major vs column-major traversals. |
| **Unit 9** | **Inheritance & Polymorphism** | Subclasses with `extends`, calling `super()`, method overriding vs overloading, polymorphic method calls (compile-time reference type vs runtime object type), `Object` class. |
| **Unit 10** | **Recursion** | Base cases and recursive steps, call stack tracing, classic algorithms (Factorial, Fibonacci, Binary Search). |

---

## Running the Code

Navigate to this directory in your terminal and run:

```bash
javac IntroToJava.java
java IntroToJava
```
