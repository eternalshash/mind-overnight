import numpy as np
import easynn as nn
import multiprocessing

try:
    multiprocessing.set_start_method('fork')
except Exception:
    pass

# Create a numpy array of 10 rows and 5 columns.
# Set the element at row i and column j to be i+j.
def Q1():
    return np.fromfunction(lambda i, j: i + j, (10, 5), dtype = int)

# Add two numpy arrays together.
def Q2(a, b):
    return a + b

# Multiply two 2D numpy arrays using matrix multiplication.
def Q3(a, b):
    return np.matmul(a, b)

# For each row of a 2D numpy array, find the column index
# with the maximum element. Return all these column indices.
def Q4(a):
    return np.argmax(a, axis = 1)

# Solve Ax = b.
def Q5(A, b):
    return np.linalg.solve(A, b)

# Return an EasyNN expression for a+b.
def Q6():
    return nn.Input("a") + nn.Input("b")

# Return an EasyNN expression for a+b*c.
def Q7():
    return nn.Input("a") + nn.Input("b") * nn.Input("c")

# Given A and b, return an EasyNN expression for Ax+b.
def Q8(A, b):
    return nn.Const(A) * nn.Input("x") + nn.Const(b)

# Given n, return an EasyNN expression for x**n.
def Q9(n):
    x = nn.Input("x")
    res = x
    for _ in range(n - 1):
        res = res * x
    return res

# Return an EasyNN expression to compute
# the element-wise absolute value |x|.
def Q10():
    x = nn.Input("x")
    return nn.ReLU()(x) + nn.ReLU()(-x)
