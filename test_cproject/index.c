#include <stdio.h>
#include <string.h>
#include "civetweb.h"
#include "index.h"

int handle_index(struct mg_connection *conn, void *cbdata) {
    const char *html =
        "<html>\n"
        "<head><title>Test C Project</title></head>\n"
        "<body>\n"
        "    <h1>Test C Project - Vulnerability Demo</h1>\n"
        "    <h2>Command Injection</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/ping?host=127.0.0.1\">Ping Test</a></li>\n"
        "        <li><a href=\"/exec?cmd=ls\">Command Exec</a></li>\n"
        "    </ul>\n"
        "    <h2>Arbitrary File Read</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/read?file=README.md\">File Read</a></li>\n"
        "        <li><a href=\"/download?file=README.md\">File Download</a></li>\n"
        "    </ul>\n"
        "    <h2>Format String</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/format?msg=hello\">Format String</a></li>\n"
        "    </ul>\n"
        "    <h2>Memory Leak</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/calc?size=1000\">Memory Leak (calc)</a></li>\n"
        "    </ul>\n"
        "    <h2>Null Pointer Dereference</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/nullptr?null=1\">Null Pointer</a></li>\n"
        "    </ul>\n"
        "    <h2>Race Condition</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/race?file=counter.txt&action=read\">Race Condition</a></li>\n"
        "    </ul>\n"
        "    <h2>Use-After-Free</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/uaf/alloc\">UAF Allocate</a></li>\n"
        "        <li><a href=\"/uaf/use\">UAF Use</a></li>\n"
        "        <li><a href=\"/uaf/free\">UAF Free</a></li>\n"
        "    </ul>\n"
        "    <h2>Information Leak</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/info?file=config\">Info Leak</a></li>\n"
        "    </ul>\n"
        "    <h2>Denial of Service</h2>\n"
        "    <ul>\n"
        "        <li><a href=\"/dos?count=100\">DoS Test</a></li>\n"
        "    </ul>\n"
        "</body>\n"
        "</html>\n";
    
    mg_send_http_ok(conn, "text/html", strlen(html));
    mg_printf(conn, "%s", html);
    return 200;
}
