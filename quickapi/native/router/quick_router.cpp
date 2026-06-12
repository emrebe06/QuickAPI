#include "quick_router.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <vector>

namespace {
struct Route {
    std::string method;
    std::string path;
    std::string handler_name;
};

struct Router {
    std::vector<Route> routes;
};

thread_local std::string quick_router_buffer;

std::string clean(const char* value) {
    return value == nullptr ? "" : value;
}

std::string upper(const char* value) {
    std::string out = clean(value);
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
    return out;
}
}

quickapi_router_t quickapi_router_create(void) {
    return new Router();
}

void quickapi_router_destroy(quickapi_router_t router) {
    delete static_cast<Router*>(router);
}

int quickapi_router_add(quickapi_router_t router, const char* method, const char* path, const char* handler_name) {
    if (router == nullptr || method == nullptr || path == nullptr) {
        return 0;
    }
    auto* state = static_cast<Router*>(router);
    state->routes.push_back(Route{upper(method), clean(path), clean(handler_name)});
    return 1;
}

const char* quickapi_router_match(quickapi_router_t router, const char* method, const char* path) {
    if (router == nullptr || method == nullptr || path == nullptr) {
        return nullptr;
    }
    auto* state = static_cast<Router*>(router);
    std::string wanted_method = upper(method);
    std::string wanted_path = clean(path);
    for (const Route& route : state->routes) {
        if (route.method == wanted_method && route.path == wanted_path) {
            quick_router_buffer = route.handler_name;
            return quick_router_buffer.c_str();
        }
    }
    return nullptr;
}

const char* quickapi_router_allowed_methods(quickapi_router_t router, const char* path) {
    if (router == nullptr || path == nullptr) {
        return "";
    }
    auto* state = static_cast<Router*>(router);
    std::string wanted_path = clean(path);
    std::ostringstream out;
    bool first = true;
    for (const Route& route : state->routes) {
        if (route.path == wanted_path) {
            if (!first) {
                out << ",";
            }
            out << route.method;
            first = false;
        }
    }
    quick_router_buffer = out.str();
    return quick_router_buffer.c_str();
}
