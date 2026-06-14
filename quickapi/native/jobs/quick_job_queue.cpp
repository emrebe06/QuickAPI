#include "quick_job_queue.h"

#include <cstdlib>
#include <mutex>
#include <new>

struct quickapi_job_queue {
    unsigned long long* values;
    size_t capacity;
    size_t head;
    size_t tail;
    size_t size;
    mutable std::mutex lock;
};

quickapi_job_queue* quickapi_job_queue_create(size_t capacity) {
    if (capacity == 0) return nullptr;
    quickapi_job_queue* queue = new (std::nothrow) quickapi_job_queue;
    if (!queue) return nullptr;
    queue->values = static_cast<unsigned long long*>(std::calloc(capacity, sizeof(unsigned long long)));
    if (!queue->values) {
        delete queue;
        return nullptr;
    }
    queue->capacity = capacity;
    queue->head = 0;
    queue->tail = 0;
    queue->size = 0;
    return queue;
}

void quickapi_job_queue_destroy(quickapi_job_queue* queue) {
    if (!queue) return;
    std::free(queue->values);
    delete queue;
}

quickapi_result quickapi_job_queue_push(quickapi_job_queue* queue, unsigned long long job_id) {
    if (!queue || !queue->values) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid job queue");
    }
    std::lock_guard<std::mutex> guard(queue->lock);
    if (queue->size >= queue->capacity) {
        return quickapi_result_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "job queue is full");
    }
    queue->values[queue->tail] = job_id;
    queue->tail = (queue->tail + 1) % queue->capacity;
    queue->size += 1;
    return quickapi_result_ok(queue->size);
}

quickapi_result quickapi_job_queue_pop(quickapi_job_queue* queue) {
    if (!queue || !queue->values) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid job queue");
    }
    std::lock_guard<std::mutex> guard(queue->lock);
    if (queue->size == 0) {
        return quickapi_result_error(QUICKAPI_ERROR_NOT_FOUND, "job queue is empty");
    }
    unsigned long long value = queue->values[queue->head];
    queue->values[queue->head] = 0;
    queue->head = (queue->head + 1) % queue->capacity;
    queue->size -= 1;
    return quickapi_result_ok(static_cast<size_t>(value));
}

size_t quickapi_job_queue_size(const quickapi_job_queue* queue) {
    if (!queue) return 0;
    std::lock_guard<std::mutex> guard(queue->lock);
    return queue->size;
}

size_t quickapi_job_queue_capacity(const quickapi_job_queue* queue) {
    return queue ? queue->capacity : 0;
}

int quickapi_job_queue_is_full(const quickapi_job_queue* queue) {
    if (!queue || queue->capacity == 0) return 0;
    std::lock_guard<std::mutex> guard(queue->lock);
    return queue->size >= queue->capacity ? 1 : 0;
}

double quickapi_job_queue_load_factor(const quickapi_job_queue* queue) {
    if (!queue || queue->capacity == 0) return 0.0;
    std::lock_guard<std::mutex> guard(queue->lock);
    return static_cast<double>(queue->size) / static_cast<double>(queue->capacity);
}
