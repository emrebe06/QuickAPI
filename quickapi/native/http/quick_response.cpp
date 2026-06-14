#include "quick_response.h"
#include "quick_http.h"

#include <cstring>
#include <string>

struct quickapi_response_writer {
    quickapi_buffer* buffer;
    int status;
};

quickapi_response_writer* quickapi_response_writer_create(size_t max_bytes) {
    if (max_bytes == 0) {
        max_bytes = 1024 * 1024;
    }
    quickapi_response_writer* writer = new quickapi_response_writer;
    writer->buffer = quickapi_buffer_create(512, max_bytes);
    writer->status = 200;
    if (!writer->buffer) {
        delete writer;
        return nullptr;
    }
    return writer;
}

void quickapi_response_writer_destroy(quickapi_response_writer* writer) {
    if (!writer) return;
    quickapi_buffer_destroy(writer->buffer);
    delete writer;
}

void quickapi_response_writer_reset(quickapi_response_writer* writer) {
    if (!writer || !writer->buffer) {
        return;
    }
    writer->status = 200;
    quickapi_buffer_clear(writer->buffer);
}

quickapi_result quickapi_response_writer_status(quickapi_response_writer* writer, int status) {
    if (!writer || !writer->buffer) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid response writer");
    }
    writer->status = status;
    quickapi_buffer_clear(writer->buffer);
    quickapi_result result = quickapi_buffer_append_cstr(writer->buffer, "HTTP/1.1 ");
    if (!result.ok) return result;
    std::string status_text = std::to_string(status);
    result = quickapi_buffer_append(writer->buffer, status_text.c_str(), status_text.size());
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(writer->buffer, " ");
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(writer->buffer, quickapi_http_status_message(status));
    if (!result.ok) return result;
    return quickapi_buffer_append_cstr(writer->buffer, "\r\n");
}

quickapi_result quickapi_response_writer_header(quickapi_response_writer* writer, const char* key, const char* value) {
    if (!writer || !writer->buffer || !key || !value) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid response header");
    }
    quickapi_result result = quickapi_buffer_append_cstr(writer->buffer, key);
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(writer->buffer, ": ");
    if (!result.ok) return result;
    result = quickapi_buffer_append_cstr(writer->buffer, value);
    if (!result.ok) return result;
    return quickapi_buffer_append_cstr(writer->buffer, "\r\n");
}

quickapi_result quickapi_response_writer_body(quickapi_response_writer* writer, const char* data, size_t size) {
    if (!writer || !writer->buffer) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid response body");
    }
    quickapi_result result = quickapi_buffer_append_cstr(writer->buffer, "\r\n");
    if (!result.ok) return result;
    return quickapi_buffer_append(writer->buffer, data, size);
}

quickapi_result quickapi_response_writer_json(quickapi_response_writer* writer, int status, const char* json_body, int keep_alive) {
    if (!writer || !writer->buffer) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid response writer");
    }
    const char* body = json_body ? json_body : "null";
    size_t body_size = std::strlen(body);
    quickapi_result result = quickapi_response_writer_status(writer, status);
    if (!result.ok) return result;
    result = quickapi_response_writer_header(writer, "Content-Type", "application/json; charset=utf-8");
    if (!result.ok) return result;
    std::string length = std::to_string(body_size);
    result = quickapi_response_writer_header(writer, "Content-Length", length.c_str());
    if (!result.ok) return result;
    result = quickapi_response_writer_header(writer, "Connection", keep_alive ? "keep-alive" : "close");
    if (!result.ok) return result;
    return quickapi_response_writer_body(writer, body, body_size);
}

quickapi_result quickapi_response_writer_error_json(quickapi_response_writer* writer, int status, const char* code, const char* message, int keep_alive) {
    if (!writer || !writer->buffer) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid response writer");
    }
    const char* safe_code = code ? code : quickapi_http_status_code_name(status);
    const char* safe_message = message ? message : quickapi_http_status_message(status);
    std::string body = "{\"ok\":false,\"status\":";
    body += std::to_string(status);
    body += ",\"code\":\"";
    body += safe_code;
    body += "\",\"message\":\"";
    body += safe_message;
    body += "\",\"data\":null,\"error\":{\"type\":\"native_http_error\",\"detail\":\"";
    body += safe_message;
    body += "\"},\"meta\":{\"engine\":\"quickapi-native\"}}";
    return quickapi_response_writer_json(writer, status, body.c_str(), keep_alive);
}

const char* quickapi_response_writer_data(const quickapi_response_writer* writer) {
    return writer && writer->buffer ? quickapi_buffer_data(writer->buffer) : "";
}

size_t quickapi_response_writer_size(const quickapi_response_writer* writer) {
    return writer && writer->buffer ? quickapi_buffer_size(writer->buffer) : 0;
}
