#include <assert.h>
#include <iostream>
#include "evaluation.h"

evaluation::evaluation(const std::vector<expression> &exprs)
    : expressions_(exprs), result_tensor_(0.0)
{
}

void evaluation::add_kwargs_double(
    const char *key,
    double value)
{
    if (key)
    {
        kwargs_tensor_[key] = tensor(value);
    }
}

void evaluation::add_kwargs_ndarray(
    const char *key,
    int dim,
    size_t shape[],
    double data[])
{
    if (key)
    {
        kwargs_tensor_[key] = tensor(dim, shape, data);
    }
}

int evaluation::execute()
{
    std::map<int, tensor> val_map;

    for (const auto &expr : expressions_)
    {
        tensor val;
        const std::string &op_type = expr.op_type_;

        if (op_type == "Input")
        {
            auto it = kwargs_tensor_.find(expr.op_name_);
            if (it == kwargs_tensor_.end())
            {
                std::cerr << "Missing input for: " << expr.op_name_ << std::endl;
                return -1;
            }
            val = it->second;
        }
        else if (op_type == "Const")
        {
            auto it = expr.op_param_tensor_.find("value");
            if (it == expr.op_param_tensor_.end())
            {
                std::cerr << "Missing parameter 'value' for Const" << std::endl;
                return -1;
            }
            val = it->second;
        }
        else if (op_type == "Add")
        {
            assert(expr.inputs_.size() >= 2);
            const tensor &a = val_map[expr.inputs_[0]];
            const tensor &b = val_map[expr.inputs_[1]];

            if (a.is_scalar() && b.is_scalar())
            {
                val = tensor(a.data[0] + b.data[0]);
            }
            else if (!a.is_scalar() && !b.is_scalar())
            {
                if (a.shape != b.shape)
                {
                    std::cerr << "Add size mismatch" << std::endl;
                    return -1;
                }
                tensor res(a.shape);
                for (size_t i = 0; i < a.data.size(); ++i)
                {
                    res.data[i] = a.data[i] + b.data[i];
                }
                val = res;
            }
            else
            {
                std::cerr << "Add: cannot mix scalar and ndarray" << std::endl;
                return -1;
            }
        }
        else if (op_type == "Sub")
        {
            assert(expr.inputs_.size() >= 2);
            const tensor &a = val_map[expr.inputs_[0]];
            const tensor &b = val_map[expr.inputs_[1]];

            if (a.is_scalar() && b.is_scalar())
            {
                val = tensor(a.data[0] - b.data[0]);
            }
            else if (!a.is_scalar() && !b.is_scalar())
            {
                if (a.shape != b.shape)
                {
                    std::cerr << "Sub size mismatch" << std::endl;
                    return -1;
                }
                tensor res(a.shape);
                for (size_t i = 0; i < a.data.size(); ++i)
                {
                    res.data[i] = a.data[i] - b.data[i];
                }
                val = res;
            }
            else
            {
                std::cerr << "Sub: cannot mix scalar and ndarray" << std::endl;
                return -1;
            }
        }
        else if (op_type == "Mul")
        {
            assert(expr.inputs_.size() >= 2);
            const tensor &a = val_map[expr.inputs_[0]];
            const tensor &b = val_map[expr.inputs_[1]];

            if (a.is_scalar() && b.is_scalar())
            {
                val = tensor(a.data[0] * b.data[0]);
            }
            else if (a.is_scalar() && !b.is_scalar())
            {
                tensor res(b.shape);
                double s = a.data[0];
                for (size_t i = 0; i < b.data.size(); ++i)
                {
                    res.data[i] = s * b.data[i];
                }
                val = res;
            }
            else if (!a.is_scalar() && b.is_scalar())
            {
                tensor res(a.shape);
                double s = b.data[0];
                for (size_t i = 0; i < a.data.size(); ++i)
                {
                    res.data[i] = a.data[i] * s;
                }
                val = res;
            }
            else
            {
                // Both are tensors: must be 2D matrices for matmul
                if (a.dim() != 2 || b.dim() != 2)
                {
                    std::cerr << "Mul: matmul requires 2D matrices" << std::endl;
                    return -1;
                }
                if (a.shape[1] != b.shape[0])
                {
                    std::cerr << "Mul size mismatch: ("
                              << a.shape[0] << "," << a.shape[1] << ") * ("
                              << b.shape[0] << "," << b.shape[1] << ")" << std::endl;
                    return -1;
                }
                size_t M = a.shape[0];
                size_t K = a.shape[1];
                size_t N = b.shape[1];
                tensor res({M, N});
                for (size_t i = 0; i < M; ++i)
                {
                    for (size_t k = 0; k < K; ++k)
                    {
                        double a_ik = a.data[i * K + k];
                        for (size_t j = 0; j < N; ++j)
                        {
                            res.data[i * N + j] += a_ik * b.data[k * N + j];
                        }
                    }
                }
                val = res;
            }
        }
        else if (op_type == "Neg")
        {
            assert(expr.inputs_.size() >= 1);
            const tensor &a = val_map[expr.inputs_[0]];
            tensor res = a;
            for (size_t i = 0; i < res.data.size(); ++i)
            {
                res.data[i] = -res.data[i];
            }
            val = res;
        }
        else
        {
            std::cerr << "Unsupported op_type: " << op_type << std::endl;
            return -1;
        }

        val_map[expr.expr_id_] = val;
        result_tensor_ = val;
    }

    return 0;
}

double &evaluation::get_result()
{
    return result_tensor_.data[0];
}

int evaluation::get_result_dim() const
{
    return result_tensor_.dim();
}

size_t *evaluation::get_result_shape()
{
    return result_tensor_.shape.empty() ? nullptr : result_tensor_.shape.data();
}

double *evaluation::get_result_data()
{
    return result_tensor_.data.data();
}
