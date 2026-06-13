#include "quick_file_stream.h"

#include <cstdio>
#include <cstdlib>
#include <new>

struct quickapi_file_stream {
    FILE* file;
    char* chunk;
    size_t chunk_size;
    size_t last_read;
    unsigned long long total_read;
};

quickapi_file_stream* quickapi_file_stream_open(const char* path, size_t chunk_size) {
    if (!path) return nullptr;
    if (chunk_size == 0) chunk_size = 1024 * 256;
    quickapi_file_stream* stream = new (std::nothrow) quickapi_file_stream;
    if (!stream) return nullptr;
    stream->file = std::fopen(path, "rb");
    if (!stream->file) {
        delete stream;
        return nullptr;
    }
    stream->chunk = static_cast<char*>(std::malloc(chunk_size));
    if (!stream->chunk) {
        std::fclose(stream->file);
        delete stream;
        return nullptr;
    }
    stream->chunk_size = chunk_size;
    stream->last_read = 0;
    stream->total_read = 0;
    return stream;
}

void quickapi_file_stream_close(quickapi_file_stream* stream) {
    if (!stream) return;
    if (stream->file) std::fclose(stream->file);
    std::free(stream->chunk);
    delete stream;
}

quickapi_result quickapi_file_stream_read(quickapi_file_stream* stream) {
    if (!stream || !stream->file || !stream->chunk) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid file stream");
    }
    stream->last_read = std::fread(stream->chunk, 1, stream->chunk_size, stream->file);
    stream->total_read += stream->last_read;
    if (stream->last_read == 0 && std::ferror(stream->file)) {
        return quickapi_result_error(QUICKAPI_ERROR_IO, "file read failed");
    }
    return quickapi_result_ok(stream->last_read);
}

const char* quickapi_file_stream_chunk(const quickapi_file_stream* stream) {
    return stream && stream->chunk ? stream->chunk : nullptr;
}

size_t quickapi_file_stream_chunk_size(const quickapi_file_stream* stream) {
    return stream ? stream->last_read : 0;
}

unsigned long long quickapi_file_stream_total_read(const quickapi_file_stream* stream) {
    return stream ? stream->total_read : 0;
}
