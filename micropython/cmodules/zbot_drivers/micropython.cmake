add_library(usermod_zbot_drivers INTERFACE)

target_sources(usermod_zbot_drivers INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/zbot_motor.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_servo.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_button.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_tca9548a.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_mpu6050.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_tcs3472.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_vl53l0x.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_vl53l1x.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_oled.c
    ${CMAKE_CURRENT_LIST_DIR}/zbot_drive.c
)

target_include_directories(usermod_zbot_drivers INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_zbot_drivers)
