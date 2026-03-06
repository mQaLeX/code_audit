#ifndef FILE_READ_H
#define FILE_READ_H

#include "civetweb.h"

int handle_read(struct mg_connection *conn, void *cbdata);
int handle_download(struct mg_connection *conn, void *cbdata);

#endif
