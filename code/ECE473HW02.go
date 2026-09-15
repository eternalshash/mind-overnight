package main

import (
	"fmt"
	"math/rand"
)

// ==========================================
// Question 1: Slice appending demonstration
// ==========================================

// Primary fix: Return the updated slice header (Idiomatic Go)
func appendRand(a []float64) []float64 {
	return append(a, rand.Float64())
}

// Alternative fix: Pass slice by pointer
func appendRandPtr(a *[]float64) {
	*a = append(*a, rand.Float64())
}

func runQuestion1() {
	fmt.Println("--- Question 1 Output ---")
	a := make([]float64, 0)
	for i := 0; i < 10; i++ {
		a = appendRand(a)
		fmt.Printf("%d: %v\n", i, a)
	}
}

// ==========================================
// Question 2: Vertex struct manipulation
// ==========================================

type Vertex struct {
	X, Y int
}

func (v *Vertex) Move(dx, dy int) {
	v.X += dx
	v.Y += dy
}

func (v Vertex) String() string {
	return fmt.Sprintf("(%d,%d)", v.X, v.Y)
}

func runQuestion2() {
	fmt.Println("\n--- Question 2 Output ---")
	a := make([]Vertex, 0)
	for i := 0; i < 10; i++ {
		a = append(a, Vertex{X: i, Y: i * 2})
	}

	fmt.Printf("before move: %v\n", a)

	// Primary fix: Index into slice to mutate elements in place
	for i := range a {
		a[i].Move(1, 2)
	}

	fmt.Printf("after move: %v\n", a)
}

func main() {
	runQuestion1()
	runQuestion2()
}

/*
================================================================================
ANSWERS AND EXPLANATIONS
================================================================================

QUESTION 1

1. Expected Output:
In each iteration of the loop from 0 to 9, one random float64 number is added to
the slice a. In each step i, the slice contains i + 1 random numbers.
Example expected output:
0: [0.6046602879796196]
1: [0.6046602879796196 0.9405090880450124]
2: [0.6046602879796196 0.9405090880450124 0.6645600532184904]
...
9: [0.604660... (total of 10 random float values)]

2. Actual Output:
0: []
1: []
2: []
3: []
4: []
5: []
6: []
7: []
8: []
9: []

3. Why the code does not work and the primary correction:
In Go, a slice is a header struct consisting of three fields: a pointer to the
underlying array, a length, and a capacity. Arguments in Go are always passed by
value. When appendRand(a) is called, the function receives a copy of the slice
header. Inside appendRand, append() updates the local header (and may reallocate
the backing array), but this change is only made to the local copy. The slice
variable 'a' in main() retains its original length of 0.

Primary Correction:
Have appendRand return the modified slice, and reassign the result in main():

    func appendRand(a []float64) []float64 {
        return append(a, rand.Float64())
    }

    // In main:
    a = appendRand(a)

4. Alternative Correction:
Pass a pointer to the slice header (*[]float64):

    func appendRand(a *[]float64) {
        *a = append(*a, rand.Float64())
    }

    // In main:
    appendRand(&a)

5. Preferred Correction:
The primary correction (returning the slice and reassigning it) is preferred.
In Go, slice headers are small, and returning the updated slice is the idiomatic
pattern used across the standard library (matching the behavior of the built-in
append function). Passing slice pointers adds unnecessary indirection and goes
against standard Go style conventions unless dynamic mutation of an existing
shared reference is explicitly required.


================================================================================
QUESTION 2

1. Expected Output:
Each Vertex element in the slice 'a' should have its X coordinate incremented by
1 and its Y coordinate incremented by 2.
Expected output:
before move: [(0,0) (1,2) (2,4) (3,6) (4,8) (5,10) (6,12) (7,14) (8,16) (9,18)]
after move: [(1,2) (2,4) (3,6) (4,8) (5,10) (6,12) (7,14) (8,16) (9,18) (10,20)]

2. Actual Output:
before move: [(0,0) (1,2) (2,4) (3,6) (4,8) (5,10) (6,12) (7,14) (8,16) (9,18)]
after move: [(0,0) (1,2) (2,4) (3,6) (4,8) (5,10) (6,12) (7,14) (8,16) (9,18)]

3. Why the code does not work and the primary correction:
In Go, the 'for _, v := range a' loop copies each element of the slice into the
iteration variable 'v'. When calling v.Move(1, 2), Go automatically takes the
address of 'v' (&v) to call the pointer receiver method. As a result, Move()
mutates the temporary local copy 'v' instead of the element stored in the slice.
Once the iteration finishes, the changes are discarded, leaving slice 'a'
unmodified.

Primary Correction:
Iterate by index and mutate the slice element directly:

    for i := range a {
        a[i].Move(1, 2)
    }

Calling a[i].Move(1, 2) passes the address &a[i] of the actual element inside the
underlying slice array, updating it in place.

4. Alternative Correction:
Store pointers to Vertex in the slice ([]*Vertex) rather than values ([]Vertex):

    a := make([]*Vertex, 0)
    for i := 0; i < 10; i++ {
        a = append(a, &Vertex{X: i, Y: i * 2})
    }
    for _, v := range a {
        v.Move(1, 2)
    }

5. Preferred Correction:
The primary correction (indexing into the slice: a[i].Move(1, 2)) is preferred
for this scenario. It keeps the data contiguous in memory (improving cache
locality and eliminating heap allocations per vertex) and fixes the bug with
minimal code changes while preserving value semantics.
================================================================================
*/
