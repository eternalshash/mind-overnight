#ifndef EVALUATION_H
#define EVALUATION_H

#include <vector>
#include <map>
#include <string>
#include "expression.h"
#include "tensor.h"

class evaluation
{
public:
    evaluation(const std::vector<expression> &exprs);

    void add_kwargs_double(
        const char *key,
        double value);

    void add_kwargs_ndarray(
        const char *key,
        int dim,
        size_t shape[],
        double data[]);

    // return 0 for success
    int execute();

    // return the variable computed by the last expression
    double &get_result();

    int get_result_dim() const;
    size_t *get_result_shape();
    double *get_result_data();

private:
    std::vector<expression> expressions_;
    std::map<std::string, tensor> kwargs_tensor_;
    tensor result_tensor_;
}; // class evaluation

#endif // EVALUATION_H
