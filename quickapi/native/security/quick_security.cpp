#include "quick_security.h"

#include <algorithm>
#include <cctype>
#include <string>
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

const char* quickapi_security_last_reason(void) {
    return quick_security_reason.c_str();
}
