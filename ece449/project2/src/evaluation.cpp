#include <assert.h>
#include <iostream>
#include "evaluation.h"

evaluation::evaluation(const std::vector<expression> &exprs)
    : expressions_(exprs), result_(0.0)
{
}

void evaluation::add_kwargs_double(
    const char *key,
    double value)
{
    if (key)
    {
        kwargs_double_[key] = value;
    }
}

void evaluation::add_kwargs_ndarray(
    const char *key,
    int dim,
    size_t shape[],
    double data[])
{
}

int evaluation::execute()
{
    std::map<int, double> val_map;

    for (const auto &expr : expressions_)
    {
        double val = 0.0;
        const std::string &op_type = expr.op_type_;

        if (op_type == "Input")
        {
            auto it = kwargs_double_.find(expr.op_name_);
            if (it == kwargs_double_.end())
            {
                std::cerr << "Missing input for: " << expr.op_name_ << std::endl;
                return -1;
            }
            val = it->second;
        }
        else if (op_type == "Const")
        {
            auto it = expr.op_param_double_.find("value");
            if (it == expr.op_param_double_.end())
            {
                std::cerr << "Missing parameter 'value' for Const" << std::endl;
                return -1;
            }
            val = it->second;
        }
        else if (op_type == "Add")
        {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] + val_map[expr.inputs_[1]];
        }
        else if (op_type == "Sub")
        {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] - val_map[expr.inputs_[1]];
        }
        else if (op_type == "Mul")
        {
            assert(expr.inputs_.size() >= 2);
            val = val_map[expr.inputs_[0]] * val_map[expr.inputs_[1]];
        }
        else if (op_type == "Neg")
        {
            assert(expr.inputs_.size() >= 1);
            val = -val_map[expr.inputs_[0]];
        }
        else
        {
            std::cerr << "Unsupported op_type: " << op_type << std::endl;
            return -1;
        }

        val_map[expr.expr_id_] = val;
        result_ = val;
    }

    return 0;
}

double &evaluation::get_result()
{
    return result_;
}
