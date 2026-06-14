#include "../json/quick_json_writer.h"
#include "../core/quick_memory.h"
#include "../http/quick_http.h"
#include "../http/quick_listener.h"
#include "../http/quick_response.h"
#include "../router/quick_router.h"
#include "../security/quick_security.h"

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

struct BenchResult {
    std::string name;
    int iterations;
    double ms;
    unsigned long long checksum;
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

void add_routes(quickapi_router_t router, int count) {
    quickapi_router_add(router, "GET", "/", "root");
    quickapi_router_add(router, "GET", "/api/health", "health");
    quickapi_router_add(router, "POST", "/api/checkout", "checkout");
    quickapi_router_add(router, "GET", "/api/products", "products");
    quickapi_router_add(router, "GET", "/api/products/{product_id}", "product_detail");
    quickapi_router_add(router, "PUT", "/api/admin/products/{product_id}", "product_update");
    quickapi_router_add(router, "DELETE", "/api/admin/products/{product_id}", "product_delete");
    quickapi_router_add(router, "GET", "/static/{file_path:path}", "static_file");

    for (int i = 0; i < count; ++i) {
        std::string path = "/api/v1/resources/" + std::to_string(i) + "/items/{item_id}";
        std::string handler = "resource_" + std::to_string(i);
        quickapi_router_add(router, "GET", path.c_str(), handler.c_str());
        quickapi_router_add(router, "POST", path.c_str(), handler.c_str());
    }
}

BenchResult bench_router(int iterations, int route_count) {
    quickapi_router_t router = quickapi_router_create();
    add_routes(router, route_count);

    std::vector<std::string> paths = {
        "/",
        "/api/health",
        "/api/products/42",
        "/api/admin/products/99",
        "/static/assets/images/logo.png",
        "/api/v1/resources/24/items/abc",
        "/api/v1/resources/78/items/xyz",
        "/api/v1/resources/149/items/sku-9",
    };
    std::vector<std::string> methods = {"GET", "GET", "GET", "PUT", "GET", "GET", "POST", "GET"};

    unsigned long long checksum = 0;
    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        size_t index = static_cast<size_t>(i) % paths.size();
        const char* handler = quickapi_router_match(router, methods[index].c_str(), paths[index].c_str());
        checksum += handler ? static_cast<unsigned long long>(handler[0]) : 1ULL;
        checksum += static_cast<unsigned long long>(quickapi_router_match_score(router, methods[index].c_str(), paths[index].c_str()) + 7);
    }
    auto end = Clock::now();

    quickapi_router_destroy(router);
    return {"router_match", iterations, elapsed_ms(start, end), checksum};
}

BenchResult bench_json_writer(int iterations) {
    unsigned long long checksum = 0;
    const char* data = "{\"id\":42,\"name\":\"Karamel Roast\",\"price\":249.9,\"stock\":12}";
    quickapi_buffer* buffer = quickapi_buffer_create(512, 1024 * 1024);
    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        quickapi_json_writer_success_into(buffer, 200, "OK", "Product loaded", data);
        const char* json = quickapi_buffer_data(buffer);
        checksum += static_cast<unsigned long long>(json[0]);
        checksum += static_cast<unsigned long long>(json[25]);
    }
    auto end = Clock::now();
    quickapi_buffer_destroy(buffer);
    return {"json_success_write", iterations, elapsed_ms(start, end), checksum};
}

BenchResult bench_security(int iterations) {
    unsigned long long checksum = 0;
    const char* safe_payload = "{\"product_id\":\"sku-42\",\"quantity\":1,\"card_last4\":\"4242\"}";
    const char* bad_payload = "{\"q\":\"1 union select password from users --\"}";
    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        const char* payload = (i % 97 == 0) ? bad_payload : safe_payload;
        unsigned int flags = quickapi_security_fast_scan(
            "POST",
            "/api/checkout",
            "application/json",
            std::char_traits<char>::length(payload),
            1024 * 1024,
            payload
        );
        checksum += static_cast<unsigned long long>(flags);
        checksum += quickapi_security_fingerprint("/api/checkout", payload) & 0xffULL;
    }
    auto end = Clock::now();
    return {"security_fast_scan", iterations, elapsed_ms(start, end), checksum};
}

BenchResult bench_arena(int iterations) {
    unsigned long long checksum = 0;
    quickapi_arena* arena = quickapi_arena_create(1024 * 1024 * 8);
    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        if (quickapi_arena_remaining(arena) < 256) {
            quickapi_arena_reset(arena);
        }
        quickapi_result result = quickapi_arena_alloc_zeroed(arena, 96, 16);
        checksum += static_cast<unsigned long long>(result.ok ? result.value : 7);
        checksum += static_cast<unsigned long long>(quickapi_arena_allocation_count(arena));
    }
    auto end = Clock::now();
    checksum += static_cast<unsigned long long>(quickapi_arena_high_watermark(arena));
    quickapi_arena_destroy(arena);
    return {"arena_alloc_zeroed", iterations, elapsed_ms(start, end), checksum};
}

BenchResult bench_http_parse_response(int iterations) {
    unsigned long long checksum = 0;
    std::string raw =
        "POST /api/checkout?dry_run=0 HTTP/1.1\r\n"
        "Host: 127.0.0.1:8080\r\n"
        "User-Agent: quickapi-bench\r\n"
        "Content-Type: application/json\r\n"
        "Connection: keep-alive\r\n"
        "Content-Length: 58\r\n"
        "\r\n"
        "{\"product_id\":\"sku-42\",\"quantity\":1,\"card_last4\":\"4242\"}";
    const char* json = "{\"ok\":true,\"status\":200,\"code\":\"OK\",\"message\":\"accepted\",\"data\":{\"order_id\":\"ord_1\"},\"error\":null,\"meta\":{}}";
    quickapi_response_writer* writer = quickapi_response_writer_create(4096);

    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        quickapi_http_request_parse parsed = quickapi_http_parse_request(raw.c_str(), raw.size(), 32, 1024 * 1024);
        checksum += static_cast<unsigned long long>(parsed.ok);
        checksum += static_cast<unsigned long long>(parsed.method.size + parsed.path.size + parsed.query.size + parsed.body.size);
        quickapi_string_view content_type = quickapi_http_header_value(parsed, "Content-Type");
        checksum += static_cast<unsigned long long>(content_type.size);
        quickapi_response_writer_json(writer, 200, json, quickapi_http_request_should_keep_alive(parsed));
        checksum += static_cast<unsigned long long>(quickapi_response_writer_size(writer));
        quickapi_response_writer_reset(writer);
    }
    auto end = Clock::now();

    quickapi_response_writer_destroy(writer);
    return {"http_parse_response", iterations, elapsed_ms(start, end), checksum};
}

BenchResult bench_listener_exchange(int iterations, int route_count) {
    unsigned long long checksum = 0;
    quickapi_router_t router = quickapi_router_create();
    add_routes(router, route_count);
    quickapi_response_writer* writer = quickapi_response_writer_create(8192);
    std::string raw =
        "POST /api/checkout HTTP/1.1\r\n"
        "Host: 127.0.0.1:8080\r\n"
        "User-Agent: quickapi-bench\r\n"
        "Content-Type: application/json\r\n"
        "Connection: keep-alive\r\n"
        "Content-Length: 58\r\n"
        "\r\n"
        "{\"product_id\":\"sku-42\",\"quantity\":1,\"card_last4\":\"4242\"}";

    auto start = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        quickapi_listener_exchange exchange = quickapi_listener_handle_json(
            router,
            raw.c_str(),
            raw.size(),
            writer,
            1024 * 1024
        );
        checksum += static_cast<unsigned long long>(exchange.ok);
        checksum += static_cast<unsigned long long>(exchange.status);
        checksum += static_cast<unsigned long long>(exchange.response_size);
        checksum += static_cast<unsigned long long>(exchange.handler.size);
        quickapi_response_writer_reset(writer);
    }
    auto end = Clock::now();

    quickapi_response_writer_destroy(writer);
    quickapi_router_destroy(router);
    return {"listener_exchange", iterations, elapsed_ms(start, end), checksum};
}

void print_result(const BenchResult& result) {
    double seconds = result.ms / 1000.0;
    double rps = seconds > 0 ? static_cast<double>(result.iterations) / seconds : 0.0;
    std::cout << std::left << std::setw(22) << result.name
              << " iterations=" << std::setw(10) << result.iterations
              << " time_ms=" << std::setw(12) << std::fixed << std::setprecision(3) << result.ms
              << " ops_sec=" << std::setw(12) << std::fixed << std::setprecision(0) << rps
              << " checksum=" << result.checksum
              << "\n";
}

int parse_iterations(int argc, char** argv) {
    if (argc < 2) {
        return 1000000;
    }
    int value = std::atoi(argv[1]);
    return value > 0 ? value : 1000000;
}

}

int main(int argc, char** argv) {
    int iterations = parse_iterations(argc, argv);
    int route_count = argc >= 3 ? std::atoi(argv[2]) : 200;
    if (route_count < 1) {
        route_count = 200;
    }

    std::cout << "QuickAPI native hot-path benchmark\n";
    std::cout << "iterations=" << iterations << " route_count=" << route_count << "\n";
    std::cout << "------------------------------------------------------------\n";
    print_result(bench_router(iterations, route_count));
    print_result(bench_json_writer(iterations));
    print_result(bench_security(iterations));
    print_result(bench_arena(iterations));
    print_result(bench_http_parse_response(iterations));
    print_result(bench_listener_exchange(iterations, route_count));
    return 0;
}
