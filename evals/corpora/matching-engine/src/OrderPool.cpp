#include "OrderPool.hpp"

#include <utility>

namespace hft {

OrderPool::OrderPool(std::size_t initial_capacity) {
    storage_.reserve(initial_capacity);
    free_.reserve(initial_capacity);

    for (std::size_t i = 0; i < initial_capacity; ++i) {
        storage_.push_back(std::make_unique<Order>());
        free_.push_back(storage_.back().get());
    }
}

Order* OrderPool::acquire(OrderId id,
                          Side side,
                          Price price,
                          Quantity quantity,
                          std::uint64_t sequence) {
    if (free_.empty()) {
        storage_.push_back(std::make_unique<Order>());
        free_.push_back(storage_.back().get());
    }

    Order* order = free_.back();
    free_.pop_back();
    *order = Order{id, side, price, quantity, sequence};
    return order;
}

void OrderPool::release(Order* order) {
    if (order != nullptr) {
        free_.push_back(order);
    }
}

} // namespace hft
