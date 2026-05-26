#include "py/runtime.h"
#include "py/obj.h"
#include <string.h>

STATIC void user_main_notify(mp_obj_t zbot, const char *message) {
    if (zbot == mp_const_none) {
        return;
    }

    mp_obj_t dest[3];
    mp_load_method_maybe(zbot, MP_QSTR_notify, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return;
    }

    dest[2] = mp_obj_new_str(message, strlen(message));
    mp_call_method_n_kw(1, 0, dest);
}

STATIC void user_main_stop(mp_obj_t zbot) {
    if (zbot == mp_const_none) {
        return;
    }

    mp_obj_t dest[2];
    mp_load_method_maybe(zbot, MP_QSTR_stop, dest);
    if (dest[0] != MP_OBJ_NULL) {
        mp_call_method_n_kw(0, 0, dest);
    }
}

STATIC mp_obj_t user_main_main(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;

    user_main_notify(zbot, "Hello from native user_main.c");

    // Put the user's native robot routine here. Keep it short if the runtime
    // should continue serving BLE, sensors, and display tasks.

    user_main_stop(zbot);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_main_obj, 0, 1, user_main_main);

STATIC const mp_rom_map_elem_t user_main_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_user_main) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_KIND), MP_ROM_QSTR(MP_QSTR_c) },
    { MP_ROM_QSTR(MP_QSTR_main), MP_ROM_PTR(&user_main_main_obj) },
};
STATIC MP_DEFINE_CONST_DICT(user_main_module_globals, user_main_module_globals_table);

const mp_obj_module_t user_main_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&user_main_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_user_main, user_main_module);
