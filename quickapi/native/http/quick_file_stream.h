#ifndef QUICKAPI_FILE_STREAM_H
#define QUICKAPI_FILE_STREAM_H

#include <stddef.h>
#include "../core/quick_core.h"
#include "../core/quick_result.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_file_stream quickapi_file_stream;

QUICKAPI_EXPORT quickapi_file_stream* quickapi_file_stream_open(const char* path, size_t chunk_size);
QUICKAPI_EXPORT void quickapi_file_stream_close(quickapi_file_stream* stream);
QUICKAPI_EXPORT quickapi_result quickapi_file_stream_read(quickapi_file_stream* stream);
QUICKAPI_EXPORT const char* quickapi_file_stream_chunk(const quickapi_file_stream* stream);
QUICKAPI_EXPORT size_t quickapi_file_stream_chunk_size(const quickapi_file_stream* stream);
QUICKAPI_EXPORT unsigned long long quickapi_file_stream_total_read(const quickapi_file_stream* stream);

#ifdef __cplusplus
}
#endif

#endif
