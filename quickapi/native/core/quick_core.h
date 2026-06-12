#ifndef QUICKAPI_CORE_H
#define QUICKAPI_CORE_H

#ifdef _WIN32
#define QUICKAPI_EXPORT __declspec(dllexport)
#else
#define QUICKAPI_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT const char* quickapi_core_name(void);
QUICKAPI_EXPORT const char* quickapi_core_version(void);

#ifdef __cplusplus
}
#endif

#endif
