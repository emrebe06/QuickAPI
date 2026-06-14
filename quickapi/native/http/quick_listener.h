#ifndef QUICKAPI_LISTENER_H
#define QUICKAPI_LISTENER_H

#include <stddef.h>
#include "../core/quick_core.h"
#include "../core/quick_result.h"
#include "../core/quick_string.h"
#include "../router/quick_router.h"
#include "quick_response.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_listener_exchange {
    int ok;
    int status;
    quickapi_result result;
    quickapi_string_view handler;
    quickapi_string_view path;
    size_t response_size;
    unsigned int security_flags;
} quickapi_listener_exchange;

QUICKAPI_EXPORT quickapi_listener_exchange quickapi_listener_handle_json(
    quickapi_router_t router,
    const char* raw_request,
    size_t raw_request_size,
    quickapi_response_writer* writer,
    size_t max_body_size
);

#ifdef __cplusplus
}
#endif

#endif
