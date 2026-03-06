#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "civetweb.h"
#include "dos.h"

int handle_dos(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char count_str[32] = "10";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        
        char *count_param = strstr(query, "count=");
        if (count_param) {
            char *value = count_param + 6;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(count_str) - 1) {
                count_str[i] = value[i];
                i++;
            }
            count_str[i] = '\0';
        }
    }
    
    int count = atoi(count_str);
    if (count > 10000) {
        count = 10000;
    }
    
    mg_send_http_ok(conn, "text/plain", -1);
    
    for (int i = 0; i < count; i++) {
        mg_printf(conn, "Response line %d\n", i);
        
        if (i % 100 == 0) {
            usleep(1000);
        }
    }
    
    return 200;
}
