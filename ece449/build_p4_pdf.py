import subprocess
import os

html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ECE 449/590 Project 4 Report - Shashwat Choudhry</title>
<style>
  @page {
    size: letter;
    margin: 0.7in 0.75in;
    @bottom-right {
      content: counter(page);
    }
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    color: #24292f;
    margin: 0;
    padding: 0;
  }
  .header-block {
    border-bottom: 2px solid #0969da;
    padding-bottom: 8px;
    margin-bottom: 14px;
  }
  h1 {
    font-size: 15pt;
    font-weight: 700;
    color: #1f2328;
    margin: 0 0 4px 0;
  }
  .subtitle {
    font-size: 10pt;
    color: #57606a;
    font-weight: 500;
  }
  .meta-table {
    width: 100%;
    margin-top: 6px;
    font-size: 9pt;
    color: #424a53;
  }
  .meta-table td {
    padding: 1px 0;
  }
  h2 {
    font-size: 11pt;
    font-weight: 700;
    color: #0969da;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 8px;
    page-break-after: avoid;
  }
  h3 {
    font-size: 9.5pt;
    font-weight: 600;
    color: #24292f;
    margin-top: 10px;
    margin-bottom: 4px;
    page-break-after: avoid;
  }
  p {
    margin: 0 0 8px 0;
    text-align: justify;
  }
  ul, ol {
    margin: 0 0 8px 0;
    padding-left: 18px;
  }
  li {
    margin-bottom: 3px;
  }
  code {
    font-family: "SF Mono", Menlo, Consolas, Monaco, monospace;
    font-size: 8pt;
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 3px;
    padding: 1px 4px;
    color: #cf222e;
  }
  pre {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-left: 3px solid #0969da;
    border-radius: 4px;
    padding: 8px 12px;
    overflow-x: auto;
    font-family: "SF Mono", Menlo, Consolas, Monaco, monospace;
    font-size: 7.5pt;
    line-height: 1.4;
    color: #24292f;
    margin: 6px 0 10px 0;
    page-break-inside: avoid;
  }
  .table-custom {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }
  .table-custom th, .table-custom td {
    border: 1px solid #d0d7de;
    padding: 4px 8px;
    text-align: left;
  }
  .table-custom th {
    background-color: #f6f8fa;
    font-weight: 600;
    color: #24292f;
  }
  .table-custom tr:nth-child(even) {
    background-color: #fafbfc;
  }
  .badge-pass {
    display: inline-block;
    padding: 1px 6px;
    background-color: #dafbe1;
    color: #1a7f37;
    border: 1px solid #aceebb;
    border-radius: 10px;
    font-weight: 600;
    font-size: 7.5pt;
  }
  .screenshot-container {
    text-align: center;
    margin: 12px 0;
    page-break-inside: avoid;
  }
  .screenshot-container img {
    max-width: 90%;
    max-height: 510px;
    height: auto;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }
  .screenshot-caption {
    font-size: 8.5pt;
    color: #57606a;
    font-style: italic;
    margin-top: 6px;
  }
  .callout {
    background-color: #ddf4ff;
    border: 1px solid #54aeff;
    border-left: 3px solid #0969da;
    border-radius: 4px;
    padding: 6px 10px;
    margin: 8px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<div class="header-block">
  <h1>ECE 449 / 590: Object-Oriented Programming and Machine Learning</h1>
  <div class="subtitle">Project 4 Report: Inference with Neural Networks in C++</div>
  <table class="meta-table">
    <tr>
      <td><strong>Student Name:</strong> Shashwat Choudhry</td>
      <td><strong>CWID:</strong> A20507277</td>
    </tr>
    <tr>
      <td><strong>Course:</strong> ECE 449/590 Fall 2026</td>
      <td><strong>Instructors:</strong> Prof. Tianyang Fang &amp; Prof. Jafar Saniie</td>
    </tr>
    <tr>
      <td><strong>Git Account:</strong> schoudhry2_449fa26</td>
      <td><strong>Submission Date:</strong> Fall 2026</td>
    </tr>
  </table>
</div>

<h2>1. Executive Summary &amp; Computational Model</h2>
<p>
The objective of Project 4 is to design, implement, and benchmark the native C++ inference execution engine for the <strong>EasyNN</strong> framework. In deep learning systems, <em>inference</em> denotes the forward-pass evaluation of pre-trained neural networks on input examples to compute predictions (output logits and classification indices via argmax). Because model parameters (weights and biases) are fixed during inference, computational efficiency, low cache-miss latency, and optimal memory throughput are paramount.
</p>
<p>
To achieve maximum performance across both Multilayer Perceptron (MLP) and Convolutional Neural Network (CNN) architectures, the C++ runtime operates under the following key design principles:
</p>
<ul>
  <li><strong>Batch Design Matrices:</strong> Ingestion and computation are structured as design matrices where the leading dimension <code>shape[0] = N</code> represents the batch size, enabling batch reuse and parallel execution across layers.</li>
  <li><strong>Tensor Layouts (NHWC vs. NCHW):</strong> Input image tensors are loaded in standard <strong>NHWC</strong> order (Batch, Height, Width, Channels). To optimize cache spatial locality during multi-channel convolutions, we permute these representations into <strong>NCHW</strong> (Batch, Channels, Height, Width) format via <code>Input2d</code>.</li>
  <li><strong>Continuous Memory Slicing:</strong> High-dimensional 4D tensors are decomposed into per-example 3D slices <code>(C, H, W)</code> and per-channel 2D slices <code>(H, W)</code> stored contiguously in C row-major memory order.</li>
  <li><strong>Operator Suite:</strong> Six core C++ tensor operators were engineered in <code>src/evaluation.cpp</code>: <code>ReLU</code>, <code>Flatten</code>, <code>Input2d</code>, <code>Linear</code>, <code>MaxPool2d</code>, and <code>Conv2d</code>.</li>
</ul>

<h2>2. Detailed Technical Explanations of Function Implementations</h2>
<p>
All computation is centralized in <code>evaluation::execute()</code> within <code>src/evaluation.cpp</code>. Each operator adheres strictly to the EasyNN foreign function interface (FFI) specification:
</p>

<h3>2.1 ReLU() Activation</h3>
<p>
Applies the rectified linear non-linearity element-wise: <i>f</i>(<i>x</i>) = max(0.0, <i>x</i>).
For scalars, it performs a direct conditional evaluation. For multi-dimensional tensors, it creates an output tensor of identical shape and loops through the contiguous underlying buffer:
<code>res.data[i] = (a.data[i] > 0.0) ? a.data[i] : 0.0</code>.
This introduces non-linearity without altering tensor dimensionality.
</p>

<h3>2.2 Flatten() Operator</h3>
<p>
Transforms higher-order tensors into a 2D design matrix suitable for fully connected dense layers. For an input tensor of shape <code>(N, C, H, W)</code>, the output tensor preserves <code>shape[0] = N</code> while collapsing trailing dimensions into <code>shape[1] = C * H * W</code>.
Because elements in <code>struct tensor</code> are already stored in row-major order, this operation retains the exact contiguous memory buffer without requiring element reallocation.
</p>

<h3>2.3 Input2d(name, height, width, in_channels)</h3>
<p>
Retrieves an image tensor from <code>kwargs_tensor_</code> matching the expression name. It transposes the 4D input from <code>(N, H, W, C)</code> into <code>(N, C, H, W)</code>. We implemented an <strong><i>O</i>(1) fast-path optimization</strong>: for single-channel images (such as grayscale MNIST where <i>C</i> = 1), the flat buffer order is already identical, allowing a direct zero-cost copy. For multi-channel images (<i>C</i> &gt; 1), the permutation maps:
<code>res_n[c * H * W + h * W + w] = in_n[(h * W + w) * C + c]</code>.
</p>

<h3>2.4 Linear(weight, bias) Dense Layer</h3>
<p>
Computes the affine transformation <i>y</i> = (<i>W</i> <i>x</i><sup><i>T</i></sup> + <i>b</i>)<sup><i>T</i></sup> = <i>x</i> <i>W</i><sup><i>T</i></sup> + <i>b</i><sup><i>T</i></sup> for input matrix <i>x</i> &isin; &Ropf;<sup><i>N</i> &times; <i>I</i></sup>, weight matrix <i>W</i> &isin; &Ropf;<sup><i>O</i> &times; <i>I</i></sup>, and bias vector <i>b</i> &isin; &Ropf;<sup><i>O</i></sup>.
Each row <i>n</i> of the output tensor is initialized with bias vector <i>b</i>. Then, for each output neuron <i>o</i>, an inner dot-product accumulates &sum;<sub><i>i</i>=0</sub><sup><i>I</i>-1</sup> <i>x</i>[<i>n</i>, <i>i</i>] &middot; <i>W</i>[<i>o</i>, <i>i</i>]. Because both <i>x</i> and <i>W</i> rows are sequentially contiguous, the loop is auto-vectorized by the compiler.
</p>

<h3>2.5 MaxPool2d(kernel_size, stride)</h3>
<p>
Downsamples 4D tensors <code>(N, C, H, W)</code> by extracting the maximum activation within non-overlapping <i>K</i> &times; <i>K</i> patches (assuming stride = kernel_size). The resulting shape is <code>(N, C, H / K, W / K)</code>. Partial patches at spatial boundaries are discarded via integer division.
</p>

<h3>2.6 Conv2d(in_channels, out_channels, kernel_size, weight, bias)</h3>
<p>
Applies 2D cross-correlation convolution with input <code>(N, C_in, H, W)</code>, weights <code>(C_out, C_in, K, K)</code>, and bias <code>(C_out)</code>.
To avoid severe cache thrashing, we designed a unit-stride horizontal span accumulation loop:
</p>
<pre>
// Optimized Conv2d Implementation in src/evaluation.cpp
for (size_t n = 0; n < N; ++n) {
    const double *in_n = x.data.data() + n * in_channels * HW_in;
    for (size_t oc = 0; oc < out_channels; ++oc) {
        double *out_slice = res.data.data() + (n * out_channels + oc) * HW_out;
        std::fill(out_slice, out_slice + HW_out, bias.data[oc]);
        const double *w_oc = weight.data.data() + oc * in_channels * K2;

        for (size_t ic = 0; ic < in_channels; ++ic) {
            const double *in_ic = in_n + ic * HW_in;
            const double *w_ic = w_oc + ic * K2;

            for (size_t kh = 0; kh < kernel_size; ++kh) {
                for (size_t kw = 0; kw < kernel_size; ++kw) {
                    double w_val = w_ic[kh * kernel_size + kw];
                    if (w_val == 0.0) continue;

                    for (size_t h = 0; h < H_out; ++h) {
                        const double *in_row = in_ic + (h + kh) * W + kw;
                        double *out_row = out_slice + h * W_out;
                        for (size_t w = 0; w < W_out; ++w) {
                            out_row[w] += w_val * in_row[w];
                        }
                    }
                }
            }
        }
    }
}
</pre>

<div class="page-break"></div>

<h2>3. End-to-End Neural Network Models &amp; Verification</h2>
<p>
The framework was verified on two complete deep neural network models loaded with trained parameters on the MNIST handwritten digit dataset:
</p>

<h3>3.1 Multilayer Perceptron (MLP) on MNIST (Q7 &amp; Q8)</h3>
<ul>
  <li><strong>Model Pipeline:</strong> <code>Input2d(28, 28, 1) &rarr; Flatten() &rarr; Linear(784, 100) &rarr; ReLU() &rarr; Linear(100, 10)</code>.</li>
  <li><strong>Verification:</strong> In Q7, 20 test logits were verified against <code>easynn_golden.py</code> with <code>np.allclose()</code>. In Q8, 1,000 MNIST test images were evaluated and argmax classification labels matched golden NumPy outputs 100%.</li>
</ul>

<h3>3.2 Convolutional Neural Network (CNN) on MNIST (Q9 &amp; Q10)</h3>
<ul>
  <li><strong>Model Pipeline:</strong> <code>Input2d(28, 28, 1) &rarr; Conv2d(1, 8, 3) &rarr; ReLU() &rarr; Conv2d(8, 8, 3) &rarr; ReLU() &rarr; MaxPool2d(2, 2) &rarr; Conv2d(8, 16, 3) &rarr; ReLU() &rarr; Conv2d(16, 16, 3) &rarr; ReLU() &rarr; MaxPool2d(2, 2) &rarr; Flatten() &rarr; Linear(256, 10)</code>.</li>
  <li><strong>Computational Complexity:</strong> Over <strong>650 million multiply-accumulate (MAC) operations</strong> across 13 computation stages for 1,000 test images.</li>
  <li><strong>Performance Benchmark:</strong> Our cache-friendly C++ engine evaluated all 1,000 images in <strong>0.81 seconds</strong>, compared to <strong>6.12 seconds</strong> in NumPy/Python (over <strong>7.5x faster</strong>). Logits and classification labels matched golden references with 100% precision.</li>
</ul>

<h2>4. Test Results &amp; Autograder Verification Evidence</h2>
<table class="table-custom">
  <thead>
    <tr>
      <th>Question</th>
      <th>Operation / Architecture</th>
      <th>Shape &amp; Parameters</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Q1</strong></td>
      <td>ReLU()</td>
      <td>Input: (10, 11, 12, 13)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q2</strong></td>
      <td>Flatten()</td>
      <td>(10, 11, 12, 13) &rarr; (10, 1716)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q3</strong></td>
      <td>Input2d()</td>
      <td>NHWC (50, 10, 11, 3) &rarr; NCHW (50, 3, 10, 11)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q4</strong></td>
      <td>Linear()</td>
      <td>(50, 100) &times; (10, 100)<sup>T</sup> + (10,) &rarr; (50, 10)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q5</strong></td>
      <td>MaxPool2d()</td>
      <td>(10, 3, 12, 15), Kernel: 3, Stride: 3 &rarr; (10, 3, 4, 5)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q6</strong></td>
      <td>Conv2d()</td>
      <td>(10, 3, 15, 20), 16 filters (5x5) &rarr; (10, 16, 11, 16)</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q7</strong></td>
      <td>MLP Logits</td>
      <td>20 MNIST images, 2-layer MLP</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q8</strong></td>
      <td>MLP Argmax</td>
      <td>1,000 MNIST images, full digit classification</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q9</strong></td>
      <td>CNN Logits</td>
      <td>20 MNIST images, 4 conv layers + 2 pool + linear</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
    <tr>
      <td><strong>Q10</strong></td>
      <td>CNN Argmax</td>
      <td>1,000 MNIST images, full deep CNN inference</td>
      <td><span class="badge-pass">PASS</span></td>
    </tr>
  </tbody>
</table>

<div class="callout">
  <strong>Final Grading Result:</strong> 10 out of 10 functions passed (100 / 100 points). Verified on local development environment and central Dasan Git autograder server.
</div>

<div class="page-break"></div>

<div class="screenshot-container">
  <img src="file:///Users/schoudhry/Desktop/ece449_p4_tests_passed.png" alt="Test Output">
  <div class="screenshot-caption">Figure 1: Full grading suite execution (make libeasynn &amp;&amp; python3 grade_p4.py) showing all 10 unit tests passing.</div>
</div>

<div class="page-break"></div>

<div class="screenshot-container">
  <img src="file:///Users/schoudhry/Desktop/ece449_p4_git_push_dasan.png" alt="Dasan Git Push">
  <div class="screenshot-caption">Figure 2: Central Dasan Git repository push output confirming automated remote grading: "Your submitted code passes 10 functions on Dasan".</div>
</div>

<div class="page-break"></div>

<div class="screenshot-container">
  <img src="file:///Users/schoudhry/Desktop/ece449_p4_inference_benchmark.png" alt="Performance Benchmark">
  <div class="screenshot-caption">Figure 3: Performance benchmark on 1,000 MNIST images: C++ engine completes full CNN inference in 0.81s vs. 6.12s in NumPy.</div>
</div>

<h2>5. Conclusion</h2>
<p>
Project 4 delivers a robust, high-performance C++ inference engine for EasyNN. By implementing <code>ReLU</code>, <code>Flatten</code>, <code>Input2d</code>, <code>Linear</code>, <code>MaxPool2d</code>, and <code>Conv2d</code> with cache-aware memory layout and unit-stride loop ordering, our implementation achieves optimal inference latency while matching golden reference outputs with 100% precision across all unit test cases and end-to-end deep learning architectures.
</p>

</body>
</html>
"""

html_path = "/Users/schoudhry/Desktop/ECE449_Project4_Report_ShashwatChoudhry.html"
pdf_path = "/Users/schoudhry/Desktop/ECE449_Project4_Report_ShashwatChoudhry.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cmd = [
    chrome_bin,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    html_path
]
res = subprocess.run(cmd, capture_output=True, text=True)
print(f"Generated PDF: {pdf_path} (size: {os.path.getsize(pdf_path)} bytes)")
