"""
PlatformIO build script to exclude cJSON test/fuzzing files.
These files contain their own main() which conflicts with firmware main.
"""
Import("env")

# Get the cJSON library path
cjson_lib = None
for lb in env.GetLibBuilders():
    if "cJSON" in lb.name:
        cjson_lib = lb
        break

if cjson_lib:
    # Remove test.c and fuzzing files from the source filter
    src_filter = cjson_lib.src_filter
    if src_filter:
        # Add exclusions
        src_filter.append("-<test.c>")
        src_filter.append("-<fuzzing/*>")
        src_filter.append("-<test*.c>")
        cjson_lib.src_filter = src_filter
        print("Excluded cJSON test files from build")
