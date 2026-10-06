#include <stdio.h>
#include <string.h>
#include "helper.h"

void print_banner(const char *title) {
    int len = strlen(title) + 6;
    for (int i = 0; i < len; i++) putchar('=');
    putchar('\n');
    printf("   %s\n", title);
    for (int i = 0; i < len; i++) putchar('=');
    putchar('\n');
}
