#include "expression.h"

expression::expression(
    int expr_id,
    const char *op_name,
    const char *op_type,
    int *inputs,
    int num_inputs)
    : expr_id_(expr_id),
      op_name_(op_name ? op_name : ""),
      op_type_(op_type ? op_type : "")
{
    if (inputs && num_inputs > 0)
    {
        inputs_.assign(inputs, inputs + num_inputs);
    }
}

void expression::add_op_param_double(
    const char *key,
    double value)
{
    if (key)
    {
        op_param_double_[key] = value;
        op_param_tensor_[key] = tensor(value);
    }
}

void expression::add_op_param_ndarray(
    const char *key,
    int dim,
    size_t shape[],
    double data[])
{
    if (key)
    {
        op_param_tensor_[key] = tensor(dim, shape, data);
    }
}
