#include "quick_router.h"

#include <algorithm>
#include <cctype>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
struct Route {
    std::string method;
    std::string path;
    std::string handler_name;
    std::vector<std::string> segments;
    bool dynamic;
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
    struct TrieNode {
        std::unordered_map<std::string, size_t> literal;
        size_t param = static_cast<size_t>(-1);
        std::string param_name;
        size_t path_param = static_cast<size_t>(-1);
        std::string path_param_name;
        size_t route_index = static_cast<size_t>(-1);
    };

    std::vector<Route> routes;
    std::unordered_map<std::string, size_t> exact_routes;
    std::unordered_map<std::string, std::vector<size_t>> method_routes;
    std::unordered_map<std::string, std::vector<size_t>> prefix_routes;
    std::vector<TrieNode> trie;
    std::unordered_map<std::string, size_t> method_roots;
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

std::string route_key(const std::string& method, const std::string& path) {
    return method + "\n" + path;
}

std::string prefix_key(const std::string& method, const std::vector<std::string>& segments, size_t count) {
    std::ostringstream out;
    out << method << "\n";
    for (size_t i = 0; i < count && i < segments.size(); ++i) {
        out << "/" << segments[i];
    }
    return out.str();
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

bool route_is_dynamic(const std::vector<std::string>& segments) {
    for (const std::string& segment : segments) {
        if (is_param_segment(segment) || is_path_param_segment(segment)) {
            return true;
        }
    }
    return false;
}

size_t route_static_prefix_count(const std::vector<std::string>& segments) {
    size_t count = 0;
    for (const std::string& segment : segments) {
        if (is_param_segment(segment) || is_path_param_segment(segment)) {
            break;
        }
        ++count;
    }
    return count;
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

void trie_insert(Router* router, size_t route_index);
MatchResult trie_match(Router* router, const std::string& method, const std::vector<std::string>& path);

MatchResult match_one(const Route& route, const std::vector<std::string>& path) {
    MatchResult result{false, -1, route.order, &route, {}};
    int score = 0;
    size_t i = 0;
    size_t j = 0;

    while (i < route.segments.size()) {
        const std::string& part = route.segments[i];
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

    if (i == route.segments.size() && j == path.size()) {
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
    std::vector<std::string> path_segments = split_path(wanted_path);
    MatchResult trie = trie_match(router, wanted_method, path_segments);
    if (trie.matched) {
        return trie;
    }

    auto exact = router->exact_routes.find(route_key(wanted_method, wanted_path));
    if (exact != router->exact_routes.end() && exact->second < router->routes.size()) {
        const Route& route = router->routes[exact->second];
        return MatchResult{true, static_cast<int>(route.segments.size() * 10), route.order, &route, {}};
    }

    for (size_t prefix_len = path_segments.size() + 1; prefix_len > 0; --prefix_len) {
        size_t count = prefix_len - 1;
        auto bucket = router->prefix_routes.find(prefix_key(wanted_method, path_segments, count));
        if (bucket == router->prefix_routes.end()) {
            continue;
        }
        for (size_t route_index : bucket->second) {
            if (route_index >= router->routes.size()) {
                continue;
            }
            const Route& route = router->routes[route_index];
            MatchResult candidate = match_one(route, path_segments);
            if (!candidate.matched) {
                continue;
            }
            bool better_score = candidate.score > best.score;
            bool same_score_earlier = candidate.score == best.score && candidate.order < best.order;
            if (!best.matched || better_score || same_score_earlier) {
                best = candidate;
            }
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

size_t trie_node_create(Router* router) {
    router->trie.emplace_back();
    return router->trie.size() - 1;
}

size_t trie_root(Router* router, const std::string& method) {
    auto found = router->method_roots.find(method);
    if (found != router->method_roots.end()) {
        return found->second;
    }
    size_t root = trie_node_create(router);
    router->method_roots[method] = root;
    return root;
}

void trie_insert(Router* router, size_t route_index) {
    Route& route = router->routes[route_index];
    size_t node_index = trie_root(router, route.method);
    for (const std::string& segment : route.segments) {
        if (is_path_param_segment(segment)) {
            if (router->trie[node_index].path_param == static_cast<size_t>(-1)) {
                size_t child = trie_node_create(router);
                router->trie[node_index].path_param = child;
                router->trie[node_index].path_param_name = param_name(segment);
            }
            node_index = router->trie[node_index].path_param;
            break;
        }
        if (is_param_segment(segment)) {
            if (router->trie[node_index].param == static_cast<size_t>(-1)) {
                size_t child = trie_node_create(router);
                router->trie[node_index].param = child;
                router->trie[node_index].param_name = param_name(segment);
            }
            node_index = router->trie[node_index].param;
            continue;
        }
        auto found = router->trie[node_index].literal.find(segment);
        if (found == router->trie[node_index].literal.end()) {
            size_t child = trie_node_create(router);
            router->trie[node_index].literal[segment] = child;
            node_index = child;
        } else {
            node_index = found->second;
        }
    }
    router->trie[node_index].route_index = route_index;
}

MatchResult trie_match(Router* router, const std::string& method, const std::vector<std::string>& path) {
    MatchResult result{false, -1, 0, nullptr, {}};
    auto root = router->method_roots.find(method);
    if (root == router->method_roots.end()) {
        return result;
    }
    size_t node_index = root->second;
    int score = 0;
    for (size_t i = 0; i < path.size(); ++i) {
        if (node_index >= router->trie.size()) {
            return result;
        }
        Router::TrieNode& node = router->trie[node_index];
        auto literal = node.literal.find(path[i]);
        if (literal != node.literal.end()) {
            node_index = literal->second;
            score += 10;
            continue;
        }
        if (node.param != static_cast<size_t>(-1)) {
            result.params[node.param_name] = path[i];
            node_index = node.param;
            score += 4;
            continue;
        }
        if (node.path_param != static_cast<size_t>(-1)) {
            result.params[node.path_param_name] = join_tail(path, i);
            node_index = node.path_param;
            score += 1;
            break;
        }
        return result;
    }
    if (node_index >= router->trie.size()) {
        return result;
    }
    Router::TrieNode& terminal = router->trie[node_index];
    if (terminal.route_index == static_cast<size_t>(-1) || terminal.route_index >= router->routes.size()) {
        return result;
    }
    const Route& route = router->routes[terminal.route_index];
    result.matched = true;
    result.score = score;
    result.order = route.order;
    result.route = &route;
    return result;
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
    route.segments = split_path(route.path);
    route.dynamic = route_is_dynamic(route.segments);
    route.order = state->next_order++;
    size_t index = state->routes.size();
    state->routes.push_back(route);
    state->method_routes[state->routes[index].method].push_back(index);
    if (!state->routes[index].dynamic) {
        state->exact_routes[route_key(state->routes[index].method, state->routes[index].path)] = index;
    } else {
        size_t prefix_count = route_static_prefix_count(state->routes[index].segments);
        state->prefix_routes[prefix_key(state->routes[index].method, state->routes[index].segments, prefix_count)].push_back(index);
    }
    trie_insert(state, index);
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
    std::vector<std::string> path_segments = split_path(wanted_path);
    std::set<std::string> allowed;

    for (const Route& route : state->routes) {
        MatchResult candidate = match_one(route, path_segments);
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
