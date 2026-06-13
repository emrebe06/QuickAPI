#include "quick_response.h"
#include "quick_http.h"

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

const char* quickapi_response_writer_data(const quickapi_response_writer* writer) {
    return writer && writer->buffer ? quickapi_buffer_data(writer->buffer) : "";
}

size_t quickapi_response_writer_size(const quickapi_response_writer* writer) {
    return writer && writer->buffer ? quickapi_buffer_size(writer->buffer) : 0;
}
