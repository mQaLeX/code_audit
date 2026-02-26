#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include "utils.h"

void sanitize_input(char *input, size_t max_len) {
    if (!input || max_len == 0) return;
    
    size_t len = strlen(input);
    for (size_t i = 0; i < len && i < max_len; i++) {
        if (!isprint(input[i]) || input[i] == '\n' || input[i] == '\r') {
            input[i] = ' ';
        }
    }
}

int validate_hostname(const char *hostname) {
    if (!hostname || strlen(hostname) == 0) return 0;
    
    for (size_t i = 0; hostname[i]; i++) {
        if (!(isalnum(hostname[i]) || hostname[i] == '.' || hostname[i] == '-')) {
            return 0;
        }
    }
    return 1;
}

int validate_filename(const char *filename) {
    if (!filename || strlen(filename) == 0) return 0;
    
    for (size_t i = 0; filename[i]; i++) {
        if (filename[i] == '/' || filename[i] == '\\' || filename[i] == ':') {
            return 0;
        }
    }
    return 1;
}

int validate_command(const char *cmd) {
    if (!cmd || strlen(cmd) == 0) return 0;
    
    const char *allowed_commands[] = {"ls", "pwd", "date", "whoami", NULL};
    
    for (int i = 0; allowed_commands[i]; i++) {
        if (strncmp(cmd, allowed_commands[i], strlen(allowed_commands[i])) == 0) {
            return 1;
        }
    }
    return 0;
}

void log_access(const char *endpoint, const char *param) {
    char log_msg[512];
    snprintf(log_msg, sizeof(log_msg), "Access: %s with param: %s", endpoint, param ? param : "none");
    printf("[LOG] %s\n", log_msg);
}

void send_error_response(struct mg_connection *conn, int code, const char *message) {
    char html[1024];
    snprintf(html, sizeof(html),
        "<html><head><title>Error %d</title></head>"
        "<body><h1>Error %d</h1><p>%s</p></body></html>",
        code, code, message);
    
    mg_send_http_error(conn, code, "%s", message);
}

int check_file_exists(const char *filename) {
    FILE *fp = fopen(filename, "r");
    if (fp) {
        fclose(fp);
        return 1;
    }
    return 0;
}

long get_file_size(const char *filename) {
    FILE *fp = fopen(filename, "r");
    if (!fp) return -1;
    
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fclose(fp);
    
    return size;
}

int is_safe_path(const char *path) {
    if (!path) return 0;
    
    if (strstr(path, "..") != NULL) {
        return 0;
    }
    
    if (path[0] == '/') {
        return 0;
    }
    
    return 1;
}
