#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include "civetweb.h"
#include "utils.h"
#include "race_condition.h"

static pthread_mutex_t file_lock = PTHREAD_MUTEX_INITIALIZER;

int handle_race(struct mg_connection *conn, void *cbdata) {
    const struct mg_request_info *ri = mg_get_request_info(conn);
    char query[1024];
    char filename[256] = "counter.txt";
    char action[16] = "read";
    
    if (ri->query_string) {
        strncpy(query, ri->query_string, sizeof(query) - 1);
        
        char *file_param = strstr(query, "file=");
        char *action_param = strstr(query, "action=");
        
        if (file_param) {
            char *value = file_param + 5;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(filename) - 1) {
                filename[i] = value[i];
                i++;
            }
            filename[i] = '\0';
        }
        
        if (action_param) {
            char *value = action_param + 7;
            size_t i = 0;
            while (value[i] && value[i] != '&' && i < sizeof(action) - 1) {
                action[i] = value[i];
                i++;
            }
            action[i] = '\0';
        }
    }
    
    if (!check_file_exists(filename)) {
        send_error_response(conn, 404, "File not found");
        return 404;
    }
    
    pthread_mutex_lock(&file_lock);
    
    FILE *fp = fopen(filename, action[0] == 'w' ? "w" : "r");
    if (!fp) {
        pthread_mutex_unlock(&file_lock);
        send_error_response(conn, 500, "Failed to open file");
        return 500;
    }
    
    if (action[0] == 'w') {
        fprintf(fp, "updated at %ld\n", time(NULL));
    } else {
        char buffer[256];
        while (fgets(buffer, sizeof(buffer), fp)) {
            mg_printf(conn, "%s", buffer);
        }
    }
    
    fclose(fp);
    pthread_mutex_unlock(&file_lock);
    
    return 200;
}
