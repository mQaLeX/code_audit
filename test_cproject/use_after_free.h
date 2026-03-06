#ifndef USE_AFTER_FREE_H
#define USE_AFTER_FREE_H

#include "civetweb.h"

int handle_uaf_alloc(struct mg_connection *conn, void *cbdata);
int handle_uaf_use(struct mg_connection *conn, void *cbdata);
int handle_uaf_free(struct mg_connection *conn, void *cbdata);

#endif
