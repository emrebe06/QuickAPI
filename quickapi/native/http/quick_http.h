#ifndef QUICKAPI_HTTP_H
#define QUICKAPI_HTTP_H

#include <stddef.h>
#include "../core/quick_core.h"
#include "../core/quick_result.h"
#include "../core/quick_string.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_http_request_parse {
    int ok;
    quickapi_result result;
    quickapi_string_view method;
    quickapi_string_view target;
    quickapi_string_view path;
    quickapi_string_view query;
    quickapi_string_view version;
    quickapi_string_view headers;
    quickapi_string_view body;
    size_t header_count;
    size_t content_length;
    int keep_alive;
} quickapi_http_request_parse;

QUICKAPI_EXPORT const char* quickapi_http_status_code_name(int status);
QUICKAPI_EXPORT const char* quickapi_http_status_message(int status);
QUICKAPI_EXPORT int quickapi_http_method_supported(const char* method);
QUICKAPI_EXPORT quickapi_http_request_parse quickapi_http_parse_request(const char* data, size_t size, size_t max_headers, size_t max_body_size);
QUICKAPI_EXPORT quickapi_string_view quickapi_http_header_value(quickapi_http_request_parse request, const char* name);
QUICKAPI_EXPORT int quickapi_http_request_should_keep_alive(quickapi_http_request_parse request);
QUICKAPI_EXPORT const char* quickapi_http_parse_error(quickapi_http_request_parse request);

#ifdef __cplusplus
}
#endif

#endif
