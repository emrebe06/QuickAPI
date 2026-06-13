#include "quick_security.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <set>
#include <vector>

namespace {
thread_local std::string quick_security_reason;

std::string lower_text(const char* value) {
    std::string text = value == nullptr ? "" : value;
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return text;
}

bool contains_any(const std::string& value, const std::vector<std::string>& tokens) {
    for (const std::string& token : tokens) {
        if (value.find(token) != std::string::npos) {
            quick_security_reason = "blocked token: " + token;
            return true;
        }
    }
    return false;
}

unsigned long long fnv1a(const std::string& value) {
    unsigned long long hash = 1469598103934665603ULL;
    for (unsigned char ch : value) {
        hash ^= static_cast<unsigned long long>(ch);
        hash *= 1099511628211ULL;
    }
    return hash;
}

unsigned int count_features(const std::string& value) {
    static const std::vector<std::string> tokens = {
        "<script", "javascript:", "drop table", "union select", "../", "..\\", "%2e", "%2f", "'--", "\"--", " or 1=1"
    };
    unsigned int hits = 0;
    for (const std::string& token : tokens) {
        if (value.find(token) != std::string::npos) {
            ++hits;
        }
    }
    return hits;
}

bool supported_method(const std::string& method) {
    static const std::set<std::string> methods = {
        "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"
    };
    return methods.find(method) != methods.end();
}

std::string upper_text(const char* value) {
    std::string text = value == nullptr ? "" : value;
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
    return text;
}

bool has_control_chars(const std::string& value) {
    for (unsigned char ch : value) {
        if (ch < 32 && ch != '\t' && ch != '\n' && ch != '\r') {
            return true;
        }
    }
    return false;
}

bool looks_encoded_traversal(const std::string& value) {
    return value.find("%2e%2e") != std::string::npos
        || value.find("%252e") != std::string::npos
        || value.find("%5c") != std::string::npos
        || value.find("%2f") != std::string::npos;
}

bool content_type_required(const std::string& method, size_t body_size) {
    return body_size > 0 && method != "GET" && method != "HEAD" && method != "OPTIONS";
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

std::string reasons_json(const std::vector<std::string>& reasons) {
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < reasons.size(); ++i) {
        if (i != 0) {
            out << ",";
        }
        out << "\"" << json_escape(reasons[i]) << "\"";
    }
    out << "]";
    return out.str();
}

std::vector<std::string> scan_reasons(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
) {
    std::vector<std::string> reasons;
    std::string method_text = upper_text(method);
    std::string path_text = lower_text(path);
    std::string payload_text = lower_text(payload);

    if (!supported_method(method_text)) {
        reasons.push_back("unsupported_method");
    }
    if (!quickapi_security_body_allowed(body_size, max_body_size)) {
        reasons.push_back("body_too_large");
    }
    if (content_type_required(method_text, body_size) && !quickapi_security_content_type_json(content_type)) {
        reasons.push_back("invalid_content_type");
    }
    if (path_text.empty() || path_text[0] != '/') {
        reasons.push_back("invalid_path");
    }
    if (has_control_chars(path_text) || has_control_chars(payload_text)) {
        reasons.push_back("control_character");
    }
    if (looks_encoded_traversal(path_text) || looks_encoded_traversal(payload_text)) {
        reasons.push_back("encoded_traversal");
    }
    if (quickapi_security_path_suspicious(path)) {
        reasons.push_back("suspicious_path");
    }
    if (quickapi_security_payload_suspicious(payload)) {
        reasons.push_back("suspicious_payload");
    }
    if (count_features(path_text + " " + payload_text) >= 3) {
        reasons.push_back("multi_signal_payload");
    }
    return reasons;
}
}

int quickapi_security_body_allowed(size_t body_size, size_t max_body_size) {
    return body_size <= max_body_size;
}

int quickapi_security_content_type_json(const char* content_type) {
    if (content_type == nullptr) {
        return 0;
    }
    std::string value = lower_text(content_type);
    return value.find("application/json") != std::string::npos;
}

int quickapi_security_path_suspicious(const char* path) {
    static const std::vector<std::string> tokens = {
        "..", "%2e", "%2f", "\\", "<script", "${"
    };
    quick_security_reason.clear();
    return contains_any(lower_text(path), tokens) ? 1 : 0;
}

int quickapi_security_payload_suspicious(const char* payload) {
    static const std::vector<std::string> tokens = {
        "<script", "javascript:", "drop table", "union select", "../", "..\\"
    };
    quick_security_reason.clear();
    return contains_any(lower_text(payload), tokens) ? 1 : 0;
}

unsigned int quickapi_security_payload_feature_count(const char* payload) {
    quick_security_reason.clear();
    return count_features(lower_text(payload));
}

double quickapi_security_payload_risk_score(const char* path, const char* payload) {
    quick_security_reason.clear();
    std::string combined = lower_text(path) + " " + lower_text(payload);
    unsigned int hits = count_features(combined);
    double score = 0.04 + (0.22 * static_cast<double>(hits));
    if (combined.find("payment") != std::string::npos || combined.find("checkout") != std::string::npos) {
        score += 0.16;
    }
    if (combined.size() > 1024 * 1024) {
        score += 0.12;
    }
    if (score > 0.99) {
        score = 0.99;
    }
    return score;
}

unsigned long long quickapi_security_fingerprint(const char* path, const char* payload) {
    quick_security_reason.clear();
    return fnv1a(lower_text(path) + "\n" + lower_text(payload));
}

int quickapi_security_request_allowed(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
) {
    std::vector<std::string> reasons = scan_reasons(method, path, content_type, body_size, max_body_size, payload);
    quick_security_reason = reasons.empty() ? "" : reasons.front();
    return reasons.empty() ? 1 : 0;
}

const char* quickapi_security_scan_request(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
) {
    std::vector<std::string> reasons = scan_reasons(method, path, content_type, body_size, max_body_size, payload);
    double score = quickapi_security_payload_risk_score(path, payload);
    if (!reasons.empty()) {
        score += 0.12 * static_cast<double>(reasons.size());
    }
    if (score > 0.99) {
        score = 0.99;
    }
    bool allowed = reasons.empty() && score < 0.80;
    quick_security_reason = reasons.empty() ? "" : reasons.front();

    std::ostringstream out;
    out << "{";
    out << "\"allowed\":" << (allowed ? "true" : "false") << ",";
    out << "\"risk_score\":" << score << ",";
    out << "\"reasons\":" << reasons_json(reasons) << ",";
    out << "\"fingerprint\":" << quickapi_security_fingerprint(path, payload);
    out << "}";
    quick_security_reason = out.str();
    return quick_security_reason.c_str();
}

const char* quickapi_security_last_reason(void) {
    return quick_security_reason.c_str();
}
