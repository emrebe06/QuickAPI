#include "quick_json_writer.h"

#include <string>

quickapi_result quickapi_json_writer_escape(quickapi_buffer* buffer, const char* text) {
    quickapi_result result = quickapi_buffer_append_char(buffer, '"');
    if (!result.ok) return result;
    if (text) {
        for (const char* cursor = text; *cursor; ++cursor) {
            switch (*cursor) {
                case '"': result = quickapi_buffer_append_cstr(buffer, "\\\""); break;
                case '\\': result = quickapi_buffer_append_cstr(buffer, "\\\\"); break;
                case '\n': result = quickapi_buffer_append_cstr(buffer, "\\n"); break;
                case '\r': result = quickapi_buffer_append_cstr(buffer, "\\r"); break;
                case '\t': result = quickapi_buffer_append_cstr(buffer, "\\t"); break;
                default: result = quickapi_buffer_append_char(buffer, *cursor); break;
            }
            if (!result.ok) return result;
        }
    }
    return quickapi_buffer_append_char(buffer, '"');
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

quickapi_result quickapi_json_writer_success_into(quickapi_buffer* buffer, int status, const char* code, const char* message, const char* data_json) {
    if (!buffer) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid json writer buffer");
    }
    quickapi_buffer_clear(buffer);
    quickapi_result result = quickapi_buffer_append_cstr(buffer, "{\"ok\":true,\"status\":");
    if (!result.ok) return result;
    std::string status_text = std::to_string(status);
    result = quickapi_buffer_append(buffer, status_text.c_str(), status_text.size());
    if (!result.ok) return result;
    result = quickapi_json_writer_field(buffer, "code", code ? code : "OK", 1);
    if (!result.ok) return result;
    result = quickapi_json_writer_field(buffer, "message", message ? message : "Success", 1);
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(buffer, ",\"data\":");
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(buffer, data_json ? data_json : "null");
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(buffer, ",\"error\":null,\"meta\":{}}");
    if (!result.ok) return result;
    return quickapi_result_ok(quickapi_buffer_size(buffer));
}

const char* quickapi_json_writer_success(int status, const char* code, const char* message, const char* data_json) {
    thread_local std::string out;
    quickapi_buffer* buffer = quickapi_buffer_create(512, 1024 * 1024);
    if (!buffer) {
        out = "{\"ok\":false,\"status\":500,\"code\":\"NATIVE_OOM\"}";
        return out.c_str();
    }
    quickapi_result result = quickapi_json_writer_success_into(buffer, status, code, message, data_json);
    out = result.ok ? quickapi_buffer_data(buffer) : "{\"ok\":false,\"status\":500,\"code\":\"NATIVE_JSON_WRITE_FAILED\"}";
    quickapi_buffer_destroy(buffer);
    return out.c_str();
}
