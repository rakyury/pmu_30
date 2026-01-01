/**
 * @file table.c
 * @brief Logic Engine - Table Lookup Implementation
 */

#include "table.h"

/*============================================================================
 * Helper Functions
 *============================================================================*/

uint8_t Table_FindIndex(const int32_t* arr, uint8_t count, int32_t value)
{
    if (count == 0) return 0;
    if (count == 1) return 0;

    /* Value below first point */
    if (value <= arr[0]) return 0;

    /* Value above last point */
    if (value >= arr[count - 1]) return count - 2;

    /* Binary search for interval */
    uint8_t low = 0;
    uint8_t high = count - 1;

    while (low < high - 1) {
        uint8_t mid = (low + high) / 2;
        if (value < arr[mid]) {
            high = mid;
        } else {
            low = mid;
        }
    }

    return low;
}

int32_t Table_Lerp(int32_t x, int32_t x0, int32_t x1, int32_t y0, int32_t y1)
{
    /* Avoid division by zero */
    int32_t dx = x1 - x0;
    if (dx == 0) return y0;

    /* Calculate interpolation using 64-bit to avoid overflow */
    int64_t dy = (int64_t)(y1 - y0);
    int64_t offset = (int64_t)(x - x0);

    return y0 + (int32_t)((dy * offset) / dx);
}

/*============================================================================
 * 2D Table Functions
 *============================================================================*/

int32_t Table2D_Lookup(const Table2D_t* table, int32_t x)
{
    if (!table || table->count == 0) return 0;

    /* Single point table */
    if (table->count == 1) return table->y[0];

    /* Find interval */
    uint8_t i = Table_FindIndex(table->x, table->count, x);

    /* Clamp to valid range for interpolation */
    if (i >= table->count - 1) i = table->count - 2;

    /* Linear interpolation */
    return Table_Lerp(x,
                      table->x[i], table->x[i + 1],
                      table->y[i], table->y[i + 1]);
}

int32_t Table2D_LookupRaw(const Table2D_t* table, int32_t x)
{
    if (!table || table->count == 0) return 0;

    uint8_t i = Table_FindIndex(table->x, table->count, x);
    return table->y[i];
}

int32_t Table2D_Validate(const Table2D_t* table)
{
    if (!table) return 0;
    if (table->count == 0 || table->count > TABLE_2D_MAX_POINTS) return 0;

    /* Check X values are sorted */
    for (uint8_t i = 1; i < table->count; i++) {
        if (table->x[i] <= table->x[i - 1]) return 0;
    }

    return 1;
}

/*============================================================================
 * 3D Table Functions
 *============================================================================*/

int32_t Table3D_Lookup(const Table3D_t* table, int32_t x, int32_t y)
{
    if (!table || table->x_count == 0 || table->y_count == 0) return 0;

    /* Single cell table */
    if (table->x_count == 1 && table->y_count == 1) {
        return table->z[0][0];
    }

    /* Find X interval */
    uint8_t xi = 0;
    if (table->x_count > 1) {
        xi = Table_FindIndex(table->x, table->x_count, x);
        if (xi >= table->x_count - 1) xi = table->x_count - 2;
    }

    /* Find Y interval */
    uint8_t yi = 0;
    if (table->y_count > 1) {
        yi = Table_FindIndex(table->y, table->y_count, y);
        if (yi >= table->y_count - 1) yi = table->y_count - 2;
    }

    /* Handle edge cases */
    if (table->x_count == 1) {
        /* 1D interpolation along Y only */
        return Table_Lerp(y,
                          table->y[yi], table->y[yi + 1],
                          table->z[yi][0], table->z[yi + 1][0]);
    }

    if (table->y_count == 1) {
        /* 1D interpolation along X only */
        return Table_Lerp(x,
                          table->x[xi], table->x[xi + 1],
                          table->z[0][xi], table->z[0][xi + 1]);
    }

    /* Bilinear interpolation */
    /* Get corner values */
    int32_t z00 = table->z[yi][xi];         /* Bottom-left */
    int32_t z10 = table->z[yi][xi + 1];     /* Bottom-right */
    int32_t z01 = table->z[yi + 1][xi];     /* Top-left */
    int32_t z11 = table->z[yi + 1][xi + 1]; /* Top-right */

    /* Get axis values */
    int32_t x0 = table->x[xi];
    int32_t x1 = table->x[xi + 1];
    int32_t y0 = table->y[yi];
    int32_t y1 = table->y[yi + 1];

    /* Interpolate along X for both Y rows */
    int32_t z_y0 = Table_Lerp(x, x0, x1, z00, z10);
    int32_t z_y1 = Table_Lerp(x, x0, x1, z01, z11);

    /* Interpolate along Y */
    return Table_Lerp(y, y0, y1, z_y0, z_y1);
}

int32_t Table3D_LookupRaw(const Table3D_t* table, int32_t x, int32_t y)
{
    if (!table || table->x_count == 0 || table->y_count == 0) return 0;

    uint8_t xi = Table_FindIndex(table->x, table->x_count, x);
    uint8_t yi = Table_FindIndex(table->y, table->y_count, y);

    return table->z[yi][xi];
}

int32_t Table3D_Validate(const Table3D_t* table)
{
    if (!table) return 0;
    if (table->x_count == 0 || table->x_count > TABLE_3D_MAX_X) return 0;
    if (table->y_count == 0 || table->y_count > TABLE_3D_MAX_Y) return 0;

    /* Check X values are sorted */
    for (uint8_t i = 1; i < table->x_count; i++) {
        if (table->x[i] <= table->x[i - 1]) return 0;
    }

    /* Check Y values are sorted */
    for (uint8_t i = 1; i < table->y_count; i++) {
        if (table->y[i] <= table->y[i - 1]) return 0;
    }

    return 1;
}
