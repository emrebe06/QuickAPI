#ifndef QUICKAPI_JOB_QUEUE_H
#define QUICKAPI_JOB_QUEUE_H

#include <stddef.h>
#include "../core/quick_core.h"
#include "../core/quick_result.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_job_queue quickapi_job_queue;

QUICKAPI_EXPORT quickapi_job_queue* quickapi_job_queue_create(size_t capacity);
QUICKAPI_EXPORT void quickapi_job_queue_destroy(quickapi_job_queue* queue);
QUICKAPI_EXPORT quickapi_result quickapi_job_queue_push(quickapi_job_queue* queue, unsigned long long job_id);
QUICKAPI_EXPORT quickapi_result quickapi_job_queue_pop(quickapi_job_queue* queue);
QUICKAPI_EXPORT size_t quickapi_job_queue_size(const quickapi_job_queue* queue);
QUICKAPI_EXPORT size_t quickapi_job_queue_capacity(const quickapi_job_queue* queue);

#ifdef __cplusplus
}
#endif

#endif
