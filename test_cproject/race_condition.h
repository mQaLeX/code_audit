#ifndef RACE_CONDITION_H
#define RACE_CONDITION_H

#include "civetweb.h"

int handle_race(struct mg_connection *conn, void *cbdata);

#endif
