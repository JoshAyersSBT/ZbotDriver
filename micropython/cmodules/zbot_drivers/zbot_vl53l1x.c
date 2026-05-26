#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"

#define VL1_DEFAULT_ADDR (0x29)
#define VL1_REG_SOFT_RESET (0x0000)
#define VL1_REG_IDENTIFICATION__MODEL_ID (0x010f)
#define VL1_REG_GPIO__TIO_HV_STATUS (0x0031)
#define VL1_REG_SYSTEM__INTERRUPT_CLEAR (0x0086)
#define VL1_REG_SYSTEM__MODE_START (0x0087)
#define VL1_REG_VHV_CONFIG__TIMEOUT_MACROP_LOOP_BOUND (0x0008)
#define VL1_REG_PHASECAL_CONFIG__OVERRIDE (0x000b)

typedef struct _zbot_vl53l1x_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    uint8_t address;
    uint16_t model_id;
} zbot_vl53l1x_obj_t;

STATIC void vl1_write_reg(zbot_vl53l1x_obj_t *self, uint16_t reg, const uint8_t *data, size_t len) {
    if (len > 8) {
        mp_raise_ValueError(MP_ERROR_TEXT("VL53L1X write too large"));
    }
    uint8_t buf[10];
    buf[0] = reg >> 8;
    buf[1] = reg & 0xff;
    for (size_t i = 0; i < len; i++) {
        buf[i + 2] = data[i];
    }
    mp_obj_t dest[4];
    mp_load_method(self->i2c, MP_QSTR_writeto, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_bytes(buf, len + 2);
    mp_call_method_n_kw(2, 0, dest);
}

STATIC mp_obj_t vl1_read_reg_obj(zbot_vl53l1x_obj_t *self, uint16_t reg, size_t len) {
    uint8_t reg_bytes[2] = { (uint8_t)(reg >> 8), (uint8_t)reg };
    mp_obj_t write_dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto, write_dest);
    write_dest[2] = mp_obj_new_int(self->address);
    write_dest[3] = mp_obj_new_bytes(reg_bytes, 2);
    write_dest[4] = mp_const_false;
    mp_call_method_n_kw(3, 0, write_dest);

    mp_obj_t read_dest[4];
    mp_load_method(self->i2c, MP_QSTR_readfrom, read_dest);
    read_dest[2] = mp_obj_new_int(self->address);
    read_dest[3] = mp_obj_new_int(len);
    return mp_call_method_n_kw(2, 0, read_dest);
}

STATIC uint8_t vl1_read_u8(zbot_vl53l1x_obj_t *self, uint16_t reg) {
    mp_obj_t raw = vl1_read_reg_obj(self, reg, 1);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    return ((const uint8_t *)bufinfo.buf)[0];
}

STATIC uint16_t vl1_read_u16(zbot_vl53l1x_obj_t *self, uint16_t reg) {
    mp_obj_t raw = vl1_read_reg_obj(self, reg, 2);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    const uint8_t *data = (const uint8_t *)bufinfo.buf;
    return (uint16_t)((data[0] << 8) | data[1]);
}

STATIC void vl1_write_u8(zbot_vl53l1x_obj_t *self, uint16_t reg, uint8_t value) {
    vl1_write_reg(self, reg, &value, 1);
}

STATIC bool vl1_address_present(zbot_vl53l1x_obj_t *self) {
    mp_obj_t dest[2];
    mp_load_method(self->i2c, MP_QSTR_scan, dest);
    mp_obj_t scan = mp_call_method_n_kw(0, 0, dest);
    size_t len;
    mp_obj_t *items;
    mp_obj_get_array(scan, &len, &items);
    for (size_t i = 0; i < len; i++) {
        if (mp_obj_get_int(items[i]) == self->address) {
            return true;
        }
    }
    return false;
}

STATIC mp_obj_t zbot_vl53l1x_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_i2c,
        ARG_address,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_i2c, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_address, MP_ARG_INT, {.u_int = VL1_DEFAULT_ADDR} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_vl53l1x_obj_t *self = m_new_obj(zbot_vl53l1x_obj_t);
    self->base.type = type;
    self->i2c = args[ARG_i2c].u_obj;
    self->address = args[ARG_address].u_int & 0x7f;

    if (!vl1_address_present(self)) {
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("VL53L1X not found"));
    }

    mp_hal_delay_ms(100);
    self->model_id = vl1_read_u16(self, VL1_REG_IDENTIFICATION__MODEL_ID);
    vl1_write_u8(self, VL1_REG_SOFT_RESET, 0x00);
    mp_hal_delay_ms(5);
    vl1_write_u8(self, VL1_REG_SOFT_RESET, 0x01);
    mp_hal_delay_ms(50);
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t zbot_vl53l1x_start(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    vl1_write_u8(self, VL1_REG_VHV_CONFIG__TIMEOUT_MACROP_LOOP_BOUND, 0x09);
    vl1_write_u8(self, VL1_REG_PHASECAL_CONFIG__OVERRIDE, 0x00);
    vl1_write_u8(self, VL1_REG_SYSTEM__MODE_START, 0x40);
    mp_hal_delay_ms(100);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_start_obj, zbot_vl53l1x_start);

STATIC mp_obj_t zbot_vl53l1x_stop(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    vl1_write_u8(self, VL1_REG_SYSTEM__MODE_START, 0x00);
    mp_hal_delay_ms(5);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_stop_obj, zbot_vl53l1x_stop);

STATIC mp_obj_t zbot_vl53l1x_clear_interrupt(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    vl1_write_u8(self, VL1_REG_SYSTEM__INTERRUPT_CLEAR, 0x01);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_clear_interrupt_obj, zbot_vl53l1x_clear_interrupt);

STATIC mp_obj_t zbot_vl53l1x_data_ready(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    uint8_t a = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
    mp_hal_delay_ms(2);
    uint8_t b = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
    return mp_obj_new_bool(((a & 0x01) == 0) && (a == b));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_data_ready_obj, zbot_vl53l1x_data_ready);

STATIC mp_obj_t zbot_vl53l1x_read_raw_block(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return vl1_read_reg_obj(self, 0x0089, 17);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_read_raw_block_obj, zbot_vl53l1x_read_raw_block);

STATIC mp_obj_t zbot_vl53l1x_read_debug(size_t n_args, const mp_obj_t *args) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    int timeout_ms = n_args > 1 ? mp_obj_get_int(args[1]) : 200;
    mp_uint_t start = mp_hal_ticks_ms();
    while (true) {
        uint8_t a = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
        mp_hal_delay_ms(2);
        uint8_t b = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
        if (((a & 0x01) == 0) && (a == b)) {
            break;
        }
        if (mp_hal_ticks_ms() - start > (mp_uint_t)timeout_ms) {
            mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("VL53L1X timeout waiting for data"));
        }
        mp_hal_delay_ms(5);
    }

    mp_obj_t raw = vl1_read_reg_obj(self, 0x0089, 24);
    uint16_t cand_96 = vl1_read_u16(self, 0x0096);
    uint16_t cand_9c = vl1_read_u16(self, 0x009c);
    uint16_t cand_a0 = vl1_read_u16(self, 0x00a0);
    uint8_t gpio_status = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
    vl1_write_u8(self, VL1_REG_SYSTEM__INTERRUPT_CLEAR, 0x01);

    mp_obj_t dict = mp_obj_new_dict(5);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_gpio_status), mp_obj_new_int(gpio_status));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_cand_96), mp_obj_new_int(cand_96));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_cand_9C), mp_obj_new_int(cand_9c));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_cand_A0), mp_obj_new_int(cand_a0));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_raw), raw);
    return dict;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_vl53l1x_read_debug_obj, 1, 2, zbot_vl53l1x_read_debug);

STATIC mp_obj_t zbot_vl53l1x_read(size_t n_args, const mp_obj_t *args) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    int timeout_ms = n_args > 1 ? mp_obj_get_int(args[1]) : 200;
    mp_uint_t start = mp_hal_ticks_ms();
    while (true) {
        uint8_t a = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
        mp_hal_delay_ms(2);
        uint8_t b = vl1_read_u8(self, VL1_REG_GPIO__TIO_HV_STATUS);
        if (((a & 0x01) == 0) && (a == b)) {
            break;
        }
        if (mp_hal_ticks_ms() - start > (mp_uint_t)timeout_ms) {
            mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("VL53L1X timeout waiting for data"));
        }
        mp_hal_delay_ms(5);
    }

    int dist = vl1_read_u16(self, 0x0096);
    vl1_write_u8(self, VL1_REG_SYSTEM__INTERRUPT_CLEAR, 0x01);
    if (dist <= 0 || dist >= 4000 || dist == 5633 || dist == 65535) {
        mp_raise_msg_varg(&mp_type_OSError, MP_ERROR_TEXT("VL53L1X invalid range %d"), dist);
    }
    return mp_obj_new_int(dist);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_vl53l1x_read_obj, 1, 2, zbot_vl53l1x_read);

STATIC mp_obj_t zbot_vl53l1x_info(mp_obj_t self_in) {
    zbot_vl53l1x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t dict = mp_obj_new_dict(2);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_address), mp_obj_new_int(self->address));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_model_id), mp_obj_new_int(self->model_id));
    return dict;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l1x_info_obj, zbot_vl53l1x_info);

STATIC const mp_rom_map_elem_t zbot_vl53l1x_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&zbot_vl53l1x_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&zbot_vl53l1x_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear_interrupt), MP_ROM_PTR(&zbot_vl53l1x_clear_interrupt_obj) },
    { MP_ROM_QSTR(MP_QSTR_data_ready), MP_ROM_PTR(&zbot_vl53l1x_data_ready_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_raw_block), MP_ROM_PTR(&zbot_vl53l1x_read_raw_block_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_debug), MP_ROM_PTR(&zbot_vl53l1x_read_debug_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&zbot_vl53l1x_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&zbot_vl53l1x_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_info), MP_ROM_PTR(&zbot_vl53l1x_info_obj) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_vl53l1x_locals_dict, zbot_vl53l1x_locals_dict_table);

STATIC const mp_obj_type_t zbot_vl53l1x_type = {
    { &mp_type_type },
    .name = MP_QSTR_VL53L1X,
    .make_new = zbot_vl53l1x_make_new,
    .locals_dict = (mp_obj_dict_t *)&zbot_vl53l1x_locals_dict,
};

STATIC const mp_rom_map_elem_t zbot_vl53l1x_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_vl53l1x) },
    { MP_ROM_QSTR(MP_QSTR_VL53L1X), MP_ROM_PTR(&zbot_vl53l1x_type) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_vl53l1x_module_globals, zbot_vl53l1x_module_globals_table);

const mp_obj_module_t zbot_vl53l1x_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_vl53l1x_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_vl53l1x, zbot_vl53l1x_module);
