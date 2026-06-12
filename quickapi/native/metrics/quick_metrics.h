#ifndef QUICKAPI_METRICS_H
#define QUICKAPI_METRICS_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT double quickapi_metrics_now_ms(void);
QUICKAPI_EXPORT double quickapi_metrics_elapsed_ms(double start_ms);

#ifdef __cplusplus
}
#endif

#endif
