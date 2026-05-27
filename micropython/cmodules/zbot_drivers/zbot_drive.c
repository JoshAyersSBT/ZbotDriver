#include "py/runtime.h"
#include "py/obj.h"

static int zbot_drive_clamp_int(int value, int lo, int hi) {
    if (value < lo) {
        return lo;
    }
    if (value > hi) {
        return hi;
    }
    return value;
}

static mp_obj_t zbot_drive_mix(mp_obj_t throttle_in, mp_obj_t steering_in) {
    int throttle = zbot_drive_clamp_int(mp_obj_get_int(throttle_in), -100, 100);
    int steering = zbot_drive_clamp_int(mp_obj_get_int(steering_in), -100, 100);
    int left = zbot_drive_clamp_int(throttle + steering, -100, 100);
    int right = zbot_drive_clamp_int(throttle - steering, -100, 100);

    mp_obj_t items[2] = {
        mp_obj_new_int(left),
        mp_obj_new_int(right),
    };
    return mp_obj_new_tuple(2, items);
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_drive_mix_obj, zbot_drive_mix);

static mp_obj_t zbot_drive_duty(mp_obj_t command_in, mp_obj_t max_duty_in) {
    int command = zbot_drive_clamp_int(mp_obj_get_int(command_in), -100, 100);
    int max_duty = zbot_drive_clamp_int(mp_obj_get_int(max_duty_in), 0, 65535);
    int mag = command < 0 ? -command : command;
    return mp_obj_new_int((mag * max_duty) / 100);
}
static MP_DEFINE_CONST_FUN_OBJ_2(zbot_drive_duty_obj, zbot_drive_duty);

static mp_obj_t zbot_drive_clamp(mp_obj_t value_in) {
    return mp_obj_new_int(zbot_drive_clamp_int(mp_obj_get_int(value_in), -100, 100));
}
static MP_DEFINE_CONST_FUN_OBJ_1(zbot_drive_clamp_obj, zbot_drive_clamp);

static const mp_rom_map_elem_t zbot_drive_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_drive) },
    { MP_ROM_QSTR(MP_QSTR_mix), MP_ROM_PTR(&zbot_drive_mix_obj) },
    { MP_ROM_QSTR(MP_QSTR_duty), MP_ROM_PTR(&zbot_drive_duty_obj) },
    { MP_ROM_QSTR(MP_QSTR_clamp), MP_ROM_PTR(&zbot_drive_clamp_obj) },
};
static MP_DEFINE_CONST_DICT(zbot_drive_module_globals, zbot_drive_module_globals_table);

const mp_obj_module_t zbot_drive_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_drive_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_drive, zbot_drive_module);
