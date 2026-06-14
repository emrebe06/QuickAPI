#include "quick_plugin.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <vector>

namespace {
thread_local std::string quick_plugin_buffer;

std::string lower(const char* value) {
    std::string text = value ? value : "";
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return text;
}

std::string escape_json(const char* value) {
    std::ostringstream out;
    for (const char* cursor = value ? value : ""; *cursor; ++cursor) {
        switch (*cursor) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default: out << *cursor; break;
        }
    }
    return out.str();
}

std::vector<const char*> permission_names(unsigned int permissions) {
    std::vector<const char*> names;
    if (permissions & QUICKAPI_PLUGIN_FILE_READ) names.push_back("file:read");
    if (permissions & QUICKAPI_PLUGIN_FILE_WRITE) names.push_back("file:write");
    if (permissions & QUICKAPI_PLUGIN_NETWORK) names.push_back("network");
    if (permissions & QUICKAPI_PLUGIN_SHELL) names.push_back("shell");
    if (permissions & QUICKAPI_PLUGIN_LLM) names.push_back("llm");
    if (permissions & QUICKAPI_PLUGIN_DATABASE) names.push_back("database");
    if (permissions & QUICKAPI_PLUGIN_AUTOMATION) names.push_back("automation");
    return names;
}
}

unsigned int quickapi_plugin_permission_from_name(const char* name) {
    std::string text = lower(name);
    if (text == "file:read") return QUICKAPI_PLUGIN_FILE_READ;
    if (text == "file:write") return QUICKAPI_PLUGIN_FILE_WRITE;
    if (text == "network") return QUICKAPI_PLUGIN_NETWORK;
    if (text == "shell") return QUICKAPI_PLUGIN_SHELL;
    if (text == "llm") return QUICKAPI_PLUGIN_LLM;
    if (text == "database") return QUICKAPI_PLUGIN_DATABASE;
    if (text == "automation") return QUICKAPI_PLUGIN_AUTOMATION;
    return 0;
}

int quickapi_plugin_manifest_valid(quickapi_plugin_manifest manifest) {
    if (!manifest.name || !*manifest.name) {
        return 0;
    }
    if (manifest.max_runtime_ms > 0 && manifest.max_runtime_ms < 10) {
        return 0;
    }
    if (manifest.max_memory_mb > 0 && manifest.max_memory_mb < 4) {
        return 0;
    }
    return 1;
}

const char* quickapi_plugin_manifest_json(quickapi_plugin_manifest manifest) {
    std::ostringstream out;
    out << "{";
    out << "\"valid\":" << (quickapi_plugin_manifest_valid(manifest) ? "true" : "false") << ",";
    out << "\"name\":\"" << escape_json(manifest.name) << "\",";
    out << "\"version\":\"" << escape_json(manifest.version ? manifest.version : "0.1.0") << "\",";
    out << "\"max_runtime_ms\":" << manifest.max_runtime_ms << ",";
    out << "\"max_memory_mb\":" << manifest.max_memory_mb << ",";
    out << "\"permissions\":[";
    std::vector<const char*> names = permission_names(manifest.permissions);
    for (size_t i = 0; i < names.size(); ++i) {
        if (i != 0) out << ",";
        out << "\"" << names[i] << "\"";
    }
    out << "]}";
    quick_plugin_buffer = out.str();
    return quick_plugin_buffer.c_str();
}

int quickapi_plugin_permission_allowed(unsigned int granted, unsigned int required) {
    return (granted & required) == required ? 1 : 0;
}
