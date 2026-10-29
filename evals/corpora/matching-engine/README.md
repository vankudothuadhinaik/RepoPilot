[![C++20 CI](https://github.com/vankudothuadhinaik/low-latency-matching-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/vankudothuadhinaik/low-latency-matching-engine/actions/workflows/ci.yml)

# Low-Latency Limit Order Book & Matching Engine

A C++20 educational trading-engine project designed around HFT-style order
matching, deterministic execution, concurrency, and low-latency systems concepts.

## Features

- Limit orders
- Bid/ask order books
- Price-time priority
- Full and partial fills
- Order cancellation
- Order-ID lookup using `std::unordered_map`
- Fixed-point integer prices
- Reusable order object pool
- Unit tests
- Bounded lock-free SPSC queue
- Producer/consumer market-event pipeline
- Multi-run throughput benchmark
- CMake build

## Architecture

```text
Market Event Producer
        |
        v
   SPSC Queue
        |
        v
Market Event Consumer
        |
        v
  MatchingEngine
        |
        +----> Bid Book
        |
        +----> Ask Book
        |
        v
      Trades
```

The matching engine itself is intentionally single-threaded. A bounded
single-producer/single-consumer queue connects the simulated market-event
producer and consumer. This separates the event transport path from the
deterministic matching logic while keeping the core engine simple.

## Build

### Linux / macOS

Requirements:
- C++20 compiler
- CMake 3.16+

```bash
git clone https://github.com/vankudothuadhinaik/low-latency-matching-engine.git
cd low-latency-matching-engine

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

## Run demo

```bash
./build/exchange_demo
```

## Run tests

```bash
ctest --test-dir build --output-on-failure
```

The test target keeps assertions enabled even in Release builds, so the `assert()` checks are not compiled out by `NDEBUG`. GitHub Actions runs the Release suite and a separate Debug suite under AddressSanitizer and UndefinedBehaviorSanitizer; see the [CI run history](https://github.com/vankudothuadhinaik/low-latency-matching-engine/actions).

The test suite covers matching behavior, partial fills, cancellation,
order-book operations, the SPSC queue, and concurrent producer/consumer
correctness.

## Run benchmark

### Matching engine benchmark

```bash
./build/engine_benchmark
```

This benchmark measures aggregate order-processing throughput for the matching
engine.

It also samples per-order latency at the configured interval and reports nearest-rank percentiles from the final run. Sampling starts with the first measured order; if a run contains no samples, latency percentile fields are reported as zero rather than indexing an empty collection. Percentiles describe sampled calls only and should not be compared across machines without recording compiler, build mode, CPU, and workload settings.

### Event pipeline benchmark

```bash
./build/event_simulator
```

The event simulator accepts optional event-count and run-count arguments:

```bash
./build/event_simulator 5000000 5
```

The benchmark measures the wall-clock time for a producer/consumer pipeline
that generates market events, transfers them through the bounded SPSC queue,
and processes them through the matching engine.

For one measured Windows/MSYS2 Release environment, 5 million events per run
across 5 runs produced:

- Median throughput: approximately 4.14 million events/sec
- Average throughput: approximately 4.14 million events/sec
- Minimum throughput: approximately 4.05 million events/sec
- Maximum throughput: approximately 4.19 million events/sec
- Coefficient of variation: 1.18%

These results are environment-dependent and can vary with CPU, compiler,
operating system, background load, and machine configuration. The throughput
figure is an aggregate pipeline measurement, not a per-order latency
distribution or a p50/p95/p99 latency measurement.

## Benchmark evidence and interpretation

The CI workflow runs several workload shapes, including mixed, marketable,
non-crossing, skewed-price, and cancellation-heavy traffic. It records raw
outputs and runner/compiler metadata as workflow artifacts so results can be
inspected rather than relying on a single headline number. See the detailed
[benchmark methodology and interpretation guide](docs/BENCHMARKING.md) and
[workflow artifacts](https://github.com/vankudothuadhinaik/low-latency-matching-engine/actions).

CI throughput numbers are measurements from a shared GitHub-hosted runner,
not guaranteed performance on another machine. Workloads with high run-to-run
variation should be treated as directional evidence, not a stable performance
claim. Compare results only with the same build mode, workload, compiler, and
machine context.

## Design notes

### Price-time priority

For a buy order, the engine consumes the lowest available ask first. For a
sell order, it consumes the highest available bid first. Within one price
level, earlier orders are consumed first.

### Fixed-point prices

Prices use integer ticks rather than floating point:

```text
100.25 -> 10025
```

This avoids floating-point comparison issues in matching logic.

### Order lookup

The order book maintains an `unordered_map<OrderId, Order*>` so that order
IDs can be located without scanning every price level. Resting orders also have
an indexed queue position, allowing cancellation to remove an order from its
price-level FIFO list without scanning that entire queue. The index is updated
when orders are cancelled or fully filled; tests exercise cancellation and FIFO
behavior across a 1,000-order workload.

### Object pool

Orders are allocated from a reusable pool. This reduces repeated allocation
and deallocation during order processing.

### SPSC queue

The event pipeline uses a bounded single-producer/single-consumer ring
buffer implemented with atomic head and tail indices. The queue avoids mutexes
and dynamic allocation in its push/pop operations. One slot distinguishes full
from empty, so a declared storage capacity of `N` provides `N - 1` usable items;
capacities below two are rejected at compile time.

### Important limitation

This is a learning project, not production exchange infrastructure. It does
not implement production-grade networking, persistence, risk controls,
sequence recovery, market-data protocols, hardware timestamping, NUMA
placement, or kernel bypass.
