"""
PMU-30 Emulator Pre-Build Script
Prepares the build environment for the hardware emulator.
"""

Import("env")

# Add emulator source directory
env.Append(CPPPATH=[
    env.subst("$PROJECT_DIR/emulator"),
    env.subst("$PROJECT_DIR/include")
])

# Define emulator-specific macros
env.Append(CPPDEFINES=[
    "PMU_EMULATOR",
    "NATIVE_BUILD"
])

# Print build info
print("=" * 60)
print("PMU-30 Hardware Emulator Build")
print("=" * 60)
print(f"Platform: {env['PIOPLATFORM']}")
print(f"Build type: Native (PC)")
print("=" * 60)
