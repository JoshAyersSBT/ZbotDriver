#include "py/runtime.h"
#include "py/obj.h"

#define TCS3472_ADDR (0x29)
#define TCS3472_CMD (0x80)
#define TCS3472_ENABLE (0x00)
#define TCS3472_ATIME (0x01)
#define TCS3472_CONTROL (0x0f)
#define TCS3472_ID (0x12)
#define TCS3472_CDATA (0x14)

typedef struct _zbot_tcs3472_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    uint8_t addr;
} zbot_tcs3472_obj_t;

STATIC void zbot_tcs_write8(zbot_tcs3472_obj_t *self, uint8_t reg, uint8_t value) {
    uint8_t data[1] = { value };
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto_mem, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_int(TCS3472_CMD | reg);
    dest[4] = mp_obj_new_bytes(data, 1);
    mp_call_method_n_kw(3, 0, dest);
}

STATIC mp_obj_t zbot_tcs_read_mem(zbot_tcs3472_obj_t *self, uint8_t reg, size_t len) {
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_readfrom_mem, dest);
    dest[2] = mp_obj_new_int(self->addr);
    dest[3] = mp_obj_new_int(TCS3472_CMD | reg);
    dest[4] = mp_obj_new_int(len);
    return mp_call_method_n_kw(3, 0, dest);
}

STATIC uint16_t zbot_u16_le(const uint8_t *data) {
    return (uint16_t)(data[0] | (data[1] << 8));
}

STATIC mp_obj_t zbot_tcs3472_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_i2c,
        ARG_addr,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_i2c, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_addr, MP_ARG_INT, {.u_int = TCS3472_ADDR} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_tcs3472_obj_t *self = m_new_obj(zbot_tcs3472_obj_t);
    self->base.type = type;
    self->i2c = args[ARG_i2c].u_obj;
    self->addr = args[ARG_addr].u_int & 0x7f;

    mp_obj_t id_obj = zbot_tcs_read_mem(self, TCS3472_ID, 1);
    mp_buffer_info_t id_buf;
    mp_get_buffer_raise(id_obj, &id_buf, MP_BUFFER_READ);
    uint8_t chip_id = ((const uint8_t *)id_buf.buf)[0];
    if (chip_id != 0x44 && chip_id != 0x4d) {
        mp_raise_msg_varg(&mp_type_RuntimeError, MP_ERROR_TEXT("unexpected TCS3472 ID: 0x%02x"), chip_id);
    }

    zbot_tcs_write8(self, TCS3472_ATIME, 0xeb);
    zbot_tcs_write8(self, TCS3472_CONTROL, 0x01);
    zbot_tcs_write8(self, TCS3472_ENABLE, 0x01);
    zbot_tcs_write8(self, TCS3472_ENABLE, 0x03);
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t zbot_tcs3472_read(mp_obj_t self_in) {
    zbot_tcs3472_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t raw = zbot_tcs_read_mem(self, TCS3472_CDATA, 8);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    const uint8_t *data = (const uint8_t *)bufinfo.buf;

    mp_obj_t dict = mp_obj_new_dict(4);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_clear), mp_obj_new_int(zbot_u16_le(data + 0)));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_r), mp_obj_new_int(zbot_u16_le(data + 2)));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_g), mp_obj_new_int(zbot_u16_le(data + 4)));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_b), mp_obj_new_int(zbot_u16_le(data + 6)));
    return dict;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_tcs3472_read_obj, zbot_tcs3472_read);

STATIC const mp_rom_map_elem_t zbot_tcs3472_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&zbot_tcs3472_read_obj) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_tcs3472_locals_dict, zbot_tcs3472_locals_dict_table);

STATIC const mp_obj_type_t zbot_tcs3472_type = {
    { &mp_type_type },
    .name = MP_QSTR_TCS3472,
    .make_new = zbot_tcs3472_make_new,
    .locals_dict = (mp_obj_dict_t *)&zbot_tcs3472_locals_dict,
};

STATIC const mp_rom_map_elem_t zbot_tcs3472_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_tcs3472) },
    { MP_ROM_QSTR(MP_QSTR_TCS3472), MP_ROM_PTR(&zbot_tcs3472_type) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_tcs3472_module_globals, zbot_tcs3472_module_globals_table);

const mp_obj_module_t zbot_tcs3472_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_tcs3472_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_tcs3472, zbot_tcs3472_module);
