#ifndef QUICKAPI_ROUTER_H
#define QUICKAPI_ROUTER_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef void* quickapi_router_t;

QUICKAPI_EXPORT quickapi_router_t quickapi_router_create(void);
QUICKAPI_EXPORT void quickapi_router_destroy(quickapi_router_t router);
QUICKAPI_EXPORT int quickapi_router_add(quickapi_router_t router, const char* method, const char* path, const char* handler_name);
QUICKAPI_EXPORT const char* quickapi_router_match(quickapi_router_t router, const char* method, const char* path);
QUICKAPI_EXPORT int quickapi_router_match_score(quickapi_router_t router, const char* method, const char* path);
QUICKAPI_EXPORT const char* quickapi_router_params(quickapi_router_t router, const char* method, const char* path);
QUICKAPI_EXPORT const char* quickapi_router_allowed_methods(quickapi_router_t router, const char* path);

#ifdef __cplusplus
}
#endif

#endif
