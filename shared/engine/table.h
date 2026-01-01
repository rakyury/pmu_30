/**
 * @file table.h
 * @brief Logic Engine - Table Lookup Functions (Pure Functions)
 *
 * 2D and 3D lookup tables with linear interpolation.
 * All functions are stateless - table data is passed as parameter.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_TABLE_H
#define ENGINE_TABLE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Table Limits
 *============================================================================*/

#define TABLE_2D_MAX_POINTS     16   /**< Maximum points in 2D table */
#define TABLE_3D_MAX_X          8    /**< Maximum X axis points in 3D table */
#define TABLE_3D_MAX_Y          8    /**< Maximum Y axis points in 3D table */

/*============================================================================
 * 2D Table Structure
 *============================================================================*/

/**
 * 2D Lookup Table with linear interpolation.
 *
 * X values must be sorted in ascending order.
 * Interpolation is performed between adjacent points.
 * Values outside range are clamped to first/last point.
 */
typedef struct {
    uint8_t  count;                          /**< Number of points (1-16) */
    uint8_t  reserved[3];
    int32_t  x[TABLE_2D_MAX_POINTS];         /**< X axis values (sorted) */
    int32_t  y[TABLE_2D_MAX_POINTS];         /**< Y axis values */
} Table2D_t;

/*============================================================================
 * 3D Table Structure
 *============================================================================*/

/**
 * 3D Lookup Table with bilinear interpolation.
 *
 * X and Y axis values must be sorted in ascending order.
 * Z values are stored row-major: z[y][x]
 */
typedef struct {
    uint8_t  x_count;                        /**< Number of X points (1-8) */
    uint8_t  y_count;                        /**< Number of Y points (1-8) */
    uint8_t  reserved[2];
    int32_t  x[TABLE_3D_MAX_X];              /**< X axis values (sorted) */
    int32_t  y[TABLE_3D_MAX_Y];              /**< Y axis values (sorted) */
    int32_t  z[TABLE_3D_MAX_Y][TABLE_3D_MAX_X]; /**< Z values [y][x] */
} Table3D_t;

/*============================================================================
 * 2D Table Functions
 *============================================================================*/

/**
 * 2D table lookup with linear interpolation.
 *
 * @param table Pointer to table data
 * @param x Input value
 * @return Interpolated output value
 */
int32_t Table2D_Lookup(const Table2D_t* table, int32_t x);

/**
 * 2D table lookup (raw, no interpolation - returns nearest lower point).
 */
int32_t Table2D_LookupRaw(const Table2D_t* table, int32_t x);

/**
 * Validate 2D table (check sorting, count, etc.).
 *
 * @param table Table to validate
 * @return 1 if valid, 0 if invalid
 */
int32_t Table2D_Validate(const Table2D_t* table);

/*============================================================================
 * 3D Table Functions
 *============================================================================*/

/**
 * 3D table lookup with bilinear interpolation.
 *
 * @param table Pointer to table data
 * @param x X input value
 * @param y Y input value
 * @return Interpolated output value
 */
int32_t Table3D_Lookup(const Table3D_t* table, int32_t x, int32_t y);

/**
 * 3D table lookup (raw, no interpolation - returns nearest lower cell).
 */
int32_t Table3D_LookupRaw(const Table3D_t* table, int32_t x, int32_t y);

/**
 * Validate 3D table.
 *
 * @param table Table to validate
 * @return 1 if valid, 0 if invalid
 */
int32_t Table3D_Validate(const Table3D_t* table);

/*============================================================================
 * Interpolation Helpers (exposed for advanced use)
 *============================================================================*/

/**
 * Linear interpolation between two points.
 *
 * @param x Input value
 * @param x0 First X point
 * @param x1 Second X point
 * @param y0 First Y value
 * @param y1 Second Y value
 * @return Interpolated Y value
 */
int32_t Table_Lerp(int32_t x, int32_t x0, int32_t x1, int32_t y0, int32_t y1);

/**
 * Find index of lower bound in sorted array.
 *
 * @param arr Sorted array
 * @param count Array length
 * @param value Value to find
 * @return Index i such that arr[i] <= value < arr[i+1]
 */
uint8_t Table_FindIndex(const int32_t* arr, uint8_t count, int32_t value);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_TABLE_H */
