#ifndef TENSOR_H
#define TENSOR_H

#include <vector>
#include <cstddef>

struct tensor
{
    std::vector<size_t> shape;
    std::vector<double> data;

    tensor() : shape{}, data{} {}

    // Scalar constructor
    tensor(double val) : shape{}, data{val} {}

    // Pre-allocated tensor with given shape (initialized to 0.0)
    tensor(const std::vector<size_t> &s) : shape(s)
    {
        size_t total = 1;
        for (size_t d : s)
        {
            total *= d;
        }
        data.assign(total, 0.0);
    }

    // Construct from C array
    tensor(int dim, const size_t s[], const double *d)
    {
        if (dim == 0)
        {
            shape.clear();
            if (d)
            {
                data.assign(d, d + 1);
            }
            else
            {
                data.assign(1, 0.0);
            }
        }
        else
        {
            shape.assign(s, s + dim);
            size_t total = 1;
            for (int i = 0; i < dim; ++i)
            {
                total *= s[i];
            }
            if (d)
            {
                data.assign(d, d + total);
            }
            else
            {
                data.assign(total, 0.0);
            }
        }
    }

    bool is_scalar() const
    {
        return shape.empty();
    }

    int dim() const
    {
        return static_cast<int>(shape.size());
    }

    size_t size() const
    {
        return data.size();
    }
};

#endif // TENSOR_H
