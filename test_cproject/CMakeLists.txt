cmake_minimum_required(VERSION 3.10)
project(test_cproject C)

set(CMAKE_C_STANDARD 99)

# 禁用 CivetWeb 的单元测试
set(BUILD_TESTING OFF CACHE BOOL "Disable testing" FORCE)
set(ENABLE_CPP OFF CACHE BOOL "Disable C++ API" FORCE)
set(ENABLE_TESTS OFF CACHE BOOL "Disable tests" FORCE)
set(ENABLE_EXAMPLES OFF CACHE BOOL "Disable examples" FORCE)

# 使用FetchContent获取civetweb
include(FetchContent)
FetchContent_Declare(
    civetweb
    GIT_REPOSITORY https://github.com/civetweb/civetweb.git
    GIT_TAG master
)

# 配置CivetWeb选项
set(CIVETWEB_BUILD_TESTING OFF CACHE BOOL "Disable CivetWeb testing" FORCE)
set(CIVETWEB_ENABLE_TESTS OFF CACHE BOOL "Disable CivetWeb tests" FORCE)
set(CIVETWEB_ENABLE_EXAMPLES OFF CACHE BOOL "Disable CivetWeb examples" FORCE)
set(CIVETWEB_ENABLE_CPP OFF CACHE BOOL "Disable CivetWeb C++ API" FORCE)

FetchContent_MakeAvailable(civetweb)

# 包含civetweb头文件
include_directories(${civetweb_SOURCE_DIR}/include)

# 添加可执行文件
add_executable(test_cproject main.c utils.c index.c cmd_injection.c file_read.c format_string.c memory_leak.c null_pointer.c race_condition.c use_after_free.c info_leak.c dos.c)

# 直接编译civetweb源文件
target_sources(test_cproject PRIVATE
    ${civetweb_SOURCE_DIR}/src/civetweb.c
)

# 添加必要的定义
target_compile_definitions(test_cproject PRIVATE
    NO_SSL
    NO_CGI
)

# 添加必要的链接库
if(UNIX AND NOT APPLE)
    target_link_libraries(test_cproject PRIVATE dl pthread)
elseif(APPLE)
    target_link_libraries(test_cproject PRIVATE pthread)
elseif(WIN32)
    target_link_libraries(test_cproject PRIVATE ws2_32 crypt32)
endif()
