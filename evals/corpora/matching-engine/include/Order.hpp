#pragma once

#include <cstdint>

namespace hft {

using OrderId = std::uint64_t;
using Quantity = std::uint64_t;
using Price = std::int64_t; // Fixed-point price: 100.25 -> 10025 with tick size 0.01.

enum class Side {
    Buy,
    Sell
};

enum class OrderType {
    Limit
};

struct Order {
    OrderId id{};
    Side side{};
    Price price{};
    Quantity quantity{};
    Quantity remaining{};
    std::uint64_t sequence{}; // Monotonically increasing arrival sequence.

    Order() = default;

    Order(OrderId id_,
          Side side_,
          Price price_,
          Quantity quantity_,
          std::uint64_t sequence_)
        : id(id_),
          side(side_),
          price(price_),
          quantity(quantity_),
          remaining(quantity_),
          sequence(sequence_) {}
};

struct Trade {
    OrderId aggressive_order_id{};
    OrderId resting_order_id{};
    Price price{};
    Quantity quantity{};
};

} // namespace hft
