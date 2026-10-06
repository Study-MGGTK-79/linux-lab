/*
 * Демонстрационная уязвимая SUID программа: vuln_status.c
 * Имитирует служебную системную утилиту администратора.
 * Уязвимость: вызов системной утилиты без абсолютного пути в функции system().
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    printf("[*] Запуск служебной проверки сетевых служб...\n");

    // Критическая ошибка: относительный путь 'service' вместо '/usr/sbin/service'
    // Позволяет эксплуатацию через PATH Hijacking при наличии бита SUID
    int ret = system("service --status-all");

    if (ret != 0) {
        printf("[-] Служба завершила работу с ошибкой.\n");
        return EXIT_FAILURE;
    }

    printf("[+] Проверка успешно завершена.\n");
    return EXIT_SUCCESS;
}
