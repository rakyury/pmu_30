/**
 ******************************************************************************
 * @file           : test_main.c
 * @brief          : Main test runner for all PMU tests
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"

/* External test function declarations */
extern int test_protection_main(void);
extern int test_can_main(void);
extern int test_logging_main(void);
extern int test_ui_main(void);
extern int test_lua_main(void);

/* Test statistics */
static int total_tests = 0;
static int passed_tests = 0;
static int failed_tests = 0;

void print_test_summary(void)
{
    printf("\n");
    printf("==============================================\n");
    printf("       PMU-30 TEST SUMMARY\n");
    printf("==============================================\n");
    printf("Total Tests:  %d\n", total_tests);
    printf("Passed:       %d\n", passed_tests);
    printf("Failed:       %d\n", failed_tests);
    printf("Success Rate: %.1f%%\n",
           total_tests > 0 ? (passed_tests * 100.0f / total_tests) : 0.0f);
    printf("==============================================\n");
}

int main(int argc, char** argv)
{
    int result = 0;

    printf("\n");
    printf("==============================================\n");
    printf("  PMU-30 FIRMWARE TEST SUITE\n");
    printf("  Version: 1.0\n");
    printf("  Date: 2025-12-21\n");
    printf("==============================================\n");
    printf("\n");

    /* Run all test suites */

    printf("Running Protection System Tests...\n");
    result += test_protection_main();

    printf("\nRunning CAN System Tests...\n");
    result += test_can_main();

    printf("\nRunning Logging System Tests...\n");
    result += test_logging_main();

    printf("\nRunning UI System Tests...\n");
    result += test_ui_main();

    printf("\nRunning Lua Scripting Tests...\n");
    result += test_lua_main();

    /* Print summary */
    print_test_summary();

    return result;
}
