#include "quick_router.h"

#include <algorithm>
#include <cctype>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {
struct Route {
    std::string method;
    std::string path;
    std::string handler_name;
    size_t order;
};

struct MatchResult {
    bool matched;
    int score;
    size_t order;
    const Route* route;
    std::map<std::string, std::string> params;
};

struct Router {
    std::vector<Route> routes;
    size_t next_order = 0;
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

std::string strip_query(std::string path) {
    size_t marker = path.find('?');
    if (marker != std::string::npos) {
        path.resize(marker);
    }
    if (path.empty()) {
        return "/";
    }
    return path;
}

std::vector<std::string> split_path(const std::string& raw_path) {
    std::string path = strip_query(raw_path);
    std::vector<std::string> segments;
    std::string current;
    for (char ch : path) {
        if (ch == '/') {
            if (!current.empty()) {
                segments.push_back(current);
                current.clear();
            }
        } else {
            current.push_back(ch);
        }
    }
    if (!current.empty()) {
        segments.push_back(current);
    }
    return segments;
}

bool is_param_segment(const std::string& segment) {
    if (segment.size() > 1 && segment[0] == ':') {
        return true;
    }
    return segment.size() > 2 && segment.front() == '{' && segment.back() == '}';
}

bool is_path_param_segment(const std::string& segment) {
    if (segment == "*") {
        return true;
    }
    if (segment.size() > 7 && segment.front() == '{' && segment.back() == '}') {
        std::string inside = segment.substr(1, segment.size() - 2);
        return inside.size() > 5 && inside.substr(inside.size() - 5) == ":path";
    }
    return false;
}

std::string param_name(const std::string& segment) {
    if (segment == "*") {
        return "wildcard";
    }
    if (segment.size() > 1 && segment[0] == ':') {
        return segment.substr(1);
    }
    if (segment.size() > 2 && segment.front() == '{' && segment.back() == '}') {
        std::string inside = segment.substr(1, segment.size() - 2);
        size_t type_marker = inside.find(':');
        if (type_marker != std::string::npos) {
            inside.resize(type_marker);
        }
        return inside.empty() ? "param" : inside;
    }
    return "";
}

std::string join_tail(const std::vector<std::string>& segments, size_t start) {
    std::ostringstream out;
    for (size_t i = start; i < segments.size(); ++i) {
        if (i != start) {
            out << "/";
        }
        out << segments[i];
    }
    return out.str();
}

std::string json_escape(const std::string& value) {
    std::ostringstream out;
    for (char ch : value) {
        switch (ch) {
        case '\\':
            out << "\\\\";
            break;
        case '"':
            out << "\\\"";
            break;
        case '\n':
            out << "\\n";
            break;
        case '\r':
            out << "\\r";
            break;
        case '\t':
            out << "\\t";
            break;
        default:
            out << ch;
            break;
        }
    }
    return out.str();
}

MatchResult match_one(const Route& route, const std::string& wanted_method, const std::string& wanted_path) {
    MatchResult result{false, -1, route.order, &route, {}};
    if (route.method != wanted_method) {
        return result;
    }

    std::vector<std::string> pattern = split_path(route.path);
    std::vector<std::string> path = split_path(wanted_path);
    int score = 0;
    size_t i = 0;
    size_t j = 0;

    while (i < pattern.size()) {
        const std::string& part = pattern[i];
        if (is_path_param_segment(part)) {
            result.params[param_name(part)] = join_tail(path, j);
            score += 1;
            j = path.size();
            ++i;
            break;
        }
        if (j >= path.size()) {
            return result;
        }
        if (part == path[j]) {
            score += 10;
        } else if (is_param_segment(part)) {
            result.params[param_name(part)] = path[j];
            score += 4;
        } else {
            return result;
        }
        ++i;
        ++j;
    }

    if (i == pattern.size() && j == path.size()) {
        result.matched = true;
        result.score = score;
    }
    return result;
}

MatchResult best_match(Router* router, const char* method, const char* path) {
    MatchResult best{false, -1, 0, nullptr, {}};
    if (router == nullptr || method == nullptr || path == nullptr) {
        return best;
    }
    std::string wanted_method = upper(method);
    std::string wanted_path = strip_query(clean(path));

    for (const Route& route : router->routes) {
        MatchResult candidate = match_one(route, wanted_method, wanted_path);
        if (!candidate.matched) {
            continue;
        }
        bool better_score = candidate.score > best.score;
        bool same_score_earlier = candidate.score == best.score && candidate.order < best.order;
        if (!best.matched || better_score || same_score_earlier) {
            best = candidate;
        }
    }
    return best;
}

std::string params_json(const std::map<std::string, std::string>& params) {
    std::ostringstream out;
    out << "{";
    bool first = true;
    for (const auto& item : params) {
        if (!first) {
            out << ",";
        }
        out << "\"" << json_escape(item.first) << "\":\"" << json_escape(item.second) << "\"";
        first = false;
    }
    out << "}";
    return out.str();
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
    Route route;
    route.method = upper(method);
    route.path = strip_query(clean(path));
    route.handler_name = clean(handler_name);
    route.order = state->next_order++;
    state->routes.push_back(route);
    return 1;
}

const char* quickapi_router_match(quickapi_router_t router, const char* method, const char* path) {
    MatchResult match = best_match(static_cast<Router*>(router), method, path);
    if (!match.matched || match.route == nullptr) {
        return nullptr;
    }
    quick_router_buffer = match.route->handler_name;
    return quick_router_buffer.c_str();
}

int quickapi_router_match_score(quickapi_router_t router, const char* method, const char* path) {
    MatchResult match = best_match(static_cast<Router*>(router), method, path);
    return match.matched ? match.score : -1;
}

const char* quickapi_router_params(quickapi_router_t router, const char* method, const char* path) {
    MatchResult match = best_match(static_cast<Router*>(router), method, path);
    quick_router_buffer = match.matched ? params_json(match.params) : "{}";
    return quick_router_buffer.c_str();
}

const char* quickapi_router_allowed_methods(quickapi_router_t router, const char* path) {
    if (router == nullptr || path == nullptr) {
        return "";
    }
    auto* state = static_cast<Router*>(router);
    std::string wanted_path = strip_query(clean(path));
    std::set<std::string> allowed;

    for (const Route& route : state->routes) {
        MatchResult candidate = match_one(route, route.method, wanted_path);
        if (candidate.matched) {
            allowed.insert(route.method);
        }
    }

    std::ostringstream out;
    bool first = true;
    for (const std::string& method : allowed) {
        if (!first) {
            out << ",";
        }
        out << method;
        first = false;
    }
    quick_router_buffer = out.str();
    return quick_router_buffer.c_str();
}
