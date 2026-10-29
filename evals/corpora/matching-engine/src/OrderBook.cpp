#include "OrderBook.hpp"

#include <algorithm>
#include <limits>

namespace hft {

OrderBook::OrderBook(std::size_t pool_capacity)
    : pool_(pool_capacity) {}

bool OrderBook::addOrder(OrderId id, Side side, Price price, Quantity quantity) {
    if (price <= 0 || quantity == 0 || orders_.contains(id)) {
        return false;
    }

    Order* order = pool_.acquire(id, side, price, quantity, next_sequence_++);
    orders_.emplace(id, order);

    if (side == Side::Buy) {
        auto& queue = bids_[price];
        queue.push_back(order);
        queue_positions_.emplace(id, std::prev(queue.end()));
    } else {
        auto& queue = asks_[price];
        queue.push_back(order);
        queue_positions_.emplace(id, std::prev(queue.end()));
    }

    return true;
}

bool OrderBook::crosses(Side incoming_side,
                        Price incoming_price,
                        Price resting_price) const {
    if (incoming_side == Side::Buy) {
        return incoming_price >= resting_price;
    }
    return incoming_price <= resting_price;
}

void OrderBook::removeEmptyLevel(Side side, Price price) {
    if (side == Side::Buy) {
        auto it = bids_.find(price);
        if (it != bids_.end() && it->second.empty()) {
            bids_.erase(it);
        }
    } else {
        auto it = asks_.find(price);
        if (it != asks_.end() && it->second.empty()) {
            asks_.erase(it);
        }
    }
}

void OrderBook::eraseFromLevel(Side side, Price price, Order* order) {
    const auto position = queue_positions_.find(order->id);
    if (position == queue_positions_.end()) {
        return;
    }

    if (side == Side::Buy) {
        auto level = bids_.find(price);
        if (level != bids_.end()) {
            level->second.erase(position->second);
            removeEmptyLevel(side, price);
        }
    } else {
        auto level = asks_.find(price);
        if (level != asks_.end()) {
            level->second.erase(position->second);
            removeEmptyLevel(side, price);
        }
    }

    queue_positions_.erase(position);
}

bool OrderBook::cancelOrder(OrderId id) {
    auto it = orders_.find(id);
    if (it == orders_.end()) {
        return false;
    }

    Order* order = it->second;
    eraseFromLevel(order->side, order->price, order);
    orders_.erase(it);
    pool_.release(order);
    return true;
}

std::vector<Trade> OrderBook::match(OrderId incoming_id,
                                    Side side,
                                    Price price,
                                    Quantity quantity) {
    std::vector<Trade> trades;
    Quantity remaining = quantity;

    if (remaining == 0) {
        return trades;
    }

    auto execute_level = [&](auto& levels) {
        while (!levels.empty() && remaining > 0) {
            auto level_it = levels.begin();
            const Price resting_price = level_it->first;

            if (!crosses(side, price, resting_price)) {
                break;
            }

            auto& queue = level_it->second;

            while (!queue.empty() && remaining > 0) {
                Order* resting = queue.front();
                const Quantity executed = std::min(remaining, resting->remaining);

                trades.push_back(
                    Trade{incoming_id, resting->id, resting->price, executed});

                remaining -= executed;
                resting->remaining -= executed;

                if (resting->remaining == 0) {
                    orders_.erase(resting->id);
                    queue_positions_.erase(resting->id);
                    pool_.release(resting);
                    queue.pop_front();
                }
            }

            if (queue.empty()) {
                levels.erase(level_it);
            }
        }
    };

    if (side == Side::Buy) {
        execute_level(asks_);
    } else {
        execute_level(bids_);
    }

    return trades;
}

const Order* OrderBook::find(OrderId id) const noexcept {
    auto it = orders_.find(id);
    return it == orders_.end() ? nullptr : it->second;
}

Price OrderBook::bestBid() const {
    return bids_.empty()
        ? std::numeric_limits<Price>::min()
        : bids_.begin()->first;
}

Price OrderBook::bestAsk() const {
    return asks_.empty()
        ? std::numeric_limits<Price>::max()
        : asks_.begin()->first;
}

} // namespace hft
