cmake_minimum_required(VERSION 3.16)
project(quickapi_native VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_library(quickapi_native SHARED
    core/quick_core.c
    core/quick_memory.cpp
    core/quick_buffer.cpp
    core/quick_string.cpp
    http/quick_http.cpp
    http/quick_file_stream.cpp
    http/quick_request.cpp
    http/quick_response.cpp
    isolate/quick_isolate.cpp
    json/quick_json.cpp
    json/quick_json_writer.cpp
    jobs/quick_job_queue.cpp
    loader/quick_native_loader.cpp
    metrics/quick_metrics.cpp
    router/quick_router.cpp
    security/quick_security.cpp
)

target_include_directories(quickapi_native PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/core
)

if(NOT WIN32)
    target_link_libraries(quickapi_native PRIVATE dl)
endif()
