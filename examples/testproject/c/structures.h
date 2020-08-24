/**
 * @file
 */

/**
 * Example structure 1
 */
struct s1 {
	int a, b, c;
	char *_x; /**< Test a reference to s2::b */
};

/**
 * Example structure 2
 */
struct s2 {
	/**
	 * Test a function pointer.
	 *
	 * @param	a	thing
	 * @param	b	other thing
	 * @return	something
	 */
	int (*b)(int a, struct s1 *b);
	/**
	 * Test another function pointer.
	 */
	int (*c)(float a, float b);
};

/**
 * Struct with flex member.
 */
struct fm {
	unsigned l; /**< Length of d */
	char d[];   /**< data. */
};
