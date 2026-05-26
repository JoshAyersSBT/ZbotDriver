add_library(usermod_user_main INTERFACE)

target_sources(usermod_user_main INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/user_main.c
)

target_include_directories(usermod_user_main INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_user_main)
