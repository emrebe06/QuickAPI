#ifndef QUICKAPI_JSON_WRITER_H
#define QUICKAPI_JSON_WRITER_H

#include "../core/quick_buffer.h"

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT quickapi_result quickapi_json_writer_escape(quickapi_buffer* buffer, const char* text);
QUICKAPI_EXPORT quickapi_result quickapi_json_writer_field(quickapi_buffer* buffer, const char* key, const char* value, int comma);
QUICKAPI_EXPORT const char* quickapi_json_writer_success(int status, const char* code, const char* message, const char* data_json);

#ifdef __cplusplus
}
#endif

#endif
