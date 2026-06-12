#include "quick_http.h"

#include <algorithm>
#include <cctype>
#include <string>

namespace {
std::string upper(const char* value) {
    std::string out = value == nullptr ? "" : value;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
    return out;
}
}

const char* quickapi_http_status_code_name(int status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "CREATED";
        case 202: return "ACCEPTED";
        case 204: return "NO_CONTENT";
        case 400: return "BAD_REQUEST";
        case 401: return "UNAUTHORIZED";
        case 402: return "PAYMENT_REQUIRED";
        case 403: return "FORBIDDEN";
        case 404: return "NOT_FOUND";
        case 405: return "METHOD_NOT_ALLOWED";
        case 409: return "CONFLICT";
        case 413: return "PAYLOAD_TOO_LARGE";
        case 415: return "UNSUPPORTED_MEDIA_TYPE";
        case 422: return "VALIDATION_ERROR";
        case 429: return "TOO_MANY_REQUESTS";
        case 500: return "INTERNAL_SERVER_ERROR";
        case 502: return "BAD_GATEWAY";
        case 503: return "SERVICE_UNAVAILABLE";
        case 504: return "GATEWAY_TIMEOUT";
        default: return "UNKNOWN";
    }
}

const char* quickapi_http_status_message(int status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "Created";
        case 202: return "Accepted";
        case 204: return "No content";
        case 400: return "Bad request";
        case 401: return "Unauthorized";
        case 402: return "Payment required";
        case 403: return "Forbidden";
        case 404: return "Not found";
        case 405: return "Method not allowed";
        case 409: return "Conflict";
        case 413: return "Payload too large";
        case 415: return "Unsupported media type";
        case 422: return "Validation error";
        case 429: return "Too many requests";
        case 500: return "Internal server error";
        case 502: return "Bad gateway";
        case 503: return "Service unavailable";
        case 504: return "Gateway timeout";
        default: return "Unknown";
    }
}

int quickapi_http_method_supported(const char* method) {
    std::string value = upper(method);
    return value == "GET" || value == "POST" || value == "PUT" || value == "PATCH" || value == "DELETE" || value == "OPTIONS";
}
