CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
PREFIX ?= /opt/sysstat_mini

SRC = src/main.c src/helper.c
OBJ = $(SRC:.c=.o)
TARGET = sysstat_mini

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

install: $(TARGET)
	install -d $(DESTDIR)$(PREFIX)/bin
	install -m 755 $(TARGET) $(DESTDIR)$(PREFIX)/bin/

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/$(TARGET)

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all install uninstall clean
