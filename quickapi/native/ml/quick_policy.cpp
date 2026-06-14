#include "quick_policy.h"

#include <sstream>
#include <string>

namespace {
thread_local std::string policy_buffer;

unsigned int popcount(unsigned int value) {
    unsigned int count = 0;
    while (value) {
        count += value & 1u;
        value >>= 1u;
    }
    return count;
}

double clamp_score(double value) {
    if (value < 0.0) return 0.0;
    if (value > 0.99) return 0.99;
    return value;
}
}

quickapi_policy_action quickapi_policy_decide(double risk_score, unsigned int security_flags, unsigned int route_sensitivity) {
    double score = clamp_score(risk_score);
    unsigned int signals = popcount(security_flags);
    if (route_sensitivity > 10u) {
        route_sensitivity = 10u;
    }
    score += static_cast<double>(route_sensitivity) * 0.025;
    if (signals >= 3) {
        score += 0.18;
    } else if (signals == 2) {
        score += 0.10;
    } else if (signals == 1) {
        score += 0.05;
    }
    score = clamp_score(score);

    if (score >= 0.88 || signals >= 5) {
        return QUICKAPI_POLICY_BLOCK;
    }
    if (score >= 0.72 || signals >= 3) {
        return QUICKAPI_POLICY_CHALLENGE;
    }
    if (score >= 0.45 || signals >= 1) {
        return QUICKAPI_POLICY_OBSERVE;
    }
    return QUICKAPI_POLICY_ALLOW;
}

const char* quickapi_policy_action_name(quickapi_policy_action action) {
    switch (action) {
    case QUICKAPI_POLICY_ALLOW:
        return "allow";
    case QUICKAPI_POLICY_OBSERVE:
        return "observe";
    case QUICKAPI_POLICY_CHALLENGE:
        return "challenge";
    case QUICKAPI_POLICY_BLOCK:
        return "block";
    default:
        return "unknown";
    }
}

const char* quickapi_policy_decision_json(double risk_score, unsigned int security_flags, unsigned int route_sensitivity) {
    quickapi_policy_action action = quickapi_policy_decide(risk_score, security_flags, route_sensitivity);
    unsigned int signals = popcount(security_flags);
    std::ostringstream out;
    out << "{";
    out << "\"action\":\"" << quickapi_policy_action_name(action) << "\",";
    out << "\"risk_score\":" << clamp_score(risk_score) << ",";
    out << "\"security_flags\":" << security_flags << ",";
    out << "\"signal_count\":" << signals << ",";
    out << "\"route_sensitivity\":" << route_sensitivity << ",";
    out << "\"engine\":\"native-policy-v1\"";
    out << "}";
    policy_buffer = out.str();
    return policy_buffer.c_str();
}
