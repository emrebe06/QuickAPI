#ifndef QUICKAPI_RESPONSE_H
#define QUICKAPI_RESPONSE_H

#include "../core/quick_buffer.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_response_writer quickapi_response_writer;

QUICKAPI_EXPORT quickapi_response_writer* quickapi_response_writer_create(size_t max_bytes);
QUICKAPI_EXPORT void quickapi_response_writer_destroy(quickapi_response_writer* writer);
QUICKAPI_EXPORT void quickapi_response_writer_reset(quickapi_response_writer* writer);
QUICKAPI_EXPORT quickapi_result quickapi_response_writer_status(quickapi_response_writer* writer, int status);
QUICKAPI_EXPORT quickapi_result quickapi_response_writer_header(quickapi_response_writer* writer, const char* key, const char* value);
QUICKAPI_EXPORT quickapi_result quickapi_response_writer_body(quickapi_response_writer* writer, const char* data, size_t size);
QUICKAPI_EXPORT quickapi_result quickapi_response_writer_json(quickapi_response_writer* writer, int status, const char* json_body, int keep_alive);
QUICKAPI_EXPORT quickapi_result quickapi_response_writer_error_json(quickapi_response_writer* writer, int status, const char* code, const char* message, int keep_alive);
QUICKAPI_EXPORT const char* quickapi_response_writer_data(const quickapi_response_writer* writer);
QUICKAPI_EXPORT size_t quickapi_response_writer_size(const quickapi_response_writer* writer);

#ifdef __cplusplus
}
#endif

#endif
