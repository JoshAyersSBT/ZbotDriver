#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"

#define VL0_DEFAULT_ADDR (0x29)
#define VL0_SYSRANGE_START (0x00)
#define VL0_SYSTEM_SEQUENCE_CONFIG (0x01)
#define VL0_SYSTEM_INTERMEASUREMENT_PERIOD (0x04)
#define VL0_SYSTEM_INTERRUPT_CONFIG_GPIO (0x0a)
#define VL0_SYSTEM_INTERRUPT_CLEAR (0x0b)
#define VL0_RESULT_INTERRUPT_STATUS (0x13)
#define VL0_RESULT_RANGE_STATUS (0x14)
#define VL0_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT (0x44)
#define VL0_MSRC_CONFIG_CONTROL (0x60)
#define VL0_GPIO_HV_MUX_ACTIVE_HIGH (0x84)
#define VL0_I2C_SLAVE_DEVICE_ADDRESS (0x8a)
#define VL0_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV (0x89)
#define VL0_IDENTIFICATION_MODEL_ID (0xc0)
#define VL0_IDENTIFICATION_REVISION_ID (0xc2)
#define VL0_OSC_CALIBRATE_VAL (0xf8)
#define VL0_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD (0x4e)
#define VL0_DYNAMIC_SPAD_REF_EN_START_OFFSET (0x4f)
#define VL0_GLOBAL_CONFIG_REF_EN_START_SELECT (0xb6)

typedef struct _zbot_vl53l0x_obj_t {
    mp_obj_base_t base;
    mp_obj_t i2c;
    uint8_t address;
    int io_timeout;
    bool did_timeout;
    uint8_t stop_variable;
    int measurement_timing_budget_us;
    bool initialized;
} zbot_vl53l0x_obj_t;

STATIC void vl0_write_reg(zbot_vl53l0x_obj_t *self, uint8_t reg, uint8_t value) {
    uint8_t data[1] = { value };
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_bytes(data, 1);
    mp_call_method_n_kw(3, 0, dest);
}

STATIC uint8_t vl0_read_reg(zbot_vl53l0x_obj_t *self, uint8_t reg) {
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_readfrom_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_int(1);
    mp_obj_t raw = mp_call_method_n_kw(3, 0, dest);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    return ((const uint8_t *)bufinfo.buf)[0];
}

STATIC void vl0_write_reg16(zbot_vl53l0x_obj_t *self, uint8_t reg, uint16_t value) {
    uint8_t data[2] = { (uint8_t)(value >> 8), (uint8_t)value };
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_bytes(data, 2);
    mp_call_method_n_kw(3, 0, dest);
}

STATIC uint16_t vl0_read_reg16(zbot_vl53l0x_obj_t *self, uint8_t reg) {
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_readfrom_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_int(2);
    mp_obj_t raw = mp_call_method_n_kw(3, 0, dest);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(raw, &bufinfo, MP_BUFFER_READ);
    const uint8_t *data = (const uint8_t *)bufinfo.buf;
    return (uint16_t)((data[0] << 8) | data[1]);
}

STATIC void vl0_write_reg32(zbot_vl53l0x_obj_t *self, uint8_t reg, uint32_t value) {
    uint8_t data[4] = {
        (uint8_t)(value >> 24),
        (uint8_t)(value >> 16),
        (uint8_t)(value >> 8),
        (uint8_t)value,
    };
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_writeto_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_bytes(data, 4);
    mp_call_method_n_kw(3, 0, dest);
}

STATIC mp_obj_t vl0_read_multi_obj(zbot_vl53l0x_obj_t *self, uint8_t reg, size_t len) {
    mp_obj_t dest[5];
    mp_load_method(self->i2c, MP_QSTR_readfrom_mem, dest);
    dest[2] = mp_obj_new_int(self->address);
    dest[3] = mp_obj_new_int(reg);
    dest[4] = mp_obj_new_int(len);
    return mp_call_method_n_kw(3, 0, dest);
}

STATIC bool vl0_address_present(zbot_vl53l0x_obj_t *self) {
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

STATIC mp_obj_t zbot_vl53l0x_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    enum {
        ARG_i2c,
        ARG_address,
        ARG_io_timeout,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_i2c, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_address, MP_ARG_INT, {.u_int = VL0_DEFAULT_ADDR} },
        { MP_QSTR_io_timeout, MP_ARG_INT, {.u_int = 500} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    zbot_vl53l0x_obj_t *self = m_new_obj(zbot_vl53l0x_obj_t);
    self->base.type = type;
    self->i2c = args[ARG_i2c].u_obj;
    self->address = args[ARG_address].u_int & 0x7f;
    self->io_timeout = args[ARG_io_timeout].u_int;
    self->did_timeout = false;
    self->stop_variable = 0;
    self->measurement_timing_budget_us = 0;
    self->initialized = false;
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t zbot_vl53l0x_init(size_t n_args, const mp_obj_t *args) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    bool io_2v8 = n_args < 2 || mp_obj_is_true(args[1]);

    if (!vl0_address_present(self)) {
        mp_raise_msg_varg(&mp_type_OSError, MP_ERROR_TEXT("VL53L0X not found at 0x%02x"), self->address);
    }

    (void)vl0_read_reg(self, VL0_IDENTIFICATION_MODEL_ID);
    if (io_2v8) {
        vl0_write_reg(self, VL0_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV, vl0_read_reg(self, VL0_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV) | 0x01);
    }

    vl0_write_reg(self, 0x88, 0x00);
    vl0_write_reg(self, 0x80, 0x01);
    vl0_write_reg(self, 0xff, 0x01);
    vl0_write_reg(self, 0x00, 0x00);
    self->stop_variable = vl0_read_reg(self, 0x91);
    vl0_write_reg(self, 0x00, 0x01);
    vl0_write_reg(self, 0xff, 0x00);
    vl0_write_reg(self, 0x80, 0x00);
    vl0_write_reg(self, VL0_MSRC_CONFIG_CONTROL, vl0_read_reg(self, VL0_MSRC_CONFIG_CONTROL) | 0x12);
    vl0_write_reg16(self, VL0_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT, (uint16_t)(0.25f * (1 << 7)));
    vl0_write_reg(self, VL0_SYSTEM_SEQUENCE_CONFIG, 0xff);
    vl0_write_reg(self, 0xff, 0x01);
    vl0_write_reg(self, VL0_DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00);
    vl0_write_reg(self, VL0_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2c);
    vl0_write_reg(self, 0xff, 0x00);
    vl0_write_reg(self, VL0_GLOBAL_CONFIG_REF_EN_START_SELECT, 0xb4);
    vl0_write_reg(self, VL0_SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04);
    vl0_write_reg(self, VL0_GPIO_HV_MUX_ACTIVE_HIGH, vl0_read_reg(self, VL0_GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10);
    vl0_write_reg(self, VL0_SYSTEM_INTERRUPT_CLEAR, 0x01);
    vl0_write_reg(self, VL0_SYSTEM_SEQUENCE_CONFIG, 0xe8);

    self->measurement_timing_budget_us = 33000;
    self->initialized = true;
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_vl53l0x_init_obj, 1, 2, zbot_vl53l0x_init);

STATIC mp_obj_t zbot_vl53l0x_start_continuous(size_t n_args, const mp_obj_t *args) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    int period_ms = n_args > 1 ? mp_obj_get_int(args[1]) : 0;
    if (!self->initialized) {
        mp_obj_t init_args[1] = { args[0] };
        zbot_vl53l0x_init(1, init_args);
    }

    vl0_write_reg(self, 0x80, 0x01);
    vl0_write_reg(self, 0xff, 0x01);
    vl0_write_reg(self, 0x00, 0x00);
    vl0_write_reg(self, 0x91, self->stop_variable);
    vl0_write_reg(self, 0x00, 0x01);
    vl0_write_reg(self, 0xff, 0x00);
    vl0_write_reg(self, 0x80, 0x00);

    if (period_ms != 0) {
        uint16_t osc = vl0_read_reg16(self, VL0_OSC_CALIBRATE_VAL);
        uint32_t period = period_ms;
        if (osc != 0) {
            period *= osc;
        }
        vl0_write_reg32(self, VL0_SYSTEM_INTERMEASUREMENT_PERIOD, period);
        vl0_write_reg(self, VL0_SYSRANGE_START, 0x04);
    } else {
        vl0_write_reg(self, VL0_SYSRANGE_START, 0x02);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(zbot_vl53l0x_start_continuous_obj, 1, 2, zbot_vl53l0x_start_continuous);

STATIC mp_obj_t zbot_vl53l0x_stop_continuous(mp_obj_t self_in) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    vl0_write_reg(self, VL0_SYSRANGE_START, 0x01);
    vl0_write_reg(self, 0xff, 0x01);
    vl0_write_reg(self, 0x00, 0x00);
    vl0_write_reg(self, 0x91, 0x00);
    vl0_write_reg(self, 0x00, 0x01);
    vl0_write_reg(self, 0xff, 0x00);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l0x_stop_continuous_obj, zbot_vl53l0x_stop_continuous);

STATIC mp_obj_t zbot_vl53l0x_read_range_continuous_mm(mp_obj_t self_in) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->did_timeout = false;
    mp_uint_t start = mp_hal_ticks_ms();
    while ((vl0_read_reg(self, VL0_RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
        if (self->io_timeout > 0 && mp_hal_ticks_ms() - start > (mp_uint_t)self->io_timeout) {
            self->did_timeout = true;
            mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("VL53L0X timeout"));
        }
        mp_hal_delay_ms(5);
    }
    uint16_t mm = vl0_read_reg16(self, VL0_RESULT_RANGE_STATUS + 10);
    vl0_write_reg(self, VL0_SYSTEM_INTERRUPT_CLEAR, 0x01);
    return mp_obj_new_int(mm);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l0x_read_range_continuous_mm_obj, zbot_vl53l0x_read_range_continuous_mm);

STATIC mp_obj_t zbot_vl53l0x_read_range_single_mm(mp_obj_t self_in) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized) {
        mp_obj_t init_args[1] = { self_in };
        zbot_vl53l0x_init(1, init_args);
    }
    vl0_write_reg(self, 0x80, 0x01);
    vl0_write_reg(self, 0xff, 0x01);
    vl0_write_reg(self, 0x00, 0x00);
    vl0_write_reg(self, 0x91, self->stop_variable);
    vl0_write_reg(self, 0x00, 0x01);
    vl0_write_reg(self, 0xff, 0x00);
    vl0_write_reg(self, 0x80, 0x00);
    vl0_write_reg(self, VL0_SYSRANGE_START, 0x01);

    self->did_timeout = false;
    mp_uint_t start = mp_hal_ticks_ms();
    while ((vl0_read_reg(self, VL0_SYSRANGE_START) & 0x01) != 0) {
        if (self->io_timeout > 0 && mp_hal_ticks_ms() - start > (mp_uint_t)self->io_timeout) {
            self->did_timeout = true;
            mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("VL53L0X timeout starting single shot"));
        }
        mp_hal_delay_ms(5);
    }
    return zbot_vl53l0x_read_range_continuous_mm(self_in);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l0x_read_range_single_mm_obj, zbot_vl53l0x_read_range_single_mm);

STATIC mp_obj_t zbot_vl53l0x_read_debug(mp_obj_t self_in) {
    zbot_vl53l0x_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t dict = mp_obj_new_dict(3);
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_distance), mp_obj_new_int(vl0_read_reg16(self, VL0_RESULT_RANGE_STATUS + 10)));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_irq), mp_obj_new_int(vl0_read_reg(self, VL0_RESULT_INTERRUPT_STATUS)));
    mp_obj_dict_store(dict, MP_OBJ_NEW_QSTR(MP_QSTR_raw), vl0_read_multi_obj(self, VL0_RESULT_RANGE_STATUS, 16));
    return dict;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(zbot_vl53l0x_read_debug_obj, zbot_vl53l0x_read_debug);

STATIC const mp_rom_map_elem_t zbot_vl53l0x_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&zbot_vl53l0x_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_start_continuous), MP_ROM_PTR(&zbot_vl53l0x_start_continuous_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop_continuous), MP_ROM_PTR(&zbot_vl53l0x_stop_continuous_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_range_continuous_mm), MP_ROM_PTR(&zbot_vl53l0x_read_range_continuous_mm_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_range_single_mm), MP_ROM_PTR(&zbot_vl53l0x_read_range_single_mm_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&zbot_vl53l0x_read_range_continuous_mm_obj) },
    { MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&zbot_vl53l0x_read_range_continuous_mm_obj) },
    { MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&zbot_vl53l0x_start_continuous_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&zbot_vl53l0x_stop_continuous_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_debug), MP_ROM_PTR(&zbot_vl53l0x_read_debug_obj) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_vl53l0x_locals_dict, zbot_vl53l0x_locals_dict_table);

STATIC const mp_obj_type_t zbot_vl53l0x_type = {
    { &mp_type_type },
    .name = MP_QSTR_VL53L0X,
    .make_new = zbot_vl53l0x_make_new,
    .locals_dict = (mp_obj_dict_t *)&zbot_vl53l0x_locals_dict,
};

STATIC const mp_rom_map_elem_t zbot_vl53l0x_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_zbot_vl53l0x) },
    { MP_ROM_QSTR(MP_QSTR_VL53L0X), MP_ROM_PTR(&zbot_vl53l0x_type) },
};
STATIC MP_DEFINE_CONST_DICT(zbot_vl53l0x_module_globals, zbot_vl53l0x_module_globals_table);

const mp_obj_module_t zbot_vl53l0x_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&zbot_vl53l0x_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_zbot_vl53l0x, zbot_vl53l0x_module);
