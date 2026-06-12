#include "quick_native_loader.h"

#include <string>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace {
thread_local std::string quick_loader_error;

void set_error(const char* message) {
    quick_loader_error = message == nullptr ? "" : message;
}
}

void* quickapi_native_open(const char* library_path) {
    if (library_path == nullptr) {
        set_error("library_path is null");
        return nullptr;
    }
#ifdef _WIN32
    HMODULE handle = LoadLibraryA(library_path);
    if (handle == nullptr) {
        set_error("LoadLibraryA failed");
    }
    return reinterpret_cast<void*>(handle);
#else
    void* handle = dlopen(library_path, RTLD_NOW);
    if (handle == nullptr) {
        set_error(dlerror());
    }
    return handle;
#endif
}

void quickapi_native_close(void* handle) {
    if (handle == nullptr) {
        return;
    }
#ifdef _WIN32
    FreeLibrary(reinterpret_cast<HMODULE>(handle));
#else
    dlclose(handle);
#endif
}

quickapi_native_json_fn quickapi_native_symbol(void* handle, const char* symbol) {
    if (handle == nullptr || symbol == nullptr) {
        set_error("handle or symbol is null");
        return nullptr;
    }
#ifdef _WIN32
    FARPROC proc = GetProcAddress(reinterpret_cast<HMODULE>(handle), symbol);
    if (proc == nullptr) {
        set_error("GetProcAddress failed");
    }
    return reinterpret_cast<quickapi_native_json_fn>(proc);
#else
    void* proc = dlsym(handle, symbol);
    if (proc == nullptr) {
        set_error(dlerror());
    }
    return reinterpret_cast<quickapi_native_json_fn>(proc);
#endif
}

const char* quickapi_native_last_error(void) {
    return quick_loader_error.c_str();
}
