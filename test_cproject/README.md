# Test C Project

这是一个使用 C 语言编写的测试项目，使用 cmake 编译，引入 civetweb 作为 web 框架。该项目包含多个 API 接口，并故意设计了命令注入和任意文件读漏洞。

## 项目结构

```
test_cproject/
├── CMakeLists.txt      # CMake 配置文件
├── main.c             # 主程序文件
└── README.md          # 说明文档
```

## 漏洞列表

### 1. 命令注入漏洞

#### `/ping` 端点
- **漏洞类型**: 命令注入
- **位置**: main.c 第 44-77 行
- **描述**: 使用 `popen()` 直接执行包含用户输入的命令
- **利用方式**: `/ping?host=127.0.0.1;whoami` 或 `/ping?host=127.0.0.1|cat /etc/passwd`

#### `/exec` 端点
- **漏洞类型**: 命令注入
- **位置**: main.c 第 99-127 行
- **描述**: 使用 `popen()` 直接执行用户输入的命令
- **利用方式**: `/exec?cmd=whoami` 或 `/exec?cmd=cat /etc/passwd`

### 2. 任意文件读取漏洞

#### `/read` 端点
- **漏洞类型**: 任意文件读取
- **位置**: main.c 第 79-97 行
- **描述**: 直接读取用户指定的文件路径，未进行路径验证
- **利用方式**: `/read?file=/etc/passwd` 或 `/read?file=../../../etc/passwd`

#### `/download` 端点
- **漏洞类型**: 任意文件读取
- **位置**: main.c 第 129-167 行
- **描述**: 直接下载用户指定的文件，未进行路径验证
- **利用方式**: `/download?file=/etc/passwd` 或 `/download?file=../../../etc/passwd`

## 构建和运行

### 构建步骤

1. **创建构建目录**:
   ```bash
   cd test_cproject
   mkdir build
   cd build
   ```

2. **运行 CMake**:
   ```bash
   cmake ..
   ```

3. **编译项目**:
   ```bash
   cmake --build .
   ```

### 运行项目

```bash
./test_cproject
```

应用将在 `http://localhost:8080` 上运行。

## 测试漏洞

### 测试命令注入漏洞

```bash
# 测试 /ping 端点
curl "http://localhost:8080/ping?host=127.0.0.1;whoami"
curl "http://localhost:8080/ping?host=127.0.0.1|cat /etc/passwd"

# 测试 /exec 端点
curl "http://localhost:8080/exec?cmd=whoami"
curl "http://localhost:8080/exec?cmd=cat /etc/passwd"
```

### 测试任意文件读取漏洞

```bash
# 测试 /read 端点
curl "http://localhost:8080/read?file=/etc/passwd"
curl "http://localhost:8080/read?file=../../../etc/passwd"

# 测试 /download 端点
curl "http://localhost:8080/download?file=/etc/passwd" -O
```

## 使用代码审计Agent进行测试

```bash
# 回到项目根目录
cd ..

# 运行代码审计
python main.py test_cproject c web --skip-exploit --verbose
```

## 预期结果

代码审计Agent应该能够发现以下漏洞：

1. **命令注入漏洞** (2个)
   - `/ping` 端点
   - `/exec` 端点

2. **任意文件读取漏洞** (2个)
   - `/read` 端点
   - `/download` 端点

## 注意事项

⚠️ **警告**: 此测试应用包含真实的安全漏洞，仅用于教育和测试目的。请勿在生产环境中使用或部署此应用。

⚠️ **安全提示**: 在运行此应用时，请确保：
1. 仅在本地测试环境中运行
2. 不要暴露在公网上
3. 测试完成后及时停止应用

## 修复建议

### 命令注入漏洞修复

使用白名单验证或参数化命令：

```c
// 错误的方式
char command[256];
snprintf(command, sizeof(command), "ping -c 4 %s", host);
popen(command, "r");

// 正确的方式
if (is_valid_host(host)) {
    char command[256];
    snprintf(command, sizeof(command), "ping -c 4 %s", host);
    popen(command, "r");
}
```

### 任意文件读取漏洞修复

验证和规范化文件路径：

```c
// 错误的方式
const char *file = mg_get_query_var(conn, "file", "README.md");
FILE *fp = fopen(file, "r");

// 正确的方式
const char *file = mg_get_query_var(conn, "file", "README.md");
if (is_safe_path(file)) {
    FILE *fp = fopen(file, "r");
    // ...
}
```

## 依赖

- **CMake**: 3.10 或更高版本
- **C编译器**: 支持 C99 标准
- **civetweb**: 通过 FetchContent 自动获取

## 技术细节

- **Web框架**: civetweb v1.16
- **监听端口**: 8080
- **API端点**:
  - `/` - 首页
  - `/ping` - Ping测试（命令注入）
  - `/read` - 文件读取（任意文件读）
  - `/exec` - 命令执行（命令注入）
  - `/download` - 文件下载（任意文件读）
