#include "quick_json_writer.h"

#include <string>

quickapi_result quickapi_json_writer_escape(quickapi_buffer* buffer, const char* text) {
    quickapi_result result = quickapi_buffer_append_cstr(buffer, "\"");
    if (!result.ok) return result;
    if (text) {
        for (const char* cursor = text; *cursor; ++cursor) {
            switch (*cursor) {
                case '"': result = quickapi_buffer_append_cstr(buffer, "\\\""); break;
                case '\\': result = quickapi_buffer_append_cstr(buffer, "\\\\"); break;
                case '\n': result = quickapi_buffer_append_cstr(buffer, "\\n"); break;
                case '\r': result = quickapi_buffer_append_cstr(buffer, "\\r"); break;
                case '\t': result = quickapi_buffer_append_cstr(buffer, "\\t"); break;
                default: result = quickapi_buffer_append(buffer, cursor, 1); break;
            }
            if (!result.ok) return result;
        }
    }
    return quickapi_buffer_append_cstr(buffer, "\"");
}

quickapi_result quickapi_json_writer_field(quickapi_buffer* buffer, const char* key, const char* value, int comma) {
    quickapi_result result;
    if (comma) {
        result = quickapi_buffer_append_cstr(buffer, ",");
        if (!result.ok) return result;
    }
    result = quickapi_json_writer_escape(buffer, key);
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(buffer, ":");
    if (!result.ok) return result;
    return quickapi_json_writer_escape(buffer, value);
}

const char* quickapi_json_writer_success(int status, const char* code, const char* message, const char* data_json) {
    thread_local std::string out;
    quickapi_buffer* buffer = quickapi_buffer_create(512, 1024 * 1024);
    if (!buffer) {
        out = "{\"ok\":false,\"status\":500,\"code\":\"NATIVE_OOM\"}";
        return out.c_str();
    }
    quickapi_buffer_append_cstr(buffer, "{\"ok\":true,\"status\":");
    std::string status_text = std::to_string(status);
    quickapi_buffer_append(buffer, status_text.c_str(), status_text.size());
    quickapi_json_writer_field(buffer, "code", code ? code : "OK", 1);
    quickapi_json_writer_field(buffer, "message", message ? message : "Success", 1);
    quickapi_buffer_append_cstr(buffer, ",\"data\":");
    quickapi_buffer_append_cstr(buffer, data_json ? data_json : "null");
    quickapi_buffer_append_cstr(buffer, ",\"error\":null,\"meta\":{}}");
    out = quickapi_buffer_data(buffer);
    quickapi_buffer_destroy(buffer);
    return out.c_str();
}
