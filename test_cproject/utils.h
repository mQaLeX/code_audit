#ifndef UTILS_H
#define UTILS_H

#include "civetweb.h"

void sanitize_input(char *input, size_t max_len);
int validate_hostname(const char *hostname);
int validate_filename(const char *filename);
int validate_command(const char *cmd);
void log_access(const char *endpoint, const char *param);
void send_error_response(struct mg_connection *conn, int code, const char *message);
int check_file_exists(const char *filename);
long get_file_size(const char *filename);
int is_safe_path(const char *path);

#endif
