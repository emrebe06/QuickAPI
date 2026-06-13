#include "quick_isolate.h"

#include <sstream>
#include <string>

namespace {
thread_local std::string isolate_buffer;

bool has_control_chars(const char* value) {
    if (!value) return true;
    for (const unsigned char* cursor = reinterpret_cast<const unsigned char*>(value); *cursor; ++cursor) {
        if (*cursor < 32) return true;
    }
    return false;
}
}

int quickapi_isolate_spec_valid(quickapi_isolate_spec spec) {
    if (has_control_chars(spec.executable) || has_control_chars(spec.working_directory)) {
        return 0;
    }
    if (spec.timeout_ms == 0 || spec.timeout_ms > 3600U * 1000U) {
        return 0;
    }
    if (spec.memory_limit_mb == 0 || spec.memory_limit_mb > 1024U * 64U) {
        return 0;
    }
    return 1;
}

const char* quickapi_isolate_plan(quickapi_isolate_spec spec) {
    std::ostringstream out;
    out << "{\"valid\":" << (quickapi_isolate_spec_valid(spec) ? "true" : "false")
        << ",\"mode\":\"planned_isolated_worker\""
        << ",\"timeout_ms\":" << spec.timeout_ms
        << ",\"memory_limit_mb\":" << spec.memory_limit_mb
        << "}";
    isolate_buffer = out.str();
    return isolate_buffer.c_str();
}
