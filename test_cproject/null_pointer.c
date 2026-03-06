#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "null_pointer.h"

int handle_nullptr(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char data[256] = "";
    int use_null = 0;
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        
        char *data_param = strstr(query, "data=");
        char *null_param = strstr(query, "null=1");
        
        if (data_param) {
            char *value = data_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(data) - 1) {
                data[i] = value[i];
                i++;
            }
            data[i] = '\0';
        }
        
        if (null_param) {
            use_null = 1;
        }
    }
    
    char *ptr = NULL;
    if (use_null) {
        ptr = NULL;
    } else {
        ptr = data;
    }
    
    log_access("/nullptr", ptr);
    
    size_t len = strlen(ptr);
    
    mg_send_http_ok(conn, "text/plain", -1);
    mg_printf(conn, "Length: %zu\n", len);
    
    return 200;
}
