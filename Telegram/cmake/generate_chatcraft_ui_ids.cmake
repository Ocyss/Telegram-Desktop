if (CHATCRAFT_ENABLED)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    file(GLOB_RECURSE chatcraft_ui_sources CONFIGURE_DEPENDS
        "${src_loc}/settings/*.cpp"
    )
    list(APPEND chatcraft_ui_sources "${src_loc}/window/window_main_menu.cpp")
    set(chatcraft_ui_generator "${CMAKE_CURRENT_SOURCE_DIR}/build/chatcraft/generate-ui-ids.py")
    set(chatcraft_ui_output "${CMAKE_CURRENT_BINARY_DIR}/gen/chatcraft_ui_ids.inc")
    set(chatcraft_ui_manifest "${CMAKE_CURRENT_BINARY_DIR}/gen/chatcraft_ui_sources.txt")
    file(GENERATE OUTPUT "${chatcraft_ui_manifest}" CONTENT "${chatcraft_ui_sources}\n")
    set(chatcraft_ui_stamp "${CMAKE_CURRENT_BINARY_DIR}/gen/chatcraft_ui_ids.timestamp")
    add_custom_command(
        OUTPUT "${chatcraft_ui_stamp}"
        BYPRODUCTS "${chatcraft_ui_output}"
        COMMAND "${Python3_EXECUTABLE}" "${chatcraft_ui_generator}"
            --source "${src_loc}" --output "${chatcraft_ui_output}"
        COMMAND "${CMAKE_COMMAND}" -E touch "${chatcraft_ui_stamp}"
        DEPENDS "${chatcraft_ui_generator}" "${chatcraft_ui_manifest}" ${chatcraft_ui_sources}
        COMMENT "Generating Chatcraft UI IDs"
        VERBATIM
    )
    add_custom_target(chatcraft_ui_ids DEPENDS "${chatcraft_ui_stamp}")
    add_dependencies(Telegram chatcraft_ui_ids)
    target_sources(Telegram PRIVATE "${chatcraft_ui_output}")
    target_include_directories(Telegram PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/gen")
endif()
