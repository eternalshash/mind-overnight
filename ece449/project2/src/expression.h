#ifndef EXPRESSION_H
#define EXPRESSION_H

#include <vector>
#include <string>
#include <map>

class evaluation;

class expression
{
    friend class evaluation;
public:
    expression(
        int expr_id,
        const char *op_name,
        const char *op_type,
        int *inputs,
        int num_inputs);

    void add_op_param_double(
        const char *key,
        double value);

    void add_op_param_ndarray(
        const char *key,
        int dim,
        size_t shape[],
        double data[]);

    int get_expr_id() const { return expr_id_; }
    const std::string &get_op_name() const { return op_name_; }
    const std::string &get_op_type() const { return op_type_; }
    const std::vector<int> &get_inputs() const { return inputs_; }

private:
    int expr_id_;
    std::string op_name_;
    std::string op_type_;
    std::vector<int> inputs_;
    std::map<std::string, double> op_param_double_;
}; // class expression

#endif // EXPRESSION_H
