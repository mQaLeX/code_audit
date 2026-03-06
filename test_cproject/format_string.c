#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"
#include "utils.h"
#include "format_string.h"

int handle_format(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char user_input[256] = "";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        query[sizeof(query) - 1] = '\0';
        
        char *msg_param = strstr(query, "msg=");
        if (msg_param) {
            char *value = msg_param + 4;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(user_input) - 1) {
                user_input[i] = value[i];
                i++;
            }
            user_input[i] = '\0';
        }
    }
    
    log_access("/format", user_input);
    
    mg_send_http_ok(conn, "text/plain", -1);
    printf(user_input);
    mg_printf(conn, "\n");
    
    return 200;
}
