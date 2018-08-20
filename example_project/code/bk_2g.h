/**
 * @file
 * @ingroup BK
 *
 * @brief Interface to bg2g
 *
 * @author El Maestruli
 */

/**
 * aH RE LOCO
 */
#define GK(a,b) b(a)

/**
 * Possible elements of an element.
 */
enum Thing {
    CHAIR, /*!< To sit. */
    TABLE, /*!< Don't sit here. */
    CUP=10 /*!< To drink. */
};
