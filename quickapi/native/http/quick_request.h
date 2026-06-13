#ifndef QUICKAPI_REQUEST_H
#define QUICKAPI_REQUEST_H

#include <stddef.h>
#include "../core/quick_core.h"
#include "../core/quick_string.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_request_view {
    quickapi_string_view method;
    quickapi_string_view path;
    quickapi_string_view query;
    quickapi_string_view body;
    quickapi_string_view ip;
} quickapi_request_view;

QUICKAPI_EXPORT quickapi_request_view quickapi_request_view_make(
    const char* method,
    const char* path,
    const char* query,
    const char* body,
    const char* ip
);
QUICKAPI_EXPORT int quickapi_request_view_valid(quickapi_request_view request);
QUICKAPI_EXPORT size_t quickapi_request_view_body_size(quickapi_request_view request);
QUICKAPI_EXPORT size_t quickapi_request_view_path_depth(quickapi_request_view request);

#ifdef __cplusplus
}
#endif

#endif
