#ifndef INFO_LEAK_H
#define INFO_LEAK_H

#include "civetweb.h"

int handle_info_leak(struct mg_connection *conn, void *cbdata);

#endif
