# ---- backend library (no nanobind dependency) -----------------------------
add_library(sudoku_backend STATIC sudoku_backend.cpp)
set_target_properties(sudoku_backend PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(sudoku_backend PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(sudoku_backend PRIVATE -Wall -Wextra -Werror)

# OpenMP (optional fallback to serial build if not available)
find_package(OpenMP COMPONENTS CXX)
if(OpenMP_CXX_FOUND)
    target_link_libraries(sudoku_backend PRIVATE OpenMP::OpenMP_CXX)
    message(STATUS "sudoku_backend: OpenMP enabled")
else()
    message(WARNING "sudoku_backend: OpenMP not found, generating serially")
endif()

# ---- nanobind module ------------------------------------------------------
nanobind_add_module(sudoku_module sudoku.cpp)
target_link_libraries(sudoku_module PRIVATE sudoku_backend)
target_include_directories(sudoku_module PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(sudoku_module PRIVATE -Wall -Wextra -Werror)

# ---- stub generation ------------------------------------------------------
nanobind_add_stub(
    sudoku_module_stub
    MODULE sudoku_module
    OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/../sudoku/sudoku_module.pyi
    DEPENDS sudoku_module
    PYTHON_PATH $<TARGET_FILE_DIR:sudoku_module> ${CMAKE_CURRENT_SOURCE_DIR}/../sudoku/
)

# ---- install --------------------------------------------------------------
if(UNIX)
    set_target_properties(sudoku_module PROPERTIES INSTALL_RPATH "$ORIGIN")
endif()
install(TARGETS sudoku_module LIBRARY DESTINATION .)
