#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "info_leak.h"

int handle_info_leak(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char secret_file[256] = "";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        
        char *file_param = strstr(query, "file=");
        if (file_param) {
            char *value = file_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(secret_file) - 1) {
                secret_file[i] = value[i];
                i++;
            }
            secret_file[i] = '\0';
        }
    }
    
    if (strcmp(secret_file, "config") == 0 || strcmp(secret_file, ".env") == 0 || 
        strcmp(secret_file, "secret") == 0 || strcmp(secret_file, "passwords") == 0) {
        
        const char *leaked_data = 
            "=== SYSTEM INFORMATION LEAK ===\n"
            "Database: postgresql://admin:password123@localhost:5432/mydb\n"
            "API Key: sk_live_1234567890abcdef\n"
            "Secret Key: my_secret_key_12345\n"
            "Admin Password: admin123\n"
            "=============================\n";
        
        mg_send_http_ok(conn, "text/plain", strlen(leaked_data));
        mg_printf(conn, "%s", leaked_data);
        
        return 200;
    }
    
    send_error_response(conn, 404, "File not found");
    return 404;
}
