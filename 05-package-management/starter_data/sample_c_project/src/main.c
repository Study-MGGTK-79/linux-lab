#include <stdio.h>
#include <stdlib.h>
#include <sys/sysinfo.h>
#include <unistd.h>
#include "helper.h"

int main(int argc, char *argv[]) {
    struct sysinfo info;

    if (sysinfo(&info) != 0) {
        perror("Ошибка получения информации ядра через sysinfo()");
        return EXIT_FAILURE;
    }

    print_banner("SysStat Mini - Enterprise Node Monitor v1.2");

    long uptime_hours = info.uptime / 3600;
    long uptime_mins = (info.uptime % 3600) / 60;
    unsigned long total_ram_mb = (info.totalram * info.mem_unit) / (1024 * 1024);
    unsigned long free_ram_mb = (info.freeram * info.mem_unit) / (1024 * 1024);

    printf(" Время непрерывной работы (Uptime): %ld ч. %ld мин.\n", uptime_hours, uptime_mins);
    printf(" Всего оперативной памяти (Total RAM): %lu MB\n", total_ram_mb);
    printf(" Свободно оперативной памяти (Free RAM): %lu MB\n", free_ram_mb);
    printf(" Количество активных процессов: %d\n", info.procs);
    printf(" Средняя нагрузка (Load Avg 1m): %.2f\n", (float)info.loads[0] / 65536.0);

    return EXIT_SUCCESS;
}
