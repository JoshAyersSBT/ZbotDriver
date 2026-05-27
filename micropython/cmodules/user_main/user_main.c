#include "py/runtime.h"
#include "py/obj.h"
#include <string.h>
#include <stdio.h>

static bool user_main_call0(mp_obj_t zbot, qstr method, mp_obj_t *result) {
    if (zbot == mp_const_none) {
        return false;
    }

    mp_obj_t dest[2];
    mp_load_method_maybe(zbot, method, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return false;
    }

    mp_obj_t value = mp_call_method_n_kw(0, 0, dest);
    if (result != NULL) {
        *result = value;
    }
    return true;
}

static bool user_main_call1(mp_obj_t zbot, qstr method, mp_obj_t arg, mp_obj_t *result) {
    if (zbot == mp_const_none) {
        return false;
    }

    mp_obj_t dest[3];
    mp_load_method_maybe(zbot, method, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return false;
    }

    dest[2] = arg;
    mp_obj_t value = mp_call_method_n_kw(1, 0, dest);
    if (result != NULL) {
        *result = value;
    }
    return true;
}

static void user_main_notify(mp_obj_t zbot, const char *message) {
    user_main_call1(zbot, MP_QSTR_notify, mp_obj_new_str(message, strlen(message)), NULL);
}

static void user_main_display(mp_obj_t zbot, const char *line1, const char *line2, const char *line3, const char *line4) {
    if (zbot == mp_const_none) {
        return;
    }

    mp_obj_t dest[6];
    mp_load_method_maybe(zbot, MP_QSTR_display, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return;
    }

    dest[2] = mp_obj_new_str(line1, strlen(line1));
    dest[3] = mp_obj_new_str(line2, strlen(line2));
    dest[4] = mp_obj_new_str(line3, strlen(line3));
    dest[5] = mp_obj_new_str(line4, strlen(line4));
    mp_call_method_n_kw(4, 0, dest);
}

static void user_main_report_result(mp_obj_t zbot, const char *name, bool ok) {
    char line[64];
    snprintf(line, sizeof(line), "NATIVE_TEST %s %s", name, ok ? "OK" : "MISS");
    user_main_notify(zbot, line);
}

static mp_obj_t user_main_main(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;

    user_main_notify(zbot, "NATIVE_TEST start user_main.c");
    user_main_display(zbot, "Native C Test", "Color P1", "ToF P2", "No motors");

    mp_obj_t value = mp_const_none;

    bool status_ok = user_main_call0(zbot, MP_QSTR_status, &value) && mp_obj_is_type(value, &mp_type_dict);
    user_main_report_result(zbot, "status", status_ok);

    bool sensors_ok = user_main_call0(zbot, MP_QSTR_sensors, &value) && mp_obj_is_type(value, &mp_type_dict);
    user_main_report_result(zbot, "sensors", sensors_ok);

    bool imu_ok = user_main_call0(zbot, MP_QSTR_imu, &value) && mp_obj_is_type(value, &mp_type_dict);
    user_main_report_result(zbot, "imu", imu_ok);

    bool rgb_ok = user_main_call1(zbot, MP_QSTR_rgb, mp_obj_new_int(1), &value) && value != mp_const_none;
    user_main_report_result(zbot, "rgb_port_1", rgb_ok);

    bool color_ok = user_main_call1(zbot, MP_QSTR_color, mp_obj_new_int(1), &value) && value != mp_const_none;
    user_main_report_result(zbot, "color_port_1", color_ok);

    bool tof_ok = user_main_call1(zbot, MP_QSTR_tof, mp_obj_new_int(2), &value) && value != mp_const_none;
    user_main_report_result(zbot, "tof_port_2", tof_ok);

    bool button_ok = user_main_call1(zbot, MP_QSTR_button, mp_obj_new_int(1), &value) && value != mp_const_none;
    user_main_report_result(zbot, "button_api", button_ok);

    user_main_display(
        zbot,
        "Native C Test",
        color_ok ? "Color P1 OK" : "Color P1 wait",
        tof_ok ? "ToF P2 OK" : "ToF P2 wait",
        imu_ok ? "IMU OK" : "IMU wait"
    );

    user_main_notify(zbot, "NATIVE_TEST complete");
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_main_obj, 0, 1, user_main_main);

static const mp_rom_map_elem_t user_main_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_user_main) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_KIND), MP_ROM_QSTR(MP_QSTR_c) },
    { MP_ROM_QSTR(MP_QSTR_main), MP_ROM_PTR(&user_main_main_obj) },
};
static MP_DEFINE_CONST_DICT(user_main_module_globals, user_main_module_globals_table);

const mp_obj_module_t user_main_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&user_main_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_user_main, user_main_module);
