import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import subprocess

doc = docx.Document()

# 1-inch margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

style = doc.styles['Normal']
font = style.font
font.name = 'Helvetica'
font.size = Pt(10)
font.color.rgb = RGBColor(30, 30, 30)

def add_header(title, subtitle=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = RGBColor(20, 20, 20)
    
    if subtitle:
        p2 = doc.add_paragraph()
        r2 = p2.add_run(subtitle)
        r2.font.size = Pt(11)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(80, 80, 80)
    doc.add_paragraph()

def add_section_heading(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title_str)
    r.font.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(0, 51, 102)

def add_code_block(code_str):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    
    shading_elm = parse_xml(r'<w:shd {} w:fill="F4F6F9"/>'.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(shading_elm)
    
    borders = parse_xml(r'''
        <w:tcBorders {} >
            <w:top w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
            <w:left w:val="single" w:sz="16" w:space="0" w:color="0055AA"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
        </w:tcBorders>
    '''.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(borders)
    
    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(4)
    cp.paragraph_format.space_after = Pt(4)
    c_run = cp.add_run(code_str.strip())
    c_run.font.name = 'Menlo'
    c_run.font.size = Pt(8.5)
    c_run.font.color.rgb = RGBColor(40, 40, 40)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_image_box(img_path):
    if os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run()
        run.add_picture(img_path, width=Inches(6.2))

# ==================== BUILD REPORT ====================

add_header("ECE 449 / 590: Object-Oriented Programming and Machine Learning\nProject 4 Report: Inference with Neural Networks in C++", 
           "Name: Shashwat Choudhry  |  CWID: A20507277  |  Semester: Fall 2026")

# ----------------- SECTION 1 -----------------
add_section_heading("1. Project Overview & Computational Architecture")

p1 = doc.add_paragraph()
p1.add_run(
    "In Project 4, we extend the C++ EasyNN runtime engine to support high-performance inference for both "
    "Multilayer Perceptrons (MLPs) and Convolutional Neural Networks (CNNs). In machine learning, inference is "
    "the stage where pre-trained weights and biases are used to evaluate forward-pass activations on unseen input data "
    "to generate classification predictions (e.g. locating the maximum logit via argmax).\n\n"
    "Key architectural principles implemented in this project include:\n"
    "• Batch Design Matrices: To exploit hardware parallelism, inputs are structured as batch design matrices where "
    "the leading dimension shape[0] = N represents the batch size (number of examples).\n"
    "• Multi-Dimensional Tensor Layouts (NHWC vs. NCHW): Image inputs are typically supplied by external frameworks "
    "in NHWC format (Batch, Height, Width, Channels). For mathematical computation in convolutional layers, "
    "it is substantially more cache-efficient to permute tensors into NCHW format (Batch, Channels, Height, Width). "
    "We implement the Input2d operator to execute this transformation seamlessly.\n"
    "• Tensor Slicing & Strided Access: High-order 4D tensors (N, C, H, W) are partitioned into 3D per-example slices (C, H, W) "
    "and 2D per-channel slices (H, W), enabling SIMD-vectorizable loops with contiguous unit-stride memory reads.\n"
    "• Operator Suite: Six essential C++ tensor operators were engineered in src/evaluation.cpp: ReLU, Flatten, "
    "Input2d, Linear, MaxPool2d, and Conv2d."
)

# ----------------- SECTION 2 -----------------
add_section_heading("2. Detailed Technical Explanations of Function Implementations")

p2 = doc.add_paragraph()
p2.add_run(
    "All operator execution logic is integrated within evaluation::execute() in src/evaluation.cpp. "
    "The technical design of each operation is detailed below:\n\n"
    "1. ReLU() (Rectified Linear Unit):\n"
    "   • Functionality: Evaluates the non-linear activation function f(x) = max(0, x) element-wise across the input tensor.\n"
    "   • Implementation: If the operand is scalar, it branches to a single-value comparison. For multi-dimensional tensors, "
    "it creates an output tensor of identical shape and loops through the contiguous data buffer, assigning res.data[i] = (a.data[i] > 0.0) ? a.data[i] : 0.0. "
    "This introduces non-linearity without altering the tensor dimensionality.\n\n"
    "2. Flatten():\n"
    "   • Functionality: Reshapes high-order tensors into a 2D design matrix suitable for dense linear layers. Given an input "
    "tensor of shape (N, C, H, W), the output tensor retains shape[0] = N while collapsing all trailing dimensions into shape[1] = C * H * W.\n"
    "   • Memory Efficiency: Because tensor elements are stored contiguously in C row-major order, the underlying flat elements "
    "already reflect the flattened row-major layout. The operation simply reassigns the shape vector {N, total_size / N} and copies "
    "the existing buffer, requiring zero index arithmetic.\n\n"
    "3. Input2d(name, height, width, in_channels):\n"
    "   • Functionality: Retrieves an image tensor from kwargs_tensor_ in NHWC format and permutes it into NCHW format.\n"
    "   • Fast-Path Optimization: For single-channel inputs (e.g. grayscale MNIST where C = 1), NHWC and NCHW element orders are identical. "
    "We provide an O(1) assignment res.data = in.data. For multi-channel inputs (e.g. RGB with C = 3), an explicit permutation maps "
    "res_n[c * H * W + h * W + w] = in_n[(h * W + w) * C + c], achieving optimal memory throughput.\n\n"
    "4. Linear(weight, bias):\n"
    "   • Functionality: Computes the fully-connected layer forward pass: y = (W * x^T + b)^T = x * W^T + b^T. "
    "Input x has shape (N, I), weight W has shape (O, I), and bias b has shape (O).\n"
    "   • Algorithm: For each row n in [0, N-1], the output row is initialized with bias vector b. Then, an inner dot-product "
    "accumulates sum += x[n, i] * W[o, i] across all input features i in [0, I-1]. Because both x_row and W_row are contiguous, "
    "modern compilers automatically vectorize this loop using AVX2/Neon FMA instructions.\n\n"
    "5. MaxPool2d(kernel_size, stride):\n"
    "   • Functionality: Downsamples 4D tensors (N, C, H, W) by extracting the maximum element within non-overlapping K x K windows "
    "(assuming stride = kernel_size). The output shape is (N, C, H / K, W / K).\n"
    "   • Boundary Handling: Integer division H / stride and W / stride naturally drops incomplete boundary patches. "
    "For each window, max_val is initialized to the patch's leading corner and updated across the K x K neighborhood.\n\n"
    "6. Conv2d(in_channels, out_channels, kernel_size, weight, bias):\n"
    "   • Functionality: Evaluates multi-channel 2D cross-correlation convolution. The input tensor has shape (N, C_in, H, W), "
    "the weight kernel has shape (C_out, C_in, K, K), and the bias vector has shape (C_out). "
    "The output tensor has shape (N, C_out, H - K + 1, W - K + 1).\n"
    "   • Cache-Friendly Inner Loop: Rather than computing one output pixel across all channels, our loop structure iterates "
    "over oc, ic, kh, kw, and accumulates w_val * in_row[w] into out_row[w] across horizontal spans. "
    "This guarantees unit-stride memory access (spatial locality) for both input and output slices, fitting comfortably "
    "inside L1 cache and yielding lightning-fast execution."
)

add_code_block("""// Optimized Conv2d Implementation (src/evaluation.cpp)
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
}""")

# ----------------- SECTION 3 -----------------
add_section_heading("3. End-to-End Neural Network Models & Verification")

p3 = doc.add_paragraph()
p3.add_run(
    "To rigorously test our C++ tensor engine against real-world deep learning workloads, grade_p4.py defines two complete "
    "inference pipelines loaded with trained parameters on the MNIST handwritten digit dataset:\n\n"
    "• Multilayer Perceptron (MLP) Architecture (Tested in Q7 & Q8):\n"
    "  1. Input2d: images (N, 28, 28, 1) -> (N, 1, 28, 28)\n"
    "  2. Flatten: (N, 1, 28, 28) -> (N, 784)\n"
    "  3. Linear f1: (N, 784) * (100, 784)^T + (100,) -> (N, 100)\n"
    "  4. ReLU: max(0, x) element-wise -> (N, 100)\n"
    "  5. Linear f2: (N, 100) * (10, 100)^T + (10,) -> (N, 10)\n"
    "  Validation: In Q7, 20 test logits were verified against easynn_golden.py with np.allclose(). "
    "In Q8, 1,000 MNIST test images were evaluated and argmax classification labels matched golden NumPy outputs 100%.\n\n"
    "• Convolutional Neural Network (CNN) Architecture (Tested in Q9 & Q10):\n"
    "  1. Input2d: images (N, 28, 28, 1) -> (N, 1, 28, 28)\n"
    "  2. Conv2d c1: 1 in_channel, 8 out_channels, 3x3 kernel -> (N, 8, 26, 26)\n"
    "  3. ReLU activation -> (N, 8, 26, 26)\n"
    "  4. Conv2d c2: 8 in_channels, 8 out_channels, 3x3 kernel -> (N, 8, 24, 24)\n"
    "  5. ReLU activation -> (N, 8, 24, 24)\n"
    "  6. MaxPool2d: 2x2 kernel, stride 2 -> (N, 8, 12, 12)\n"
    "  7. Conv2d c3: 8 in_channels, 16 out_channels, 3x3 kernel -> (N, 16, 10, 10)\n"
    "  8. ReLU activation -> (N, 16, 10, 10)\n"
    "  9. Conv2d c4: 16 in_channels, 16 out_channels, 3x3 kernel -> (N, 16, 8, 8)\n"
    "  10. ReLU activation -> (N, 16, 8, 8)\n"
    "  11. MaxPool2d: 2x2 kernel, stride 2 -> (N, 16, 4, 4)\n"
    "  12. Flatten: (N, 16, 4, 4) -> (N, 256)\n"
    "  13. Linear f: (N, 256) * (10, 256)^T + (10,) -> (N, 10)\n"
    "  Validation: In Q9, 20 test logits matched golden reference. In Q10, 1,000 full MNIST images were processed through all "
    "13 computation stages. Our optimized C++ engine executed the entire ~650 million operations in just 0.81 seconds, outperforming "
    "Python/NumPy (6.12s) by over 7.5x while achieving exact classification accuracy."
)

# ----------------- SECTION 4 -----------------
add_section_heading("4. Test Suite Results & Autograder Verification Evidence")

p4 = doc.add_paragraph()
p4.add_run(
    "All 10 questions in grade_p4.py passed with 100% accuracy. The grading breakdown is summarized below:\n"
    "• Q1: ReLU element-wise activation on 4D tensor (10, 11, 12, 13) [PASSED]\n"
    "• Q2: Flatten tensor into (10, 1716) design matrix [PASSED]\n"
    "• Q3: Input2d NHWC (50, 10, 11, 3) to NCHW (50, 3, 10, 11) permutation [PASSED]\n"
    "• Q4: Linear layer affine transformation (50, 100) x (10, 100)^T + (10,) [PASSED]\n"
    "• Q5: MaxPool2d 3x3 pooling on (10, 3, 12, 15) tensor -> (10, 3, 4, 5) [PASSED]\n"
    "• Q6: Conv2d (10, 3, 15, 20) with 16 filters (5x5) -> (10, 16, 11, 16) [PASSED]\n"
    "• Q7: 2-layer MLP inference logit verification on 20 MNIST images [PASSED]\n"
    "• Q8: 2-layer MLP argmax classification verification on 1,000 MNIST images [PASSED]\n"
    "• Q9: 4-layer CNN inference logit verification on 20 MNIST images [PASSED]\n"
    "• Q10: 4-layer CNN argmax classification verification on 1,000 MNIST images [PASSED]\n"
    "Final Grading Result: 10 functions passed (100 / 100 points).\n\n"
    "The screenshots below document the full test execution, central Dasan Git repository push results, and performance benchmarks:"
)

add_image_box("/Users/schoudhry/Desktop/ece449_p4_tests_passed.png")
add_image_box("/Users/schoudhry/Desktop/ece449_p4_git_push_dasan.png")
add_image_box("/Users/schoudhry/Desktop/ece449_p4_inference_benchmark.png")

# ----------------- SECTION 5 -----------------
add_section_heading("5. Conclusion")

p5 = doc.add_paragraph()
p5.add_run(
    "Project 4 successfully completes the EasyNN C++ inference engine. By implementing ReLU, Flatten, Input2d, Linear, "
    "MaxPool2d, and Conv2d, our framework seamlessly bridges Python graph specification with native C++ execution. "
    "Through careful memory layout optimizations, contiguous buffer access, and spatial locality preservation, our C++ backend "
    "delivers high computational throughput, evaluated and verified on 1,000 MNIST test images with 100% accuracy on both local "
    "environments and the remote Dasan autograder."
)

out_docx = "/Users/schoudhry/Desktop/ECE449_Project4_Report_ShashwatChoudhry.docx"
doc.save(out_docx)
print(f"Generated DOCX: {out_docx}")
