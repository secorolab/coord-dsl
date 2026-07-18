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

find_package(coord2b REQUIRED)

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

# FSM-coordination tree: the BT dispatches events to the arm FSMs and awaits
# their completion. Headers/XML are generated with `textx generate`.
add_executable(arm_handover_bt arm_handover_main.cpp)
target_link_libraries(arm_handover_bt PRIVATE BT::behaviortree_cpp coord2b)
target_include_directories(arm_handover_bt PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${coord2b_INCLUDE_DIRS})
target_compile_features(arm_handover_bt PRIVATE cxx_std_17)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/arm_handover.xml
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/arm_handover.xml
        ${CMAKE_CURRENT_BINARY_DIR}/arm_handover.xml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/arm_handover.xml)
add_custom_target(arm_handover_xml DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/arm_handover.xml)
add_dependencies(arm_handover_bt arm_handover_xml)

add_executable(dual_arm_bt dual_arm_main.cpp)
target_link_libraries(dual_arm_bt PRIVATE BT::behaviortree_cpp coord2b)
target_include_directories(dual_arm_bt PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${coord2b_INCLUDE_DIRS})
target_compile_features(dual_arm_bt PRIVATE cxx_std_17)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/dual_arm.xml
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/dual_arm.xml
        ${CMAKE_CURRENT_BINARY_DIR}/dual_arm.xml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/dual_arm.xml)
add_custom_target(dual_arm_xml DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/dual_arm.xml)
add_dependencies(dual_arm_bt dual_arm_xml)

# Async coordination: FSMs run in their own 1 kHz threads; the BT sends/polls.
find_package(Threads REQUIRED)
add_executable(async_pick_bt async_pick_main.cpp)
target_link_libraries(async_pick_bt PRIVATE BT::behaviortree_cpp coord2b Threads::Threads)
target_include_directories(async_pick_bt PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${coord2b_INCLUDE_DIRS})
target_compile_features(async_pick_bt PRIVATE cxx_std_17)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/async_pick.xml
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/async_pick.xml
        ${CMAKE_CURRENT_BINARY_DIR}/async_pick.xml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/async_pick.xml)
add_custom_target(async_pick_xml DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/async_pick.xml)
add_dependencies(async_pick_bt async_pick_xml)

# Synchronous C++ counterpart of py_pick_demo.py (same model, BT-driven).
add_executable(py_pick_bt py_pick_main.cpp)
target_link_libraries(py_pick_bt PRIVATE BT::behaviortree_cpp coord2b)
target_include_directories(py_pick_bt PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${coord2b_INCLUDE_DIRS})
target_compile_features(py_pick_bt PRIVATE cxx_std_17)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/py_pick.xml
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/py_pick.xml
        ${CMAKE_CURRENT_BINARY_DIR}/py_pick.xml
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/py_pick.xml)
add_custom_target(py_pick_xml DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/py_pick.xml)
add_dependencies(py_pick_bt py_pick_xml)
