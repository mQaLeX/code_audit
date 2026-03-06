#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "civetweb.h"
#include "utils.h"
#include "index.h"
#include "cmd_injection.h"
#include "file_read.h"
#include "format_string.h"
#include "memory_leak.h"
#include "null_pointer.h"
#include "race_condition.h"
#include "use_after_free.h"
#include "info_leak.h"
#include "dos.h"

int main(void) {
    struct mg_context *ctx;
    const char *options[] = {
        "listening_ports", "8080",
        "num_threads", "10",
        NULL
    };
    
    ctx = mg_start(NULL, NULL, options);
    
    if (!ctx) {
        fprintf(stderr, "Failed to start server\n");
        return 1;
    }
    
    mg_set_request_handler(ctx, "/", handle_index, NULL);
    mg_set_request_handler(ctx, "/ping", handle_ping, NULL);
    mg_set_request_handler(ctx, "/exec", handle_exec, NULL);
    mg_set_request_handler(ctx, "/read", handle_read, NULL);
    mg_set_request_handler(ctx, "/download", handle_download, NULL);
    mg_set_request_handler(ctx, "/format", handle_format, NULL);
    mg_set_request_handler(ctx, "/calc", handle_calc, NULL);
    mg_set_request_handler(ctx, "/nullptr", handle_nullptr, NULL);
    mg_set_request_handler(ctx, "/race", handle_race, NULL);
    mg_set_request_handler(ctx, "/uaf/alloc", handle_uaf_alloc, NULL);
    mg_set_request_handler(ctx, "/uaf/use", handle_uaf_use, NULL);
    mg_set_request_handler(ctx, "/uaf/free", handle_uaf_free, NULL);
    mg_set_request_handler(ctx, "/info", handle_info_leak, NULL);
    mg_set_request_handler(ctx, "/dos", handle_dos, NULL);
    
    printf("Server started on port 8080\n");
    printf("Visit http://localhost:8080/ to test\n");
    
    while (1) {
        sleep(1);
    }
    
    mg_stop(ctx);
    return 0;
}
