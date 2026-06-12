#include <string>

extern "C" __declspec(dllexport) const char* analyze_run(const char* json_input) {
    static std::string result;
    result = "{\"ok\":true,\"score\":0.42}";
    return result.c_str();
}
