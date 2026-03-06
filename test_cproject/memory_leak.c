#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "memory_leak.h"

int handle_calc(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char size_str[64] = "100";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        
        char *size_param = strstr(query, "size=");
        if (size_param) {
            char *value = size_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(size_str) - 1) {
                size_str[i] = value[i];
                i++;
            }
            size_str[i] = '\0';
        }
    }
    
    int size = atoi(size_str);
    if (size > 0 && size < 1000000) {
        char *buffer = malloc(size);
        if (!buffer) {
            send_error_response(conn, 500, "Memory allocation failed");
            return 500;
        }
        
        memset(buffer, 'A', size);
        
        snprintf(buffer, size, "Calculated: %d bytes", size);
        
        mg_send_http_ok(conn, "text/plain", size);
        mg_write(conn, buffer, size);
        
        return 200;
    }
    
    send_error_response(conn, 400, "Invalid size");
    return 400;
}
