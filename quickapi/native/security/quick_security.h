#ifndef QUICKAPI_SECURITY_H
#define QUICKAPI_SECURITY_H

#include <stddef.h>
#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT int quickapi_security_body_allowed(size_t body_size, size_t max_body_size);
QUICKAPI_EXPORT int quickapi_security_content_type_json(const char* content_type);
QUICKAPI_EXPORT int quickapi_security_path_suspicious(const char* path);
QUICKAPI_EXPORT int quickapi_security_payload_suspicious(const char* payload);
QUICKAPI_EXPORT unsigned int quickapi_security_payload_feature_count(const char* payload);
QUICKAPI_EXPORT double quickapi_security_payload_risk_score(const char* path, const char* payload);
QUICKAPI_EXPORT unsigned long long quickapi_security_fingerprint(const char* path, const char* payload);
QUICKAPI_EXPORT unsigned int quickapi_security_fast_scan(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
);
QUICKAPI_EXPORT int quickapi_security_request_allowed(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
);
QUICKAPI_EXPORT const char* quickapi_security_scan_request(
    const char* method,
    const char* path,
    const char* content_type,
    size_t body_size,
    size_t max_body_size,
    const char* payload
);
QUICKAPI_EXPORT const char* quickapi_security_flags_json(unsigned int flags);
QUICKAPI_EXPORT const char* quickapi_security_last_reason(void);

#ifdef __cplusplus
}
#endif

#endif
