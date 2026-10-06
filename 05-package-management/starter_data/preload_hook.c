/*
 * Демонстрационная библиотека для исследования механизма LD_PRELOAD: preload_hook.c
 * Перехватывает стандартную функцию puts() из glibc
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <unistd.h>

// Переопределяем функцию puts
int puts(const char *str) {
    // Указатель на оригинальную функцию puts из glibc
    static int (*real_puts)(const char *) = NULL;
    if (!real_puts) {
        real_puts = dlsym(RTLD_NEXT, "puts");
    }

    // Внедряемое поведение аудита/перехвата
    real_puts("[⚠️ AUDIT LD_PRELOAD]: Функция puts() перехвачена инжектированной библиотекой!");

    // Вызываем оригинальную функцию
    return real_puts(str);
}
