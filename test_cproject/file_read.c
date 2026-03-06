#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "file_read.h"

int handle_read(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char file[256] = " README.md";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        query[sizeof(query) - 1] = '\0';
        
        char *file_param = strstr(query, "file=");
        if (file_param) {
            char *value = file_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(file) - 1) {
                file[i] = value[i];
                i++;
            }
            file[i] = '\0';
            
            char *decoded = url_decode(file);
            if (decoded) {
                strncpy(file, decoded, sizeof(file) - 1);
                file[sizeof(file) - 1] = '\0';
                free(decoded);
            }
        }
    }
    
    log_access("/read", file);
    
    if (!is_safe_path(file)) {
        send_error_response(conn, 403, "Unsafe path");
        return 403;
    }
    
    if (!validate_filename(file)) {
        send_error_response(conn, 400, "Invalid filename");
        return 400;
    }
    
    if (!check_file_exists(file)) {
        send_error_response(conn, 404, "File Not Found");
        return 404;
    }
    
    FILE *fp = fopen(file, "r");
    if (!fp) {
        send_error_response(conn, 500, "Failed to open file");
        return 500;
    }
    
    char buffer[1024];
    size_t nread;
    
    mg_send_http_ok(conn, "text/plain", 0);
    mg_printf(conn, "File: %s\n\n", file);
    
    while ((nread = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
        mg_write(conn, buffer, nread);
    }
    
    fclose(fp);
    return 200;
}

int handle_download(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char file[256] = "README.md";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        query[sizeof(query) - 1] = '\0';
        
        char *file_param = strstr(query, "file=");
        if (file_param) {
            char *value = file_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(file) - 1) {
                file[i] = value[i];
                i++;
            }
            file[i] = '\0';
        }
    }
    
    log_access("/download", file);
    
    if (!is_safe_path(file)) {
        send_error_response(conn, 403, "Unsafe path");
        return 403;
    }
    
    if (!validate_filename(file)) {
        send_error_response(conn, 400, "Invalid filename");
        return 400;
    }
    
    if (!check_file_exists(file)) {
        send_error_response(conn, 404, "File Not Found");
        return 404;
    }
    
    FILE *fp = fopen(file, "r");
    if (!fp) {
        send_error_response(conn, 500, "Failed to open file");
        return 500;
    }
    
    long file_size = get_file_size(file);
    if (file_size < 0) {
        fclose(fp);
        send_error_response(conn, 500, "Failed to get file size");
        return 500;
    }
    
    const char *filename = strrchr(file, '/');
    if (filename) {
        filename++;
    } else {
        filename = file;
    }
    
    mg_printf(conn, "HTTP/1.1 200 OK\r\n");
    mg_printf(conn, "Content-Type: application/octet-stream\r\n");
    mg_printf(conn, "Content-Disposition: attachment; filename=%s\r\n", filename);
    mg_printf(conn, "Content-Length: %ld\r\n", file_size);
    mg_printf(conn, "\r\n");
    
    char buffer[1024];
    size_t nread;
    while ((nread = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
        mg_write(conn, buffer, nread);
    }
    
    fclose(fp);
    return 200;
}
