cmake_minimum_required(VERSION 2.8.11)
project(cmake_wrapper)

include(conanbuildinfo.cmake)
conan_basic_setup()

include_directories("source_subfolder/include")
add_subdirectory("source_subfolder")
