# CivetWeb 外部输入源

本文档描述 CivetWeb 框架中常见的外部输入源，用于数据流追踪分析。

## HTTP 请求相关

### 1. 查询参数 (Query String)

```c
// 获取查询字符串
const struct mg_request_info *ri = mg_get_request_info(conn);
const char *query = ri->query_string;  // 外部输入

// 解析查询参数
char value[256];
mg_get_var(conn, "param_name", value, sizeof(value));  // 外部输入
```

**风险**：查询参数完全由用户控制，可能包含恶意数据。

### 2. HTTP 头部

```c
// 获取请求头
const char *header = mg_get_header(conn, "Header-Name");  // 外部输入

// 常见危险头部
const char *user_agent = mg_get_header(conn, "User-Agent");
const char *referer = mg_get_header(conn, "Referer");
const char *cookie = mg_get_header(conn, "Cookie");
const char *content_type = mg_get_header(conn, "Content-Type");
const char *authorization = mg_get_header(conn, "Authorization");
```

**风险**：所有 HTTP 头部都是外部输入，可能被伪造。

### 3. HTTP 请求体 (Request Body)

```c
// 读取 POST 数据
char post_data[4096];
int len = mg_read(conn, post_data, sizeof(post_data));  // 外部输入

// 获取 Content-Length
const struct mg_request_info *ri = mg_get_request_info(conn);
long content_length = ri->content_length;
```

**风险**：POST 数据可能包含恶意内容，如注入攻击。

### 4. 路径参数 (Path Parameters)

```c
// URI 路径
const struct mg_request_info *ri = mg_get_request_info(conn);
const char *uri = ri->uri;  // 外部输入
const char *local_uri = ri->local_uri;  // 外部输入
```

**风险**：URI 路径可能包含路径遍历攻击。

### 5. Cookie

```c
// 获取 Cookie
const char *cookie = mg_get_header(conn, "Cookie");  // 外部输入

// 解析 Cookie 值
char session_id[128];
mg_get_cookie(cookie, "session_id", session_id, sizeof(session_id));  // 外部输入
```

**风险**：Cookie 可能被篡改，用于会话劫持或认证绕过。

## 文件上传相关

### 6. 上传文件信息

```c
// 文件上传处理
struct mg_form_data_handler fdh;
fdh.field_found = field_found;  // 回调函数
fdh.field_get = field_get;
fdh.field_store = field_store;

int ret = mg_handle_form_request(conn, &fdh);  // 外部输入

// 文件名和内容都是外部输入
char filename[256];
char file_data[65536];
```

**风险**：文件名可能包含路径遍历，文件内容可能包含恶意代码。

## WebSocket 相关

### 7. WebSocket 数据

```c
// WebSocket 数据帧
char buf[1024];
int len = mg_websocket_read(conn, buf, sizeof(buf));  // 外部输入
```

**风险**：WebSocket 数据完全由客户端控制。

## 客户端信息

### 8. 客户端地址

```c
// 客户端 IP 和端口
const struct mg_request_info *ri = mg_get_request_info(conn);
const char *remote_addr = ri->remote_addr;  // 可伪造（如通过 X-Forwarded-For）
int remote_port = ri->remote_port;
```

**风险**：IP 地址可能被伪造，不应直接用于安全决策。

## 常见数据流模式

### 模式 1: 查询参数 -> 命令执行

```c
// 危险模式
const char *host = mg_get_var(conn, "host", ...);  // 外部输入
char cmd[256];
sprintf(cmd, "ping %s", host);  // 污染数据
popen(cmd, "r");  // 命令注入
```

### 模式 2: 路径参数 -> 文件操作

```c
// 危险模式
const char *filename = ri->local_uri + 8;  // 外部输入
char path[512];
sprintf(path, "/var/www/%s", filename);  // 污染数据
fopen(path, "r");  // 路径遍历
```

### 模式 3: POST 数据 -> SQL 查询

```c
// 危险模式
char username[128];
mg_get_var(conn, "username", username, sizeof(username));  // 外部输入
char sql[512];
sprintf(sql, "SELECT * FROM users WHERE name='%s'", username);  // 污染数据
// SQL 注入
```

## 追踪策略

### 1. 识别入口点

在接口函数中查找以下模式：
- `mg_get_request_info(conn)` - 获取请求信息
- `mg_get_var(conn, ...)` - 获取查询参数
- `mg_get_header(conn, ...)` - 获取请求头
- `mg_read(conn, ...)` - 读取请求体
- `mg_handle_form_request(conn, ...)` - 处理表单

### 2. 追踪变量传播

追踪外部输入变量：
- 赋值操作：`var = external_input`
- 函数参数：`func(external_input)`
- 字符串操作：`strcat(buf, external_input)`
- 格式化：`sprintf(buf, "%s", external_input)`

### 3. 识别危险函数

被污染数据传递到以下函数时需要关注：
- 命令执行：`popen`, `system`, `exec*`
- 文件操作：`fopen`, `open`, `unlink`
- 数据库：`sqlite3_exec`, `mysql_query`
- 内存操作：`memcpy`, `strcpy`, `sprintf`

