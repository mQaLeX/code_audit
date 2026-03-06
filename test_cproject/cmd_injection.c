#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "cmd_injection.h"

int handle_ping(struct mg_connection *conn, void *cbdata) {
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

int handle_exec(struct mg_connection *conn, void *cbdata) {
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
