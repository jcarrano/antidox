/**
 * @file
 */

#include "structures.h"

/**
 * Test a global function pointer.
 *
 * @param	a	thing
 * @param	b	other thing
 * @return	something
 */
int (*b)(int a, struct s1 *b);

/**
 * Test another global function pointer.
 */
int (*c)(float (*a)(float*), float b);

/**
 * Test function taking function pointer.
 *
 * @param  t   pointer to func.
 * @param  u   another thing.
 */
int k(char (*t)(char, float), int u);
