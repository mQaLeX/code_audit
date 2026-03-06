#ifndef CMD_INJECTION_H
#define CMD_INJECTION_H

#include "civetweb.h"

int handle_ping(struct mg_connection *conn, void *cbdata);
int handle_exec(struct mg_connection *conn, void *cbdata);

#endif
