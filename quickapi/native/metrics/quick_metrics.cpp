#include "quick_metrics.h"

#include <chrono>

double quickapi_metrics_now_ms(void) {
    using clock = std::chrono::steady_clock;
    auto now = clock::now().time_since_epoch();
    return std::chrono::duration<double, std::milli>(now).count();
}

double quickapi_metrics_elapsed_ms(double start_ms) {
    return quickapi_metrics_now_ms() - start_ms;
}
