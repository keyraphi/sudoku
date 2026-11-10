cmake_minimum_required(VERSION 3.25)
project(winder VERSION 0.2.0 LANGUAGES C CXX CUDA)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Find required packages
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

# Include nanobind
include(FetchContent)
FetchContent_Declare(
    nanobind
    GIT_REPOSITORY https://github.com/wjakob/nanobind
    GIT_TAG v3.1.0
    SYSTEM
)
FetchContent_MakeAvailable(nanobind)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_subdirectory(src)

