#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include "civetweb.h"
#include "utils.h"

static int handle_index(struct mg_connection *conn, void *cbdata) {
    const char *html =
        "<html>\n"
        "<head><title>Test C Project</title></head>\n"
        "<body>\n"
        "    <h1>Test C Project - Vulnerability Demo</h1>\n"
        "    <ul>\n"
        "        <li><a href=\"/ping?host=127.0.0.1\">Ping Test (Command Injection)</a></li>\n"
        "        <li><a href=\"/read?file=README.md\">File Read (Arbitrary File Read)</a></li>\n"
        "        <li><a href=\"/exec?cmd=ls\">Command Exec (Command Injection)</a></li>\n"
        "        <li><a href=\"/download?file=README.md\">File Download (Arbitrary File Read)</a></li>\n"
        "    </ul>\n"
        "</body>\n"
        "</html>\n";
    
    mg_send_http_ok(conn, "text/html", strlen(html));
    mg_printf(conn, "%s", html);
    return 200;
}

static int handle_ping(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char host[256] = "127.0.0.1";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        query[sizeof(query) - 1] = '\0';
        
        char *host_param = strstr(query, "host=");
        if (host_param) {
            char *value = host_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(host) - 1) {
                host[i] = value[i];
                i++;
            }
            host[i] = '\0';
            
            char *decoded = url_decode(host);
            if (decoded) {
                strncpy(host, decoded, sizeof(host) - 1);
                host[sizeof(host) - 1] = '\0';
                free(decoded);
            }
        }
    }
    
    log_access("/ping", host);
    
    if (!validate_hostname(host)) {
        send_error_response(conn, 400, "Invalid hostname");
        return 400;
    }
    
    char command[512];
    snprintf(command, sizeof(command), "ping -c 4 %s", host);
    
    FILE *pipe = popen(command, "r");
    if (!pipe) {
        send_error_response(conn, 500, "Internal Server Error");
        return 500;
    }
    
    char buffer[1024];
    size_t nread;
    
    mg_send_http_ok(conn, "text/plain", 0);
    mg_printf(conn, "Executed command: %s\n\n", command);
    
    while ((nread = fread(buffer, 1, sizeof(buffer), pipe)) > 0) {
        mg_write(conn, buffer, nread);
    }
    
    pclose(pipe);
    return 200;
}

static int handle_read(struct mg_connection *conn, void *cbdata) {
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

static int handle_exec(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char cmd[256] = "ls -la";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        query[sizeof(query) - 1] = '\0';
        
        char *cmd_param = strstr(query, "cmd=");
        if (cmd_param) {
            char *value = cmd_param + 4;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(cmd) - 1) {
                cmd[i] = value[i];
                i++;
            }
            cmd[i] = '\0';
            
            char *decoded = url_decode(cmd);
            if (decoded) {
                strncpy(cmd, decoded, sizeof(cmd) - 1);
                cmd[sizeof(cmd) - 1] = '\0';
                free(decoded);
            }
        }
    }
    
    log_access("/exec", cmd);
    
    sanitize_input(cmd, sizeof(cmd));
    
    if (!validate_command(cmd)) {
        send_error_response(conn, 403, "Invalid command");
        return 403;
    }
    
    FILE *pipe = popen(cmd, "r");
    if (!pipe) {
        send_error_response(conn, 500, "Internal Server Error");
        return 500;
    }
    
    char buffer[1024];
    size_t nread;
    
    mg_send_http_ok(conn, "text/plain", -1);
    mg_printf(conn, "Executed command: %s\n\n", cmd);
    
    while ((nread = fread(buffer, 1, sizeof(buffer), pipe)) > 0) {
        mg_write(conn, buffer, nread);
    }
    
    pclose(pipe);
    return 200;
}

static int handle_download(struct mg_connection *conn, void *cbdata) {
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

int main(void) {
    struct mg_context *ctx;
    const char *options[] = {
        "listening_ports", "8080",
        "num_threads", "10",
        NULL
    };
    
    // Start server
    ctx = mg_start(NULL, NULL, options);
    
    if (!ctx) {
        fprintf(stderr, "Failed to start server\n");
        return 1;
    }
    
    // Register handlers
    mg_set_request_handler(ctx, "/", handle_index, NULL);
    mg_set_request_handler(ctx, "/ping", handle_ping, NULL);
    mg_set_request_handler(ctx, "/read", handle_read, NULL);
    mg_set_request_handler(ctx, "/exec", handle_exec, NULL);
    mg_set_request_handler(ctx, "/download", handle_download, NULL);
    
    printf("Server started on port 8080\n");
    printf("Visit http://localhost:8080/ to test\n");
    
    // Wait forever
    while (1) {
        sleep(1);
    }
    
    mg_stop(ctx);
    return 0;
}
