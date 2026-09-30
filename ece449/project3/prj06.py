import numpy as np
import time


# save theta to p6_params.npz that can be used by easynn
def save_theta(theta):
    c1_W, c1_b, c2_W, c2_b, f_W, f_b = theta

    np.savez_compressed("p6_params.npz", **{
        "c1.weight": c1_W,
        "c1.bias": c1_b,
        "c2.weight": c2_W,
        "c2.bias": c2_b,
        "f.weight": f_W,
        "f.bias": f_b
    })


# initialize theta using uniform distribution [-bound, bound]
# return theta as (c1_W, c1_b, c2_W, c2_b, f_W, f_b)
def initialize_theta(bound):
    c1_W = np.random.uniform(-bound, bound, (8, 1, 5, 5))
    c1_b = np.random.uniform(-bound, bound, 8)
    c2_W = np.random.uniform(-bound, bound, (8, 8, 5, 5))
    c2_b = np.random.uniform(-bound, bound, 8)
    f_W = np.random.uniform(-bound, bound, (10, 128))
    f_b = np.random.uniform(-bound, bound, 10)
    return (c1_W, c1_b, c2_W, c2_b, f_W, f_b)


# return out_nchw
def Conv2d(in_nchw, kernel_W, kernel_b):
    OC, IC, KH, KW = kernel_W.shape
    N, C, H, W = in_nchw.shape
    if C != IC or kernel_b.shape != (OC,):
        raise Exception("Conv2d size mismatch: %s @ (%s, %s)" % (
            in_nchw.shape, kernel_W.shape, kernel_b.shape))

    # view in_nchw as a 6D tensor
    shape = (N, IC, H-KH+1, W-KW+1, KH, KW)
    strides = in_nchw.strides+in_nchw.strides[2:]
    data = np.lib.stride_tricks.as_strided(in_nchw,
        shape = shape, strides = strides, writeable = False)
    # np.einsum("nihwyx,oiyx->nohw", data, kernel_W)
    nhwo = np.tensordot(data, kernel_W, ((1,4,5), (1,2,3)))
    return nhwo.transpose(0,3,1,2)+kernel_b.reshape((1, OC, 1, 1))

# return p_b for the whole batch
def Conv2d_backprop_b(p_out, in_nchw, kernel_W, kernel_b):
    OC, IC, KH, KW = kernel_W.shape
    N, C, H, W = in_nchw.shape
    if C != IC or kernel_b.shape != (OC,) or p_out.shape != (N, OC, H-KH+1, W-KW+1):
        raise Exception("Conv2d_backprop_b size mismatch: %s = %s @ (%s, %s)" % (
            p_out.shape, in_nchw.shape, kernel_W.shape, kernel_b.shape))

    return np.einsum("nohw->o", p_out, optimize = "optimal")/N

# return p_W for the whole batch
def Conv2d_backprop_W(p_out, in_nchw, kernel_W, kernel_b):
    OC, IC, KH, KW = kernel_W.shape
    N, C, H, W = in_nchw.shape
    if C != IC or kernel_b.shape != (OC,) or p_out.shape != (N, OC, H-KH+1, W-KW+1):
        raise Exception("Conv2d_backprop_W size mismatch: %s = %s @ (%s, %s)" % (
            p_out.shape, in_nchw.shape, kernel_W.shape, kernel_b.shape))
    
    # view in_nchw as a 6D tensor
    shape = (N, IC, KH, KW, H-KH+1, W-KW+1)
    strides = in_nchw.strides+in_nchw.strides[2:]
    data = np.lib.stride_tricks.as_strided(in_nchw,
        shape = shape, strides = strides, writeable = False)
    # np.einsum("nohw,niyxhw->oiyx", p_out, data)
    return np.tensordot(p_out, data, ((0,2,3), (0,4,5)))/N

# return p_in for the whole batch
def Conv2d_backprop_in(p_out, in_nchw, kernel_W, kernel_b):
    OC, IC, KH, KW = kernel_W.shape
    N, C, H, W = in_nchw.shape
    if C != IC or kernel_b.shape != (OC,) or p_out.shape != (N, OC, H-KH+1, W-KW+1):
        raise Exception("Conv2d_backprop_in size mismatch: %s = %s @ (%s, %s)" % (
            p_out.shape, in_nchw.shape, kernel_W.shape, kernel_b.shape))

    # view p_out as a padded 6D tensor
    padded = np.zeros((N, OC, H+KH-1, W+KW-1))
    padded[:, :, KH-1:-KH+1, KW-1:-KW+1] = p_out
    shape = (N, IC, H, W, KH, KW)
    strides = padded.strides+padded.strides[2:]
    data = np.lib.stride_tricks.as_strided(padded,
        shape = shape, strides = strides, writeable = False)
    # np.einsum("nohwyx,oiyx->nihw", data, kernel_W)
    nhwi = np.tensordot(data, kernel_W, ((1,4,5), (0,2,3)))
    return nhwi.transpose((0,3,1,2))


# return out_nchw
def MaxPool_2by2(in_nchw):
    N, C, H, W = in_nchw.shape
    shape = (N, C, H//2, 2, W//2, 2)
    return np.nanmax(in_nchw.reshape(shape), axis = (3,5))

# return p_in for the whole batch
def MaxPool_2by2_backprop(p_out, out_nchw, in_nchw):
    p_in = np.zeros(in_nchw.shape)
    p_in[:, :, 0::2, 0::2] = p_out*(out_nchw == in_nchw[:, :, 0::2, 0::2])
    p_in[:, :, 0::2, 1::2] = p_out*(out_nchw == in_nchw[:, :, 0::2, 1::2])
    p_in[:, :, 1::2, 0::2] = p_out*(out_nchw == in_nchw[:, :, 1::2, 0::2])
    p_in[:, :, 1::2, 1::2] = p_out*(out_nchw == in_nchw[:, :, 1::2, 1::2])
    return p_in


# forward:
#    x = NCHW(images)
#   cx = Conv2d_c1(x)
#   rx = ReLU(cx)
#    y = MaxPool(rx)
#   cy = Conv2d_c2(hx)
#   ry = ReLU(cy)
#    g = MaxPool(ry)
#    h = Flatten(g)
#    z = Linear_f(h)
# return (z, h, g, ry, cy, y, rx, cx, x)
def forward(images, theta):
    # number of samples
    N = images.shape[0]

    # unpack theta into c1, c2, and f
    c1_W, c1_b, c2_W, c2_b, f_W, f_b = theta

    # x = NCHW(images)
    x = images.astype(float).transpose(0,3,1,2)

    # cx = Conv2d_c1(x)
    cx = Conv2d(x, c1_W, c1_b)

    # rx = ReLU(cx)
    rx = cx*(cx > 0)

    # y = MaxPool(rx)
    y = MaxPool_2by2(rx)
    
    # cy = Conv2d_c2(y)
    cy = Conv2d(y, c2_W, c2_b)

    # ry = ReLU(cy)
    ry = cy*(cy > 0)

    # g = MaxPool(ry)
    g = MaxPool_2by2(ry)

    # h = Flatten(g)
    h = g.reshape((N, -1))

    # z = Linear_f(h)
    z = np.zeros((N, f_b.shape[0]))
    for i in range(N):
        z[i, :] = np.matmul(f_W, h[i])+f_b

    return (z, h, g, ry, cy, y, rx, cx, x)


# backprop:
#   J = cross entropy between labels and softmax(z)
# return nabla_J
def backprop(labels, theta, z, h, g, ry, cy, y, rx, cx, x):
    # number of samples
    N = labels.shape[0]

    # unpack theta into c1, c2, and f
    c1_W, c1_b, c2_W, c2_b, f_W, f_b = theta

    # sample-by-sample from z to h
    p_f_W = np.zeros(f_W.shape)
    p_f_b = np.zeros(f_b.shape)
    p_h = np.zeros(h.shape)

    for i in range(N):
        # compute the contribution to nabla_J for sample i

        # cross entropy and softmax
        #   compute partial J to partial z[i]
        #   scale by 1/N for averaging
        expz = np.exp(z[i]-max(z[i]))
        p_z = expz/sum(expz)/N
        p_z[labels[i]] -= 1/N

        # z = Linear_f(h)
        #   compute partial J to partial h[i]
        #   accumulate partial J to partial f_W, f_b
        # p_h[i, :] = ...
        # p_f_W += ...
        # p_f_b += ...

    # process the whole batch together for better efficiency

    # h = Flatten(g)
    #   compute partial J to partial g
    # p_g = ...

    # g = MaxPool(ry)
    #   compute partial J to partial ry
    # p_ry = ...

    # ry = ReLU(cy)
    #   compute partial J to partial cy
    # p_cy = ...

    # cy = Conv2d_c2(y)
    #   compute partial J to partial y
    #   compute partial J to partial c2_W, c2_b
    # p_y = ...
    # p_c2_W = ...
    # p_c2_b = ...

    # y = MaxPool(rx)
    #   compute partial J to partial rx
    # p_rx = ...

    # rx = ReLU(cx)
    #   compute partial J to partial cx
    # p_cx = ...

    # cx = Conv2d_c1(x)
    #   compute partial J to partial c1_W, c1_b
    # p_c1_W = ...
    # p_c1_b = ...

    # ToDo: modify code below as needed
    return None
    # return (p_c1_W, p_c1_b, p_c2_W, p_c2_b, p_f_W, p_f_b)


# apply SGD to update theta by nabla_J and the learning rate epsilon
# return updated theta
def update_theta(theta, nabla_J, epsilon):
    # ToDo: modify code below as needed
    updated_theta = theta
    return updated_theta


# ToDo: set numpy random seed to the last 8 digits of your CWID
np.random.seed(12345678)

# load training data and split them for validation/training
mnist_train = np.load("mnist_train.npz")
validation_images = mnist_train["images"][:1000]
validation_labels = mnist_train["labels"][:1000]
training_images = mnist_train["images"][1000:21000]
training_labels = mnist_train["labels"][1000:21000]

# hyperparameters
bound = 1 # initial weight range
epsilon = 0.00001 # learning rate
batch_size = 4

# start training
start = time.time()
theta = initialize_theta(bound)
batches = training_images.shape[0]//batch_size
for epoch in range(5):
    indices = np.arange(training_images.shape[0])
    np.random.shuffle(indices)
    for i in range(batches):
        batch_images = training_images[indices[i*batch_size:(i+1)*batch_size]]
        batch_labels = training_labels[indices[i*batch_size:(i+1)*batch_size]]

        z, h, g, ry, cy, y, rx, cx, x = forward(batch_images, theta)
        nabla_J = backprop(batch_labels, theta, z, h, g, ry, cy, y, rx, cx, x)
        theta = update_theta(theta, nabla_J, epsilon)

    # check accuracy using validation examples
    z, _, _, _, _, _, _, _, _ = forward(validation_images, theta)
    pred_labels = z.argmax(axis = 1)
    count = sum(pred_labels == validation_labels)
    print("epoch %d, accuracy %.3f, time %.2f" % (
        epoch, count/validation_images.shape[0], time.time()-start))

# save the weights to be submitted
save_theta(theta)
