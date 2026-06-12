#ifndef QUICKAPI_HTTP_H
#define QUICKAPI_HTTP_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT const char* quickapi_http_status_code_name(int status);
QUICKAPI_EXPORT const char* quickapi_http_status_message(int status);
QUICKAPI_EXPORT int quickapi_http_method_supported(const char* method);

#ifdef __cplusplus
}
#endif

#endif
