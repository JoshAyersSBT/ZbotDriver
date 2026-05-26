#include "py/runtime.h"
#include "py/obj.h"

typedef struct _zbot_tca9548a_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    uint8_t addr;
    int current;
} zbot_tca9548a_obj_t;

STATIC mp_obj_t zbot_tca9548a_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_i2c,
        ARG_addr,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_i2c, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_addr, MP_ARG_INT, {.u_int = 0x70} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_tca9548a_obj_t *self = m_new_obj(zbot_tca9548a_obj_t);
    self->base.type = type;
    self->i2c = args[ARG_i2c].u_obj;
    self->addr = args[ARG_addr].u_int & 0x7f;
    self->current = -1;
    return MP_OBJ_FROM_PTR(self);
}

STATIC void zbot_tca9548a_write(zbot_tca9548a_obj_t *self, uint8_t value) {
    uint8_t data[1] = { value };
    mp_obj_t data_obj = mp_obj_new_bytes(data, 1);
    mp_obj_t dest[4];
    mp_load_method(self->i2c, MP_QSTR_writeto, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = data_obj;
    mp_call_method_n_kw(2, 0, dest);
}

STATIC mp_obj_t zbot_tca9548a_select(mp_obj_t self_in, mp_obj_t channel_in) {
    zbot_tca9548a_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int channel = mp_obj_get_int(channel_in);
    if (channel < 0 || channel > 7) {
        mp_raise_ValueError(MP_ERROR_TEXT("TCA9548A channel must be 0..7"));
    }

    zbot_tca9548a_write(self, 1 << channel);
    self->current = channel;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(zbot_tca9548a_select_obj, zbot_tca9548a_select);

STATIC mp_obj_t zbot_tca9548a_disable_all(mp_obj_t self_in) {
    zbot_tca9548a_obj_t *self = MP_OBJ_TO_PTR(self_in);
    zbot_tca9548a_write(self, 0);
    self->current = -1;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_tca9548a_disable_all_obj, zbot_tca9548a_disable_all);

STATIC mp_obj_t zbot_tca9548a_current(mp_obj_t self_in) {
    zbot_tca9548a_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->current < 0) {
        return mp_const_none;
    }
    return mp_obj_new_int(self->current);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_tca9548a_current_obj, zbot_tca9548a_current);

STATIC const mp_rom_map_elem_t zbot_tca9548a_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_select), MP_ROM_PTR(&zbot_tca9548a_select_obj) },
    { MP_ROM_QSTR(MP_QSTR_disable_all), MP_ROM_PTR(&zbot_tca9548a_disable_all_obj) },
    { MP_ROM_QSTR(MP_QSTR_current_channel), MP_ROM_PTR(&zbot_tca9548a_current_obj) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_tca9548a_locals_dict, zbot_tca9548a_locals_dict_table);

STATIC const mp_obj_type_t zbot_tca9548a_type = {
    { &mp_type_type },
    .name = MP_QSTR_TCA9548A,
    .make_new = zbot_tca9548a_make_new,
    .locals_dict = (mp_obj_dict_t *)&zbot_tca9548a_locals_dict,
};

STATIC const mp_rom_map_elem_t zbot_tca9548a_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_tca9548a) },
    { MP_ROM_QSTR(MP_QSTR_TCA9548A), MP_ROM_PTR(&zbot_tca9548a_type) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_tca9548a_module_globals, zbot_tca9548a_module_globals_table);

const mp_obj_module_t zbot_tca9548a_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_tca9548a_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_tca9548a, zbot_tca9548a_module);
