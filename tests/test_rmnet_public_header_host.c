/* Standalone host smoke test of old Qualcomm librmnetctl public API header.
 * Intentionally does not link to librmnetctl, open netlink sockets, or touch
 * a modem. AOSP17 compile and kernel ABI remain unverified.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "librmnetctl.h"

#ifdef USE_OLD_RMNET_DATA
#error The historical legacy kernel RMNET_DATA flag must not be enabled
#endif

int main(void) {
    const unsigned n = (unsigned)(
        sizeof(rmnetctl_error_code_text) /
        sizeof(rmnetctl_error_code_text[0]));
    if (RMNETCTL_SUCCESS != 0 || RMNETCTL_LIB_ERR != 1 ||
        RMNETCTL_KERNEL_ERR != 2 || RMNETCTL_INVALID_ARG != 3 ||
        n != RMNETCTL_API_ERR_ENUM_LENGTH ||
        RMNETCTL_ERR_MSG_SIZE != 100) {
        fputs("FAIL: legacy RMNET public ABI constant/header mismatch\n", stderr);
        return 1;
    }
    if (strstr(rmnetctl_error_code_text[0], "succeeded") == NULL) {
        fputs("FAIL: unexpected old RMNET error-code table\n", stderr);
        return 1;
    }
    puts("PASS: original RMNET header compiled and inspected on host (no legacy driver)");
    return 0;
}
