#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "civetweb.h"
#include "utils.h"
#include "use_after_free.h"

typedef struct {
    char name[128];
    char *data;
} UserSession;

static UserSession *active_session = NULL;

int handle_uaf_alloc(struct mg_connection *conn, void *cbdata) {
    if (active_session) {
        free(active_session->data);
        free(active_session);
    }
    
    active_session = malloc(sizeof(UserSession));
    if (!active_session) {
        send_error_response(conn, 500, "Allocation failed");
        return 500;
    }
    
    strncpy(active_session->name, "user_session", sizeof(active_session->name) - 1);
    active_session->data = malloc(256);
    if (active_session->data) {
        snprintf(active_session->data, 256, "session data at %ld", time(NULL));
    }
    
    mg_send_http_ok(conn, "text/plain", -1);
    mg_printf(conn, "Allocated session: %s\n", active_session->name);
    
    return 200;
}

int handle_uaf_use(struct mg_connection *conn, void *cbdata) {
    if (active_session) {
        mg_send_http_ok(conn, "text/plain", -1);
        mg_printf(conn, "Session name: %s\n", active_session->name);
        if (active_session->data) {
            mg_printf(conn, "Session data: %s\n", active_session->data);
        }
        return 200;
    }
    
    send_error_response(conn, 404, "No active session");
    return 404;
}

int handle_uaf_free(struct mg_connection *conn, void *cbdata) {
    if (active_session) {
        free(active_session->data);
        free(active_session);
        // active_session = NULL;  // Should set to NULL but doesn't - UAF vulnerability
    }
    
    mg_send_http_ok(conn, "text/plain", -1);
    mg_printf(conn, "Session freed\n");
    
    return 200;
}
