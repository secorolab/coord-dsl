# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
cmake_minimum_required(VERSION 3.16)
project(warehouse_pick_bt LANGUAGES CXX)

set(BTCPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(BTCPP_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BTCPP_GROOT_INTERFACE OFF CACHE BOOL "" FORCE)
set(BTCPP_SQLITE_LOGGING OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../../../BehaviorTree.CPP behaviortree_cpp)

add_executable(warehouse_pick_bt warehouse_pick_main.cpp)
target_link_libraries(warehouse_pick_bt PRIVATE BT::behaviortree_cpp)
target_compile_features(warehouse_pick_bt PRIVATE cxx_std_17)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/warehouse_pick.xml
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/warehouse_pick.xml
        ${CMAKE_CURRENT_BINARY_DIR}/warehouse_pick.xml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/warehouse_pick.xml)
add_custom_target(warehouse_pick_xml DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/warehouse_pick.xml)
add_dependencies(warehouse_pick_bt warehouse_pick_xml)
