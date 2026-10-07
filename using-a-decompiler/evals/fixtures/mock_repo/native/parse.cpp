#include <cstring>
#include <cstdint>

// Parses "key=value" and returns the value length; 0 when the record has no '='.
uint32_t parse_value(const char* record, const char** value_out) {
    const char* eq = strchr(record, '=');
    if (!eq) { *value_out = nullptr; return 0; }
    *value_out = eq + 1;
    return static_cast<uint32_t>(strlen(eq + 1));
}
