#include "quick_validation.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <vector>

namespace {
thread_local std::string quick_validation_buffer;

std::string json_escape(const std::string& value) {
    std::ostringstream out;
    for (char ch : value) {
        switch (ch) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default: out << ch; break;
        }
    }
    return out.str();
}

bool suspicious_key(const std::string& key) {
    std::string lowered = key;
    std::transform(lowered.begin(), lowered.end(), lowered.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    static const std::vector<std::string> tokens = {
        "__proto__", "constructor", "prototype", "$where", "$ne", "$gt", "$lt", "$regex",
        "password", "passwd", "secret", "api_key", "access_token", "private_key"
    };
    for (const std::string& token : tokens) {
        if (lowered.find(token) != std::string::npos) {
            return true;
        }
    }
    return false;
}

std::vector<std::string> flag_names(unsigned int flags) {
    std::vector<std::string> names;
    if (flags & QUICKAPI_VALIDATION_CONTROL_CHARACTER) names.push_back("control_character");
    if (flags & QUICKAPI_VALIDATION_DEPTH_EXCEEDED) names.push_back("depth_exceeded");
    if (flags & QUICKAPI_VALIDATION_STRING_TOO_LONG) names.push_back("string_too_long");
    if (flags & QUICKAPI_VALIDATION_ARRAY_TOO_LONG) names.push_back("array_too_long");
    if (flags & QUICKAPI_VALIDATION_OBJECT_TOO_WIDE) names.push_back("object_too_wide");
    if (flags & QUICKAPI_VALIDATION_UNBALANCED_JSON) names.push_back("unbalanced_json");
    if (flags & QUICKAPI_VALIDATION_SUSPICIOUS_KEY) names.push_back("suspicious_key");
    if (flags & QUICKAPI_VALIDATION_BINARY_PAYLOAD) names.push_back("binary_payload");
    return names;
}

std::string names_json(const std::vector<std::string>& names) {
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < names.size(); ++i) {
        if (i != 0) out << ",";
        out << "\"" << json_escape(names[i]) << "\"";
    }
    out << "]";
    return out.str();
}

struct PayloadStats {
    unsigned int flags = QUICKAPI_VALIDATION_OK;
    size_t max_seen_depth = 0;
    size_t max_seen_string = 0;
    size_t estimated_array_items = 0;
    size_t estimated_object_keys = 0;
    size_t control_chars = 0;
    size_t binary_chars = 0;
};

PayloadStats scan_payload(
    const char* payload,
    size_t payload_size,
    size_t max_depth,
    size_t max_string_length,
    size_t max_array_length,
    size_t max_object_keys
) {
    PayloadStats stats;
    if (!payload || payload_size == 0) {
        return stats;
    }

    bool in_string = false;
    bool escaped = false;
    bool collecting_key = false;
    std::string key_buffer;
    size_t current_string = 0;
    size_t depth = 0;
    size_t square_depth = 0;
    size_t curly_depth = 0;

    for (size_t i = 0; i < payload_size; ++i) {
        unsigned char ch = static_cast<unsigned char>(payload[i]);
        if (ch == 0) {
            stats.flags |= QUICKAPI_VALIDATION_BINARY_PAYLOAD;
            ++stats.binary_chars;
            continue;
        }
        if (ch < 32 && ch != '\n' && ch != '\r' && ch != '\t') {
            stats.flags |= QUICKAPI_VALIDATION_CONTROL_CHARACTER;
            ++stats.control_chars;
        }

        if (in_string) {
            if (escaped) {
                escaped = false;
                ++current_string;
                if (collecting_key && key_buffer.size() < 128) key_buffer.push_back(static_cast<char>(ch));
                continue;
            }
            if (ch == '\\') {
                escaped = true;
                ++current_string;
                continue;
            }
            if (ch == '"') {
                in_string = false;
                stats.max_seen_string = std::max(stats.max_seen_string, current_string);
                if (current_string > max_string_length) {
                    stats.flags |= QUICKAPI_VALIDATION_STRING_TOO_LONG;
                }
                if (collecting_key && suspicious_key(key_buffer)) {
                    stats.flags |= QUICKAPI_VALIDATION_SUSPICIOUS_KEY;
                }
                collecting_key = false;
                key_buffer.clear();
                current_string = 0;
                continue;
            }
            ++current_string;
            if (collecting_key && key_buffer.size() < 128) key_buffer.push_back(static_cast<char>(ch));
            continue;
        }

        if (ch == '"') {
            in_string = true;
            escaped = false;
            current_string = 0;
            size_t cursor = i + 1;
            bool maybe_key = false;
            bool local_escape = false;
            while (cursor < payload_size) {
                unsigned char next = static_cast<unsigned char>(payload[cursor]);
                if (local_escape) {
                    local_escape = false;
                } else if (next == '\\') {
                    local_escape = true;
                } else if (next == '"') {
                    size_t after = cursor + 1;
                    while (after < payload_size && std::isspace(static_cast<unsigned char>(payload[after]))) ++after;
                    maybe_key = after < payload_size && payload[after] == ':';
                    break;
                }
                ++cursor;
            }
            collecting_key = maybe_key;
            continue;
        }

        if (ch == '{') {
            ++curly_depth;
            ++depth;
            stats.max_seen_depth = std::max(stats.max_seen_depth, depth);
            if (depth > max_depth) stats.flags |= QUICKAPI_VALIDATION_DEPTH_EXCEEDED;
        } else if (ch == '[') {
            ++square_depth;
            ++depth;
            stats.max_seen_depth = std::max(stats.max_seen_depth, depth);
            if (depth > max_depth) stats.flags |= QUICKAPI_VALIDATION_DEPTH_EXCEEDED;
        } else if (ch == '}') {
            if (curly_depth == 0 || depth == 0) {
                stats.flags |= QUICKAPI_VALIDATION_UNBALANCED_JSON;
            } else {
                --curly_depth;
                --depth;
            }
        } else if (ch == ']') {
            if (square_depth == 0 || depth == 0) {
                stats.flags |= QUICKAPI_VALIDATION_UNBALANCED_JSON;
            } else {
                --square_depth;
                --depth;
            }
        } else if (ch == ',') {
            if (square_depth > 0) {
                ++stats.estimated_array_items;
                if (stats.estimated_array_items > max_array_length) {
                    stats.flags |= QUICKAPI_VALIDATION_ARRAY_TOO_LONG;
                }
            }
        } else if (ch == ':') {
            if (curly_depth > 0) {
                ++stats.estimated_object_keys;
                if (stats.estimated_object_keys > max_object_keys) {
                    stats.flags |= QUICKAPI_VALIDATION_OBJECT_TOO_WIDE;
                }
            }
        }
    }

    if (in_string || curly_depth != 0 || square_depth != 0) {
        stats.flags |= QUICKAPI_VALIDATION_UNBALANCED_JSON;
    }
    return stats;
}
}

unsigned int quickapi_validation_payload_flags(
    const char* payload,
    size_t payload_size,
    size_t max_depth,
    size_t max_string_length,
    size_t max_array_length,
    size_t max_object_keys
) {
    PayloadStats stats = scan_payload(
        payload,
        payload_size,
        max_depth,
        max_string_length,
        max_array_length,
        max_object_keys
    );
    return stats.flags;
}

const char* quickapi_validation_payload_json(
    const char* payload,
    size_t payload_size,
    size_t max_depth,
    size_t max_string_length,
    size_t max_array_length,
    size_t max_object_keys
) {
    PayloadStats stats = scan_payload(
        payload,
        payload_size,
        max_depth,
        max_string_length,
        max_array_length,
        max_object_keys
    );
    std::vector<std::string> names = flag_names(stats.flags);
    std::ostringstream out;
    out << "{";
    out << "\"ok\":" << (stats.flags == QUICKAPI_VALIDATION_OK ? "true" : "false") << ",";
    out << "\"flags\":" << stats.flags << ",";
    out << "\"signals\":" << names_json(names) << ",";
    out << "\"stats\":{";
    out << "\"max_depth\":" << stats.max_seen_depth << ",";
    out << "\"max_string_length\":" << stats.max_seen_string << ",";
    out << "\"estimated_array_items\":" << stats.estimated_array_items << ",";
    out << "\"estimated_object_keys\":" << stats.estimated_object_keys << ",";
    out << "\"control_chars\":" << stats.control_chars << ",";
    out << "\"binary_chars\":" << stats.binary_chars;
    out << "},";
    out << "\"engine\":\"native-validation-v1\"";
    out << "}";
    quick_validation_buffer = out.str();
    return quick_validation_buffer.c_str();
}

const char* quickapi_validation_flags_json(unsigned int flags) {
    std::ostringstream out;
    std::vector<std::string> names = flag_names(flags);
    out << "{\"ok\":" << (flags == QUICKAPI_VALIDATION_OK ? "true" : "false")
        << ",\"flags\":" << flags
        << ",\"signals\":" << names_json(names)
        << ",\"engine\":\"native-validation-v1\"}";
    quick_validation_buffer = out.str();
    return quick_validation_buffer.c_str();
}
